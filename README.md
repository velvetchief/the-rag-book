# The RAG Book

**Retrieval, Agents & Multi-Agent Systems — From First Principles to Production Code**
By Prithvi Datla · Kilobyte Collective

The RAG Book is a 646-page field manual for building retrieval and agent systems that hold up in production. It's free. The whole book, all the code, three labs, and a multi-agent capstone are right here in this repo.

This page is the short version — what's inside, who it's for, and why it's built the way it is. If you just want to start running things, jump to [GETTING_STARTED.md](GETTING_STARTED.md).

## The problem it solves

Anyone can build a RAG demo in an afternoon. Embed some documents, drop them in a vector store, wire up a prompt, and it answers questions. It feels done.

Then you point it at real data and the cracks show. It retrieves the wrong passage. It answers confidently from something the source never said. Costs creep up as the index grows. The same question, asked two ways, gives two different answers. The afternoon project turns into months of work nobody planned for.

Most tutorials stop at the afternoon demo. This book is about everything after it — retrieval quality, evaluation, cost, the trade-offs between techniques, and the architecture calls that decide whether your system works on one document or on a million.

## Who it's for

This is written for Forward Deployed AI Engineers — the people who sit between customers and the codebase and have to make the thing actually ship. You don't need prior ML experience; if you can write Python, you can follow the engineering track.

Every chapter is written for two readers at once. Engineers get complete, runnable code — not pseudocode — with experiments and the production gotchas. Product leaders get decision frameworks, cost tables, and the right questions to ask, no code required. You read the same chapters either way.

## What's inside

Seventeen modules, first principles to production:

| #  | Module | The question it answers |
|----|--------|-------------------------|
| 01 | RAG Foundations | Why do language models need your documents? |
| 02 | The RAG Pipeline | What are the stages from document to answer? |
| 03 | Vector Databases & Indexing | Where do your vectors live? |
| 04 | Chunking Strategies | How do you split documents without losing meaning? |
| 05 | Embedding Models | How do you turn text into vectors that retrieve well? |
| 06 | Query Enhancement | How do you fix the question before you search? |
| 07 | Multi-Query RAG | What do you do when one query isn't enough? |
| 08 | Hybrid Search | How do you combine keyword and vector search? |
| 09 | Reranking | How do you get the right results to the top? |
| 10 | GraphRAG | How do you retrieve over a knowledge graph? |
| 11 | Multimodal RAG | What about images, tables, and charts? |
| 12 | Structured RAG | How do you handle structured and tabular data? |
| 13 | Evaluation & Observability | How do you measure quality, not just eyeball it? |
| 14 | Agent Foundations | What actually makes something an agent? |
| 15 | Multi-Agent Orchestration | How do agents work together on a task? |
| 16 | Agentic RAG | What if one retrieval pass isn't enough? |
| 17 | Security & Guardrails | How do you keep it from doing harm in production? |

Plus three appendices: a vendor swap guide (you're not locked into any one stack), a version-pinning playbook for when models change, and a catalog of production patterns.

## What makes it different

**One example, all the way through.** A single document — a made-up company's quarterly strategy memo — runs through all seventeen modules. The input never changes, so you can see exactly what each technique buys you: this chunking strategy against that one, this retriever against that one, on the same data.

**It shows you what breaks.** Every module walks through how the technique fails, on purpose — bad retrieval, stale embeddings, cost runaway, the works. Knowing what failure looks like is worth more than another happy-path demo.

**The code runs.** `pip install`, then `python script.py`. That's it. Running the whole book costs about $4–11 in API calls, and the scripts tell you the cost as they go.

**It's honest about its limits.** There's a section up front called "What Ten Days Does Not Give You." It says plainly that finishing this makes you competent, not done — that scale intuition and production scars come from real deployments, not a book. Most material oversells. This one tries to tell you the truth and show you where the map ends.

**It's built to last.** Model names and SDKs change fast. The code pins exact versions so it keeps working, and an appendix shows you how to keep your setup current. The patterns outlive the specific APIs.

## The labs and the capstone

Reading isn't building, so the repo includes four projects that put it together:

- **Lab 01** — your first RAG pipeline, from scratch
- **Lab 02** — advanced RAG: hybrid search, reranking, evaluation
- **Lab 03** — a three-agent intelligence pipeline on LangGraph
- **Capstone** — a multi-agent system that reads an RFP, pulls from past proposals, drafts a response section by section, and reviews its own work before handing it back

Each one is self-contained, with its own setup and a `verify_setup.py` to check your environment before you spend a cent on API calls.

## Getting started

1. Read the book — [`The_RAG_Book.pdf`](The_RAG_Book.pdf) is right here in the repo, or grab it from [theragbook.com](https://www.theragbook.com).
2. Clone the repo and run the code as you read.
3. Do the labs in order, then build the capstone.

Full setup — API keys, virtual environment, everything — is in [GETTING_STARTED.md](GETTING_STARTED.md).

## Why it's free

Because I'm thankful I've been able to learn this stuff, and I want to give back. There's a lot of noise out there, and a lot of expensive options to learn. Getting the book is not the gate — finishing it is. There's good stuff beyond.

## About the author

Prithvi Datla is the founder of [Dinealog](https://dinealog.com), a voice agent that answers the phone for restaurants, and Kilobyte Collective, an AI lab. This book came out of real deployments — the ones that didn't work as much as the ones that did — boiled down to what actually mattered. He holds bachelor's and master's degrees in Computer Science and Engineering and an MBA from Cornell.

[theragbook.com](https://www.theragbook.com) · [prithvidatla.com](https://prithvidatla.com)
