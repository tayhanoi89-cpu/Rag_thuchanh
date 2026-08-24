from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup


INVALID_TEXT_VALUES = {"", "null", "none", "nan", "chua phan loai", "chưa phân loại"}


def clean_html(value: object) -> str:
    if pd.isna(value):
        return ""
    soup = BeautifulSoup(str(value), "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def invalid_value_mask(series: pd.Series) -> pd.Series:
    normalized = series.fillna("").astype(str).str.strip().str.casefold()
    return normalized.isin(INVALID_TEXT_VALUES)


def print_samples(documents: pd.DataFrame) -> None:
    for index, row in documents.head(2).iterrows():
        raw_html = str(row["content_html"]).replace("\n", " ")[:300]
        clean_text = row["content_clean"][:300]
        print(f"Sample {index + 1} id={row['id']}")
        print(f"  content_html: {raw_html}")
        print(f"  content_clean: {clean_text}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate legal document CSVs and clean HTML content.")
    parser.add_argument("--data-dir", default="ner_kb", help="Directory containing metadata.csv and content.csv.")
    parser.add_argument("--output", default="ner_kb/cleaned_documents.csv", help="CSV path for cleaned documents.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"
    if not metadata_path.exists() or not content_path.exists():
        raise FileNotFoundError("metadata.csv and content.csv must both exist.")

    metadata = pd.read_csv(metadata_path, dtype={"id": "string"})
    content = pd.read_csv(content_path, dtype={"id": "string"})
    metadata["id"] = metadata["id"].str.strip()
    content["id"] = content["id"].str.strip()

    metadata_duplicate_ids = int(metadata["id"].duplicated().sum())
    content_duplicate_ids = int(content["id"].duplicated().sum())
    metadata_only_ids = sorted(set(metadata["id"].dropna()) - set(content["id"].dropna()))
    content_only_ids = sorted(set(content["id"].dropna()) - set(metadata["id"].dropna()))

    if metadata_duplicate_ids or content_duplicate_ids:
        raise ValueError("Duplicate IDs prevent a one-to-one merge.")

    documents = metadata.merge(content, on="id", how="inner", validate="one_to_one")
    documents["content_clean"] = documents["content_html"].map(clean_html)

    missing_values = metadata.isna().sum()
    invalid_values = metadata.apply(invalid_value_mask).sum()
    empty_clean_content = int(documents["content_clean"].eq("").sum())

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    documents.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Metadata rows/columns: {metadata.shape[0]}/{metadata.shape[1]}")
    print(f"Content rows/columns: {content.shape[0]}/{content.shape[1]}")
    print(f"Merged documents: {len(documents)}")
    print(f"Duplicate IDs (metadata/content): {metadata_duplicate_ids}/{content_duplicate_ids}")
    print(f"ID mismatches (metadata-only/content-only): {len(metadata_only_ids)}/{len(content_only_ids)}")
    print("Missing values in metadata:")
    print(missing_values.to_string())
    print("Invalid values in metadata (NULL, empty, Chua phan loai):")
    print(invalid_values.to_string())
    print(f"Empty content_clean values: {empty_clean_content}")
    print_samples(documents)
    print(f"Wrote cleaned documents to {output_path}")


if __name__ == "__main__":
    main()