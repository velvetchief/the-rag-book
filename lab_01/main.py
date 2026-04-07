#!/usr/bin/env python3
"""
main.py — Complete RAG pipeline for Lab 01.

Pipeline stages:
1. Extract text from PDF (with table and header/footer handling)
2. Chunk the extracted text using recursive splitting
3. Embed chunks using OpenAI text-embedding-3-small
4. Store embeddings in Pinecone
5. Accept user queries, retrieve relevant chunks, generate answers with Claude

Usage:
    # Index the document (run once)
    python main.py --index

    # Query the pipeline
    python main.py --query "What is Product Alpha's revenue?"

    # Run all test queries
    python main.py --test

    # Interactive mode
    python main.py --interactive

Requirements:
    pip install -r requirements.txt
    Create .env with ANTHROPIC_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY
"""

import os
import re
import sys
import json
import time
import hashlib
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

import numpy as np
from dotenv import load_dotenv

import anthropic
import openai
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
PINECONE_INDEX_NAME = "rag-lab-01"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 75
TOP_K = 5


# ── The Acme Corp Q3 Strategy Memo (text version) ─────────────────────────
# In production, this would come from PDF extraction (see extract_pdf below).
# We include the raw text as a fallback for students without a PDF file.

ACME_MEMO_TEXT = """
ACME CORPORATION
Q3 2024 STRATEGY MEMO
Prepared by: Sarah Chen, VP of Strategy
Date: July 1, 2024
Classification: Confidential

EXECUTIVE SUMMARY

Acme Corporation enters Q3 2024 with strong momentum across our product portfolio.
Product Alpha achieved Q2 revenue of $12.4M, representing 34% year-over-year growth
and bringing our annual recurring revenue (ARR) to $48.2M. Enterprise adoption
continues to accelerate, with 23 new logos added in Q2 alone.

Product Beta stabilized at $3.8M Q2 revenue after the pricing restructure in Q1.
While churn remains elevated at 4.2% (target: <3%), the new onboarding flow has
reduced time-to-value by 40%. We expect churn improvements to materialize in Q3
as the Q2 cohort matures through the revised onboarding experience.

Product Gamma remains in private beta with 47 design partners actively testing
the platform. Launch is scheduled for September 15, 2024. Early feedback indicates
strong product-market fit in the mid-market segment, with a projected average
selling price (ASP) of $45K.

PRODUCT PERFORMANCE SUMMARY

| Product | Q2 Revenue | ARR     | YoY Growth | Churn | Status       |
|---------|-----------|---------|------------|-------|--------------|
| Alpha   | $12.4M    | $48.2M  | 34%        | 1.8%  | Growth       |
| Beta    | $3.8M     | $14.1M  | -2%        | 4.2%  | Stabilizing  |
| Gamma   | $0.0M     | N/A     | N/A        | N/A   | Private Beta |

Q3 FINANCIAL TARGETS

Combined Q3 revenue target: $18.6M
- Product Alpha: $14.2M (Q3 target, representing 15% sequential growth)
- Product Beta: $4.0M (Q3 target, modest 5% sequential growth)
- Product Gamma: $0.4M (post-launch partial quarter revenue)

The $18.6M target represents a 22% year-over-year increase and is aligned with
our board-approved annual plan of $68M in total revenue.

RISK REGISTER

1. Competitive threat from Nexus Corp's new enterprise offering (Impact: High,
   Probability: Medium). Nexus has announced a competing product at 30% lower
   price point targeting our enterprise segment. Mitigation: Accelerate Alpha's
   API platform release to differentiate on integration capabilities.

2. Beta churn exceeding 5% threshold (Impact: Medium, Probability: Medium).
   If Q2 onboarding improvements don't reduce churn by Q3 end, Beta's ARR will
   decline below $13M. Mitigation: Dedicated customer success team assigned to
   the 15 highest-risk accounts.

3. Gamma launch delay beyond September 30 (Impact: High, Probability: Low).
   Engineering team reports 92% feature completion. Remaining work is primarily
   in billing integration and SSO. Mitigation: Weekly launch readiness reviews
   with engineering leads.

4. Key person dependency on Alpha's ML infrastructure team (Impact: Medium,
   Probability: Low). Two of three senior ML engineers have been with the
   company less than 12 months. Mitigation: Cross-training program initiated
   in Q2; documentation sprint scheduled for July.

5. Regulatory changes in EU market affecting data processing capabilities
   (Impact: High, Probability: Low). Proposed amendments to data sovereignty
   requirements could affect our EU customer deployment model. Mitigation:
   Legal team monitoring; architecture review for data residency options
   initiated with target completion by August 15.

STRATEGIC PRIORITIES FOR Q3

1. Close 10 enterprise deals for Alpha (pipeline: 34 qualified opportunities)
2. Reduce Beta churn to below 3.5% by end of Q3
3. Launch Gamma by September 15 with 20 paying customers in first 2 weeks
4. Complete Series C fundraising preparation (target: $50M at $400M valuation)
5. Hire VP of Engineering and 8 senior engineers across all product lines
"""


# ── PDF Extraction ─────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF with table handling and header/footer removal.

    Uses pdfplumber for table-aware extraction.
    Falls back to basic text extraction if tables aren't detected.
    """
    import pdfplumber

    pages_text = []
    all_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract tables first
            tables = page.extract_tables()
            table_regions = []

            for table_data in tables:
                if table_data and len(table_data) >= 2:
                    headers = [str(cell or "").strip() for cell in table_data[0]]
                    rows = [
                        [str(cell or "").strip() for cell in row]
                        for row in table_data[1:]
                    ]
                    # Convert to markdown
                    md_lines = ["| " + " | ".join(headers) + " |"]
                    md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                    for row in rows:
                        padded = row + [""] * (len(headers) - len(row))
                        md_lines.append("| " + " | ".join(padded[:len(headers)]) + " |")
                    all_tables.append({
                        "page": page_num,
                        "markdown": "\n".join(md_lines)
                    })

            # Extract full page text
            text = page.extract_text() or ""
            pages_text.append(text)

    # Detect and remove headers/footers (repeated text across pages)
    if len(pages_text) >= 3:
        from collections import Counter
        top_lines = Counter()
        bottom_lines = Counter()
        for pt in pages_text:
            lines = [l.strip() for l in pt.split('\n') if l.strip()]
            for l in lines[:2]:
                top_lines[l] += 1
            for l in lines[-2:]:
                bottom_lines[l] += 1

        noise = set()
        for line, count in top_lines.items():
            if count >= 3:
                noise.add(line)
        for line, count in bottom_lines.items():
            if count >= 3:
                noise.add(line)

        cleaned_pages = []
        for pt in pages_text:
            lines = pt.split('\n')
            cleaned = [l for l in lines if l.strip() not in noise]
            cleaned_pages.append('\n'.join(cleaned))
        pages_text = cleaned_pages

    # Remove page number patterns
    full_text = '\n\n'.join(pages_text)
    full_text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', full_text)
    full_text = re.sub(r'^\s*\d+\s*$', '', full_text, flags=re.MULTILINE)

    # Insert table markdown at appropriate locations
    for table in all_tables:
        full_text += f"\n\n[Table from page {table['page']}]\n{table['markdown']}"

    return full_text.strip()


# ── Chunking ───────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    """A chunk of text with metadata."""
    text: str
    chunk_id: str
    source: str
    section: str = ""
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text)
        if not self.chunk_id:
            self.chunk_id = hashlib.md5(self.text.encode()).hexdigest()[:12]


def chunk_document(
    text: str,
    source: str = "acme_q3_memo",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Chunk]:
    """
    Chunk document text using recursive splitting.

    Preserves section context by detecting section headers
    and prepending them to each chunk.
    """
    # Detect section headers
    section_pattern = re.compile(
        r'^([A-Z][A-Z\s]{3,})$',
        re.MULTILINE
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    raw_chunks = splitter.split_text(text)

    # Assign section labels to chunks
    chunks = []
    current_section = "Document Start"
    section_headers = set()

    # Pre-scan for section headers
    for match in section_pattern.finditer(text):
        section_headers.add(match.group(1).strip())

    for i, chunk_text in enumerate(raw_chunks):
        # Check if this chunk starts with or contains a section header
        for header in section_headers:
            if header in chunk_text:
                current_section = header.title()
                break

        chunk = Chunk(
            text=chunk_text.strip(),
            chunk_id=f"{source}_chunk_{i:03d}",
            source=source,
            section=current_section,
        )
        chunks.append(chunk)

    return chunks


# ── Embedding ──────────────────────────────────────────────────────────────

def embed_texts(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    batch_size: int = 100,
) -> List[List[float]]:
    """
    Embed a list of texts using OpenAI's embedding API.
    Handles batching for large lists.
    """
    client = openai.OpenAI()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=model,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        if len(texts) > batch_size:
            print(f"  Embedded batch {i//batch_size + 1}/"
                  f"{(len(texts) + batch_size - 1)//batch_size}")

    return all_embeddings


# ── Pinecone Vector Store ─────────────────────────────────────────────────

def init_pinecone_index(
    index_name: str = PINECONE_INDEX_NAME,
    dimension: int = EMBEDDING_DIMENSIONS,
) -> object:
    """Initialize Pinecone and create index if it doesn't exist."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    # Check if index exists
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"  Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1",
            ),
        )
        # Wait for index to be ready
        while not pc.describe_index(index_name).status["ready"]:
            print("  Waiting for index to be ready...")
            time.sleep(2)

    return pc.Index(index_name)


def upsert_chunks(
    index,
    chunks: List[Chunk],
    embeddings: List[List[float]],
    batch_size: int = 100,
) -> None:
    """Upsert chunk embeddings and metadata into Pinecone."""
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        vectors.append({
            "id": chunk.chunk_id,
            "values": embedding,
            "metadata": {
                "text": chunk.text,
                "source": chunk.source,
                "section": chunk.section,
                "char_count": chunk.char_count,
            },
        })

    # Upsert in batches
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        if len(vectors) > batch_size:
            print(f"  Upserted batch {i//batch_size + 1}/"
                  f"{(len(vectors) + batch_size - 1)//batch_size}")

    print(f"  Total vectors upserted: {len(vectors)}")


# ── Retrieval ──────────────────────────────────────────────────────────────

def retrieve_chunks(
    index,
    query: str,
    top_k: int = TOP_K,
) -> List[Dict]:
    """
    Embed the query and retrieve the top-k most similar chunks from Pinecone.
    """
    # Embed the query
    query_embedding = embed_texts([query])[0]

    # Search Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )

    # Format results
    retrieved = []
    for match in results["matches"]:
        retrieved.append({
            "chunk_id": match["id"],
            "score": match["score"],
            "text": match["metadata"]["text"],
            "section": match["metadata"].get("section", ""),
            "source": match["metadata"].get("source", ""),
        })

    return retrieved


# ── Answer Generation ──────────────────────────────────────────────────────

def generate_answer(query: str, retrieved_chunks: List[Dict]) -> str:
    """
    Generate an answer using Claude with retrieved context.
    """
    client = anthropic.Anthropic()

    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        section_label = f" (Section: {chunk['section']})" if chunk['section'] else ""
        context_parts.append(
            f"[Chunk {i}, Relevance: {chunk['score']:.3f}{section_label}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        system="""You are a helpful assistant that answers questions based on the
provided context from business documents. Follow these rules:
1. Only use information from the provided context
2. If the context doesn't contain enough information, say so explicitly
3. Cite specific numbers and facts from the context
4. Be concise but complete""",
        messages=[{
            "role": "user",
            "content": f"""Context:
{context}

Question: {query}

Answer:"""
        }],
    )

    return message.content[0].text


# ── Indexing Pipeline ──────────────────────────────────────────────────────

def run_indexing(pdf_path: Optional[str] = None) -> None:
    """
    Full indexing pipeline: extract → chunk → embed → store.
    """
    print("=" * 60)
    print("  RAG INDEXING PIPELINE")
    print("=" * 60)

    # Step 1: Extract text
    print("\n[1/4] Extracting text...")
    if pdf_path and os.path.exists(pdf_path):
        text = extract_text_from_pdf(pdf_path)
        print(f"  Extracted {len(text)} characters from PDF: {pdf_path}")
    else:
        text = ACME_MEMO_TEXT
        print(f"  Using built-in Acme memo text ({len(text)} characters)")
        if pdf_path:
            print(f"  (PDF not found at {pdf_path}, using fallback)")

    # Step 2: Chunk
    print(f"\n[2/4] Chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_document(text)
    print(f"  Generated {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"    Chunk {i}: {chunk.char_count} chars, section='{chunk.section}'")

    # Step 3: Embed
    print(f"\n[3/4] Embedding with {EMBEDDING_MODEL}...")
    chunk_texts = [c.text for c in chunks]
    embeddings = embed_texts(chunk_texts)
    print(f"  Generated {len(embeddings)} embeddings ({EMBEDDING_DIMENSIONS} dimensions each)")

    # Step 4: Store in Pinecone
    print(f"\n[4/4] Storing in Pinecone ({PINECONE_INDEX_NAME})...")
    index = init_pinecone_index()
    upsert_chunks(index, chunks, embeddings)

    print(f"\n{'='*60}")
    print("  INDEXING COMPLETE")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Index: {PINECONE_INDEX_NAME}")
    print(f"{'='*60}")


# ── Query Pipeline ─────────────────────────────────────────────────────────

def run_query(query: str, verbose: bool = True) -> str:
    """
    Full query pipeline: embed → retrieve → generate.
    """
    if verbose:
        print(f"\n{'─'*60}")
        print(f"  Query: \"{query}\"")
        print(f"{'─'*60}")

    # Connect to Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(PINECONE_INDEX_NAME)

    # Retrieve
    start = time.time()
    retrieved = retrieve_chunks(index, query)
    retrieval_time = time.time() - start

    if verbose:
        print(f"\n  Retrieved {len(retrieved)} chunks ({retrieval_time:.2f}s):")
        for i, r in enumerate(retrieved):
            print(f"    [{i+1}] score={r['score']:.4f} section='{r['section']}'")
            print(f"        {r['text'][:80]}...")

    # Generate
    start = time.time()
    answer = generate_answer(query, retrieved)
    generation_time = time.time() - start

    if verbose:
        print(f"\n  Answer ({generation_time:.2f}s):")
        print(f"    {answer}")
        print(f"\n  Total time: {retrieval_time + generation_time:.2f}s")

    return answer


# ── Test Suite ─────────────────────────────────────────────────────────────

TEST_QUERIES = [
    {
        "query": "What is Product Alpha's Q2 revenue?",
        "expected_contains": "$12.4M",
        "category": "factual_specific",
    },
    {
        "query": "What is Product Beta's churn rate?",
        "expected_contains": "4.2%",
        "category": "factual_specific",
    },
    {
        "query": "When is Product Gamma scheduled to launch?",
        "expected_contains": "September 15",
        "category": "factual_specific",
    },
    {
        "query": "What is the combined Q3 revenue target?",
        "expected_contains": "$18.6M",
        "category": "factual_specific",
    },
    {
        "query": "Who prepared this strategy memo?",
        "expected_contains": "Sarah Chen",
        "category": "factual_specific",
    },
    {
        "query": "What competitive threats does the company face?",
        "expected_contains": "Nexus Corp",
        "category": "analytical",
    },
    {
        "query": "What is the mitigation plan for Beta's churn problem?",
        "expected_contains": "customer success",
        "category": "analytical",
    },
    {
        "query": "How many design partners does Gamma have?",
        "expected_contains": "47",
        "category": "factual_specific",
    },
    {
        "query": "What is the company's annual revenue plan?",
        "expected_contains": "$68M",
        "category": "factual_inferred",
    },
    {
        "query": "What are the strategic priorities for Q3?",
        "expected_contains": "enterprise deals",
        "category": "analytical",
    },
]


def run_tests() -> None:
    """Run all test queries and evaluate results."""
    print("=" * 60)
    print("  RAG PIPELINE TEST SUITE")
    print("=" * 60)

    results = []
    pass_count = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'─'*50}")
        print(f"  Test {i}/{len(TEST_QUERIES)}: {test['category']}")
        print(f"  Q: {test['query']}")

        answer = run_query(test["query"], verbose=False)
        expected = test["expected_contains"]
        passed = expected.lower() in answer.lower()

        if passed:
            pass_count += 1

        status = "PASS" if passed else "FAIL"
        print(f"  A: {answer[:150]}...")
        print(f"  Expected to contain: \"{expected}\"")
        print(f"  Result: {status}")

        results.append({
            "query": test["query"],
            "category": test["category"],
            "expected": expected,
            "answer": answer[:200],
            "passed": passed,
        })

    # Summary
    print(f"\n{'='*60}")
    print(f"  TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Passed: {pass_count}/{len(TEST_QUERIES)} ({pass_count/len(TEST_QUERIES):.0%})")

    # By category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["pass"] += 1

    print(f"\n  By category:")
    for cat, counts in categories.items():
        pct = counts["pass"] / counts["total"]
        print(f"    {cat:<25}: {counts['pass']}/{counts['total']} ({pct:.0%})")

    # Failed tests
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n  Failed queries:")
        for r in failed:
            print(f"    - \"{r['query']}\"")
            print(f"      Expected: \"{r['expected']}\"")
            print(f"      Got: \"{r['answer'][:100]}...\"")


# ── Interactive Mode ───────────────────────────────────────────────────────

def run_interactive() -> None:
    """Interactive query mode."""
    print("=" * 60)
    print("  RAG PIPELINE — INTERACTIVE MODE")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 60)

    while True:
        print()
        query = input("  Your question: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            print("  Goodbye!")
            break
        if not query:
            continue

        answer = run_query(query)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RAG Lab 01 Pipeline")
    parser.add_argument(
        "--index",
        action="store_true",
        help="Run the indexing pipeline (extract, chunk, embed, store)",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Path to PDF file (optional, uses built-in text if not provided)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the full test suite",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive query mode",
    )

    args = parser.parse_args()

    if args.index:
        run_indexing(pdf_path=args.pdf)
    elif args.query:
        run_query(args.query)
    elif args.test:
        run_tests()
    elif args.interactive:
        run_interactive()
    else:
        parser.print_help()
        print("\n  Quick start:")
        print("    python main.py --index        # Index the Acme memo")
        print("    python main.py --test          # Run test suite")
        print("    python main.py --interactive   # Ask questions")


if __name__ == "__main__":
    main()
