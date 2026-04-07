# Lab 01: Building Your First RAG Pipeline

## Quick Start

**Step 1 — Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2 — Set up your API keys**
```bash
cp .env.example .env
# Edit .env and fill in your real API keys:
#   ANTHROPIC_API_KEY
#   OPENAI_API_KEY
#   PINECONE_API_KEY
```

**Step 3 — Run**
```bash
# Index the document (run once to populate Pinecone)
python main.py --index

# Then query it
python main.py --query "What is Product Alpha's Q2 revenue?"

# Or run the full test suite
python main.py --test

# Or ask questions interactively
python main.py --interactive
```

---

## What the Script Does

`main.py` is a complete end-to-end RAG (Retrieval-Augmented Generation) pipeline built around an Acme Corporation Q3 Strategy Memo. The pipeline has two phases:

**Indexing phase** (`--index`):
1. Extracts text from a PDF (or falls back to the built-in memo text if no PDF is provided)
2. Removes headers, footers, and page numbers; converts tables to Markdown
3. Chunks the text into 500-character segments with 75-character overlap using recursive splitting
4. Embeds each chunk with OpenAI `text-embedding-3-small` (1536 dimensions)
5. Stores the embeddings and metadata in a Pinecone serverless index (`rag-lab-01`)

**Query phase** (`--query`, `--test`, `--interactive`):
1. Embeds the user's question with the same OpenAI model
2. Searches Pinecone for the top-5 most similar chunks (cosine similarity)
3. Passes the retrieved chunks as context to Claude (`claude-sonnet-4-6-20250514`)
4. Returns Claude's grounded answer, citing only information from the retrieved chunks

---

## Expected Output

**After `--index`:**
```
============================================================
  RAG INDEXING PIPELINE
============================================================

[1/4] Extracting text...
  Using built-in Acme memo text (2847 characters)
[2/4] Chunking (size=500, overlap=75)...
  Generated 8 chunks
[3/4] Embedding with text-embedding-3-small...
  Generated 8 embeddings (1536 dimensions each)
[4/4] Storing in Pinecone (rag-lab-01)...
  Total vectors upserted: 8
============================================================
  INDEXING COMPLETE
  Chunks: 8
  Index: rag-lab-01
============================================================
```

**After `--test`:**
```
============================================================
  RAG PIPELINE TEST SUITE
============================================================
  Test 1/10: factual_specific
  Q: What is Product Alpha's Q2 revenue?
  A: Product Alpha achieved Q2 revenue of $12.4M...
  Expected to contain: "$12.4M"
  Result: PASS
  ...
  Passed: 9/10 (90%)
```

---

## Troubleshooting

**"No results found" / empty retrieval**
Run this snippet to check if the index has vectors:
```python
from pinecone import Pinecone
import os
from dotenv import load_dotenv
load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("rag-lab-01")
print(index.describe_index_stats())
# vector_count should be > 0
```
If it is 0, re-run `python main.py --index`.

**Low similarity scores (all below 0.5)**
You must use the same embedding model for both indexing and querying. Both sides use `text-embedding-3-small`. If you accidentally indexed with a different model, delete the index in the Pinecone console and re-run `--index`.

**Right chunks retrieved but wrong answer**
Add a temporary `print(context)` inside `generate_answer()` before the API call to inspect what Claude is receiving. Verify the retrieved chunks actually contain the answer.

**Pinecone index creation fails**
Verify your Pinecone API key is correct and that your plan supports serverless indexes. The free tier supports 1 index with up to 100K vectors, which is sufficient for this lab.

**Rate limit errors from OpenAI**
Reduce `batch_size` in the `embed_texts()` call or add a `time.sleep(1)` between batches. The default batch size of 100 is conservative but may still hit limits on new accounts.

**`ModuleNotFoundError`**
Make sure you ran `pip install -r requirements.txt` and that you are using the same Python environment where you installed the packages. Check with `which python` and `pip list`.
