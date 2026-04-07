# Lab 02: Advanced RAG — Upgrading Your Pipeline

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your actual keys

export ANTHROPIC_API_KEY=your-key-here
export OPENAI_API_KEY=your-key-here
export CO_API_KEY=your-key-here

# 3. Run the lab
python main.py
```

## What This Lab Does

This lab starts from the baseline RAG pipeline (Lab 01) and adds five upgrades
one at a time, measuring the impact of each with RAGAS evaluation metrics.

**Step 0 — Baseline Pipeline**
Simple vector-search RAG using OpenAI embeddings and cosine similarity. This
is the Lab 01 output used as the comparison baseline.

**Step 1 — Multi-Query Retrieval (M07)**
Claude generates 3 alternative phrasings of each user query. Retrieval runs
for every variant; results are merged and deduplicated (highest score wins).
Expected benefit: higher context recall, especially on broad aggregation queries.

**Step 2 — Hybrid Search (M08)**
Combines dense embedding similarity with a BM25 keyword index (implemented
from scratch — no external BM25 library required). Scores are normalised to
[0, 1] then blended with a configurable `dense_weight` (default 0.7).
Expected benefit: better precision on queries containing specific names or numbers.

**Step 3 — Cohere Reranking (M09)**
After hybrid retrieval, Cohere `rerank-v3.5` reorders the candidate chunks
using a cross-encoder. The pipeline fetches 2x more candidates than needed and
lets the reranker cut them down to `top_k`.
Expected benefit: most relevant chunks rise to the top, improving answer quality.

**Step 4 — GraphRAG Comparison (M10)**
Claude extracts entities (Person, Product, Company, Metric, Risk, Date,
Strategy) and relationships from the full memo using tool use. A NetworkX
directed graph is built and queried at inference time to produce entity-
relationship context that is appended to the vector context.
Expected benefit: better answers on relationship queries (who is responsible
for what, how risks are connected, etc.).

**Step 5 — RAGAS Evaluation (M12)**
All pipeline versions are run against an 8-query golden dataset covering
factual, multi-hop, aggregation, comparison, and reasoning categories.
RAGAS scores four metrics (faithfulness, answer relevancy, context precision,
context recall) for each version. A side-by-side comparison table and a delta
table are printed, and results are saved to `lab02_results.json`.

## Prerequisites

**Lab 01 must be completed first** if you intend to reuse a Pinecone index.
This standalone version of `main.py` uses an in-memory chunk store (no
Pinecone required), so it can also run independently.

API keys required:
- `ANTHROPIC_API_KEY` — Claude generation and entity extraction
- `OPENAI_API_KEY` — text-embedding-3-small embeddings and RAGAS evaluation
- `CO_API_KEY` — Cohere rerank-v3.5 (Step 3 onwards)

Python 3.10+ recommended.

## Expected Output

A dependency check runs first, followed by each pipeline stage. The final
output is a comparison table similar to:

```
================================================================================
PIPELINE COMPARISON TABLE
================================================================================

Pipeline            Faithful  Relevancy  Precision     Recall    Latency
------------------------------------------------------------------------------
Baseline               0.850      0.800      0.700      0.650      1.50s
MultiQuery             0.840      0.820      0.720      0.780      2.50s
Hybrid                 0.850      0.830      0.780      0.800      2.60s
Reranked               0.870      0.850      0.850      0.800      2.90s
GraphAugmented         0.860      0.840      0.830      0.820      3.40s

Delta vs Baseline   Faithful  Relevancy  Precision     Recall    Latency
------------------------------------------------------------------------------
MultiQuery            -0.010     +0.020     +0.020     +0.130     +1.00s
Hybrid                +0.000     +0.030     +0.080     +0.150     +1.10s
Reranked              +0.020     +0.050     +0.150     +0.150     +1.40s
GraphAugmented        +0.010     +0.040     +0.130     +0.170     +1.90s
```

Results are also saved to `lab02_results.json` for further analysis.

Key observations:
- Context Recall improves most from Multi-Query (+0.13)
- Context Precision improves most from Reranking (+0.15)
- Faithfulness stays roughly stable across all versions
- Full stack adds ~2.3x latency over baseline
- Recommended configuration for most use cases: Baseline + Multi-Query + Reranking
