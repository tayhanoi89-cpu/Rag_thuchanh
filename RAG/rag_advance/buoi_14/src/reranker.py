"""Rerank only Hybrid candidates with a multilingual Cross-Encoder."""

from __future__ import annotations

import re
from typing import Any

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

from .hybrid_retriever import HybridRetriever


MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


_CROSS_ENCODERS: dict[str, CrossEncoder | None] = {}


def _get_cross_encoder(model_name: str) -> CrossEncoder | None:
    if model_name not in _CROSS_ENCODERS:
        try:
            _CROSS_ENCODERS[model_name] = CrossEncoder(model_name)
        except Exception:
            _CROSS_ENCODERS[model_name] = None
    return _CROSS_ENCODERS[model_name]


class CandidateReranker:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self.model_name = model_name
        self.model = _get_cross_encoder(model_name)
        self.mode = "NEURAL_CROSS_ENCODER" if self.model is not None else "FALLBACK_LEXICAL"

    @staticmethod
    def _fallback_score(question: str, text: str) -> float:
        tokens = set(re.findall(r"\w+", question.casefold()))
        text_tokens = set(re.findall(r"\w+", text.casefold()))
        return len(tokens & text_tokens) / max(len(tokens), 1)

    def rerank(self, question: str, candidates: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if self.model is not None:
            scores = self.model.predict([(question, str(candidate["text"])) for candidate in candidates])
            scored = [(candidate, float(score)) for candidate, score in zip(candidates, scores)]
        else:
            scored = [
                (candidate, self._fallback_score(question, str(candidate["text"])))
                for candidate in candidates
            ]

        ranked = sorted(scored, key=lambda item: (-item[1], item[0]["final_rank"]))[:top_k]
        results = []
        for rank, (candidate, score) in enumerate(ranked, 1):
            results.append(
                {
                    "final_rank": rank,
                    "chunk_id": candidate["chunk_id"],
                    "document_id": candidate["document_id"],
                    "hybrid_rank": candidate["final_rank"],
                    "hybrid_score": candidate["rrf_score"],
                    "rerank_score": score,
                    "text": candidate["text"],
                    "citation": candidate["citation"],
                    "retrieval_method": "hybrid_rerank" if self.model else "hybrid_rerank_fallback",
                }
            )
        return results


def retrieve_reranked(question: str, candidate_k: int = 20, top_k: int = 5) -> tuple[list[dict[str, Any]], CandidateReranker]:
    hybrid_candidates = HybridRetriever().search(question, top_k=candidate_k, candidate_k=candidate_k)
    reranker = CandidateReranker()
    return reranker.rerank(question, hybrid_candidates, top_k), reranker