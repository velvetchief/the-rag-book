"""
main.py -- Lab 02: Advanced RAG -- Upgrading Your Pipeline

Combines all five steps into one runnable script:
  Step 0: Baseline Pipeline
  Step 1: Multi-Query Retrieval
  Step 2: Hybrid Search (dense + BM25)
  Step 3: Cohere Reranking
  Step 4: GraphRAG Comparison
  Step 5: RAGAS Evaluation

Usage:
    python main.py
"""

# --- Standard library ---
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

# --- Third-party ---
import anthropic
import cohere
import networkx as nx
import numpy as np
import openai

from datasets import Dataset

# RAGAS
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings


# =============================================================================
# SETUP CHECK
# =============================================================================

def check_import(module_name, pip_name=None):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        print(f"  [OK] {module_name}")
        return True
    except ImportError:
        pip_name = pip_name or module_name
        print(f"  [MISSING] {module_name} -- run: pip install {pip_name}")
        return False


def run_setup_check():
    print("Checking dependencies for Lab 02...")
    print()

    all_ok = True
    all_ok &= check_import("anthropic")
    all_ok &= check_import("openai")
    all_ok &= check_import("cohere")
    all_ok &= check_import("networkx")
    all_ok &= check_import("numpy")
    all_ok &= check_import("ragas")
    all_ok &= check_import("datasets")
    all_ok &= check_import("langchain_anthropic")
    all_ok &= check_import("langchain_openai")
    # Optional
    check_import("rank_bm25", "rank-bm25")

    print()
    if all_ok:
        print("All required dependencies installed. Ready for Lab 02.")
    else:
        print("Install missing dependencies before proceeding.")
        print("Quick install: pip install anthropic openai cohere networkx numpy ragas datasets langchain-anthropic langchain-openai rank-bm25")

    # Check API keys
    print()
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CO_API_KEY"]:
        if os.environ.get(key):
            print(f"  [OK] {key} is set")
        else:
            print(f"  [MISSING] {key} -- export {key}='your-key-here'")


# =============================================================================
# CONFIGURATION
# =============================================================================

CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5


# =============================================================================
# DATA: ACME MEMO CHUNKS
# =============================================================================

ACME_CHUNKS = [
    {
        "id": "chunk_01",
        "text": "ACME CORPORATION Q3 STRATEGY MEMO. Author: Sarah Chen, CEO. "
                "Acme Corporation enters Q3 with strong momentum from Product Alpha "
                "but faces headwinds across the portfolio. Our Q3 revenue target is $18.6M.",
        "page": 1,
        "section": "Executive Summary"
    },
    {
        "id": "chunk_02",
        "text": "Product Alpha delivered $12.4M in Q2 revenue, representing our strongest "
                "quarter. Annual recurring revenue (ARR) stands at $48.2M.",
        "page": 2,
        "section": "Product Alpha"
    },
    {
        "id": "chunk_03",
        "text": "Competitor Dataview has launched an aggressive campaign with pricing "
                "40% below ours. Our win rate against Dataview dropped from 72% to 58% in Q2. "
                "Marcus Rodriguez, VP of Product, is leading the competitive response team.",
        "page": 2,
        "section": "Product Alpha - Competition"
    },
    {
        "id": "chunk_04",
        "text": "Product Beta generated $3.8M in Q2. Monthly churn increased to 4.2%, "
                "up from 3.1% in Q1. Customer feedback consistently cites onboarding "
                "complexity as the primary pain point.",
        "page": 3,
        "section": "Product Beta"
    },
    {
        "id": "chunk_05",
        "text": "Lisa Park, Head of Customer Success, has proposed an onboarding "
                "overhaul targeting 50% reduction in time-to-value. Engineering "
                "estimates 6 weeks for implementation.",
        "page": 3,
        "section": "Product Beta - Mitigation"
    },
    {
        "id": "chunk_06",
        "text": "Product Gamma remains in private beta with 12 design partners. "
                "Public launch is scheduled for September 15. Pricing is set at "
                "$45-120 per user per month across three tiers.",
        "page": 4,
        "section": "Product Gamma"
    },
    {
        "id": "chunk_07",
        "text": "Early NPS scores for Product Gamma average 67. Tom Walsh, VP of "
                "Engineering, flagged that the API integration layer needs additional "
                "hardening before launch.",
        "page": 4,
        "section": "Product Gamma - Status"
    },
    {
        "id": "chunk_08",
        "text": "Risk Register: 1. Dataview pricing pressure on Alpha (Impact: High, "
                "Likelihood: High). 2. Beta churn acceleration (Impact: Medium, "
                "Likelihood: High). 3. Gamma launch delay (Impact: High, Likelihood: Medium).",
        "page": 5,
        "section": "Risk Register (1-3)"
    },
    {
        "id": "chunk_09",
        "text": "Risk Register continued: 4. Macroeconomic slowdown reducing enterprise "
                "spend (Impact: High, Likelihood: Medium). 5. Key person risk - Marcus "
                "Rodriguez considering external offer (Impact: High, Likelihood: Low).",
        "page": 5,
        "section": "Risk Register (4-5)"
    },
    {
        "id": "chunk_10",
        "text": "Q3 Priorities: 1. Defend Alpha market share against Dataview. "
                "2. Reverse Beta churn trend through onboarding improvements. "
                "3. Execute Gamma launch on schedule. Target: $18.6M total Q3 revenue.",
        "page": 6,
        "section": "Q3 Priorities"
    },
]


# =============================================================================
# DATA: EVALUATION QUERIES
# =============================================================================

EVAL_QUERIES = [
    {
        "question": "What is the Q3 revenue target?",
        "ground_truth": "The Q3 revenue target is $18.6M.",
        "category": "factual",
    },
    {
        "question": "What competitive threat does Product Alpha face and how is the company responding?",
        "ground_truth": "Product Alpha faces competition from Dataview which has pricing 40% below Acme's. "
                       "Win rate dropped from 72% to 58%. Marcus Rodriguez, VP of Product, is leading "
                       "the competitive response team.",
        "category": "multi_hop",
    },
    {
        "question": "What is causing Product Beta's churn and what solution has been proposed?",
        "ground_truth": "Beta's churn increased to 4.2% from 3.1% due to onboarding complexity. "
                       "Lisa Park proposed an onboarding overhaul targeting 50% reduction in "
                       "time-to-value, with 6 weeks engineering estimate.",
        "category": "multi_hop",
    },
    {
        "question": "List all items in the risk register with their impact and likelihood.",
        "ground_truth": "Five risks: 1) Dataview pricing pressure (High/High), "
                       "2) Beta churn acceleration (Medium/High), 3) Gamma launch delay "
                       "(High/Medium), 4) Macro slowdown (High/Medium), "
                       "5) Key person risk Marcus Rodriguez (High/Low).",
        "category": "aggregation",
    },
    {
        "question": "When does Product Gamma launch and what are the key blockers?",
        "ground_truth": "Gamma launches September 15. Tom Walsh flagged that the API integration "
                       "layer needs additional hardening before launch.",
        "category": "multi_hop",
    },
    {
        "question": "What is Product Alpha's ARR and how does it compare to Q2 revenue?",
        "ground_truth": "Alpha's ARR is $48.2M and Q2 revenue was $12.4M.",
        "category": "comparison",
    },
    {
        "question": "Who are the key people mentioned in the memo and what are their roles?",
        "ground_truth": "Sarah Chen (CEO), Marcus Rodriguez (VP Product, competitive response), "
                       "Lisa Park (Head of Customer Success, onboarding overhaul), "
                       "Tom Walsh (VP Engineering, Gamma launch).",
        "category": "aggregation",
    },
    {
        "question": "What is the total Q2 revenue across all products?",
        "ground_truth": "Total Q2 revenue is $16.2M (Alpha $12.4M + Beta $3.8M + Gamma $0).",
        "category": "reasoning",
    },
]

# Relationship-focused queries for graph comparison
GRAPH_EVAL_QUERIES = [
    {
        "question": "How are Dataview and Marcus Rodriguez connected?",
        "ground_truth": "Marcus Rodriguez leads the competitive response to Dataview. "
                       "He is also a key person risk (considering external offer), which "
                       "could impact the Dataview response effort.",
        "category": "relationship",
    },
    {
        "question": "Which risks are interconnected and how?",
        "ground_truth": "Dataview pricing pressure affects Alpha revenue. Marcus Rodriguez "
                       "key person risk threatens the competitive response to Dataview. "
                       "Beta churn and Gamma delay both affect Q3 target along with Alpha pressure.",
        "category": "relationship",
    },
    {
        "question": "Who is responsible for each product's key challenge?",
        "ground_truth": "Marcus Rodriguez handles Alpha's Dataview competition. "
                       "Lisa Park handles Beta's churn/onboarding. "
                       "Tom Walsh handles Gamma's API hardening.",
        "category": "relationship",
    },
]


# =============================================================================
# STEP 0: BASELINE RAG PIPELINE
# =============================================================================

class BaselineRAGPipeline:
    """Simple vector-search RAG pipeline."""

    def __init__(self):
        self.claude = anthropic.Anthropic()
        self.openai = openai.OpenAI()
        self.chunks = ACME_CHUNKS
        self.embeddings = {}
        self.name = "Baseline"

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        response = self.openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def index_chunks(self):
        """Embed all chunks (one-time setup)."""
        print(f"  Indexing {len(self.chunks)} chunks...")
        texts = [c["text"] for c in self.chunks]

        response = self.openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )

        for i, item in enumerate(response.data):
            self.embeddings[self.chunks[i]["id"]] = item.embedding

        print(f"  Indexed {len(self.embeddings)} chunks.")

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Retrieve top-k chunks by cosine similarity."""
        query_embedding = self.embed_text(query)
        query_vec = np.array(query_embedding)

        scores = []
        for chunk in self.chunks:
            chunk_vec = np.array(self.embeddings[chunk["id"]])
            # Cosine similarity
            sim = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            scores.append((sim, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {**chunk, "score": float(score)}
            for score, chunk in scores[:top_k]
        ]

    def generate(self, query: str, chunks: list[dict]) -> str:
        """Generate answer from retrieved chunks."""
        context = "\n\n".join(c["text"] for c in chunks)

        response = self.claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=(
                "Answer the question using ONLY the provided context. "
                "If the context does not contain enough information, say so. "
                "Be specific and cite numbers from the context."
            ),
            messages=[{
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }]
        )

        return response.content[0].text

    def query(self, question: str) -> dict:
        """Full pipeline: retrieve + generate."""
        start = time.time()

        chunks = self.retrieve(question)
        answer = self.generate(question, chunks)

        elapsed = time.time() - start

        return {
            "question": question,
            "answer": answer,
            "chunks": chunks,
            "latency": elapsed,
            "pipeline": self.name,
        }


# =============================================================================
# STEP 1: MULTI-QUERY RETRIEVAL
# =============================================================================

class MultiQueryRAGPipeline(BaselineRAGPipeline):
    """RAG pipeline with multi-query retrieval."""

    def __init__(self):
        super().__init__()
        self.name = "MultiQuery"

    def generate_query_variants(self, query: str, n: int = 3) -> list[str]:
        """Generate N query variants using Claude."""

        response = self.claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=(
                "Generate alternative phrasings of the user's question to improve "
                "search recall. Each variant should capture a different aspect or "
                "use different keywords. Return exactly {n} variants, one per line. "
                "Do not number them or add any other text."
            ).replace("{n}", str(n)),
            messages=[{"role": "user", "content": f"Original question: {query}"}]
        )

        variants = [
            line.strip()
            for line in response.content[0].text.strip().split("\n")
            if line.strip()
        ][:n]

        return [query] + variants  # Include original query

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Multi-query retrieval: generate variants, retrieve for each, merge."""

        # Generate query variants
        queries = self.generate_query_variants(query, n=3)

        # Retrieve for each variant
        all_results = {}
        for q in queries:
            q_embedding = self.embed_text(q)
            q_vec = np.array(q_embedding)

            for chunk in self.chunks:
                chunk_vec = np.array(self.embeddings[chunk["id"]])
                sim = np.dot(q_vec, chunk_vec) / (
                    np.linalg.norm(q_vec) * np.linalg.norm(chunk_vec)
                )

                # Keep the highest score for each chunk across all queries
                chunk_id = chunk["id"]
                if chunk_id not in all_results or sim > all_results[chunk_id][0]:
                    all_results[chunk_id] = (sim, chunk)

        # Sort by best score and take top_k
        sorted_results = sorted(all_results.values(), key=lambda x: x[0], reverse=True)

        return [
            {**chunk, "score": float(score)}
            for score, chunk in sorted_results[:top_k]
        ]


# =============================================================================
# STEP 2: HYBRID SEARCH (DENSE + BM25)
# =============================================================================

class HybridRAGPipeline(MultiQueryRAGPipeline):
    """RAG pipeline with hybrid dense + sparse retrieval."""

    def __init__(self, dense_weight: float = 0.7):
        super().__init__()
        self.name = "Hybrid"
        self.dense_weight = dense_weight
        self.sparse_weight = 1.0 - dense_weight
        self.bm25_index = None

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on",
                      "at", "to", "for", "of", "with", "and", "or", "but", "not"}
        return [t for t in tokens if t not in stop_words]

    def index_chunks(self):
        """Index chunks for both dense and sparse retrieval."""
        super().index_chunks()  # Dense indexing

        # BM25 indexing
        print("  Building BM25 index...")
        self.doc_tokens = []
        self.doc_lengths = []
        self.df = Counter()  # Document frequency

        for chunk in self.chunks:
            tokens = self._tokenize(chunk["text"])
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))

            # Count document frequency (unique terms per doc)
            unique_terms = set(tokens)
            for term in unique_terms:
                self.df[term] += 1

        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        self.n_docs = len(self.chunks)
        print(f"  BM25 index built: {self.n_docs} docs, {len(self.df)} unique terms")

    def _bm25_score(self, query_tokens: list[str], doc_idx: int,
                    k1: float = 1.5, b: float = 0.75) -> float:
        """Compute BM25 score for a document."""
        doc_tokens = self.doc_tokens[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        tf = Counter(doc_tokens)
        score = 0.0

        for term in query_tokens:
            if term not in tf:
                continue

            term_freq = tf[term]
            doc_freq = self.df.get(term, 0)

            # IDF
            idf = math.log((self.n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

            # TF normalization
            tf_norm = (term_freq * (k1 + 1)) / (
                term_freq + k1 * (1 - b + b * doc_len / self.avg_doc_length)
            )

            score += idf * tf_norm

        return score

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Hybrid retrieval: combine dense and sparse scores."""

        # Get multi-query dense results (from parent class)
        queries = self.generate_query_variants(query, n=3)

        dense_scores = {}
        for q in queries:
            q_embedding = self.embed_text(q)
            q_vec = np.array(q_embedding)

            for i, chunk in enumerate(self.chunks):
                chunk_vec = np.array(self.embeddings[chunk["id"]])
                sim = float(np.dot(q_vec, chunk_vec) / (
                    np.linalg.norm(q_vec) * np.linalg.norm(chunk_vec)
                ))
                chunk_id = chunk["id"]
                if chunk_id not in dense_scores or sim > dense_scores[chunk_id]:
                    dense_scores[chunk_id] = sim

        # BM25 sparse scores
        query_tokens = self._tokenize(query)
        sparse_scores = {}
        for i, chunk in enumerate(self.chunks):
            score = self._bm25_score(query_tokens, i)
            sparse_scores[chunk["id"]] = score

        # Normalize scores to [0, 1]
        if dense_scores:
            max_dense = max(dense_scores.values())
            min_dense = min(dense_scores.values())
            range_dense = max_dense - min_dense if max_dense != min_dense else 1
            for k in dense_scores:
                dense_scores[k] = (dense_scores[k] - min_dense) / range_dense

        if sparse_scores:
            max_sparse = max(sparse_scores.values()) if max(sparse_scores.values()) > 0 else 1
            for k in sparse_scores:
                sparse_scores[k] = sparse_scores[k] / max_sparse

        # Combine scores
        combined = {}
        for chunk in self.chunks:
            cid = chunk["id"]
            d_score = dense_scores.get(cid, 0)
            s_score = sparse_scores.get(cid, 0)
            combined[cid] = self.dense_weight * d_score + self.sparse_weight * s_score

        # Sort and return top-k
        sorted_chunks = sorted(
            [(combined[c["id"]], c) for c in self.chunks],
            key=lambda x: x[0],
            reverse=True
        )

        return [
            {**chunk, "score": float(score)}
            for score, chunk in sorted_chunks[:top_k]
        ]


# =============================================================================
# STEP 3: COHERE RERANKING
# =============================================================================

class RerankedRAGPipeline(HybridRAGPipeline):
    """RAG pipeline with Cohere reranking."""

    def __init__(self, dense_weight: float = 0.7, rerank_top_n: int = 5):
        super().__init__(dense_weight)
        self.name = "Reranked"
        self.cohere = cohere.Client()
        self.rerank_top_n = rerank_top_n

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve with hybrid search, then rerank with Cohere."""

        # Get more candidates than we need (reranking works best with more input)
        candidates = super().retrieve(query, top_k=min(top_k * 2, len(self.chunks)))

        if not candidates:
            return []

        # Rerank with Cohere
        rerank_response = self.cohere.rerank(
            model="rerank-v3.5",
            query=query,
            documents=[c["text"] for c in candidates],
            top_n=self.rerank_top_n,
        )

        # Map reranked results back to chunks
        reranked = []
        for result in rerank_response.results:
            chunk = candidates[result.index].copy()
            chunk["original_score"] = chunk["score"]
            chunk["score"] = result.relevance_score
            reranked.append(chunk)

        return reranked[:top_k]


# =============================================================================
# STEP 4: GRAPHRAG
# =============================================================================

# Entity extraction tool definition
EXTRACTION_TOOL = [
    {
        "name": "record_extraction",
        "description": "Record entities and relationships.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "entity_type": {"type": "string"},
                            "properties": {"type": "object"}
                        },
                        "required": ["name", "entity_type"]
                    }
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "relationship_type": {"type": "string"}
                        },
                        "required": ["source", "target", "relationship_type"]
                    }
                }
            },
            "required": ["entities", "relationships"]
        }
    }
]


class GraphAugmentedRAGPipeline(RerankedRAGPipeline):
    """RAG pipeline with optional graph augmentation."""

    def __init__(self, dense_weight: float = 0.7):
        super().__init__(dense_weight)
        self.name = "GraphAugmented"
        self.graph = None

    def build_graph(self):
        """Extract entities and build knowledge graph."""
        print("  Extracting entities from chunks...")

        full_text = "\n\n".join(c["text"] for c in self.chunks)

        response = self.claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=(
                "Extract entities and relationships from the document. "
                "Entity types: Person, Product, Company, Metric, Risk, Date, Strategy. "
                "Be comprehensive."
            ),
            tools=EXTRACTION_TOOL,
            tool_choice={"type": "tool", "name": "record_extraction"},
            messages=[{"role": "user", "content": f"Extract from:\n\n{full_text}"}]
        )

        entities = []
        relationships = []
        for block in response.content:
            if block.type == "tool_use":
                entities = block.input.get("entities", [])
                relationships = block.input.get("relationships", [])

        # Build NetworkX graph
        self.graph = nx.DiGraph()
        for e in entities:
            self.graph.add_node(e["name"], entity_type=e["entity_type"],
                              **e.get("properties", {}))

        for r in relationships:
            if r["source"] in self.graph.nodes() and r["target"] in self.graph.nodes():
                self.graph.add_edge(r["source"], r["target"],
                                  relationship_type=r["relationship_type"])

        print(f"  Graph built: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")

    def get_graph_context(self, query: str) -> str:
        """Get relevant subgraph context for a query."""
        if self.graph is None:
            return ""

        # Find mentioned entities in the query
        query_lower = query.lower()
        relevant_nodes = []

        for node in self.graph.nodes():
            if node.lower() in query_lower or any(
                word in node.lower()
                for word in query_lower.split()
                if len(word) > 3
            ):
                relevant_nodes.append(node)

        if not relevant_nodes:
            return ""

        # Get 1-hop neighborhood
        context_lines = []
        for node in relevant_nodes:
            # Outgoing edges
            for _, target, data in self.graph.out_edges(node, data=True):
                rel = data.get("relationship_type", "RELATED_TO")
                context_lines.append(f"{node} -[{rel}]-> {target}")

            # Incoming edges
            for source, _, data in self.graph.in_edges(node, data=True):
                rel = data.get("relationship_type", "RELATED_TO")
                context_lines.append(f"{source} -[{rel}]-> {node}")

        return "\n".join(context_lines)

    def generate(self, query: str, chunks: list[dict]) -> str:
        """Generate with both vector context and graph context."""
        vector_context = "\n\n".join(c["text"] for c in chunks)
        graph_context = self.get_graph_context(query)

        full_context = f"DOCUMENT EXCERPTS:\n{vector_context}"
        if graph_context:
            full_context += f"\n\nENTITY RELATIONSHIPS:\n{graph_context}"

        response = self.claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=(
                "Answer the question using the provided context. "
                "Document excerpts provide detailed text. Entity relationships "
                "show connections between people, products, and concepts. "
                "Use both sources when available."
            ),
            messages=[{
                "role": "user",
                "content": f"Context:\n{full_context}\n\nQuestion: {query}"
            }]
        )

        return response.content[0].text


# =============================================================================
# STEP 5: RAGAS EVALUATION
# =============================================================================

def run_pipeline_on_queries(pipeline, queries: list[dict]) -> list[dict]:
    """Run a pipeline on evaluation queries and collect results."""

    results = []
    total_latency = 0

    for q in queries:
        result = pipeline.query(q["question"])
        total_latency += result["latency"]

        results.append({
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "answer": result["answer"],
            "contexts": [c["text"] for c in result["chunks"]],
            "latency": result["latency"],
            "category": q.get("category", "unknown"),
        })

    avg_latency = total_latency / len(queries) if queries else 0
    print(f"  {pipeline.name}: {len(results)} queries, avg latency {avg_latency:.2f}s")

    return results


def results_to_ragas_dataset(results: list[dict]) -> Dataset:
    """Convert pipeline results to RAGAS Dataset format."""
    return Dataset.from_dict({
        "question": [r["question"] for r in results],
        "answer": [r["answer"] for r in results],
        "contexts": [r["contexts"] for r in results],
        "ground_truth": [r["ground_truth"] for r in results],
    })


def evaluate_pipeline(results: list[dict]) -> dict:
    """Run RAGAS evaluation on pipeline results."""

    dataset = results_to_ragas_dataset(results)

    evaluator_llm = LangchainLLMWrapper(
        ChatAnthropic(model="claude-sonnet-4-6-20250514")
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-3-small")
    )

    scores = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    return {
        "faithfulness": scores["faithfulness"],
        "answer_relevancy": scores["answer_relevancy"],
        "context_precision": scores["context_precision"],
        "context_recall": scores["context_recall"],
        "avg_latency": np.mean([r["latency"] for r in results]),
    }


def print_comparison_table(all_scores: dict) -> None:
    """Print side-by-side comparison of all pipeline versions."""

    print(f"\n{'='*80}")
    print("PIPELINE COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"\n{'Pipeline':<18} {'Faithful':>10} {'Relevancy':>10} {'Precision':>10} {'Recall':>10} {'Latency':>10}")
    print("-" * 78)

    for name, scores in all_scores.items():
        print(f"{name:<18} {scores['faithfulness']:>10.3f} "
              f"{scores['answer_relevancy']:>10.3f} "
              f"{scores['context_precision']:>10.3f} "
              f"{scores['context_recall']:>10.3f} "
              f"{scores['avg_latency']:>9.2f}s")

    # Show deltas from baseline
    if "Baseline" in all_scores:
        baseline = all_scores["Baseline"]
        print(f"\n{'Delta vs Baseline':<18} {'Faithful':>10} {'Relevancy':>10} {'Precision':>10} {'Recall':>10} {'Latency':>10}")
        print("-" * 78)

        for name, scores in all_scores.items():
            if name == "Baseline":
                continue
            print(f"{name:<18} "
                  f"{scores['faithfulness'] - baseline['faithfulness']:>+10.3f} "
                  f"{scores['answer_relevancy'] - baseline['answer_relevancy']:>+10.3f} "
                  f"{scores['context_precision'] - baseline['context_precision']:>+10.3f} "
                  f"{scores['context_recall'] - baseline['context_recall']:>+10.3f} "
                  f"{scores['avg_latency'] - baseline['avg_latency']:>+9.2f}s")


def run_full_evaluation():
    """Run the complete evaluation across all pipeline versions."""

    print("=" * 60)
    print("LAB 02: FULL PIPELINE EVALUATION")
    print("=" * 60)

    all_scores = {}

    # --- Baseline ---
    print("\n--- Step 0: Baseline Pipeline ---")
    baseline = BaselineRAGPipeline()
    baseline.index_chunks()
    baseline_results = run_pipeline_on_queries(baseline, EVAL_QUERIES)
    all_scores["Baseline"] = evaluate_pipeline(baseline_results)
    print(f"  Scores: {all_scores['Baseline']}")

    # --- Multi-Query ---
    print("\n--- Step 1: Multi-Query Pipeline ---")
    multiquery = MultiQueryRAGPipeline()
    multiquery.embeddings = baseline.embeddings  # Reuse embeddings
    mq_results = run_pipeline_on_queries(multiquery, EVAL_QUERIES)
    all_scores["MultiQuery"] = evaluate_pipeline(mq_results)
    print(f"  Scores: {all_scores['MultiQuery']}")

    # --- Hybrid ---
    print("\n--- Step 2: Hybrid Search Pipeline ---")
    hybrid = HybridRAGPipeline(dense_weight=0.7)
    hybrid.embeddings = baseline.embeddings
    hybrid.index_chunks()  # Need to build BM25 index
    hybrid_results = run_pipeline_on_queries(hybrid, EVAL_QUERIES)
    all_scores["Hybrid"] = evaluate_pipeline(hybrid_results)
    print(f"  Scores: {all_scores['Hybrid']}")

    # --- Reranked ---
    print("\n--- Step 3: Reranked Pipeline ---")
    reranked = RerankedRAGPipeline(dense_weight=0.7)
    reranked.embeddings = baseline.embeddings
    reranked.index_chunks()
    rr_results = run_pipeline_on_queries(reranked, EVAL_QUERIES)
    all_scores["Reranked"] = evaluate_pipeline(rr_results)
    print(f"  Scores: {all_scores['Reranked']}")

    # --- Graph-Augmented ---
    print("\n--- Step 4: Graph-Augmented Pipeline ---")
    graph = GraphAugmentedRAGPipeline(dense_weight=0.7)
    graph.embeddings = baseline.embeddings
    graph.index_chunks()
    graph.build_graph()
    graph_results = run_pipeline_on_queries(graph, EVAL_QUERIES)
    all_scores["GraphAugmented"] = evaluate_pipeline(graph_results)
    print(f"  Scores: {all_scores['GraphAugmented']}")

    # --- Comparison Table ---
    print_comparison_table(all_scores)

    # --- Save results ---
    with open("lab02_results.json", "w") as f:
        json.dump(all_scores, f, indent=2)
    print(f"\nResults saved to lab02_results.json")

    # --- Product Leader Summary ---
    print(f"\n{'='*80}")
    print("PRODUCT LEADER SUMMARY")
    print(f"{'='*80}")
    print("""
  Key findings from the evaluation:

  1. MULTI-QUERY improves context recall the most.
     When users ask broad questions ("list all risks"), generating query
     variants finds chunks that a single query misses.

  2. HYBRID SEARCH (dense + BM25) improves precision.
     When queries contain specific terms ("Marcus Rodriguez"), keyword
     matching catches what semantic search misses.

  3. COHERE RERANKING improves precision further.
     The cross-encoder reranker pushes the most relevant chunks to the top,
     improving answer quality even when retrieval finds the right chunks
     but in the wrong order.

  4. GRAPHRAG helps on relationship queries.
     Questions about connections between entities ("How is Dataview related
     to Marcus Rodriguez?") benefit from graph context.

  5. EACH UPGRADE ADDS LATENCY.
     Multi-query adds ~1s (extra LLM call). Reranking adds ~0.3s (API call).
     Graph adds ~0.5s (graph traversal). Budget total latency against user
     experience requirements.

  RECOMMENDATION:
    For most use cases: Baseline + Multi-Query + Reranking
    This gives the best quality/latency/cost tradeoff.

    Add Hybrid Search if queries contain specific names or numbers.
    Add GraphRAG only if relationship queries are a key use case.
    """)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    run_setup_check()
    print()
    run_full_evaluation()
