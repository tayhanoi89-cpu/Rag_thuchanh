"""Evaluator for Buổi 09.

This evaluator is safe to import and can run offline using a stub query
generator, a stub hybrid retriever, and a stub reranker. It produces a
retrieval-only report in JSON format and avoids live model calls by default.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag_advance.buoi_09.hierarchical_rag import (
    compare_modes,
    load_runtime_config,
    run_query_pipeline,
)

DEFAULT_QUESTIONS = Path(__file__).resolve().parent / "eval" / "questions.json"
DEFAULT_REPORT = Path(__file__).resolve().parent / "reports" / "latest_report.json"
DEFAULT_STORE_DIR = Path(__file__).resolve().parent / "storage" / "hierarchy"


def _safe_load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_query_generator(question: str, config: dict[str, Any], model: str) -> dict[str, Any]:
    normalized = question.strip()
    candidates = [
        normalized,
        f"{normalized} theo quy định",
        f"{normalized} trong pháp luật",
        f"{normalized} liên quan",
    ]
    queries: list[dict[str, Any]] = []
    seen: set[str] = set()
    max_count = int(config.get("MULTI_QUERY_COUNT", 3))
    for index, text in enumerate(candidates, start=0):
        if len(queries) >= max_count:
            break
        text = text.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        queries.append(
            {
                "query_id": f"Q{index}",
                "text": text,
                "origin": "original" if index == 0 else "generated",
                "focus": "original_intent" if index == 0 else f"variant_{index}",
            }
        )
    return {"queries": queries}


def _safe_hybrid_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
    return []


def _safe_reranker(question: str, text: str, config: dict[str, Any], model: str) -> dict[str, Any]:
    return {"raw_score": 1.0}


def _normalize_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _recall_at_k(predicted: list[str], gold: list[str], k: int) -> float | None:
    if not gold:
        return None
    gold_set = set(gold)
    return len(set(predicted[:k]) & gold_set) / len(gold_set)


def _precision_at_k(predicted: list[str], gold: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(predicted[:k]) & set(gold)) / float(k)


def _evaluate_hit_lists(predicted: list[str], gold: list[str], ks: list[int]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for k in ks:
        recall = _recall_at_k(predicted, gold, k)
        precision = _precision_at_k(predicted, gold, k)
        metrics[f"recall_at_{k}"] = recall
        metrics[f"precision_at_{k}"] = precision
    return metrics


def _build_question_report(
    question: dict[str, Any],
    result: dict[str, Any],
    mode_name: str,
) -> dict[str, Any]:
    relevant_child_ids = _normalize_ids(question.get("relevant_child_ids", []))
    relevant_parent_ids = _normalize_ids(question.get("relevant_parent_ids", []))
    predicted_child_ids = [hit.get("child_id", "") for hit in (result.get("child_hits") or []) if hit.get("child_id")]
    predicted_parent_ids = [candidate.get("parent_id", "") for candidate in (result.get("parent_candidates") or []) if candidate.get("parent_id")]

    child_metrics = _evaluate_hit_lists(predicted_child_ids, relevant_child_ids, [1, 3, 5])
    parent_metrics = _evaluate_hit_lists(predicted_parent_ids, relevant_parent_ids, [1, 3, 5])

    needs_human_review = not relevant_child_ids and not relevant_parent_ids
    question_summary = {
        "question_id": question.get("question_id"),
        "question": question.get("question"),
        "mode": mode_name,
        "status": result.get("status", "unknown"),
        "child_count": len(predicted_child_ids),
        "parent_count": len(predicted_parent_ids),
        "child_ids": predicted_child_ids,
        "parent_ids": predicted_parent_ids,
        "relevant_child_ids": relevant_child_ids,
        "relevant_parent_ids": relevant_parent_ids,
        "needs_human_review": needs_human_review,
        "child_metrics": child_metrics,
        "parent_metrics": parent_metrics,
        "errors": result.get("error"),
    }
    return question_summary


def evaluate_questions(
    questions: list[dict[str, Any]],
    config: dict[str, Any],
    input_path: Path | None,
    store_dir: Path | None,
    compare: bool,
    mode: str,
) -> dict[str, Any]:
    start_time = time.time()
    question_reports: list[dict[str, Any]] = []
    mode_results: dict[str, Any] = {}
    evaluation_counts = {"total_questions": len(questions), "skipped_questions": 0, "needs_human_review": 0}

    for question in questions:
        question_text = str(question.get("question", "")).strip()
        if not question_text:
            evaluation_counts["skipped_questions"] += 1
            continue

        if compare:
            compare_result = compare_modes(
                question_text,
                config=config,
                input_path=input_path,
                store_dir=store_dir,
                query_generator_fn=_safe_query_generator,
                hybrid_retriever_fn=_safe_hybrid_retriever,
                reranker_fn=_safe_reranker,
            )
            mode_results[question.get("question_id", f"question_{len(question_reports)+1}")] = compare_result
            for mode_name, mode_result in compare_result.get("mode_results", {}).items():
                question_reports.append(_build_question_report(question, mode_result, mode_name))
        else:
            result = run_query_pipeline(
                question_text,
                mode,
                config=config,
                input_path=input_path,
                store_dir=store_dir,
                query_generator_fn=_safe_query_generator,
                hybrid_retriever_fn=_safe_hybrid_retriever,
                reranker_fn=_safe_reranker,
                answer_generator_fn=None,
            )
            mode_results[question.get("question_id", f"question_{len(question_reports)+1}")] = result
            question_reports.append(_build_question_report(question, result, mode))

        if not _normalize_ids(question.get("relevant_child_ids", [])) and not _normalize_ids(question.get("relevant_parent_ids", [])):
            evaluation_counts["needs_human_review"] += 1

    summary = {
        "evaluated_questions": len(question_reports),
        "total_questions": evaluation_counts["total_questions"],
        "skipped_questions": evaluation_counts["skipped_questions"],
        "needs_human_review": evaluation_counts["needs_human_review"],
        "compare_mode": compare,
        "mode": mode,
    }

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
        "runtime_config": config,
        "store_dir": str(store_dir or DEFAULT_STORE_DIR),
        "input_path": str(input_path or ""),
        "summary": summary,
        "questions": question_reports,
        "mode_results": mode_results,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Buổi 09 offline evaluator")
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS), help="Path to eval/questions.json")
    parser.add_argument("--output", default=str(DEFAULT_REPORT), help="Path to write the evaluation report JSON")
    parser.add_argument("--input", default=None, help="Hierarchy input path for status validation")
    parser.add_argument("--store-dir", default=str(DEFAULT_STORE_DIR), help="Hierarchy store directory")
    parser.add_argument("--mode", default="multi_parent", choices=["single_flat", "multi_flat", "single_parent", "multi_parent"], help="Evaluation mode for retrieval-only runs")
    parser.add_argument("--compare", action="store_true", help="Run all four supported modes and report per-mode results")
    args = parser.parse_args(argv)

    config = load_runtime_config()
    questions = _safe_load_json(Path(args.questions))
    if not isinstance(questions, list):
        raise ValueError("Evaluation questions file must contain a JSON array")

    report = evaluate_questions(questions, config, Path(args.input) if args.input else None, Path(args.store_dir), args.compare, args.mode)
    _safe_write_json(Path(args.output), report)
    print(f"Wrote evaluation report: {args.output}")


if __name__ == "__main__":
    main()
