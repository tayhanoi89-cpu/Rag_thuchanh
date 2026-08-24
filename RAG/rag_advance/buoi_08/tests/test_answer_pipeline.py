import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advanced_rag import answer_question, compare_retrieval_modes


class AnswerPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 4,
            "reranker_model": "demo-model",
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "bm25_candidates": 3,
            "semantic_candidates": 3,
            "rerank_candidates": 3,
            "final_top_k": 2,
            "reranker_max_length": 128,
            "rerank_batch_size": 2,
            "rerank_min_score": 0.5,
            "rerank_device": "cpu",
            "rag_max_distance": 0.45,
        }
        self.chunks = [
            {
                "chunk_id": "chunk-01",
                "strategy": "hierarchical",
                "source": "source-a",
                "page_start": 1,
                "page_end": 2,
                "text": "cơ cấu lại thời hạn trả nợ cho khách hàng khó khăn",
            },
            {
                "chunk_id": "chunk-02",
                "strategy": "hierarchical",
                "source": "source-b",
                "page_start": 3,
                "page_end": 4,
                "text": "điều chỉnh kỳ hạn trả nợ theo thỏa thuận với ngân hàng",
            },
            {
                "chunk_id": "chunk-03",
                "strategy": "hierarchical",
                "source": "source-c",
                "page_start": 5,
                "page_end": 6,
                "text": "đây là đoạn ngoài phạm vi không liên quan",
            },
        ]

    def _embedding_provider(self, text: str, config: dict) -> list[float]:
        lowered = text.lower()
        if "cơ cấu lại thời hạn trả nợ" in lowered or "thời hạn trả nợ" in lowered:
            return [1.0, 0.0, 0.0, 0.0]
        if "điều chỉnh kỳ hạn" in lowered or "thỏa thuận" in lowered or "kỳ hạn" in lowered:
            return [0.5, 1.0, 0.0, 0.0]
        return [0.0, 0.0, 1.0, 0.0]

    def test_query_uses_generation_once_and_rejects_non_accepted_evidence(self) -> None:
        calls = []

        def fake_generation(prompt: str, config: dict) -> str:
            calls.append(prompt)
            return "[E1]"

        def fake_reranker(question: str, candidates: list[dict], config: dict, model: object | None = None) -> list[dict]:
            return [
                {
                    **candidate,
                    "rerank_raw_score": 0.8,
                    "rerank_score": 0.8,
                    "rerank_rank": 1,
                    "rank_change": 0,
                }
                for candidate in candidates
            ]

        result = answer_question(
            question="cơ cấu lại thời hạn trả nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            embedding_provider=self._embedding_provider,
            generation_fn=fake_generation,
            reranker_fn=fake_reranker,
        )

        self.assertEqual(result["status"], "answered")
        self.assertEqual(len(calls), 1)
        self.assertTrue(any("[E1]" in result["answer"] for _ in [0]))
        self.assertEqual(result["trace"]["generation_called"], True)
        self.assertTrue(all(item["accepted"] is True or item["accepted"] is False for item in result["evidence"]))
        self.assertTrue(any(item["accepted"] for item in result["evidence"]))

    def test_compare_does_not_call_generation(self) -> None:
        calls = []

        def fake_generation(prompt: str, config: dict) -> str:
            calls.append(prompt)
            return "[E1]"

        result = compare_retrieval_modes(
            question="cơ cấu lại thời hạn trả nợ",
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            embedding_provider=self._embedding_provider,
            generation_fn=fake_generation,
        )

        self.assertEqual(calls, [])
        self.assertEqual(result["mode_results"]["bm25"]["mode"], "bm25")
        self.assertIn("latency_ms", result["mode_results"]["bm25"]["trace"])

    def test_reranker_unavailable_returns_schema(self) -> None:
        def failing_reranker(question: str, candidates: list[dict], config: dict, model: object | None = None) -> list[dict]:
            raise RuntimeError("boom")

        result = answer_question(
            question="cơ cấu lại thời hạn trả nợ",
            mode="hybrid_rerank",
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            embedding_provider=self._embedding_provider,
            generation_fn=None,
            reranker_fn=failing_reranker,
        )

        self.assertEqual(result["status"], "reranker_unavailable")
        self.assertEqual(result["mode"], "hybrid_rerank")
        self.assertIn("warnings", result)
        self.assertEqual(result["trace"]["generation_called"], False)


if __name__ == "__main__":
    unittest.main()
