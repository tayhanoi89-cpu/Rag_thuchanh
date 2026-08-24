from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any
from html import unescape
from bs4 import BeautifulSoup

csv.field_size_limit(10_000_000)


class ChunkingError(RuntimeError):
    pass


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr in {"style", "class", "id"}:
                del tag[attr]

    for tag in soup.find_all(["p", "span", "div", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"]):
        text = tag.get_text("\n", strip=True)
        if not text:
            continue
        tag.clear()
        tag.append(text)

    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{2,}", "\n", unescape(text)).strip()


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()


def _extract_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_chapter: dict[str, Any] | None = None
    current_article: dict[str, Any] | None = None
    current_muc: dict[str, Any] | None = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if current_chapter is None and current_article is None and current_muc is None:
            if not re.match(r"^Chương\s+\w+", line, flags=re.IGNORECASE):
                continue

        if current_chapter is not None and current_article is None and current_muc is None:
            if line.isupper() and not re.match(r"^(Chương|Mục|Điều)\s+", line, flags=re.IGNORECASE):
                continue

        if re.match(r"^Chương\s+\w+", line, flags=re.IGNORECASE):
            current_chapter = {
                "type": "chapter",
                "title": line,
                "text": line,
                "children": [],
            }
            current_article = None
            current_muc = None
            sections.append(current_chapter)
        elif re.match(r"^Mục\s+\d+", line, flags=re.IGNORECASE):
            current_muc = {
                "type": "muc",
                "title": line,
                "text": line,
                "children": [],
            }
            if current_chapter is not None:
                current_chapter["children"].append(current_muc)
            current_article = None
        elif re.match(r"^Điều\s+\d+", line, flags=re.IGNORECASE):
            current_article = {
                "type": "article",
                "title": line,
                "text": line,
                "children": [],
            }
            if current_muc is not None:
                current_muc["children"].append(current_article)
            elif current_chapter is not None:
                current_chapter["children"].append(current_article)
        else:
            clause = {
                "type": "clause",
                "title": line,
                "text": line,
                "children": [],
            }
            if current_article is not None:
                current_article["children"].append(clause)
            elif current_muc is not None:
                current_muc["children"].append(clause)
            elif current_chapter is not None:
                current_chapter["children"].append(clause)
            else:
                sections.append(clause)

    return sections


def build_chunks_from_csv(data_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(data_dir)
    content_path = root / "content.csv"
    metadata_path = root / "metadata.csv"

    if not content_path.exists() or not metadata_path.exists():
        raise ChunkingError(f"Missing input files in {root}")

    documents: list[dict[str, Any]] = []
    with content_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ChunkingError("No content rows found")

    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        metadata_rows = list(csv.DictReader(handle))

    metadata_by_id = {row["id"]: row for row in metadata_rows}

    for row in rows:
        item_id = row.get("id", "").strip()
        html_text = row.get("content_html", "")
        metadata = metadata_by_id.get(item_id, {})
        title = _normalize_title(metadata.get("title", f"Document {item_id}"))
        cleaned_text = _clean_html(html_text)
        sections = _extract_sections(cleaned_text)

        document_node = {
            "id": f"doc-{item_id}",
            "type": "document",
            "title": title,
            "text": cleaned_text,
            "children": sections,
            "metadata": metadata,
        }

        documents.append(document_node)

    def assign_ids(node: dict[str, Any], parent_id: str | None = None, prefix: str | None = None) -> None:
        if parent_id is not None:
            node["parent_id"] = parent_id
        if prefix is None:
            node_id = node["id"]
        else:
            node_id = f"{prefix}-{node['type']}"
        node["id"] = node_id

        children = node.get("children", [])
        for index, child in enumerate(children):
            child_prefix = f"{node_id}-{index + 1}"
            child["parent_id"] = node_id
            child["id"] = child_prefix
            child["next_id"] = (
                f"{child_prefix}-{children[index + 1]['type']}"
                if index + 1 < len(children)
                else None
            )
            assign_ids(child, node_id, child_prefix)

    for document_node in documents:
        assign_ids(document_node)

    return documents


def print_sample_chunks(documents: list[dict[str, Any]], limit: int = 3) -> None:
    print("Sample chunk hierarchy:")
    for doc_index, document_node in enumerate(documents[:limit], start=1):
        print(f"{doc_index}. Document: {document_node['title']}")
        for child in document_node.get("children", [])[:3]:
            print(f"   - {child['type'].upper()}: {child['title']}")
            for grandchild in child.get("children", [])[:2]:
                print(f"       * {grandchild['type'].upper()}: {grandchild['title']}")
        print()


if __name__ == "__main__":
    documents = build_chunks_from_csv(Path(__file__).resolve().parent / "kb+hops")
    print_sample_chunks(documents)
