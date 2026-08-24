import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_advance.buoi_09.app import (
    STATUS_HINTS,
    build_mode_comparison_rows,
    build_parent_tree_nodes,
    build_query_cards,
    build_query_child_matrix,
    format_citation,
    status_action_hint,
)


class AppHelperTests(unittest.TestCase):
    def test_status_action_hint_maps_known_status(self) -> None:
        self.assertEqual(status_action_hint("ready"), STATUS_HINTS["ready"])
        self.assertIn("Trạng thái chưa rõ", status_action_hint("unknown_status"))

    def test_format_citation_outputs_expected_fields(self) -> None:
        citation = {
            "evidence_id": "P1",
            "parent_id": "parent_123",
            "anchor_child_id": "child_456",
            "source": "sample.pdf",
            "page_start": 2,
            "page_end": 3,
            "structural_path": {"chapter": "Chương I", "article": "Điều 8"},
            "warnings": ["ambiguous"],
        }
        output = format_citation(citation)
        self.assertIn("P1", output)
        self.assertIn("parent=parent_123", output)
        self.assertIn("anchor_child=child_456", output)
        self.assertIn("warnings: ambiguous", output)

    def test_build_query_cards_counts_matches(self) -> None:
        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Điều 8", "origin": "original", "focus": "original_intent"},
                {"query_id": "Q1", "text": "nhu cầu vốn", "origin": "generated", "focus": "paraphrase"},
            ]
        }
        merged_children = [
            {"child_id": "c1", "per_query_ranks": {"Q0": 1, "Q1": 2}},
            {"child_id": "c2", "per_query_ranks": {"Q1": 1}},
        ]
        cards = build_query_cards(query_set, merged_children)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["query_id"], "Q0")
        self.assertEqual(cards[0]["result_count"], 1)
        self.assertEqual(cards[1]["result_count"], 2)
        self.assertTrue(cards[0]["is_original"])
        self.assertFalse(cards[1]["is_original"])

    def test_build_query_child_matrix_rows(self) -> None:
        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Điều 8", "origin": "original", "focus": "original_intent"},
                {"query_id": "Q1", "text": "nhu cầu vốn", "origin": "generated", "focus": "paraphrase"},
            ]
        }
        merged_children = [
            {
                "child_id": "c1",
                "text": "sample",
                "source": "sample.pdf",
                "page_start": 1,
                "page_end": 2,
                "multi_query_rrf_score": 0.5,
                "support_query_count": 2,
                "support_query_ids": ["Q0", "Q1"],
                "per_query_ranks": {"Q0": 1, "Q1": 2},
            }
        ]
        matrix = build_query_child_matrix(query_set, merged_children)
        self.assertEqual(len(matrix), 1)
        row = matrix[0]
        self.assertEqual(row["rank_Q0"], 1)
        self.assertEqual(row["rank_Q1"], 2)
        self.assertEqual(row["support_query_count"], 2)

    def test_build_parent_tree_nodes_preserves_scores(self) -> None:
        parent_candidates = [
            {
                "parent_id": "p1",
                "source": "sample.pdf",
                "page_start": 1,
                "page_end": 3,
                "parent_rank": 1,
                "parent_rerank_rank": 2,
                "parent_rrf_score": 0.8,
                "parent_rerank_score": 0.9,
                "anchor_child_id": "c1",
                "supporting_child_ids": ["c1", "c2"],
                "support_query_ids": ["Q0"],
                "structural_path": {"article": "Điều 8"},
                "warnings": ["ambiguous"],
                "ambiguous": True,
                "text": "parent text",
            }
        ]
        nodes = build_parent_tree_nodes(parent_candidates)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["parent_id"], "p1")
        self.assertEqual(nodes[0]["parent_rank"], 1)
        self.assertEqual(nodes[0]["parent_rerank_rank"], 2)
        self.assertTrue(nodes[0]["ambiguous"])

    def test_build_mode_comparison_rows_handles_child_and_parent_modes(self) -> None:
        compare_result = {
            "mode_results": {
                "single_flat": {
                    "status": "ready",
                    "child_hits": [{"child_id": "c1", "source": "s1"}],
                    "parent_candidates": [],
                    "accepted_evidence": [],
                    "trace": {"generation_api_call_count": 0, "answer_generation_call_count": 0, "reranker_call_count": 0},
                },
                "multi_parent": {
                    "status": "ready",
                    "child_hits": [{"child_id": "c1", "source": "s1"}],
                    "parent_candidates": [{"parent_id": "p1", "source": "s1", "structural_path": {"article": "Điều 8"}}],
                    "accepted_evidence": [{"parent_id": "p1"}],
                    "trace": {"generation_api_call_count": 1, "answer_generation_call_count": 0, "reranker_call_count": 1, "expanded_parent_chars": 100, "context_expansion_factor": 2.0},
                },
            }
        }
        rows = build_mode_comparison_rows(compare_result)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["mode"], "single_flat")
        self.assertEqual(rows[0]["unit_type"], "child")
        self.assertEqual(rows[1]["mode"], "multi_parent")
        self.assertEqual(rows[1]["unit_type"], "parent")
        self.assertEqual(rows[1]["expanded_parent_count"], 1)
        self.assertEqual(rows[1]["context_chars"], 100)


if __name__ == "__main__":
    unittest.main()
