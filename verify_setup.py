#!/usr/bin/env python3
"""
The RAG Book — Environment Verification Script
Run this before starting any lab to verify all dependencies are installed.

Usage: python verify_setup.py
"""

import sys
import os


def check_python():
    v = sys.version_info
    print(f"Python version: {v.major}.{v.minor}.{v.micro}")
    if v >= (3, 11):
        print("  [PASS] Python 3.11+")
    else:
        print("  [FAIL] Python 3.11+ required")
        return False
    return True


def check_packages():
    required = {
        "anthropic": "Anthropic Claude API",
        "openai": "OpenAI Embeddings",
        "pinecone": "Pinecone Vector DB",
        "cohere": "Cohere Reranking",
        "langchain": "LangChain Orchestration",
        "langgraph": "LangGraph Agents",
        "ragas": "RAGAS Evaluation",
        "langfuse": "Langfuse Observability",
        "dotenv": "Environment Variables (python-dotenv)",
    }

    all_ok = True
    for pkg, desc in required.items():
        try:
            __import__(pkg)
            print(f"  [PASS] {desc} ({pkg})")
        except ImportError:
            print(f"  [FAIL] {desc} ({pkg}) — run: pip install -r requirements.txt")
            all_ok = False
    return all_ok


def check_api_keys():
    from dotenv import load_dotenv
    load_dotenv()

    keys = {
        "ANTHROPIC_API_KEY": "Anthropic (Claude)",
        "OPENAI_API_KEY": "OpenAI (Embeddings)",
        "PINECONE_API_KEY": "Pinecone (Vector DB)",
        "COHERE_API_KEY": "Cohere (Reranking)",
    }

    optional_keys = {
        "LANGFUSE_PUBLIC_KEY": "Langfuse (Observability)",
        "LANGFUSE_SECRET_KEY": "Langfuse (Observability)",
    }

    all_ok = True
    for key, desc in keys.items():
        val = os.environ.get(key, "")
        if val and len(val) > 5:
            print(f"  [PASS] {key} ({desc})")
        else:
            print(f"  [FAIL] {key} ({desc}) — add to .env file")
            all_ok = False

    for key, desc in optional_keys.items():
        val = os.environ.get(key, "")
        if val and len(val) > 5:
            print(f"  [PASS] {key} ({desc})")
        else:
            print(f"  [SKIP] {key} ({desc}) — optional, needed for Lab 03+")

    return all_ok


if __name__ == "__main__":
    print("=" * 60)
    print("The RAG Book — Environment Verification")
    print("=" * 60)

    print("\n1. Python Version")
    py_ok = check_python()

    print("\n2. Required Packages")
    pkg_ok = check_packages()

    print("\n3. API Keys (.env)")
    if pkg_ok:
        key_ok = check_api_keys()
    else:
        print("  [SKIP] Install packages first")
        key_ok = False

    print("\n" + "=" * 60)
    if py_ok and pkg_ok and key_ok:
        print("ALL CHECKS PASSED — You are ready for Day 1!")
    else:
        print("SOME CHECKS FAILED — Fix the issues above before starting.")
    print("=" * 60)
