from __future__ import annotations

import csv
import json
import os
import traceback
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from chunking_pipeline import build_chunks_from_csv
from embedding_pipeline import collect_texts, embed_chunks
from neo4j_config import build_neo4j_config

BATCH_SIZE = 200


def _to_neo4j_compatible(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [ _to_neo4j_compatible(item) for item in value ]
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _load_metadata(metadata_path: Path) -> list[dict[str, Any]]:
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_relationships(relationships_path: Path) -> list[dict[str, Any]]:
    with relationships_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class Neo4jImporter:
    def __init__(self, config: dict[str, Any]) -> None:
        self.driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))
        self.database = config["database"]

    def close(self) -> None:
        self.driver.close()

    def ensure_database(self) -> None:
        with self.driver.session() as session:
            session.run("CREATE DATABASE $db IF NOT EXISTS", db=self.database)

    def reset_database(self) -> None:
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def import_documents(self, documents: list[dict[str, Any]], metadata_rows: list[dict[str, Any]]) -> None:
        document_rows = []
        chunk_rows = []

        for document_node in documents:
            metadata = document_node.get("metadata", {})
            document_rows.append({
                "id": document_node["id"],
                "title": document_node["title"],
                "source": "kb+hops",
                "metadata": _to_neo4j_compatible(metadata),
            })

            for chunk in self._iter_chunks(document_node):
                chunk_rows.append({
                    "id": chunk["id"],
                    "document_id": document_node["id"],
                    "type": chunk["type"],
                    "title": chunk["title"],
                    "text": chunk.get("text", ""),
                    "parent_id": chunk.get("parent_id"),
                    "next_id": chunk.get("next_id"),
                    "embedding": _to_neo4j_compatible(chunk.get("embedding", [])),
                    "embedding_dim": chunk.get("embedding_dim", 0),
                })

        with self.driver.session(database=self.database) as session:
            for start in range(0, len(document_rows), BATCH_SIZE):
                batch = document_rows[start:start + BATCH_SIZE]
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (d:Document {id: row.id})
                    SET d.title = row.title,
                        d.source = row.source,
                        d.metadata = row.metadata
                    """,
                    rows=batch,
                )
                print(f"Imported document batch {start // BATCH_SIZE + 1} of {((len(document_rows) + BATCH_SIZE - 1) // BATCH_SIZE)}")

            for start in range(0, len(chunk_rows), BATCH_SIZE):
                batch = chunk_rows[start:start + BATCH_SIZE]
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (c:Chunk {id: row.id})
                    SET c.type = row.type,
                        c.title = row.title,
                        c.text = row.text,
                        c.parent_id = row.parent_id,
                        c.next_id = row.next_id,
                        c.embedding = row.embedding,
                        c.embedding_dim = row.embedding_dim
                    """,
                    rows=batch,
                )
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (d:Document {id: row.document_id}), (c:Chunk {id: row.id})
                    MERGE (c)-[:PART_OF]->(d)
                    """,
                    rows=batch,
                )
                session.run(
                    """
                    UNWIND $rows AS row
                    WITH row WHERE row.parent_id IS NOT NULL
                    MATCH (parent:Chunk {id: row.parent_id}), (child:Chunk {id: row.id})
                    MERGE (parent)-[:PARENT_OF]->(child)
                    """,
                    rows=batch,
                )
                session.run(
                    """
                    UNWIND $rows AS row
                    WITH row WHERE row.next_id IS NOT NULL
                    MATCH (left:Chunk {id: row.id}), (right:Chunk {id: row.next_id})
                    MERGE (left)-[:NEXT]->(right)
                    """,
                    rows=batch,
                )
                print(f"Imported chunk batch {start // BATCH_SIZE + 1} of {((len(chunk_rows) + BATCH_SIZE - 1) // BATCH_SIZE)}")

    def import_relationships(self, relationships: list[dict[str, Any]]) -> None:
        with self.driver.session(database=self.database) as session:
            if not relationships:
                return
            for start in range(0, len(relationships), BATCH_SIZE):
                batch = relationships[start:start + BATCH_SIZE]
                session.run(
                    """
                    UNWIND $rows AS rel
                    MATCH (left:Document {id: rel.left_id}), (right:Document {id: rel.right_id})
                    MERGE (left)-[:RELATIONSHIP {type: rel.type, description: rel.description}]->(right)
                    """,
                    rows=[{
                        "left_id": f"doc-{rel['doc_id']}",
                        "right_id": f"doc-{rel['other_doc_id']}",
                        "type": rel.get("relationship_type", "RELATED"),
                        "description": rel.get("relationship", ""),
                    } for rel in batch],
                )
                print(f"Imported relationship batch {start // BATCH_SIZE + 1} of {((len(relationships) + BATCH_SIZE - 1) // BATCH_SIZE)}")

    def _iter_chunks(self, document_node: dict[str, Any]) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []

        def walk(node: dict[str, Any]) -> None:
            chunks.append(node)
            for child in node.get("children", []):
                walk(child)

        walk(document_node)
        return chunks


def main() -> None:
    root = Path(__file__).resolve().parent / "kb+hops"
    config = build_neo4j_config()
    importer = Neo4jImporter(config)

    try:
        importer.ensure_database()
        importer.reset_database()
        documents = build_chunks_from_csv(root)
        chunks = collect_texts(documents)
        embed_chunks(chunks)
        metadata_rows = _load_metadata(root / "metadata.csv")
        relationships = _load_relationships(root / "relationships.csv")
        importer.import_documents(documents, metadata_rows)
        importer.import_relationships(relationships)
        print("Imported documents, chunks, and relationships into Neo4j")
    except Exception as exc:
        print(f"Neo4j import skipped: {exc}")
        traceback.print_exc()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
