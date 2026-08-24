"""Validate the generated Obsidian Wiki Risk Graph and its normalized data."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
WIKI_DIR = PROJECT_ROOT / "wiki"
WIKILINK_PATTERN = re.compile(r"\[\[([^]|#]+)(?:\|[^\]]+)?\]\]")
PAGE_ID_PATTERN = re.compile(r"^id:\s*(\S+)\s*$", re.MULTILINE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def markdown_pages() -> list[Path]:
    return sorted(WIKI_DIR.rglob("*.md")) if WIKI_DIR.exists() else []


def page_target(path: str) -> str:
    return path.removesuffix(".md").replace("\\", "/")


def validate_wikilinks(pages: list[Path]) -> tuple[int, list[str], dict[Path, list[str]]]:
    existing_targets = {page_target(str(page.relative_to(WIKI_DIR))) for page in pages}
    broken: list[str] = []
    links_by_page: dict[Path, list[str]] = {}
    total_links = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        targets = WIKILINK_PATTERN.findall(text)
        links_by_page[page] = targets
        total_links += len(targets)
        for target in targets:
            if target not in existing_targets:
                broken.append(f"{page.relative_to(WIKI_DIR)} -> {target}")
    return total_links, broken, links_by_page


def collect_page_ids(pages: list[Path]) -> tuple[dict[str, list[str]], list[str]]:
    ids_to_pages: dict[str, list[str]] = defaultdict(list)
    pages_without_id: list[str] = []
    for page in pages:
        match = PAGE_ID_PATTERN.search(page.read_text(encoding="utf-8"))
        if match:
            ids_to_pages[match.group(1)].append(str(page.relative_to(WIKI_DIR)))
        elif page.name != "Home.md":
            pages_without_id.append(str(page.relative_to(WIKI_DIR)))
    return ids_to_pages, pages_without_id


def markdown_bullets(items: list[str], empty_message: str = "Không có.") -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty_message}"]


def validate() -> str:
    entities = read_csv(OUTPUT_DIR / "entities.csv")
    relations = read_csv(OUTPUT_DIR / "relations.csv")
    pages = markdown_pages()
    total_links, broken_links, links_by_page = validate_wikilinks(pages)
    ids_to_pages, pages_without_id = collect_page_ids(pages)

    entity_ids = [entity["id"] for entity in entities]
    duplicate_entity_ids = sorted(
        entity_id for entity_id, count in Counter(entity_ids).items() if count > 1
    )
    entity_id_set = set(entity_ids)
    page_ids_not_in_entities = sorted(
        entity_id for entity_id in ids_to_pages if entity_id not in entity_id_set
    )
    relation_orphans = sorted(
        {
            f"source_id={relation['source_id']}"
            for relation in relations
            if relation["source_id"] not in entity_id_set
        }
        | {
            f"target_id={relation['target_id']}"
            for relation in relations
            if relation["target_id"] not in entity_id_set
        }
    )

    relations_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    relations_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for relation in relations:
        relations_by_target[relation["target_id"]].append(relation)
        relations_by_source[relation["source_id"]].append(relation)

    risks_without_controls = sorted(
        entity["id"]
        for entity in entities
        if entity["type"] == "RuiRo"
        and not any(relation["relationship_type"] == "MITIGATES" for relation in relations_by_target[entity["id"]])
    )
    risks_without_events = sorted(
        entity["id"]
        for entity in entities
        if entity["type"] == "RuiRo"
        and not any(relation["relationship_type"] == "OBSERVED_AS" for relation in relations_by_source[entity["id"]])
    )
    linked_pages = {page for page, links in links_by_page.items() if links}
    for page, links in links_by_page.items():
        for target in links:
            target_path = WIKI_DIR / f"{target}.md"
            if target_path.exists():
                linked_pages.add(target_path)
    orphan_pages = sorted(
        str(page.relative_to(WIKI_DIR))
        for page in pages
        if page.name != "Home.md" and page not in linked_pages
    )

    program_errors = broken_links + page_ids_not_in_entities + pages_without_id
    data_errors = duplicate_entity_ids + relation_orphans + risks_without_controls + risks_without_events
    lines = [
        "# Wiki Risk Graph Validation Report",
        "",
        "## Summary",
        "",
        f"- Markdown files: {len(pages)}",
        f"- Wikilinks: {total_links}",
        f"- Program errors: {len(program_errors)}",
        f"- Data errors: {len(data_errors)}",
        f"- Orphan pages: {len(orphan_pages)}",
        "",
        "## Program Errors",
        "",
        "### Broken wikilinks",
        *markdown_bullets(broken_links),
        "",
        "### Page IDs missing from entities.csv",
        *markdown_bullets(page_ids_not_in_entities),
        "",
        "### Entity pages without an ID",
        *markdown_bullets(pages_without_id),
        "",
        "## Data Errors",
        "",
        "### Duplicate entity IDs",
        *markdown_bullets(duplicate_entity_ids),
        "",
        "### Relation orphan references",
        *markdown_bullets(relation_orphans),
        "",
        "### RuiRo without MITIGATES control",
        *markdown_bullets(risks_without_controls),
        "",
        "### RuiRo without OBSERVED_AS event",
        *markdown_bullets(risks_without_events),
        "",
        "## Orphan Pages",
        "",
        *markdown_bullets(orphan_pages),
        "",
        "## Result",
        "",
        "PASS: No validation issues found." if not program_errors and not data_errors and not orphan_pages else "FAIL: Review the issues listed above.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    report = validate()
    report_path = OUTPUT_DIR / "wiki_validation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()