import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advanced_rag import (
    get_chroma_client,
    hybrid_search,
    prepare_semantic_collection,
    _safe_collection_name,
)


class HybridTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 4,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "rrf_k": 60,
            "rrf_bm25_weight": 1.0,
            "rrf_semantic_weight": 1.0,
            "bm25_candidates": 3,
            "semantic_candidates": 3,
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

    def _temp_client_path(self) -> Path:
        temp_root = Path(__file__).resolve().parent / "tmp_chroma"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="hybrid-test-", dir=str(temp_root)))
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return temp_dir

    def test_rrf_formula_and_trace_counts(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )

        result = hybrid_search(
            question="cơ cấu lại thời hạn trả nợ",
            candidate_k=5,
            strategy="hierarchical",
            chunks=self.chunks,
            client=client,
            config=self.config,
            embedding_provider=self._embedding_provider,
        )

        self.assertEqual(result["trace"]["bm25_candidate_count"], 3)
        self.assertEqual(result["trace"]["semantic_candidate_count"], 3)
        self.assertEqual(result["trace"]["union_count"], 3)
        self.assertEqual(result["trace"]["overlap_count"], 3)
        self.assertEqual(result["trace"]["fused_count"], 3)
        self.assertEqual(result["results"][0]["chunk_id"], "chunk-01")
        self.assertEqual(result["results"][0]["matched_by"], ["bm25", "semantic"])

    def test_single_branch_candidates_still_appear(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )

        result = hybrid_search(
            question="điều chỉnh kỳ hạn trả nợ",
            candidate_k=5,
            strategy="hierarchical",
            chunks=self.chunks,
            client=client,
            config=self.config,
            embedding_provider=self._embedding_provider,
        )
        chunk_ids = [item["chunk_id"] for item in result["results"]]
        self.assertIn("chunk-01", chunk_ids)
        self.assertIn("chunk-02", chunk_ids)
        self.assertIn("chunk-03", chunk_ids)

    def test_weight_zero_removes_branch_contribution(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )

        result = hybrid_search(
            question="cơ cấu lại thời hạn trả nợ",
            candidate_k=5,
            strategy="hierarchical",
            chunks=self.chunks,
            client=client,
            config=self.config,
            embedding_provider=self._embedding_provider,
            bm25_weight=0.0,
            semantic_weight=1.0,
        )
        first = result["results"][0]
        self.assertEqual(first["chunk_id"], "chunk-01")
        self.assertEqual(first["matched_by"], ["semantic"])

    def test_metadata_mismatch_fails(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        collection_name = _safe_collection_name("hierarchical", self.config)
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "strategy": "hierarchical",
                "embedding_model": "gemini-embedding-2",
                "embedding_dim": 4,
                "distance_metric": "cosine",
                "schema_version": "1",
            },
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
        collection.upsert(
            ids=["chunk-01"],
            documents=["cơ cấu lại thời hạn trả nợ"],
            embeddings=[[1.0, 0.0, 0.0, 0.0]],
            metadatas=[{"chunk_id": "chunk-01", "source": "different", "page_start": 1, "page_end": 2, "strategy": "hierarchical"}],
        )

        with self.assertRaisesRegex(ValueError, "mismatch"):
            hybrid_search(
                question="cơ cấu lại thời hạn trả nợ",
                candidate_k=3,
                strategy="hierarchical",
                chunks=self.chunks,
                client=client,
                config=self.config,
                embedding_provider=self._embedding_provider,
            )

    def test_hybrid_calls_each_retriever_once(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )

        with patch("advanced_rag.search_bm25", return_value=[{"chunk_id": "chunk-01", "bm25_rank": 1, "bm25_score": 1.0, "text": "x", "source": "s", "page_start": 1, "page_end": 2}]) as bm25_mock, patch("advanced_rag.semantic_search", return_value=[{"chunk_id": "chunk-02", "semantic_rank": 1, "semantic_distance": 0.2, "text": "y", "source": "s", "page_start": 1, "page_end": 2}]) as semantic_mock:
            hybrid_search(
                question="test",
                candidate_k=3,
                strategy="hierarchical",
                chunks=self.chunks,
                client=client,
                config=self.config,
                embedding_provider=self._embedding_provider,
            )
            bm25_mock.assert_called_once()
            semantic_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
