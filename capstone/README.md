# Capstone: RFP/SOW Response Generator

A production-grade multi-agent pipeline that reads an incoming RFP document,
searches past proposals and company knowledge, generates a tailored proposal
response section by section, and self-reviews its own output with automated
revision loops.

---

## What This Builds

Acme Corporation receives an RFP from **Meridian Healthcare Systems**
(RFP-2024-MH-0847) asking for an AI-powered analytics platform enhancement.
The pipeline generates a complete formal proposal response covering all five
required sections, grounded in real past proposals and company knowledge,
without fabricating capabilities or case studies.

The scenario: Meridian is an existing $1.2M ACV customer operating 14 hospitals
and 52 clinics across the Midwest. Their RFP targets clinical decision support,
operational analytics, and patient outcome analytics — budget range $800K–$1.2M.

---

## Quick Start

```bash
# 1. Copy and fill in your credentials
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the spaCy model required by Presidio
python -m spacy download en_core_web_lg

# 4. Ingest past proposals and company knowledge into Pinecone (run once)
python main.py --ingest

# 5. Run the pipeline on the sample Meridian RFP
python main.py
```

---

## Architecture

The pipeline is a 4-agent LangGraph graph with a conditional revision loop.

```
Input Guard
    |
    v
Agent 1: RFP Analyzer          (1 Claude call)
    |   Reads the full RFP, extracts structured requirements,
    |   identifies the 5 sections needed, scores complexity 1-10.
    v
Agent 2: Knowledge Retriever   (0 Claude calls — retrieval only)
    |   For each section, routes queries to the correct Pinecone
    |   namespace (past-proposals or company-knowledge), performs
    |   iterative refinement if fewer than 3 high-relevance hits.
    v
Agent 3: Response Drafter      (1 Claude call per section = 5 calls)
    |   Generates each section grounded in retrieved context.
    |   On revision cycles, only redrafts sections that failed review.
    v
Agent 4: Quality Reviewer      (1 Claude call per section = 5 calls)
    |   Scores each section on relevance, completeness, accuracy (0-10).
    |   Provides actionable feedback for any section scoring below 7.
    v
Conditional edge: should_revise?
    |-- score < 7 AND cycles < 2 --> increment_revision --> Response Drafter
    |-- all pass OR max cycles   --> Output Guard
                                          |
                                          v
                                    Output Guard
                                    PII redaction (Presidio)
                                    Cost summary
                                    Langfuse flush
```

**Revision loop:** The Quality Reviewer triggers re-drafting of failing
sections up to 2 times. The `increment_revision` node exists as a dedicated
LangGraph node because state mutation requires a node, not just an edge.

**Security layer:**
- Input Guard: injection pattern filtering, length truncation at 50K chars,
  structural RFP validation
- Per-section cost guard: hard cap at $2.00 per RFP run
- Output Guard: Presidio PII scan (phone, email, SSN, passport, IBAN)
  with selective redaction — PERSON names are preserved since proposals
  legitimately reference team members

**Langfuse tracing:** Every agent emits a generation or span to a shared
trace keyed on `capstone-YYYYMMDD-HHMMSS`. Token counts, latency, and
scores are logged per agent and per section.

---

## Prerequisites

1. **Pinecone index populated** — run `python main.py --ingest` first.
   This embeds 3 past proposals and 4 company knowledge documents into
   two namespaces: `past-proposals` and `company-knowledge`.
   The index must use 1536-dimensional vectors (OpenAI `text-embedding-3-small`).

2. **API keys** — set in `.env`:
   - `ANTHROPIC_API_KEY` — Claude Sonnet (claude-sonnet-4-6-20250514)
   - `OPENAI_API_KEY` — embeddings (text-embedding-3-small)
   - `PINECONE_API_KEY` + `PINECONE_INDEX_NAME`
   - `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` + `LANGFUSE_HOST`

3. **spaCy model** — `python -m spacy download en_core_web_lg` (required
   by Presidio for NER-based PII detection)

---

## Expected Output

The pipeline generates a formatted proposal document with five sections:

| Section | RFP Evaluation Weight |
|---|---|
| Technical Approach | 30% |
| Healthcare Experience | 25% |
| Team Qualifications | 15% |
| Timeline | 15% |
| Cost and Value | 15% |

Each section is followed by its quality scores (relevance / completeness /
accuracy, each 0-10). Sections that pass all three dimensions at 7+ are
marked PASS; others are marked NEEDS REVIEW.

Sample metrics line from a typical run:

```
Total cost:             $0.4823
Cost utilization:       24.1%
Revision cycles:        1
PII entities redacted:  0
Sections generated:     5

Quality Scores:
  Technical Approach             avg: 8.3/10  [PASS]
  Healthcare Experience          avg: 8.3/10  [PASS]
  Team Qualifications            avg: 7.7/10  [PASS]
  Timeline                       avg: 7.3/10  [PASS]
  Cost and Value                 avg: 7.0/10  [PASS]
```

---

## Cost Estimate Per Run

| Component | Calls | Approx Cost |
|---|---|---|
| RFP Analyzer | 1 | ~$0.02 |
| Knowledge Retriever | 0 (no LLM) | $0.00 |
| Response Drafter (cycle 0) | 5 | ~$0.18 |
| Quality Reviewer (cycle 0) | 5 | ~$0.09 |
| Response Drafter (cycle 1, if triggered) | 1-5 | ~$0.04–$0.18 |
| Quality Reviewer (cycle 1, if triggered) | 1-5 | ~$0.02–$0.09 |
| **Total (typical)** | | **$0.35–$0.60** |

Hard cap: $2.00 per run (`MAX_COST_PER_RFP`). Sections are skipped with
a `[COST LIMIT REACHED]` placeholder if the cap is hit mid-pipeline.

At $0.50 average per response vs. ~$15,000 in manual labor (120 person-hours
at $125/hour loaded rate), the API cost is approximately 0.003% of the
manual process cost.

---

## Files

```
capstone/
  main.py                      Full pipeline (Steps A-L assembled)
  requirements.txt             Python dependencies
  .env.example                 Environment variable template
  sample_rfp.md                Meridian Healthcare RFP document
  sample_proposals/
    proposal_01.md             Midwest Health Network (healthcare)
    proposal_02.md             Statewide Insurance Group (insurance)
    proposal_03.md             Regional Medical Center (healthcare)
  README.md                    This file
```
