"""
Lab 03: Multi-Agent Intelligence Pipeline
==========================================
3-agent pipeline: Researcher -> Analyst -> Writer
With LangGraph orchestration, Langfuse tracing, and security guardrails.
"""

import os
import re
import json
import time
from typing import TypedDict, Annotated
from datetime import datetime

import anthropic
from openai import OpenAI
from pinecone import Pinecone
from langfuse import Langfuse
from langgraph.graph import StateGraph, END

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from dotenv import load_dotenv

load_dotenv()

# --- Clients ---
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

# --- Security engines ---
pii_analyzer = AnalyzerEngine()
pii_anonymizer = AnonymizerEngine()

# --- Constants ---
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_COST_PER_QUERY = float(os.getenv("MAX_COST_PER_QUERY", "0.50"))

# Claude Sonnet pricing (per token)
COST_PER_INPUT_TOKEN = 3.0 / 1_000_000   # $3 per 1M input tokens
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000  # $15 per 1M output tokens


class PipelineState(TypedDict):
    """State passed through the entire agent pipeline."""
    question: str                    # Original user question
    sanitized_question: str          # After input guard
    research_queries: list[str]      # Multi-query variations
    research_results: list[dict]     # Raw Pinecone results
    insights: list[dict]            # Structured analyst output
    brief: str                      # Final executive brief
    metadata: dict                  # Cost, latency, token tracking
    errors: list[str]               # Error accumulator
    trace_id: str                   # Langfuse trace ID


def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def search_pinecone(query: str, top_k: int = 5) -> list[dict]:
    """Search Pinecone index and return results with metadata."""
    query_embedding = embed_text(query)
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )
    return [
        {
            "id": match["id"],
            "score": match["score"],
            "text": match["metadata"].get("text", ""),
            "source": match["metadata"].get("source", "unknown"),
            "chunk_index": match["metadata"].get("chunk_index", -1),
        }
        for match in results["matches"]
    ]


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> dict:
    """Call Claude and return response with usage metadata."""
    start = time.time()
    response = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = time.time() - start

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)

    return {
        "content": response.content[0].text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
        "latency": elapsed,
    }


def calculate_total_cost(metadata: dict) -> float:
    """Sum all costs recorded in metadata."""
    total = 0.0
    for key, value in metadata.items():
        if isinstance(value, dict) and "cost" in value:
            total += value["cost"]
    return total


def input_guard(state: PipelineState) -> dict:
    """
    Security: Sanitize input before processing.
    - Strip potential prompt injection patterns
    - Enforce length limits
    - Log sanitization actions
    """
    trace = langfuse.trace(
        id=state["trace_id"],
        name="acme-pipeline",
    )
    span = trace.span(name="input-guard")

    question = state["question"]
    errors = list(state.get("errors", []))

    # Length check
    if len(question) > 2000:
        question = question[:2000]
        errors.append("Input truncated to 2000 characters")

    # Basic injection pattern detection
    injection_patterns = [
        r"ignore\s+(previous|above|all)\s+(instructions|prompts)",
        r"you\s+are\s+now\s+",
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"OVERRIDE",
        r"bypass\s+(safety|security|guard)",
    ]

    sanitized = question
    for pattern in injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
            errors.append(f"Injection pattern filtered: {pattern}")

    # Strip excessive whitespace
    sanitized = " ".join(sanitized.split())

    span.end(
        input={"original_question": question},
        output={"sanitized_question": sanitized, "filters_applied": len(errors)},
    )

    return {
        "sanitized_question": sanitized,
        "errors": errors,
        "metadata": {
            **state.get("metadata", {}),
            "input_guard": {
                "filters_applied": len(errors),
                "original_length": len(question),
                "sanitized_length": len(sanitized),
                "cost": 0.0,
            },
        },
    }


def researcher_agent(state: PipelineState) -> dict:
    """
    Agent 1: Researcher
    - Takes the sanitized question
    - Generates 3 query variations for better recall
    - Searches Pinecone with each variation
    - Merges and deduplicates results
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(
        name="researcher",
        model=CLAUDE_MODEL,
        input={"question": state["sanitized_question"]},
    )

    # Step 1: Generate query variations
    query_system = """You are a search query specialist for corporate document retrieval.
Given a user question about Acme Corporation, generate exactly 3 different search queries
that would help find relevant information in the company's document store.

Each query should approach the question from a different angle:
- Query 1: Direct keyword match (use specific terms, product names, numbers)
- Query 2: Broader context query (related topics, adjacent information)
- Query 3: Analytical query (implications, comparisons, trends)

Return ONLY a JSON array of 3 strings. No explanation."""

    query_prompt = f"User question: {state['sanitized_question']}"

    query_response = call_claude(query_system, query_prompt, max_tokens=300)

    try:
        queries = json.loads(query_response["content"])
        if not isinstance(queries, list) or len(queries) != 3:
            queries = [state["sanitized_question"]] * 3
    except json.JSONDecodeError:
        queries = [state["sanitized_question"]] * 3

    # Step 2: Search Pinecone with each query
    all_results = []
    seen_ids = set()

    for query in queries:
        results = search_pinecone(query, top_k=5)
        for result in results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                all_results.append(result)

    # Sort by relevance score (descending)
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Keep top 10 unique results
    all_results = all_results[:10]

    generation.end(
        output={
            "queries_generated": queries,
            "total_results": len(all_results),
            "unique_results": len(seen_ids),
        },
        usage={
            "input": query_response["input_tokens"],
            "output": query_response["output_tokens"],
        },
    )

    return {
        "research_queries": queries,
        "research_results": all_results,
        "metadata": {
            **state.get("metadata", {}),
            "researcher": {
                "queries": queries,
                "results_count": len(all_results),
                "cost": query_response["cost"],
                "latency": query_response["latency"],
                "input_tokens": query_response["input_tokens"],
                "output_tokens": query_response["output_tokens"],
            },
        },
    }


def analyst_agent(state: PipelineState) -> dict:
    """
    Agent 2: Analyst
    - Takes raw search results from the Researcher
    - Extracts structured insights
    - Each insight has: claim, evidence, confidence, source
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(
        name="analyst",
        model=CLAUDE_MODEL,
        input={"results_count": len(state["research_results"])},
    )

    # Format research results for the analyst
    context_parts = []
    for i, result in enumerate(state["research_results"]):
        context_parts.append(
            f"[Document {i+1}] (source: {result['source']}, relevance: {result['score']:.3f})\n"
            f"{result['text']}"
        )
    context_block = "\n\n---\n\n".join(context_parts)

    analyst_system = """You are a senior business analyst at Acme Corporation.
You analyze raw document excerpts and extract structured insights.

For each insight, provide:
- claim: A specific, factual statement (not a vague summary)
- evidence: The exact text or data point that supports this claim
- confidence: HIGH (directly stated in documents), MEDIUM (inferred from multiple sources),
  or LOW (limited evidence, requires verification)
- source: Which document(s) support this claim

Rules:
- Extract 3-6 insights. Quality over quantity.
- Never fabricate information not present in the documents.
- If documents are insufficient to answer the question, say so explicitly.
- Include specific numbers, dates, and names when available.

Return a JSON array of insight objects. No explanation outside the JSON."""

    analyst_prompt = f"""Question being investigated: {state['sanitized_question']}

Retrieved documents:

{context_block}

Extract structured insights from these documents."""

    analyst_response = call_claude(analyst_system, analyst_prompt, max_tokens=1500)

    try:
        insights = json.loads(analyst_response["content"])
        if not isinstance(insights, list):
            insights = [{"claim": analyst_response["content"], "evidence": "raw response",
                        "confidence": "LOW", "source": "parsing error"}]
    except json.JSONDecodeError:
        # Try to extract JSON from the response if it has surrounding text
        json_match = re.search(r'\[.*\]', analyst_response["content"], re.DOTALL)
        if json_match:
            try:
                insights = json.loads(json_match.group())
            except json.JSONDecodeError:
                insights = [{"claim": "Failed to parse analyst output",
                            "evidence": analyst_response["content"][:200],
                            "confidence": "LOW", "source": "error"}]
        else:
            insights = [{"claim": "Failed to parse analyst output",
                        "evidence": analyst_response["content"][:200],
                        "confidence": "LOW", "source": "error"}]

    generation.end(
        output={
            "insights_count": len(insights),
            "confidence_distribution": {
                "HIGH": sum(1 for i in insights if i.get("confidence") == "HIGH"),
                "MEDIUM": sum(1 for i in insights if i.get("confidence") == "MEDIUM"),
                "LOW": sum(1 for i in insights if i.get("confidence") == "LOW"),
            },
        },
        usage={
            "input": analyst_response["input_tokens"],
            "output": analyst_response["output_tokens"],
        },
    )

    return {
        "insights": insights,
        "metadata": {
            **state.get("metadata", {}),
            "analyst": {
                "insights_count": len(insights),
                "cost": analyst_response["cost"],
                "latency": analyst_response["latency"],
                "input_tokens": analyst_response["input_tokens"],
                "output_tokens": analyst_response["output_tokens"],
            },
        },
    }


def writer_agent(state: PipelineState) -> dict:
    """
    Agent 3: Writer
    - Takes structured insights from the Analyst
    - Produces a 300-400 word executive brief
    - Includes citations to source evidence
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(
        name="writer",
        model=CLAUDE_MODEL,
        input={"insights_count": len(state["insights"])},
    )

    # Format insights for the writer
    insights_text = json.dumps(state["insights"], indent=2)

    writer_system = """You are an executive communications specialist at Acme Corporation.
You write concise, actionable executive briefs based on structured analyst insights.

Brief format:
1. Opening: One sentence answering the core question
2. Key Findings: 2-3 paragraphs covering the most important insights
3. Implications: What this means for decision-makers
4. Confidence Note: Briefly flag any LOW confidence items that need verification

Rules:
- 300-400 words. Not a word more.
- Use specific numbers and data points from the insights.
- Reference evidence directly (e.g., "According to the Q3 strategy memo...").
- Write for a C-suite audience: clear, direct, no jargon.
- If insights have LOW confidence, explicitly flag them as requiring verification.
- Do NOT invent information beyond what the insights contain."""

    writer_prompt = f"""Question: {state['sanitized_question']}

Analyst Insights:
{insights_text}

Write the executive brief."""

    writer_response = call_claude(writer_system, writer_prompt, max_tokens=800)

    generation.end(
        output={"brief_length": len(writer_response["content"].split())},
        usage={
            "input": writer_response["input_tokens"],
            "output": writer_response["output_tokens"],
        },
    )

    return {
        "brief": writer_response["content"],
        "metadata": {
            **state.get("metadata", {}),
            "writer": {
                "word_count": len(writer_response["content"].split()),
                "cost": writer_response["cost"],
                "latency": writer_response["latency"],
                "input_tokens": writer_response["input_tokens"],
                "output_tokens": writer_response["output_tokens"],
            },
        },
    }


def output_guard(state: PipelineState) -> dict:
    """
    Security: Check output before returning to user.
    - PII detection and redaction using Presidio
    - Cost guard: reject if total cost exceeds limit
    """
    trace = langfuse.trace(id=state["trace_id"])
    span = trace.span(name="output-guard")

    brief = state["brief"]
    errors = list(state.get("errors", []))
    metadata = dict(state.get("metadata", {}))

    # --- PII Detection and Redaction ---
    pii_results = pii_analyzer.analyze(
        text=brief,
        language="en",
        entities=[
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CREDIT_CARD",
            "US_SSN",
            "US_PASSPORT",
            "IBAN_CODE",
        ],
    )

    redacted_brief = brief
    if pii_results:
        anonymized = pii_anonymizer.anonymize(
            text=brief,
            analyzer_results=pii_results,
        )
        redacted_brief = anonymized.text
        errors.append(
            f"PII detected and redacted: {len(pii_results)} entities "
            f"({', '.join(set(r.entity_type for r in pii_results))})"
        )

    # --- Cost Guard ---
    total_cost = calculate_total_cost(metadata)
    metadata["total_cost"] = total_cost

    if total_cost > MAX_COST_PER_QUERY:
        errors.append(
            f"COST GUARD: Pipeline cost ${total_cost:.4f} exceeded "
            f"limit ${MAX_COST_PER_QUERY:.2f}. Output still returned "
            f"but flagged for review."
        )

    # --- Calculate total latency ---
    total_latency = sum(
        v.get("latency", 0)
        for v in metadata.values()
        if isinstance(v, dict) and "latency" in v
    )
    metadata["total_latency"] = total_latency

    span.end(
        input={"brief_length": len(brief)},
        output={
            "pii_entities_found": len(pii_results),
            "total_cost": total_cost,
            "total_latency": total_latency,
            "cost_guard_triggered": total_cost > MAX_COST_PER_QUERY,
        },
    )

    # Flush traces to Langfuse
    langfuse.flush()

    return {
        "brief": redacted_brief,
        "errors": errors,
        "metadata": metadata,
    }


def build_pipeline() -> StateGraph:
    """Construct the LangGraph pipeline: Input Guard -> Researcher -> Analyst -> Writer -> Output Guard."""

    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("input_guard", input_guard)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("analyst", analyst_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("output_guard", output_guard)

    # Define edges (linear pipeline)
    workflow.set_entry_point("input_guard")
    workflow.add_edge("input_guard", "researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "output_guard")
    workflow.add_edge("output_guard", END)

    # Compile the graph
    pipeline = workflow.compile()

    return pipeline


def run_pipeline(question: str) -> dict:
    """
    Execute the full pipeline for a given question.
    Returns the final state including brief, metadata, and any errors.
    """
    # Generate a unique trace ID
    trace_id = f"lab03-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Initialize state
    initial_state: PipelineState = {
        "question": question,
        "sanitized_question": "",
        "research_queries": [],
        "research_results": [],
        "insights": [],
        "brief": "",
        "metadata": {},
        "errors": [],
        "trace_id": trace_id,
    }

    # Build and run
    pipeline = build_pipeline()

    print(f"\n{'='*60}")
    print(f"  MULTI-AGENT INTELLIGENCE PIPELINE")
    print(f"  Trace ID: {trace_id}")
    print(f"{'='*60}")
    print(f"\n  Question: {question}\n")

    try:
        # Execute the pipeline
        print("  [1/4] Running Input Guard...")
        # LangGraph executes all nodes automatically
        final_state = pipeline.invoke(initial_state)

        # The pipeline.invoke runs all steps, but we print progress
        # by checking the final state
        print("  [2/4] Researcher complete.")
        print("  [3/4] Analyst complete.")
        print("  [4/4] Writer complete.")

    except Exception as e:
        print(f"\n  ERROR: Pipeline failed: {str(e)}")
        return {
            "brief": "",
            "metadata": {},
            "errors": [f"Pipeline failure: {str(e)}"],
            "trace_id": trace_id,
        }

    # Print results
    print(f"\n{'='*60}")
    print(f"  EXECUTIVE BRIEF")
    print(f"{'='*60}\n")
    print(final_state["brief"])

    print(f"\n{'='*60}")
    print(f"  PIPELINE METRICS")
    print(f"{'='*60}")

    metadata = final_state.get("metadata", {})
    print(f"  Total cost:    ${metadata.get('total_cost', 0):.4f}")
    print(f"  Total latency: {metadata.get('total_latency', 0):.2f}s")
    print(f"  Researcher:    ${metadata.get('researcher', {}).get('cost', 0):.4f} "
          f"({metadata.get('researcher', {}).get('latency', 0):.2f}s)")
    print(f"  Analyst:       ${metadata.get('analyst', {}).get('cost', 0):.4f} "
          f"({metadata.get('analyst', {}).get('latency', 0):.2f}s)")
    print(f"  Writer:        ${metadata.get('writer', {}).get('cost', 0):.4f} "
          f"({metadata.get('writer', {}).get('latency', 0):.2f}s)")

    if final_state.get("errors"):
        print(f"\n  Warnings/Errors:")
        for error in final_state["errors"]:
            print(f"    - {error}")

    print(f"\n  View trace: {os.getenv('LANGFUSE_HOST')}/trace/{trace_id}")
    print(f"{'='*60}\n")

    return final_state


# --- Main entry point ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "What is Acme Corporation's Q3 revenue target and what are the key risks?"

    result = run_pipeline(question)
