"""Shared corpus loading and citation helpers for Buoi 14 retrieval."""

from __future__ import annotations

import csv
from pathlib import Path


csv.field_size_limit(10_000_000)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"


def load_corpus(path: Path = CORPUS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Corpus is empty: {path}")
    return rows


def citation(row: dict[str, str]) -> str:
    parts = [row.get("title", ""), row.get("citation_code", ""), row.get("chunk_id", "")]
    return " | ".join(part for part in parts if part) or row["chunk_id"]


def result(row: dict[str, str], score: float, method: str, rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "chunk_id": row["chunk_id"],
        "document_id": row["document_id"],
        "text": row["text"],
        "retrieval_score": float(score),
        "retrieval_method": method,
        "citation": citation(row),
    }