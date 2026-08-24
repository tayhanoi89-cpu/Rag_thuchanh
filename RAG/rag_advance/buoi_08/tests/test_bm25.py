import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from advanced_rag import search_bm25, tokenize_vi_legal


class BM25Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "chunks_advanced_sample.json"
        self.chunks = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_tokenizer_keeps_vietnamese_accents_and_numbers(self) -> None:
        tokens = tokenize_vi_legal("Điều 7, Khoản 2")
        self.assertEqual(tokens, ["điều", "7", "khoản", "2"])

    def test_tokenizer_keeps_vietnamese_words_with_nfc(self) -> None:
        tokens = tokenize_vi_legal("cơ cấu lại thời hạn trả nợ")
        self.assertEqual(tokens, ["cơ", "cấu", "lại", "thời", "hạn", "trả", "nợ"])

    def test_query_and_corpus_share_same_preprocessing(self) -> None:
        query_tokens = tokenize_vi_legal("Điều 7 quy định gì?")
        self.assertEqual(query_tokens, ["điều", "7", "quy", "định", "gì"])

        chunks = [
            {"chunk_id": "chunk-01", "text": "Điều 7 quy định về cơ cấu lại thời hạn trả nợ", "source": "s1", "page_start": 1, "page_end": 2},
            {"chunk_id": "chunk-02", "text": "Đây là đoạn khác không liên quan", "source": "s2", "page_start": 1, "page_end": 2},
        ]
        results = search_bm25("Điều 7 quy định gì?", chunks, candidate_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0]["chunk_id"], "chunk-01")
        self.assertEqual(results[0]["text"], chunks[0]["text"])

    def test_exact_legal_term_ranks_above_paraphrase(self) -> None:
        results = search_bm25("Điều 7 quy định gì?", self.chunks, candidate_k=3)
        self.assertEqual(results[0]["chunk_id"], "chunk-01")
        self.assertGreater(results[0]["bm25_score"], results[1]["bm25_score"])

    def test_candidate_k_larger_than_corpus_size_still_works(self) -> None:
        results = search_bm25("Điều 7 quy định gì?", self.chunks, candidate_k=100)
        self.assertEqual(len(results), len(self.chunks))

    def test_empty_question_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            search_bm25("   ", self.chunks, candidate_k=3)

    def test_tie_break_is_deterministic_by_chunk_id(self) -> None:
        chunks = [
            {"chunk_id": "chunk-b", "text": "điều 7", "source": "s", "page_start": 1, "page_end": 2},
            {"chunk_id": "chunk-a", "text": "điều 7", "source": "s", "page_start": 1, "page_end": 2},
        ]
        results = search_bm25("điều 7", chunks, candidate_k=2)
        self.assertEqual([item["chunk_id"] for item in results], ["chunk-a", "chunk-b"])


if __name__ == "__main__":
    unittest.main()
