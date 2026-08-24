from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


REFERENCE_PATTERN = re.compile(
    r"(?<![\w/])\d{1,4}/\d{4}/(?:TT|NĐ|QH|NQ|QĐ|VBHN|CT|KH|TTL)[A-Z0-9-]*(?![\w/-])",
    re.IGNORECASE,
)
TRIGGERS = (
    ("SUA_DOI_BO_SUNG", re.compile(r"sửa đổi\s*,?\s*bổ sung", re.IGNORECASE)),
    ("BAI_BO", re.compile(r"bãi bỏ", re.IGNORECASE)),
    ("THAY_THE", re.compile(r"thay thế", re.IGNORECASE)),
    ("CAN_CU", re.compile(r"căn cứ", re.IGNORECASE)),
)
TRIGGER_PRIORITY = {trigger: index for index, (trigger, _) in enumerate(TRIGGERS)}
TRIGGER_PRIORITY["VAN_BAN_DUOC_NHAC"] = len(TRIGGER_PRIORITY)


def normalize_reference(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def context_for_match(text: str, start: int, end: int, window: int = 350) -> str:
    left = max(text.rfind(".", 0, start) + 1, start - window)
    right_stop = text.find(".", end)
    right = min(len(text), right_stop + 1 if right_stop >= 0 else end + window)
    return " ".join(text[left:right].split())


def trigger_for_context(context: str) -> str:
    for trigger, pattern in TRIGGERS:
        if pattern.search(context):
            return trigger
    return "VAN_BAN_DUOC_NHAC"


def extract_candidates(documents: pd.DataFrame) -> pd.DataFrame:
    candidates: list[dict[str, str]] = []
    for row in documents.itertuples(index=False):
        source_id = str(row.id).strip()
        source_reference = str(row.so_ky_hieu).strip()
        source_normalized = normalize_reference(source_reference)
        text = str(row.content_clean)
        for match in REFERENCE_PATTERN.finditer(text):
            target_reference = match.group(0)
            if normalize_reference(target_reference) == source_normalized:
                continue
            evidence = context_for_match(text, match.start(), match.end())
            candidates.append(
                {
                    "source_id": source_id,
                    "source_so_ky_hieu": source_reference,
                    "target_so_ky_hieu": target_reference,
                    "trigger": trigger_for_context(evidence),
                    "evidence": evidence,
                }
            )

    result = pd.DataFrame(
        candidates,
        columns=["source_id", "source_so_ky_hieu", "target_so_ky_hieu", "trigger", "evidence"],
    )
    if result.empty:
        return result
    result["_trigger_priority"] = result["trigger"].map(TRIGGER_PRIORITY)
    result = result.sort_values(
        ["source_id", "target_so_ky_hieu", "_trigger_priority"], kind="stable"
    ).drop_duplicates(subset=["source_id", "target_so_ky_hieu"])
    return result.drop(columns="_trigger_priority").reset_index(drop=True)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Extract rule-based legal document reference candidates.")
    parser.add_argument("--input", default="ner_kb/cleaned_documents.csv", help="Cleaned document CSV.")
    parser.add_argument("--output", default="ner_kb/relation_candidates.csv", help="Candidate CSV output path.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")
    documents = pd.read_csv(input_path, dtype={"id": "string"})
    required_columns = {"id", "so_ky_hieu", "content_clean"}
    missing_columns = required_columns - set(documents.columns)
    if missing_columns:
        raise ValueError(f"Input is missing columns: {', '.join(sorted(missing_columns))}")

    candidates = extract_candidates(documents)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Total candidates: {len(candidates)}")
    print("Candidates by trigger:")
    print(candidates["trigger"].value_counts().to_string() if not candidates.empty else "None")
    print("Sample candidates:")
    print(candidates.head(10).to_string(index=False) if not candidates.empty else "None")
    print(f"Wrote candidates to {output_path}")


if __name__ == "__main__":
    main()