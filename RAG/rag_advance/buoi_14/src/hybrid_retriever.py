"""Hybrid BM25+dense retrieval using Reciprocal Rank Fusion."""

from __future__ import annotations

from typing import Any

from .bm25_retriever import BM25Retriever
from .corpus import load_corpus
from .dense_retriever import DenseRetriever


DEFAULT_RRF_K = 60


class HybridRetriever:
    def __init__(self, rows: list[dict[str, str]] | None = None, rrf_k: int = DEFAULT_RRF_K) -> None:
        self.rows = rows or load_corpus()
        self.rrf_k = rrf_k
        self.bm25 = BM25Retriever(self.rows)
        self.dense = DenseRetriever(self.rows)

    def search(self, question: str, top_k: int = 5, candidate_k: int = 20) -> list[dict[str, Any]]:
        bm25_results = self.bm25.search(question, candidate_k)
        dense_results = self.dense.search(question, candidate_k)
        by_chunk = {row["chunk_id"]: row for row in self.rows}
        merged: dict[str, dict[str, Any]] = {}

        for result in bm25_results:
            item = merged.setdefault(result["chunk_id"], {"row": by_chunk[result["chunk_id"]]})
            item["bm25_rank"] = result["rank"]
            item["rrf_score"] = item.get("rrf_score", 0.0) + 1.0 / (self.rrf_k + result["rank"])

        for result in dense_results:
            item = merged.setdefault(result["chunk_id"], {"row": by_chunk[result["chunk_id"]]})
            item["dense_rank"] = result["rank"]
            item["rrf_score"] = item.get("rrf_score", 0.0) + 1.0 / (self.rrf_k + result["rank"])

        ranked = sorted(
            merged.values(),
            key=lambda item: (-float(item["rrf_score"]), item["row"]["chunk_id"]),
        )[:top_k]
        results: list[dict[str, Any]] = []
        for rank, item in enumerate(ranked, 1):
            row = item["row"]
            results.append(
                {
                    "final_rank": rank,
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "bm25_rank": item.get("bm25_rank"),
                    "dense_rank": item.get("dense_rank"),
                    "rrf_score": float(item["rrf_score"]),
                    "text": row["text"],
                    "citation": " | ".join(
                        part for part in (row.get("title", ""), row.get("citation_code", ""), row["chunk_id"])
                        if part
                    ),
                    "retrieval_method": "hybrid_rrf",
                }
            )
        return results