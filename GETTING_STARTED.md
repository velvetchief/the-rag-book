# Getting Started — The RAG Book

**Retrieval, Agents & Multi-Agent Systems: From First Principles to Production Code**

By Prithvi Datla | Kilobyte Collective | First Edition, April 2026

New here? Start with the [overview](README.md). This file is the setup and quick-start guide.

---

## What's in This Repo

This repository contains the full book PDF plus all runnable code, lab starters, sample datasets, and configuration templates from The RAG Book. **The book is free** — read it, run the code, build something.

```
the-rag-book/
├── README.md          Overview of the book (what it covers and why)
├── GETTING_STARTED.md This guide — setup and quick start
├── The_RAG_Book.pdf   The complete 646-page book (PDF)
├── lab_01/            Lab 01: Build Your First RAG Pipeline
├── lab_02/            Lab 02: Advanced RAG (multi-query, hybrid, reranking)
├── lab_03/            Lab 03: Multi-Agent Intelligence Pipeline
├── capstone/          Capstone: RFP/SOW Response Generator
├── datasets/          Acme Corp Q3 Strategy Memo + sample data
├── requirements.txt   Root dependencies (all labs)
├── .env.example       API key template
└── verify_setup.py    Environment verification script
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/velvetchief/the-rag-book.git
cd the-rag-book

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API keys
cp .env.example .env
# Edit .env with your actual API keys

# 5. Verify setup
python verify_setup.py
```

## API Keys Required

| Provider  | Variable             | Sign Up                    | Free Tier |
|-----------|---------------------|----------------------------|-----------|
| Anthropic | `ANTHROPIC_API_KEY` | console.anthropic.com      | Yes ($5)  |
| OpenAI    | `OPENAI_API_KEY`    | platform.openai.com        | Yes ($5)  |
| Pinecone  | `PINECONE_API_KEY`  | app.pinecone.io            | Yes       |
| Cohere    | `COHERE_API_KEY`    | dashboard.cohere.com       | Yes       |

Optional (for Lab 03+ observability): Langfuse keys. See `.env.example`.

## Model Versions

All code uses `claude-sonnet-4-6-20250514` as the model string. This is the latest Claude Sonnet snapshot at the time of writing. **Replace with the current model version when running code.** See [Appendix B](https://theragbook.com) in the book for version pinning best practices.

## Vendor Alternatives

The book's labs use Anthropic + Pinecone + Cohere + OpenAI embeddings. See Appendix A in the book for swap guides:
- **Vector DB**: pgvector, Weaviate, Qdrant, Milvus
- **Embeddings**: Cohere, Voyage AI, local models (Ollama)
- **Reranking**: Jina, local cross-encoders
- **LLM**: Any provider with tool-use support

## First-Edition Snapshot

This is a first-edition snapshot (April 2026). The code is pinned to the libraries and model IDs documented in Appendix B; the architectural patterns persist across model versions even as specific model IDs and SDK surfaces evolve. There is no scheduled update cycle — when you swap to a newer model, follow the version-pinning guidance in Appendix B.

## License

This repository accompanies The RAG Book (First Edition, April 2026). The book and code are free for personal and educational use. Please do not redistribute or resell.

Copyright 2026 Prithvi Datla. All rights reserved.
