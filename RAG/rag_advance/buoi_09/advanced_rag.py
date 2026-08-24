"""Snapshot baseline from Buổi 08: advanced_rag.py.

This module is copied from the Buổi 08 runtime for skeleton purposes only.
It intentionally avoids importing Buổi 08 runtime modules directly and keeps
logic unchanged in this step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
STORAGE_DIR = BASE_DIR / "storage" / "chroma"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)
if ENV_EXAMPLE_PATH.exists():
    load_dotenv(ENV_EXAMPLE_PATH, override=False)


def load_runtime_config() -> dict[str, Any]:
    """Load and validate runtime configuration from the local .env file."""
    raw_values = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "").strip(),
        "GEMINI_EMBEDDING_MODEL": os.getenv("GEMINI_EMBEDDING_MODEL", "").strip(),
        "GEMINI_EMBEDDING_DIM": os.getenv("GEMINI_EMBEDDING_DIM", "768").strip(),
        "GEMINI_GENERATION_MODEL": os.getenv("GEMINI_GENERATION_MODEL", "").strip(),
        "RAG_MAX_DISTANCE": os.getenv("RAG_MAX_DISTANCE", "0.45").strip(),
        "BM25_CANDIDATES": os.getenv("BM25_CANDIDATES", "20").strip(),
        "SEMANTIC_CANDIDATES": os.getenv("SEMANTIC_CANDIDATES", "20").strip(),
        "RRF_K": os.getenv("RRF_K", "60").strip(),
    }

    if not raw_values["GEMINI_EMBEDDING_MODEL"]:
        raise ValueError("GEMINI_EMBEDDING_MODEL must be set")
    if not raw_values["GEMINI_GENERATION_MODEL"]:
        raise ValueError("GEMINI_GENERATION_MODEL must be set")

    return {
        "api_key": raw_values["GEMINI_API_KEY"],
        "embedding_model": raw_values["GEMINI_EMBEDDING_MODEL"],
        "generation_model": raw_values["GEMINI_GENERATION_MODEL"],
        "embedding_dim": int(raw_values["GEMINI_EMBEDDING_DIM"]),
        "rag_max_distance": float(raw_values["RAG_MAX_DISTANCE"]),
        "bm25_candidates": int(raw_values["BM25_CANDIDATES"]),
        "semantic_candidates": int(raw_values["SEMANTIC_CANDIDATES"]),
        "rrf_k": int(raw_values["RRF_K"]),
    }


def build_status() -> dict[str, Any]:
    """Return a read-only status payload without creating runtime resources."""
    return {
        "status": "ready",
        "storage_dir": str(STORAGE_DIR),
        "has_env_example": (BASE_DIR / ".env.example").exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Buổi 09 advanced_rag skeleton")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(build_status(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(load_runtime_config(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
