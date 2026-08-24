from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ALLOWED_TYPES = {
    "THAM_CHIEU",
    "SUA_DOI_BO_SUNG",
    "THAY_THE_BOI",
    "BAN_HANH_BOI",
    "KY_BOI",
    "AP_DUNG_CHO",
    "THUOC_LINH_VUC",
}
ENTITY_TARGET_TYPES = {"CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"}


def is_blank(value: object) -> bool:
    return not str(value if pd.notna(value) else "").strip()


def validate_row(
    row: pd.Series,
    document_ids: set[str],
    entity_ids: set[str],
    seen_edges: set[tuple[str, str, str]],
) -> str:
    for field in ("source", "target", "target_type", "relationship_type", "method", "evidence"):
        if is_blank(row[field]):
            return f"Missing required field: {field}"
    relationship_type = str(row["relationship_type"])
    if relationship_type not in ALLOWED_TYPES:
        return f"Unsupported relationship type: {relationship_type}"
    source = str(row["source"])
    target = str(row["target"])
    target_type = str(row["target_type"])
    if source not in document_ids:
        return "Source document does not exist"
    if target_type == "Document":
        if target not in document_ids:
            return "Target document does not exist"
        if relationship_type not in {"THAM_CHIEU", "SUA_DOI_BO_SUNG", "THAY_THE_BOI"}:
            return "Document target has an invalid relationship type"
        if source == target:
            return "Meaningless document self-loop"
    elif target_type in ENTITY_TARGET_TYPES:
        if target not in entity_ids:
            return "Target entity does not exist"
        expected_type = {
            "CoQuan": "BAN_HANH_BOI",
            "NguoiKy": "KY_BOI",
            "DoiTuongApDung": "AP_DUNG_CHO",
            "LinhVuc": "THUOC_LINH_VUC",
        }[target_type]
        if relationship_type != expected_type:
            return "Entity target has an invalid relationship type"
    else:
        return f"Unknown target type: {target_type}"
    edge_key = (source, target, relationship_type)
    if edge_key in seen_edges:
        return "Duplicate edge"
    seen_edges.add(edge_key)
    return ""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate extracted knowledge-graph relationships.")
    parser.add_argument("--relationships-raw", default="ner_kb/relationships_raw.csv")
    parser.add_argument("--documents", default="ner_kb/cleaned_documents.csv")
    parser.add_argument("--entities", default="ner_kb/entities.csv")
    parser.add_argument("--output", default="ner_kb/relationships.csv")
    parser.add_argument("--report", default="ner_kb/validation_report.csv")
    args = parser.parse_args()

    raw = pd.read_csv(args.relationships_raw, dtype="string")
    documents = pd.read_csv(args.documents, dtype="string")
    entities = pd.read_csv(args.entities, dtype="string")
    required = {"source", "target", "target_type", "relationship_type", "method", "confidence", "evidence"}
    if missing := required - set(raw.columns):
        raise ValueError(f"Raw relationships are missing: {', '.join(sorted(missing))}")

    document_ids = set(documents["id"].dropna())
    entity_ids = set(entities["entity_id"].dropna())
    seen_edges: set[tuple[str, str, str]] = set()
    passed_rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []
    for _, row in raw.iterrows():
        reason = validate_row(row, document_ids, entity_ids, seen_edges)
        record = row.to_dict()
        record["validation_status"] = "FAIL" if reason else "PASS"
        record["validation_reason"] = reason
        report_rows.append(record)
        if not reason:
            passed_rows.append(row.to_dict())

    output_columns = ["source", "target", "target_type", "relationship_type", "method", "confidence", "evidence"]
    passed = pd.DataFrame(passed_rows, columns=output_columns)
    report = pd.DataFrame(report_rows, columns=output_columns + ["validation_status", "validation_reason"])
    output_path = Path(args.output)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    passed.to_csv(output_path, index=False, encoding="utf-8-sig")
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    print(f"Raw relationships: {len(raw)}")
    print(f"PASS: {len(passed)}")
    print(f"FAIL: {len(report) - len(passed)}")
    print("PASS relationships by type:")
    print(passed["relationship_type"].value_counts().to_string() if not passed.empty else "None")
    failures = report.loc[report["validation_status"] == "FAIL", "validation_reason"].value_counts()
    print("Failure reasons:")
    print(failures.to_string() if not failures.empty else "None")
    print("Sample PASS relationships:")
    print(passed.head(10).to_string(index=False) if not passed.empty else "None")
    print(f"Wrote validated relationships to {output_path}")
    print(f"Wrote validation report to {report_path}")


if __name__ == "__main__":
    main()