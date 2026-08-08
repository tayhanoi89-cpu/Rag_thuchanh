import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import rag


class FakeCollection:
    def __init__(self, documents, metadatas, distances, metadata):
        self._documents = documents
        self._metadatas = metadatas
        self._distances = distances
        self.metadata = metadata
        self._embedding_function = None

    def count(self):
        return len(self._documents)

    def query(self, query_embeddings, n_results):
        return {
            "documents": [self._documents[:n_results]],
            "metadatas": [self._metadatas[:n_results]],
            "distances": [self._distances[:n_results]],
        }


class FakeClient:
    def __init__(self, collection):
        self._collection = collection

    def get_collection(self, name, embedding_function=None):
        return self._collection


class AskQuestionTests(unittest.TestCase):
    def setUp(self):
        self.base_config = {
            "api_key": "fake-key",
            "has_api_key": True,
            "embedding_model": "fake-embedding-model",
            "generation_model": "fake-generation-model",
            "embedding_dim": 3,
            "default_top_k": 5,
            "rag_max_distance": 0.5,
        }

    def _build_collection(self, documents, metadatas, distances):
        metadata = {
            "strategy": "hierarchical",
            "embedding_model": "fake-embedding-model",
            "embedding_dim": 3,
            "distance_metric": "cosine",
            "cosine_distance": "cosine",
            "schema_version": "1",
        }
        return FakeCollection(documents, metadatas, distances, metadata)

    def test_answered_status_maps_citations_and_uses_accepted_evidence_only(self):
        collection = self._build_collection(
            documents=[
                "Đây là chunk 1",
                "Đây là chunk 2",
            ],
            metadatas=[
                {
                    "source": "doc-1",
                    "page_start": 1,
                    "page_end": 2,
                    "chunk_id": "chunk-1",
                },
                {
                    "source": "doc-2",
                    "page_start": 3,
                    "page_end": 3,
                    "chunk_id": "chunk-2",
                },
            ],
            distances=[0.1, 0.9],
        )

        captured = {}

        def fake_generate(prompt, config, generation_client=None):
            captured["prompt"] = prompt
            return "Trả lời dựa trên [E1] và [E2]."

        with patch.object(rag, "load_runtime_config", return_value=self.base_config), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "embed_text", return_value=[0.1, 0.2, 0.3]), \
             patch.object(rag, "generate_answer", side_effect=fake_generate):
            result = rag.ask_question("Câu hỏi mẫu", top_k=5, strategy="hierarchical")

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["collection"], rag.build_collection_name("hierarchical", self.base_config))
        self.assertEqual(len(result["citations"]), 1)
        self.assertEqual(result["citations"][0]["chunk_id"], "chunk-1")
        self.assertIn("[Nguồn: doc-1, tr. 1-2, chunk: chunk-1]", result["answer"])
        self.assertIn("Evidence [E1]", captured["prompt"])
        self.assertNotIn("Evidence [E2]", captured["prompt"])
        self.assertIn("không đáng tin cậy", captured["prompt"])

    def test_insufficient_evidence_returns_fixed_message(self):
        collection = self._build_collection(
            documents=["Đây là chunk 1"],
            metadatas=[{"source": "doc-1", "page_start": 1, "page_end": 1, "chunk_id": "chunk-1"}],
            distances=[0.9],
        )

        with patch.object(rag, "load_runtime_config", return_value=self.base_config), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "embed_text", return_value=[0.1, 0.2, 0.3]), \
             patch.object(rag, "generate_answer") as fake_generate:
            result = rag.ask_question("Câu hỏi mẫu", top_k=2, strategy="hierarchical")

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["answer"], "Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp.")
        fake_generate.assert_not_called()

    def test_generation_error_returns_retrieval_only(self):
        collection = self._build_collection(
            documents=["Đây là chunk 1"],
            metadatas=[{"source": "doc-1", "page_start": 1, "page_end": 1, "chunk_id": "chunk-1"}],
            distances=[0.1],
        )

        with patch.object(rag, "load_runtime_config", return_value=self.base_config), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "embed_text", return_value=[0.1, 0.2, 0.3]), \
             patch.object(rag, "generate_answer", side_effect=RuntimeError("boom")):
            result = rag.ask_question("Câu hỏi mẫu", top_k=3, strategy="hierarchical")

        self.assertEqual(result["status"], "retrieval_only")
        self.assertEqual(result["citations"], [])
        self.assertIn("Đã truy xuất được nguồn", result["answer"])
        self.assertTrue(any("generation" in warning.lower() for warning in result["warnings"]))

    def test_missing_api_key_falls_back_to_deterministic_embedding(self):
        collection = self._build_collection(
            documents=["Đây là chunk 1"],
            metadatas=[{"source": "doc-1", "page_start": 1, "page_end": 1, "chunk_id": "chunk-1"}],
            distances=[0.1],
        )
        config_without_key = dict(self.base_config)
        config_without_key["has_api_key"] = False

        with patch.object(rag, "load_runtime_config", return_value=config_without_key), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "generate_answer", return_value=""):
            result = rag.ask_question("Câu hỏi mẫu", top_k=1, strategy="hierarchical")

        self.assertEqual(result["status"], "retrieval_only")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertTrue(result["evidence"][0]["accepted"])

    def test_invalid_label_is_removed_and_warned(self):
        collection = self._build_collection(
            documents=["Đây là chunk 1"],
            metadatas=[{"source": "doc-1", "page_start": 4, "page_end": 4, "chunk_id": "chunk-1"}],
            distances=[0.1],
        )

        with patch.object(rag, "load_runtime_config", return_value=self.base_config), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "embed_text", return_value=[0.1, 0.2, 0.3]), \
             patch.object(rag, "generate_answer", return_value="Câu trả lời với [E99]."):
            result = rag.ask_question("Câu hỏi mẫu", top_k=1, strategy="hierarchical")

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["answer"], "Câu trả lời với .")
        self.assertTrue(any("E99" in warning for warning in result["warnings"]))

    def test_top_k_larger_than_count_uses_collection_count(self):
        collection = self._build_collection(
            documents=["Đây là chunk 1"],
            metadatas=[{"source": "doc-1", "page_start": 1, "page_end": 1, "chunk_id": "chunk-1"}],
            distances=[0.1],
        )

        with patch.object(rag, "load_runtime_config", return_value=self.base_config), \
             patch.object(rag, "get_chroma_client", return_value=FakeClient(collection)), \
             patch.object(rag, "embed_text", return_value=[0.1, 0.2, 0.3]), \
             patch.object(rag, "generate_answer", return_value="Đã có câu trả lời."):
            result = rag.ask_question("Câu hỏi mẫu", top_k=10, strategy="hierarchical")

        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["top_k"], 10)


if __name__ == "__main__":
    unittest.main()
