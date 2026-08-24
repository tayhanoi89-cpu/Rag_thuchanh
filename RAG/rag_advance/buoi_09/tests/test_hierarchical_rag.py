import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_advance.buoi_09.hierarchical_rag import (
    build_hierarchy,
    build_store,
    compare_modes,
    generate_query_set,
    hierarchy_status,
    load_runtime_config,
    multi_child_retrieval,
    parent_retrieval,
    rerank_parent_candidates,
    run_query_pipeline,
)


class HierarchyBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_path = Path(__file__).parent / "fixtures" / "hierarchical_sample.json"

    def test_metadata_precedence_over_heading(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 4000})
        child = next(c for c in data["children"] if c["child_id"].endswith(":0001"))
        self.assertEqual(child["resolution_method"], "metadata")
        self.assertEqual(child["structural_path"]["article"], "Điều 1")
        self.assertFalse(child["ambiguous"])

    def test_heading_inferred_at_chunk_start(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 4000})
        child = next(c for c in data["children"] if c["child_id"].endswith(":0002"))
        self.assertEqual(child["resolution_method"], "heading_inferred")
        self.assertEqual(child["structural_path"]["article"], "Điều 2")

    def test_carry_forward_within_same_source_only(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 4000})
        child = next(c for c in data["children"] if c["child_id"].endswith(":0003"))
        self.assertEqual(child["resolution_method"], "carried_forward")
        self.assertEqual(child["structural_path"]["article"], "Điều 2")

    def test_inline_legal_reference_is_not_heading(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 4000})
        child = next(c for c in data["children"] if c["child_id"].endswith(":0004"))
        self.assertEqual(child["resolution_method"], "document_fallback")
        self.assertTrue(child["ambiguous"] or child["warnings"])

    def test_conflict_marks_ambiguous(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 4000})
        child = next(c for c in data["children"] if c["child_id"].endswith(":0005"))
        self.assertTrue(child["ambiguous"])
        self.assertTrue(any("conflict" in warning for warning in child["warnings"]))

    def test_numeric_chunk_ordering_and_parent_split(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 120})
        child_ids = [c["child_id"] for c in data["children"]]
        self.assertEqual(child_ids, sorted(child_ids, key=lambda cid: int(cid.rsplit(":", 1)[1])))
        self.assertGreaterEqual(len(data["parents"]), 2)
        self.assertTrue(all(child["parent_id"] for child in data["children"]))

    def test_stable_parent_ids_across_rebuilds(self) -> None:
        first = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 120})
        second = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 120})
        self.assertEqual([p["parent_id"] for p in first["parents"]], [p["parent_id"] for p in second["parents"]])

    def test_parent_ids_are_unique(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 120})
        parent_ids = [p["parent_id"] for p in data["parents"]]
        self.assertEqual(len(parent_ids), len(set(parent_ids)))

    def test_each_child_has_single_parent(self) -> None:
        data = build_hierarchy(input_path=self.fixture_path, config={"PARENT_MAX_CHARS": 120})
        child_parent_ids = [child["parent_id"] for child in data["children"] if child.get("parent_id")]
        self.assertEqual(len(child_parent_ids), len(data["children"]))
        self.assertEqual(len(child_parent_ids), len(set(data["children"][i]["child_id"] for i in range(len(data["children"])))))

    def test_build_store_writes_manifest_and_status_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = build_store(input_path=self.fixture_path, output_dir=output_dir, config={"PARENT_MAX_CHARS": 120})
            self.assertTrue((output_dir / "children.json").exists())
            self.assertTrue((output_dir / "parents.json").exists())
            self.assertTrue((output_dir / "manifest.json").exists())
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("schema_version", manifest)
            status = hierarchy_status(output_dir)
            self.assertEqual(status["status"], "ready")
            before_mtime = (output_dir / "manifest.json").stat().st_mtime_ns
            hierarchy_status(output_dir)
            after_mtime = (output_dir / "manifest.json").stat().st_mtime_ns
            self.assertEqual(before_mtime, after_mtime)

    def test_runtime_config_uses_local_env_path(self) -> None:
        config = load_runtime_config()
        self.assertIn("MULTI_QUERY_COUNT", config)
        self.assertIsInstance(config["MULTI_QUERY_COUNT"], int)

    def test_generate_query_set_preserves_q0_and_validates_schema(self) -> None:
        def fake_generator(question: str, config: dict, model: str) -> dict:
            self.assertIn("Điều 8", question)
            return {"queries": [{"text": "Điều 8 quy định nhu cầu vốn", "focus": "exact_legal_terms"}, {"text": "nhu cầu vốn không được cho vay", "focus": "paraphrase"}]}

        result = generate_query_set("Điều 8 quy định nhu cầu vốn không được cho vay?", config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2}, query_generator_fn=fake_generator)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["queries"][0]["query_id"], "Q0")
        self.assertEqual(result["queries"][0]["text"], "Điều 8 quy định nhu cầu vốn không được cho vay?")
        self.assertEqual(result["queries"][0]["origin"], "original")
        self.assertGreaterEqual(len(result["queries"]), 2)
        self.assertIn(result["queries"][1]["focus"], {"exact_legal_terms", "paraphrase", "missing_aspect"})

    def test_generate_query_set_deduplicates_and_uses_cache(self) -> None:
        calls = []

        def fake_generator(question: str, config: dict, model: str) -> dict:
            calls.append((question, config, model))
            return {"queries": [{"text": "Điều 8 quy định nhu cầu vốn", "focus": "exact_legal_terms"}, {"text": "Điều 8 quy định nhu cầu vốn", "focus": "paraphrase"}, {"text": "   nhu cầu vốn không được cho vay   ", "focus": "missing_aspect"}]}

        first = generate_query_set("Điều 8 quy định nhu cầu vốn không được cho vay?", config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2}, query_generator_fn=fake_generator)
        second = generate_query_set("Điều 8 quy định nhu cầu vốn không được cho vay?", config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2}, query_generator_fn=fake_generator)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["dropped_duplicate_count"], 1)
        self.assertEqual(len(first["queries"]), 3)
        self.assertTrue(second.get("cache_hit"))
        self.assertEqual(len(calls), 1)

    def test_generate_query_set_returns_unavailable_status_on_failure(self) -> None:
        def fake_generator(question: str, config: dict, model: str) -> dict:
            raise RuntimeError("boom")

        result = generate_query_set("Điều 8 quy định nhu cầu vốn không được cho vay?", config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2}, query_generator_fn=fake_generator, bypass_cache=True)
        self.assertEqual(result["status"], "query_generation_unavailable")
        self.assertIn("boom", result["error"])

    def test_multi_child_retrieval_applies_cross_query_rrf(self) -> None:
        def fake_retriever(query_text: str, config: dict, query_id: str, strategy: str = "hierarchical") -> list[dict]:
            if query_id == "Q0":
                return [
                    {"child_id": "c1", "text": "a", "source": "s1", "page_start": 1, "page_end": 2, "inner_rrf_rank": 1},
                    {"child_id": "c2", "text": "b", "source": "s1", "page_start": 3, "page_end": 4, "inner_rrf_rank": 2},
                ]
            return [
                {"child_id": "c2", "text": "b", "source": "s1", "page_start": 3, "page_end": 4, "inner_rrf_rank": 1},
                {"child_id": "c3", "text": "c", "source": "s2", "page_start": 5, "page_end": 6, "inner_rrf_rank": 2},
            ]

        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Điều 8", "origin": "original", "focus": "original_intent"},
                {"query_id": "Q1", "text": "nhu cầu vốn", "origin": "generated", "focus": "paraphrase"},
            ]
        }
        result = multi_child_retrieval(query_set, config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2, "MULTI_QUERY_RRF_K": 60}, hybrid_retriever_fn=fake_retriever)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["query_count_executed"], 2)
        self.assertEqual(len(result["merged_children"]), 3)
        self.assertEqual(result["merged_children"][0]["child_id"], "c2")
        self.assertEqual(result["merged_children"][0]["support_query_count"], 2)
        self.assertGreater(result["merged_children"][0]["multi_query_rrf_score"], result["merged_children"][1]["multi_query_rrf_score"])

    def test_multi_child_retrieval_reports_partial_failure(self) -> None:
        def fake_retriever(query_text: str, config: dict, query_id: str, strategy: str = "hierarchical") -> list[dict]:
            if query_id == "Q0":
                return [{"child_id": "c1", "text": "a", "source": "s1", "page_start": 1, "page_end": 2, "inner_rrf_rank": 1}]
            if query_id == "Q1":
                raise RuntimeError("retrieval failed")
            return []

        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Điều 8", "origin": "original", "focus": "original_intent"},
                {"query_id": "Q1", "text": "nhu cầu vốn", "origin": "generated", "focus": "paraphrase"},
            ]
        }
        result = multi_child_retrieval(query_set, config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2, "MULTI_QUERY_RRF_K": 60}, hybrid_retriever_fn=fake_retriever)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["query_count_failed"], 1)
        self.assertTrue(any(error["query_id"] == "Q1" for error in result["errors"]))

    def test_multi_child_retrieval_fails_on_metadata_mismatch(self) -> None:
        def fake_retriever(query_text: str, config: dict, query_id: str, strategy: str = "hierarchical") -> list[dict]:
            if query_id == "Q0":
                return [{"child_id": "c1", "text": "a", "source": "s1", "page_start": 1, "page_end": 2, "inner_rrf_rank": 1}]
            return [{"child_id": "c1", "text": "a", "source": "s2", "page_start": 1, "page_end": 2, "inner_rrf_rank": 1}]

        query_set = {
            "queries": [
                {"query_id": "Q0", "text": "Điều 8", "origin": "original", "focus": "original_intent"},
                {"query_id": "Q1", "text": "nhu cầu vốn", "origin": "generated", "focus": "paraphrase"},
            ]
        }
        result = multi_child_retrieval(query_set, config={"MULTI_QUERY_COUNT": 3, "MULTI_QUERY_MAX_CHARS": 300, "MULTI_QUERY_TEMPERATURE": 0.2, "MULTI_QUERY_RRF_K": 60}, hybrid_retriever_fn=fake_retriever)
        self.assertEqual(result["status"], "retrieval_unavailable")
        self.assertIn("metadata", result["error"].lower())

    def test_parent_retrieval_maps_children_to_parent_and_aggregates_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            build_store(input_path=self.fixture_path, output_dir=store_dir, config={"PARENT_MAX_CHARS": 4000})
            children = json.loads((store_dir / "children.json").read_text(encoding="utf-8"))
            child_a = next(child for child in children if child["child_id"].endswith(":0002"))
            child_b = next(child for child in children if child["child_id"].endswith(":0003"))
            fused_hits = [
                {
                    "child_id": child_a["child_id"],
                    "text": child_a["text"],
                    "source": child_a["source"],
                    "page_start": child_a["page_start"],
                    "page_end": child_a["page_end"],
                    "multi_query_rank": 1,
                    "support_query_ids": ["Q0", "Q1"],
                },
                {
                    "child_id": child_b["child_id"],
                    "text": child_b["text"],
                    "source": child_b["source"],
                    "page_start": child_b["page_start"],
                    "page_end": child_b["page_end"],
                    "multi_query_rank": 2,
                    "support_query_ids": ["Q0"],
                },
            ]
            result = parent_retrieval(fused_hits, input_path=self.fixture_path, store_dir=store_dir, config={"PARENT_MAX_CHARS": 4000, "PARENT_RRF_K": 60, "PARENT_SCORE_CHILD_LIMIT": 3, "PARENT_CANDIDATES": 10, "TOTAL_CONTEXT_MAX_CHARS": 20000})
            self.assertEqual(result["status"], "ready")
            self.assertEqual(len(result["parent_candidates"]), 1)
            self.assertEqual(result["parent_candidates"][0]["anchor_child_id"], child_a["child_id"])
            self.assertEqual(result["parent_candidates"][0]["supporting_child_ids"], [child_a["child_id"], child_b["child_id"]])
            self.assertEqual(result["parent_candidates"][0]["scoring_child_ids"], [child_a["child_id"], child_b["child_id"]])
            self.assertEqual(result["parent_candidates"][0]["support_query_ids"], ["Q0", "Q1"])
            self.assertGreater(result["parent_candidates"][0]["parent_rrf_score"], 0.0)
            self.assertEqual(result["trace"]["input_child_hit_count"], 2)
            self.assertEqual(result["trace"]["unique_parent_count"], 1)

    def test_parent_retrieval_rejects_stale_hierarchy_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            build_store(input_path=self.fixture_path, output_dir=store_dir, config={"PARENT_MAX_CHARS": 4000})
            result = parent_retrieval([], input_path=self.fixture_path, store_dir=store_dir, config={"PARENT_MAX_CHARS": 5000})
            self.assertEqual(result["status"], "hierarchy_not_ready")
            self.assertIn("config", result["error"].lower())

    def test_parent_retrieval_allows_no_input_path_when_store_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            build_store(input_path=self.fixture_path, output_dir=store_dir, config={"PARENT_MAX_CHARS": 4000})
            result = parent_retrieval([], input_path=None, store_dir=store_dir, config={"PARENT_MAX_CHARS": 4000, "PARENT_RRF_K": 60, "PARENT_SCORE_CHILD_LIMIT": 3, "PARENT_CANDIDATES": 10, "TOTAL_CONTEXT_MAX_CHARS": 20000})
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["parent_candidates"], [])

    def test_parent_retrieval_respects_context_budget_and_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            build_store(input_path=self.fixture_path, output_dir=store_dir, config={"PARENT_MAX_CHARS": 4000})
            parents = json.loads((store_dir / "parents.json").read_text(encoding="utf-8"))
            parent_a = parents[0]
            parent_b = parents[1]
            parent_a["text"] = "A" * 5000
            parent_b["text"] = "B" * 5000
            (store_dir / "parents.json").write_text(json.dumps(parents, ensure_ascii=False, indent=2), encoding="utf-8")
            fused_hits = [
                {
                    "child_id": parent_a["child_ids"][0],
                    "text": "x",
                    "source": parent_a["source"],
                    "page_start": parent_a["page_start"],
                    "page_end": parent_a["page_end"],
                    "multi_query_rank": 1,
                    "support_query_ids": ["Q0"],
                },
                {
                    "child_id": parent_b["child_ids"][0],
                    "text": "y",
                    "source": parent_b["source"],
                    "page_start": parent_b["page_start"],
                    "page_end": parent_b["page_end"],
                    "multi_query_rank": 2,
                    "support_query_ids": ["Q0"],
                },
            ]
            result = parent_retrieval(fused_hits, input_path=self.fixture_path, store_dir=store_dir, config={"PARENT_MAX_CHARS": 4000, "PARENT_RRF_K": 60, "PARENT_SCORE_CHILD_LIMIT": 3, "PARENT_CANDIDATES": 10, "TOTAL_CONTEXT_MAX_CHARS": 4000})
            self.assertEqual(result["status"], "ready")
            self.assertEqual(len(result["parent_candidates"]), 1)
            self.assertIn("oversized_parent_kept", result["parent_candidates"][0]["warnings"])
            self.assertGreater(len(result["trace"]["parents_dropped_by_context_budget"]), 0)

    def test_rerank_parent_candidates_uses_original_question_and_tracks_rank_change(self) -> None:
        def fake_reranker(question: str, text: str, config: dict, model: str) -> dict:
            self.assertEqual(question, "Điều 8 quy định nhu cầu vốn")
            return {"raw_score": 2.0 if "điều 8" in text.lower() else 1.0}

        candidates = [
            {"parent_id": "p2", "text": "B", "parent_rrf_score": 0.5, "parent_rank": 2, "parent_rank": 2},
            {"parent_id": "p1", "text": "Điều 8 quy định nhu cầu vốn", "parent_rrf_score": 0.7, "parent_rank": 1, "parent_rank": 1},
        ]
        result = rerank_parent_candidates(candidates, "Điều 8 quy định nhu cầu vốn", config={"RERANK_MIN_SCORE": 0.5}, reranker_fn=fake_reranker)
        self.assertEqual(result["reranked_candidates"][0]["parent_id"], "p1")
        self.assertEqual(result["reranked_candidates"][0]["parent_rerank_rank"], 1)
        self.assertEqual(result["reranked_candidates"][0]["parent_rank_change"], 0)
        self.assertGreater(result["reranked_candidates"][0]["parent_rerank_score"], 0.5)

    def test_query_pipeline_uses_answer_generation_budget_and_compare_skips_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            build_store(input_path=self.fixture_path, output_dir=store_dir, config={"PARENT_MAX_CHARS": 4000})
            generation_calls = []

            def fake_generator(question: str, config: dict, model: str) -> dict:
                generation_calls.append("query")
                return {"queries": [{"text": "nhu cầu vốn", "focus": "paraphrase"}]}

            def fake_retriever(query_text: str, config: dict, query_id: str, strategy: str = "hierarchical") -> list[dict]:
                return [{"child_id": "sample:0001", "text": "sample", "source": "sample.pdf", "page_start": 1, "page_end": 2, "inner_rrf_rank": 1}]

            def fake_reranker(question: str, text: str, config: dict, model: str) -> dict:
                return {"raw_score": 1.2}

            def fake_answer(question: str, evidence: list[dict], config: dict, model: str) -> dict:
                generation_calls.append("answer")
                return {"answer": "Trả lời dựa trên evidence", "citations": [{"evidence_id": "P1", "parent_id": evidence[0]["parent_id"], "anchor_child_id": evidence[0]["anchor_child_id"]}]}

            result = run_query_pipeline(
                "Điều 8 quy định nhu cầu vốn",
                mode="multi_parent",
                config={"PARENT_MAX_CHARS": 4000, "PARENT_RRF_K": 60, "PARENT_SCORE_CHILD_LIMIT": 3, "PARENT_CANDIDATES": 10, "FINAL_PARENT_TOP_K": 3, "TOTAL_CONTEXT_MAX_CHARS": 4000, "RERANK_MIN_SCORE": 0.5},
                input_path=self.fixture_path,
                store_dir=store_dir,
                query_generator_fn=fake_generator,
                hybrid_retriever_fn=fake_retriever,
                reranker_fn=fake_reranker,
                answer_generator_fn=fake_answer,
            )
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["trace"]["generation_api_call_count"], 2)
            self.assertEqual(result["trace"]["answer_generation_call_count"], 1)

            comparison = compare_modes(
                "Điều 8 quy định nhu cầu vốn",
                config={"PARENT_MAX_CHARS": 4000, "PARENT_RRF_K": 60, "PARENT_SCORE_CHILD_LIMIT": 3, "PARENT_CANDIDATES": 10, "FINAL_PARENT_TOP_K": 3, "TOTAL_CONTEXT_MAX_CHARS": 4000, "RERANK_MIN_SCORE": 0.5},
                input_path=self.fixture_path,
                store_dir=store_dir,
                query_generator_fn=fake_generator,
                hybrid_retriever_fn=fake_retriever,
                reranker_fn=fake_reranker,
            )
            self.assertEqual(comparison["status"], "ready")
            self.assertNotIn("answer", comparison["mode_results"]["single_flat"])
            self.assertEqual(comparison["trace"]["answer_generation_call_count"], 0)


if __name__ == "__main__":
    unittest.main()
