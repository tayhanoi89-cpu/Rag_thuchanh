from __future__ import annotations

from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from chunking_pipeline import build_chunks_from_csv
from embedding_pipeline import collect_texts, embed_chunks
from neo4j_config import build_neo4j_config


def iter_chunks(document: dict[str, Any]):
    for child in document.get("children", []):
        yield from iter_chunks(child)
    yield document


def load_to_neo4j() -> None:
    config = build_neo4j_config()
    driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))

    try:
        with driver.session(database=config["database"]) as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")

            documents = build_chunks_from_csv(Path(__file__).resolve().parent / "kb+hops")
            chunks = collect_texts(documents)
            embed_chunks(chunks)

            for doc in documents:
                session.run(
                    """
                    MERGE (d:Document {id: $id})
                    SET d.title = $title,
                        d.source = $source,
                        d.metadata = $metadata
                    """,
                    id=doc["id"],
                    title=doc["title"],
                    source="kb+hops",
                    metadata=doc.get("metadata", {}),
                )

            for chunk in chunks:
                session.run(
                    """
                    MERGE (c:Chunk {id: $id})
                    SET c.type = $type,
                        c.title = $title,
                        c.text = $text,
                        c.embedding = $embedding,
                        c.embedding_dim = $embedding_dim
                    """,
                    id=chunk["id"],
                    type=chunk["type"],
                    title=chunk.get("title", ""),
                    text=chunk.get("text", ""),
                    embedding=chunk.get("embedding", []),
                    embedding_dim=chunk.get("embedding_dim", 0),
                )

                if chunk.get("parent_id"):
                    session.run(
                        """
                        MATCH (parent:Chunk {id: $parent_id}), (child:Chunk {id: $chunk_id})
                        MERGE (parent)-[:PARENT_OF]->(child)
                        """,
                        parent_id=chunk["parent_id"],
                        chunk_id=chunk["id"],
                    )

                if chunk.get("next_id"):
                    session.run(
                        """
                        MATCH (left:Chunk {id: $chunk_id}), (right:Chunk {id: $next_id})
                        MERGE (left)-[:NEXT]->(right)
                        """,
                        chunk_id=chunk["id"],
                        next_id=chunk["next_id"],
                    )

                session.run(
                    """
                    MATCH (d:Document {id: $document_id}), (c:Chunk {id: $chunk_id})
                    MERGE (c)-[:PART_OF]->(d)
                    """,
                    document_id=chunk["parent_id"].split("-", 1)[0] if chunk.get("parent_id") else doc["id"],
                    chunk_id=chunk["id"],
                )

            print("Loaded documents and chunks into Neo4j")
    finally:
        driver.close()


if __name__ == "__main__":
    load_to_neo4j()
