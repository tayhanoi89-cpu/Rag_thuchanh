"""Build an Obsidian-compatible Wiki Risk Graph from normalized CSV files."""

from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
WIKI_DIR = PROJECT_ROOT / "wiki"

TYPE_DIRECTORIES = {
    "RuiRo": "risks",
    "KiemSoat": "controls",
    "SuKienRuiRo": "events",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def safe_filename(entity: dict[str, str]) -> str:
    normalized = unicodedata.normalize("NFKD", entity["name"])
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return f"{entity['id']}-{slug or 'entity'}.md"


def link_for(entity: dict[str, str], paths: dict[tuple[str, str], str]) -> str:
    entity_type = entity["type"]
    target_path = paths[(entity_type, entity["id"])].removesuffix(".md")
    return f"[[{target_path}|{entity['name']}]]"


def relation_details(relation: dict[str, str]) -> list[str]:
    return [
        f"- relationship_type: `{relation['relationship_type']}`",
        f"- evidence_quote: {relation['evidence_quote']}",
        f"- verification_status: `{relation['verification_status']}`",
    ]


def frontmatter(entity: dict[str, str]) -> list[str]:
    return [
        "---",
        f"id: {entity['id']}",
        f"type: {entity['type']}",
        f"verification_status: {entity['verification_status']}",
        f"data_origin: {entity['data_origin']}",
        "---",
    ]


def field_lines(entity: dict[str, str], fields: list[str]) -> list[str]:
    lines = []
    for field in fields:
        value = entity.get(field, "")
        if value:
            lines.append(f"- {field}: {value}")
    return lines or ["- Chưa có dữ liệu."]


def build_entity_page(
    entity: dict[str, str],
    relations_by_source: dict[str, list[dict[str, str]]],
    relations_by_target: dict[str, list[dict[str, str]]],
    entities_by_id: dict[str, dict[str, str]],
    paths: dict[tuple[str, str], str],
) -> str:
    lines = frontmatter(entity) + ["", f"# {entity['name']}", ""]
    entity_type = entity["type"]

    if entity_type == "RuiRo":
        lines += ["## Thông tin rủi ro", ""]
        lines += field_lines(
            entity,
            [
                "name",
                "description",
                "category",
                "cause",
                "event",
                "impact",
                "inherent_level",
                "residual_level",
                "owner_unit_id",
            ],
        )
        control_relations = [
            relation
            for relation in relations_by_target[entity["id"]]
            if relation["relationship_type"] == "MITIGATES"
        ]
        event_relations = [
            relation
            for relation in relations_by_source[entity["id"]]
            if relation["relationship_type"] == "OBSERVED_AS"
        ]
        lines += ["", "## Kiểm soát liên quan", ""]
        if control_relations:
            for relation in control_relations:
                control = entities_by_id[relation["source_id"]]
                lines += [link_for(control, paths), *relation_details(relation), ""]
        else:
            lines.append("- Chưa có dữ liệu.")
        lines += ["", "## Sự kiện liên quan", ""]
        if event_relations:
            for relation in event_relations:
                event = entities_by_id[relation["target_id"]]
                lines += [link_for(event, paths), *relation_details(relation), ""]
        else:
            lines.append("- Chưa có dữ liệu.")
    elif entity_type == "KiemSoat":
        lines += ["## Thông tin kiểm soát", ""]
        lines += field_lines(entity, ["name", "control_type", "frequency", "owner_role_id", "effectiveness"])
        lines += ["", "## Rủi ro được giảm thiểu", ""]
        risk_relations = [
            relation
            for relation in relations_by_source[entity["id"]]
            if relation["relationship_type"] == "MITIGATES"
        ]
        if risk_relations:
            for relation in risk_relations:
                risk = entities_by_id[relation["target_id"]]
                lines += [link_for(risk, paths), *relation_details(relation), ""]
        else:
            lines.append("- Chưa có dữ liệu.")
    else:
        lines += ["## Thông tin sự kiện", ""]
        lines += field_lines(
            entity,
            ["name", "risk_id", "occurred_at", "discovered_at", "severity", "loss_amount_vnd", "description"],
        )
        lines += ["", "## Rủi ro liên quan", ""]
        risk_relations = [
            relation
            for relation in relations_by_target[entity["id"]]
            if relation["relationship_type"] == "OBSERVED_AS"
        ]
        if risk_relations:
            for relation in risk_relations:
                risk = entities_by_id[relation["source_id"]]
                lines += [link_for(risk, paths), *relation_details(relation), ""]
        else:
            lines.append("- Chưa có dữ liệu.")

    return "\n".join(lines).rstrip() + "\n"


def build_home(entities: list[dict[str, str]], relations: list[dict[str, str]], paths: dict[tuple[str, str], str]) -> str:
    lines = [
        "# Wiki Risk Graph",
        "",
        "## Thống kê",
        "",
        f"- Số node: {len(entities)}",
        f"- Số edge: {len(relations)}",
        "",
        "## Danh mục",
        "",
        "- [Danh sách rủi ro](#ruirro)",
        "- [Danh sách kiểm soát](#kiemsoat)",
        "- [Danh sách sự kiện](#sukienruiro)",
        "",
    ]
    for entity_type, directory in TYPE_DIRECTORIES.items():
        lines += [f"## {entity_type}", ""]
        for entity in sorted((item for item in entities if item["type"] == entity_type), key=lambda item: item["id"]):
            lines.append(f"- {link_for(entity, paths)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    entities = read_csv(OUTPUT_DIR / "entities.csv")
    relations = read_csv(OUTPUT_DIR / "relations.csv")
    entities_by_id = {entity["id"]: entity for entity in entities}
    relations_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    relations_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for relation in relations:
        relations_by_source[relation["source_id"]].append(relation)
        relations_by_target[relation["target_id"]].append(relation)

    paths: dict[tuple[str, str], str] = {}
    for entity in entities:
        directory = TYPE_DIRECTORIES[entity["type"]]
        paths[(entity["type"], entity["id"])] = f"{directory}/{safe_filename(entity)}"

    if WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)
    for directory in TYPE_DIRECTORIES.values():
        (WIKI_DIR / directory).mkdir(parents=True, exist_ok=True)

    for entity in entities:
        relative_path = paths[(entity["type"], entity["id"])]
        output_path = WIKI_DIR / relative_path
        output_path.write_text(
            build_entity_page(entity, relations_by_source, relations_by_target, entities_by_id, paths),
            encoding="utf-8",
        )

    (WIKI_DIR / "Home.md").write_text(build_home(entities, relations, paths), encoding="utf-8")
    wiki_links = sum(1 for path in WIKI_DIR.rglob("*.md") for _ in re.finditer(r"\[\[[^\]]+\]\]", path.read_text(encoding="utf-8")))
    print(f"wiki_pages: {len(entities) + 1}")
    print(f"entity_pages: {len(entities)}")
    print(f"wikilinks: {wiki_links}")
    print("example_path: [[controls/...|KiemSoat]] -> [[risks/...|RuiRo]] -> [[events/...|SuKienRuiRo]]")
    print(f"wiki: {WIKI_DIR}")


if __name__ == "__main__":
    main()