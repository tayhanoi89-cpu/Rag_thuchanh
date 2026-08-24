"""Normalize the Buoi 14 source documents into a retrieval corpus."""

from __future__ import annotations

import csv
import html
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


csv.field_size_limit(10_000_000)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTED_SOURCE_DIR = PROJECT_ROOT.parent / "kb+hops"
FALLBACK_SOURCE_DIR = PROJECT_ROOT.parents[2] / "graph_rag_labs" / "graph_rag_labs" / "kb+hops"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"


class HtmlTextParser(HTMLParser):
    """Extract readable text while retaining block boundaries."""

    BLOCK_TAGS = {
        "address", "article", "aside", "br", "div", "h1", "h2", "h3", "h4",
        "h5", "h6", "li", "p", "section", "table", "tr", "td",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def resolve_source_dir() -> Path:
    if DOCUMENTED_SOURCE_DIR.exists():
        return DOCUMENTED_SOURCE_DIR
    if FALLBACK_SOURCE_DIR.exists():
        print(f"source_path_fallback: {FALLBACK_SOURCE_DIR}")
        return FALLBACK_SOURCE_DIR
    raise FileNotFoundError(
        "Could not find kb+hops source data at the documented or fallback path."
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def clean_html(raw_html: str) -> str:
    parser = HtmlTextParser()
    parser.feed(raw_html or "")
    parser.close()
    decoded = html.unescape("".join(parser.parts))
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in decoded.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def required_value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def build_rows(source_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    metadata_rows = read_csv(source_dir / "metadata.csv")
    content_rows = read_csv(source_dir / "content.csv")
    relationship_rows = read_csv(source_dir / "relationships.csv")
    metadata_by_id = {required_value(row, "id"): row for row in metadata_rows}

    normalized: list[dict[str, str]] = []
    for content in content_rows:
        document_id = required_value(content, "id")
        metadata = metadata_by_id.get(document_id, {})
        normalized.append(
            {
                "chunk_id": f"{document_id}__full",
                "document_id": document_id,
                "text": clean_html(content.get("content_html", "")),
                "source_file": "content.csv",
                "title": required_value(metadata, "title"),
                "document_type": required_value(metadata, "loai_van_ban"),
                "effective_date": required_value(metadata, "ngay_co_hieu_luc"),
                "status": required_value(metadata, "tinh_trang_hieu_luc"),
                "citation_code": required_value(metadata, "so_ky_hieu"),
                "issued_date": required_value(metadata, "ngay_ban_hanh"),
                "source_document_id": document_id,
            }
        )

    relationship_types = sorted({required_value(row, "relationship_type") for row in relationship_rows})
    return normalized, relationship_types


def write_output(rows: list[dict[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else ["chunk_id", "document_id", "text", "source_file"]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_dir = resolve_source_dir()
    rows, relationship_types = build_rows(source_dir)
    duplicate_chunk_ids = sorted(
        chunk_id for chunk_id, count in Counter(row["chunk_id"] for row in rows).items() if count > 1
    )
    if duplicate_chunk_ids:
        raise ValueError(f"Duplicate chunk_id values: {', '.join(duplicate_chunk_ids)}")

    missing_text = sum(not row["text"] for row in rows)
    write_output(rows)
    print(f"chunks: {len(rows)}")
    print(f"documents: {len({row['document_id'] for row in rows})}")
    print(f"missing_text: {missing_text}")
    print(f"duplicate_chunk_ids: {duplicate_chunk_ids or 'none'}")
    print(f"relationship_types_read: {relationship_types}")
    for index, row in enumerate(rows[:3], start=1):
        print(f"sample_{index}: chunk_id={row['chunk_id']}, document_id={row['document_id']}, text={row['text'][:180]}")
    print(f"output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()