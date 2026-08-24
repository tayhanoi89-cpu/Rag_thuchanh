"""Unified retrieval API for the Buoi 14 pipeline."""

from __future__ import annotations

from typing import Any

from .bm25_retriever import BM25Retriever
from .corpus import load_corpus
from .dense_retriever import DenseRetriever
from .hybrid_retriever import HybridRetriever
from .reranker import CandidateReranker


def _standard_result(row: dict[str, Any], method: str, score: float) -> dict[str, Any]:
    return {
        "rank": row.get("final_rank", row.get("rank")),
        "chunk_id": row["chunk_id"],
        "document_id": row["document_id"],
        "text": row["text"],
        "score": float(score),
        "citation": row["citation"],
        "retrieval_method": method,
    }


def retrieve(question: str, method: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Retrieve top-k results using one of the supported methods."""
    rows = load_corpus()
    if method == "bm25":
        retriever = BM25Retriever(rows)
        return [_standard_result(row, method, row["retrieval_score"]) for row in retriever.search(question, top_k)]
    if method == "dense":
        retriever = DenseRetriever(rows)
        return [_standard_result(row, method, row["retrieval_score"]) for row in retriever.search(question, top_k)]
    if method == "hybrid":
        retriever = HybridRetriever(rows)
        results = retriever.search(question, top_k=top_k, candidate_k=max(top_k, 20))
        return [_standard_result(row, method, row["rrf_score"]) for row in results]
    if method == "hybrid_rerank":
        hybrid = HybridRetriever(rows)
        candidates = hybrid.search(question, top_k=max(top_k, 20), candidate_k=max(top_k, 20))
        reranker = CandidateReranker()
        results = reranker.rerank(question, candidates, top_k)
        output = []
        for row in results:
            item = _standard_result(row, method, row["rerank_score"])
            item["hybrid_score"] = row["hybrid_score"]
            item["rerank_score"] = row["rerank_score"]
            item["hybrid_rank"] = row["hybrid_rank"]
            output.append(item)
        return output
    raise ValueError(f"Unsupported retrieval method: {method}")