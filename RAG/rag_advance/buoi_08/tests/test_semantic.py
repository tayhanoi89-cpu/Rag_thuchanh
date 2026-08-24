import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advanced_rag import (
    build_status,
    get_chroma_client,
    prepare_semantic_collection,
    semantic_search,
    _safe_collection_name,
)


class SemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "has_api_key": True,
            "embedding_model": "gemini-embedding-2",
            "embedding_dim": 4,
            "reranker_model": "BAAI/bge-reranker-v2-m3",
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

    def _temp_client_path(self) -> Path:
        temp_root = Path(__file__).resolve().parent / "tmp_chroma"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="semantic-test-", dir=str(temp_root)))
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return temp_dir

    def _embedding_provider(self, text: str, config: dict) -> list[float]:
        lowered = text.lower()
        if "cơ cấu lại thời hạn trả nợ" in lowered or "thời hạn trả nợ" in lowered or "thời hạn" in lowered:
            return [1.0, 0.0, 0.0, 0.0]
        if "điều chỉnh kỳ hạn" in lowered or "thỏa thuận" in lowered or "kỳ hạn" in lowered:
            return [0.5, 1.0, 0.0, 0.0]
        return [0.0, 0.0, 1.0, 0.0]

    def test_semantic_top_k_count_and_order(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )
        results = semantic_search(
            question="cơ cấu lại thời hạn trả nợ",
            candidate_k=2,
            strategy="hierarchical",
            client=client,
            config=self.config,
            embedding_provider=self._embedding_provider,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual([item["chunk_id"] for item in results], ["chunk-01", "chunk-02"])

    def test_semantic_results_include_metadata_and_ranking(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        prepare_semantic_collection(
            strategy="hierarchical",
            chunks=self.chunks,
            config=self.config,
            client=client,
            embedding_provider=self._embedding_provider,
        )
        results = semantic_search(
            question="thời hạn trả nợ",
            candidate_k=2,
            strategy="hierarchical",
            client=client,
            config=self.config,
            embedding_provider=self._embedding_provider,
        )
        first = results[0]
        self.assertEqual(first["chunk_id"], "chunk-01")
        self.assertEqual(first["source"], "source-a")
        self.assertEqual(first["page_start"], 1)
        self.assertEqual(first["page_end"], 2)
        self.assertEqual(first["semantic_rank"], 1)
        self.assertGreaterEqual(first["semantic_distance"], 0.0)

    def test_collection_mismatch_is_rejected(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        collection_name = _safe_collection_name("hierarchical", self.config)
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "strategy": "fixed-size",
                "embedding_model": "other-model",
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
            metadatas=[{"chunk_id": "chunk-01", "source": "s", "page_start": 1, "page_end": 2, "strategy": "fixed-size"}],
        )
        with self.assertRaisesRegex(ValueError, "mismatch"):
            semantic_search(
                question="thời hạn trả nợ",
                candidate_k=1,
                strategy="hierarchical",
                client=client,
                config=self.config,
                embedding_provider=self._embedding_provider,
            )

    def test_status_does_not_create_collection(self) -> None:
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        status = build_status(strategy="hierarchical", client=client, config=self.config)
        self.assertFalse(status["collection_exists"])
        self.assertEqual(status["collection_count"], 0)
        self.assertFalse(status["reranker_cache_exists"])

    def test_missing_api_key_does_not_use_fake_vectors(self) -> None:
        config = dict(self.config)
        config["has_api_key"] = False
        temp_dir = self._temp_client_path()
        client = get_chroma_client(temp_dir)
        with self.assertRaisesRegex(ValueError, "API key"):
            prepare_semantic_collection(
                strategy="hierarchical",
                chunks=self.chunks,
                config=config,
                client=client,
                embedding_provider=self._embedding_provider,
            )


if __name__ == "__main__":
    unittest.main()
