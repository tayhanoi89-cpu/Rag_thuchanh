"""Evaluate BM25, dense, Hybrid RRF, and Hybrid plus reranking."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bm25_retriever import BM25Retriever
from src.corpus import load_corpus
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import CandidateReranker


QUESTIONS_PATH = PROJECT_ROOT / "data" / "eval" / "questions.csv"
COMPARISON_PATH = PROJECT_ROOT / "outputs" / "retrieval_comparison.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "evaluation_report.md"
METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")


def load_questions() -> list[dict[str, str]]:
    with QUESTIONS_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def hit_at(results: list[dict[str, object]], expected: str, limit: int) -> int:
    return int(any(row.get("chunk_id") == expected for row in results[:limit]))


def reciprocal_rank(results: list[dict[str, object]], expected: str) -> float:
    for rank, row in enumerate(results, 1):
        if row.get("chunk_id") == expected:
            return 1.0 / rank
    return 0.0


def retrieve_all(question: str, bm25, dense, hybrid, reranker) -> dict[str, list[dict[str, object]]]:
    candidates = hybrid.search(question, top_k=20, candidate_k=20)
    reranked = reranker.rerank(question, candidates, top_k=5)
    return {
        "bm25": bm25.search(question, top_k=5),
        "dense": dense.search(question, top_k=5),
        "hybrid": hybrid.search(question, top_k=5, candidate_k=20),
        "hybrid_rerank": reranked,
    }


def main() -> None:
    questions = load_questions()
    rows = load_corpus()
    bm25 = BM25Retriever(rows)
    dense = DenseRetriever(rows)
    hybrid = HybridRetriever(rows)
    reranker = CandidateReranker()
    evaluation_rows: list[dict[str, object]] = []
    method_scores: dict[str, list[dict[str, float]]] = defaultdict(list)

    for question in questions:
        results_by_method = retrieve_all(question["question"], bm25, dense, hybrid, reranker)
        for method in METHODS:
            results = results_by_method[method]
            record = {
                "question_id": question["question_id"],
                "query_type": question["query_type"],
                "method": method,
                "expected_chunk_id": question["expected_chunk_id"],
                "top1_chunk_id": results[0]["chunk_id"] if results else "",
                "hit_at_1": hit_at(results, question["expected_chunk_id"], 1),
                "hit_at_3": hit_at(results, question["expected_chunk_id"], 3),
                "hit_at_5": hit_at(results, question["expected_chunk_id"], 5),
                "mrr": reciprocal_rank(results, question["expected_chunk_id"]),
                "reranker_mode": reranker.mode if method == "hybrid_rerank" else "",
            }
            evaluation_rows.append(record)
            method_scores[method].append({
                "hit_at_1": float(record["hit_at_1"]),
                "hit_at_3": float(record["hit_at_3"]),
                "hit_at_5": float(record["hit_at_5"]),
                "mrr": float(record["mrr"]),
            })

    COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COMPARISON_PATH.open("w", encoding="utf-8", newline="") as file:
        fieldnames = list(evaluation_rows[0])
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evaluation_rows)

    summary: dict[str, dict[str, float]] = {}
    for method, scores in method_scores.items():
        summary[method] = {
            metric: sum(score[metric] for score in scores) / len(scores)
            for metric in ("hit_at_1", "hit_at_3", "hit_at_5", "mrr")
        }

    failure_lines = []
    for record in evaluation_rows:
        if record["hit_at_5"] == 0:
            failure_lines.append(
                f"- {record['question_id']} / {record['method']}: expected "
                f"`{record['expected_chunk_id']}`, top-1 was `{record['top1_chunk_id']}`."
            )

    report_lines = [
        "# Retrieval Evaluation Report",
        "",
        f"- Questions: {len(questions)}",
        f"- Methods: {', '.join(METHODS)}",
        f"- Gold policy: expected IDs were selected only where the source title/code/content directly verified the target chunk.",
        "",
        "## Aggregate Metrics",
        "",
        "| Method | Hit@1 | Hit@3 | Hit@5 | MRR |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for method in METHODS:
        metrics = summary[method]
        report_lines.append(
            f"| {method} | {metrics['hit_at_1']:.3f} | {metrics['hit_at_3']:.3f} | "
            f"{metrics['hit_at_5']:.3f} | {metrics['mrr']:.3f} |"
        )
    report_lines += [
        "",
        "## Observations",
        "",
        "- BM25 is expected to be strongest for exact document codes and identifiers.",
        "- Dense retrieval is evaluated for semantic similarity, but a small three-question set cannot establish general superiority.",
        "- Hybrid uses both rank lists through RRF; it does not add raw BM25 and cosine scores.",
        f"- Reranker mode observed: `{reranker.mode}`.",
        "- Ranking changes are visible in `retrieval_examples.md`; metric changes should be interpreted only on this small verified set.",
        "",
        "## Failure Cases",
        "",
        *(failure_lines or ["- No Hit@5 failures in this evaluation set."]),
        "",
        "## Limitations",
        "",
        "- The corpus contains 15 full-document records, not article-level chunks.",
        "- The evaluation has three questions and one verified target per question.",
        "- No claim about production retrieval quality should be made from these metrics alone.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"questions: {len(questions)}")
    print(f"reranker_mode: {reranker.mode}")
    for method in METHODS:
        print(f"{method}: {summary[method]}")
    print(f"comparison: {COMPARISON_PATH}")
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    main()