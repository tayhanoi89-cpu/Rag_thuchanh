"""Assign RBAC metadata to the normalized Buoi 14 retrieval corpus."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ROLES, validate_roles


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"

HR_ROLES = validate_roles(("Admin", "HR_Manager"))
RISK_ROLES = validate_roles(("Admin", "Risk_Officer", "Employee"))
GENERAL_ROLES = validate_roles(ROLES)

HR_KEYWORDS = (
    "nhan su",
    "luong thuong",
    "tuyen dung",
    "bo nhiem",
    "ky luat",
    "tien luong",
)
RISK_KEYWORDS = (
    "tin dung",
    "rui ro",
    "han muc",
    "phe duyet vay",
    "thu hoi no",
    "no xau",
)
REQUIRED_COLUMNS = {"document_id", "text"}


def normalize_for_matching(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.casefold().split())


def classify_security(row: pd.Series) -> tuple[str, tuple[str, ...]]:
    metadata = " ".join(str(row.get(column, "")) for column in ("document_id", "title", "document_type"))
    searchable_text = normalize_for_matching(metadata + " " + str(row.get("text", ""))[:1200])
    if any(keyword in searchable_text for keyword in HR_KEYWORDS):
        return "HR", HR_ROLES
    if any(keyword in searchable_text for keyword in RISK_KEYWORDS):
        return "Risk", RISK_ROLES
    return "General", GENERAL_ROLES


def assign_security_tags(dataframe: pd.DataFrame) -> pd.DataFrame:
    missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    tagged = dataframe.copy()
    classifications = tagged.apply(classify_security, axis=1)
    tagged["security_class"] = classifications.map(lambda item: item[0])
    tagged["allowed_roles"] = classifications.map(lambda item: json.dumps(item[1], ensure_ascii=False))
    return tagged


def validate_security_tags(tagged: pd.DataFrame) -> None:
    if tagged.empty:
        raise ValueError("Tagged corpus is empty")

    parsed_roles = tagged["allowed_roles"].map(json.loads)
    if parsed_roles.map(lambda roles: not roles or not all(role in ROLES for role in roles)).any():
        raise ValueError("Every chunk must have at least one valid allowed role")

def print_report(tagged: pd.DataFrame, output_path: Path) -> None:
    print(f"chunks_tagged: {len(tagged)}")
    print("security_class_counts:")
    for security_class, count in Counter(tagged["security_class"]).most_common():
        print(f"  {security_class}: {count}")

    print("representative_samples:")
    for security_class in ("HR", "Risk", "General"):
        samples = tagged.loc[tagged["security_class"] == security_class]
        if samples.empty:
            print(f"  {security_class}: unavailable in source corpus")
        else:
            sample = samples.iloc[0]
            print(
                f"  {security_class}: document_id={sample['document_id']}, "
                f"allowed_roles={sample['allowed_roles']}"
            )
    print(f"output: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    dataframe = pd.read_csv(args.input)
    tagged = assign_security_tags(dataframe)
    validate_security_tags(tagged)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tagged.to_csv(args.output, index=False, encoding="utf-8")
    print_report(tagged, args.output)


if __name__ == "__main__":
    main()