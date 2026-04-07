# Lab 03: Multi-Agent Intelligence Pipeline

3-agent LangGraph pipeline that transforms a user question about Acme Corp into a polished executive brief, with Langfuse tracing and security guardrails throughout.

---

## Quick Start

**1. Install dependencies**

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

**2. Set environment variables**

```bash
cp .env.example .env
# Edit .env and fill in all API keys
```

**3. Run**

```bash
python main.py "What is Acme Corporation's Q3 revenue target?"
```

Or pass a question as a command-line argument:

```bash
python main.py "What are the top 5 risks identified for Q3 execution?"
```

---

## Prerequisites

- Completed Labs 01 and 02 — your Pinecone index must be populated with Acme Corp documents
- The `PINECONE_INDEX_NAME` in `.env` must match the index name created in Lab 01 (default: `acme-corp-docs`)
- Python 3.11+

---

## Architecture

The pipeline passes a single `PipelineState` object through five nodes in sequence:

```
User Question
      |
      v
INPUT GUARD       -- regex injection filter, 2000-char length cap (no LLM cost)
      |
      v
AGENT 1: RESEARCHER   -- 1 Claude call to generate 3 query variations
      |                   3 Pinecone searches, dedup, top-10 results kept
      v
AGENT 2: ANALYST      -- 1 Claude call reads all retrieved chunks
      |                   outputs structured JSON: claim / evidence / confidence / source
      v
AGENT 3: WRITER       -- 1 Claude call reads analyst insights
      |                   writes 300-400 word executive brief with citations
      v
OUTPUT GUARD      -- Presidio PII redaction, $0.50 cost cap check
      |
      v
  Executive Brief
```

**State fields passed through the pipeline:**

| Field | Type | Description |
|---|---|---|
| `question` | str | Original user question |
| `sanitized_question` | str | After input guard |
| `research_queries` | list[str] | 3 query variations from Researcher |
| `research_results` | list[dict] | Pinecone search results |
| `insights` | list[dict] | Structured insights from Analyst |
| `brief` | str | Executive brief from Writer |
| `metadata` | dict | Per-agent costs, latencies, token counts |
| `errors` | list[str] | Warnings and errors accumulated |
| `trace_id` | str | Langfuse trace ID |

**Technology stack:**

| Component | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Claude claude-sonnet-4-6-20250514 |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | Pinecone |
| Observability | Langfuse |
| PII Redaction | Microsoft Presidio |

---

## What You Will See in Langfuse

Open Langfuse at your `LANGFUSE_HOST` and find the trace named `acme-pipeline-{timestamp}`. Each pipeline run produces:

- **Span: `input-guard`** — duration ~10ms, cost $0.00, shows original vs. sanitized question and filter count
- **Generation: `researcher`** — shows the 3 queries generated and total unique chunks retrieved; logs input/output token counts
- **Generation: `analyst`** — shows insight count and confidence distribution (HIGH / MEDIUM / LOW breakdown)
- **Generation: `writer`** — shows word count of the produced brief
- **Span: `output-guard`** — shows PII entity count, total pipeline cost, total latency, and whether the cost guard triggered

The trace URL is printed to stdout at the end of each run:

```
View trace: https://cloud.langfuse.com/trace/lab03-20250915-143022
```

Key metrics to review in Langfuse:

| Metric | Target |
|---|---|
| Total latency | < 12 seconds |
| Total cost | < $0.05 per query |
| PII entities in output | 0 |
| Error count | 0 on standard queries |

---

## 5 Test Queries

| # | Query | What It Tests |
|---|---|---|
| 1 | `"What is Acme Corporation's Q3 revenue target and how does it compare to Q2?"` | Multi-fact retrieval, numerical comparison |
| 2 | `"Describe Product Alpha's competitive position against Dataview"` | Competitive analysis, specific competitor |
| 3 | `"What are the top 5 risks identified for Q3 execution?"` | List extraction, risk enumeration |
| 4 | `"When does Product Gamma launch and what are the key milestones?"` | Date extraction, timeline reconstruction |
| 5 | `"Compare the financial performance of Product Alpha ($12.4M Q2) versus Product Beta ($3.8M Q2)"` | Cross-product comparison, numerical accuracy |

---

## Expected Output Format

For query 1 you will see output structured like this:

```
============================================================
  MULTI-AGENT INTELLIGENCE PIPELINE
  Trace ID: lab03-20250915-143022
============================================================

  Question: What is Acme Corporation's Q3 revenue target and how does it compare to Q2?

  [1/4] Running Input Guard...
  [2/4] Researcher complete.
  [3/4] Analyst complete.
  [4/4] Writer complete.

============================================================
  EXECUTIVE BRIEF
============================================================

Acme Corporation has set a Q3 revenue target of $18.6 million, representing
a significant increase from the $12.4 million achieved by Product Alpha
alone in Q2. This target reflects confidence in the combined performance
of the company's three product lines.

Product Alpha remains the primary revenue driver with $48.2 million in
annual recurring revenue (ARR) and strong Q2 performance of $12.4 million.
The product's competitive position against Dataview continues to
strengthen, though specific competitive dynamics require monitoring.

Product Beta contributed $3.8 million in Q2 revenue with a churn rate of
4.2%, which the strategy memo identifies as an area for improvement.
Reducing churn in Beta is likely critical to achieving the aggregate Q3
target.

Product Gamma, currently in private beta with a September 15 launch date,
represents upside potential but also execution risk for Q3. The timing of
the launch means Gamma revenue contribution to Q3 will be limited to the
final weeks of the quarter.

The $18.6 million target implies roughly 50% growth over Q2's combined
product revenue, an ambitious goal that depends on Alpha maintaining
momentum, Beta reducing churn, and Gamma launching on schedule. According
to the strategy memo, five specific risks have been identified that could
impact this target.

Note: The specific details of the five Q3 risks were not fully captured
in the retrieved documents. This finding should be verified against the
complete Q3 strategy memo.

============================================================
  PIPELINE METRICS
============================================================
  Total cost:    $0.0299
  Total latency: 8.35s
  Researcher:    $0.0089 (2.34s)
  Analyst:       $0.0118 (3.12s)
  Writer:        $0.0092 (2.89s)

  View trace: https://cloud.langfuse.com/trace/lab03-20250915-143022
============================================================
```

The brief section will vary based on what your Pinecone index contains. The metrics section reflects real per-agent cost and latency breakdowns.
