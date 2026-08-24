from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pair_key(left_id: str, right_id: str) -> tuple[str, str]:
    return tuple(sorted((left_id, right_id)))


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: _clean(value) for key, value in row.items()} for row in reader]


def _normalize_relation_type(value: str) -> str:
    normalized = value.strip().upper()
    return normalized.replace(" ", "_")


def _collect_truth_pairs(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    pairs: dict[tuple[str, str], str] = {}
    for row in rows:
        left_id = row.get("doc_id") or row.get("left_id") or row.get("source_id")
        right_id = row.get("other_doc_id") or row.get("right_id") or row.get("target_id")
        if not left_id or not right_id or left_id == right_id:
            continue

        relation_type = row.get("relationship_type") or row.get("relationship") or row.get("type") or "RELATED"
        pairs[_pair_key(left_id, right_id)] = _normalize_relation_type(relation_type)
    return pairs


def _collect_predicted_pairs(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    pairs: dict[tuple[str, str], str] = {}
    for row in rows:
        left_id = row.get("doc_id") or row.get("left_id") or row.get("source_id")
        right_id = row.get("other_doc_id") or row.get("right_id") or row.get("target_id")
        if not left_id or not right_id or left_id == right_id:
            continue

        has_relation = str(row.get("has_relation", "")).strip().lower() in {"true", "1", "yes", "y"}
        if not has_relation:
            relation_type = row.get("relationship_type") or row.get("relationship") or row.get("type") or ""
            if not relation_type or _normalize_relation_type(relation_type) in {"KHONG_CO", "NONE", "NO_RELATION"}:
                continue
        relation_type = row.get("relationship_type") or row.get("relationship") or row.get("type") or "RELATED"
        pairs[_pair_key(left_id, right_id)] = _normalize_relation_type(relation_type)
    return pairs


def compute_metrics(truth_rows: list[dict[str, str]], pred_rows: list[dict[str, str]]) -> dict[str, Any]:
    truth_pairs = _collect_truth_pairs(truth_rows)
    pred_pairs = _collect_predicted_pairs(pred_rows)

    actual = set(truth_pairs)
    predicted = set(pred_pairs)

    tp = len(actual & predicted)
    fp = len(predicted - actual)
    fn = len(actual - predicted)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    exact_type_match = 0
    for pair in actual & predicted:
        if truth_pairs.get(pair) == pred_pairs.get(pair):
            exact_type_match += 1

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "actual_positive": len(actual),
        "predicted_positive": len(predicted),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "exact_type_match_count": exact_type_match,
        "exact_type_accuracy": round(exact_type_match / len(actual & predicted), 4) if (actual & predicted) else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate predicted legal relationships against a gold-standard CSV.")
    parser.add_argument("--ground-truth", required=True, help="Path to the gold-standard relationships CSV, e.g. medium/relationships.csv")
    parser.add_argument("--predictions", required=True, help="Path to the predicted relationships CSV")
    args = parser.parse_args()

    gt_path = Path(args.ground_truth)
    pred_path = Path(args.predictions)

    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {gt_path}")
    if not pred_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {pred_path}")

    truth_rows = _load_csv(gt_path)
    pred_rows = _load_csv(pred_path)
    metrics = compute_metrics(truth_rows, pred_rows)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
