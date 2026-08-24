import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advanced_rag import rerank_candidates


class RerankTests(unittest.TestCase):
    def test_lazy_loading_and_injection(self) -> None:
        called = []

        def fake_reranker(question: str, candidates: list[dict], config: dict, model: object | None = None) -> list[dict]:
            called.append((question, len(candidates)))
            return [
                {**candidate, "rerank_raw_score": 1.0, "rerank_score": 0.88, "rerank_rank": 1, "rank_change": 0}
                for candidate in candidates
            ]

        fused_candidates = [
            {"chunk_id": "a", "fused_rank": 1, "text": "one"},
            {"chunk_id": "b", "fused_rank": 2, "text": "two"},
        ]
        result = rerank_candidates(
            question="query",
            fused_candidates=fused_candidates,
            config={"reranker_model": "demo-model", "rerank_candidates": 2, "final_top_k": 2, "reranker_max_length": 128, "rerank_batch_size": 2, "rerank_min_score": 0.0, "rerank_device": "cpu"},
            reranker_fn=fake_reranker,
        )
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(called[0][1], 2)
        self.assertIn("rerank_latency_ms", result["trace"])

    def test_sigmoid_and_tie_break(self) -> None:
        def fake_reranker(question: str, candidates: list[dict], config: dict, model: object | None = None) -> list[dict]:
            return [
                {**candidate, "rerank_raw_score": 1.0, "rerank_score": 0.88, "rerank_rank": 1, "rank_change": 0}
                for candidate in candidates
            ]

        fused_candidates = [
            {"chunk_id": "b", "fused_rank": 2, "text": "two"},
            {"chunk_id": "a", "fused_rank": 1, "text": "one"},
        ]
        result = rerank_candidates(
            question="query",
            fused_candidates=fused_candidates,
            config={"reranker_model": "demo-model", "rerank_candidates": 2, "final_top_k": 2, "reranker_max_length": 128, "rerank_batch_size": 2, "rerank_min_score": 0.0, "rerank_device": "cpu"},
            reranker_fn=fake_reranker,
        )
        self.assertEqual([item["chunk_id"] for item in result["results"]], ["a", "b"])

    def test_model_failure_returns_unavailable(self) -> None:
        def failing_reranker(question: str, candidates: list[dict], config: dict, model: object | None = None) -> list[dict]:
            raise RuntimeError("boom")

        result = rerank_candidates(
            question="query",
            fused_candidates=[{"chunk_id": "a", "fused_rank": 1, "text": "one"}],
            config={"reranker_model": "demo-model", "rerank_candidates": 1, "final_top_k": 1, "reranker_max_length": 128, "rerank_batch_size": 1, "rerank_min_score": 0.0, "rerank_device": "cpu"},
            reranker_fn=failing_reranker,
        )
        self.assertEqual(result["status"], "reranker_unavailable")
        self.assertEqual(result["results"][0]["chunk_id"], "a")


if __name__ == "__main__":
    unittest.main()
