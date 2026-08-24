from __future__ import annotations

from neo4j import GraphDatabase
from neo4j_config import build_neo4j_config


def main() -> None:
    config = build_neo4j_config()
    driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))

    try:
        with driver.session(database=config["database"]) as session:
            counts = session.run(
                """
                MATCH (d:Document)
                RETURN count(d) AS document_count
                """
            ).single()
            rel_count = session.run(
                """
                MATCH ()-[r]->()
                WHERE type(r) IN ['PART_OF', 'PARENT_OF', 'NEXT', 'RELATIONSHIP']
                RETURN count(r) AS relation_count
                """
            ).single()
            print(f"Document count: {counts['document_count']}")
            print(f"Relationship count: {rel_count['relation_count']}")
            print("Cypher queries to run in Neo4j Browser:")
            print("MATCH (d:Document) RETURN count(d) AS document_count;")
            print("MATCH ()-[r]->() RETURN count(r) AS relation_count;")
            print("MATCH (d:Document)-[:PART_OF]->(c:Chunk) RETURN count(c) AS chunk_count;")
            print("MATCH (a:Chunk)-[:NEXT]->(b:Chunk) RETURN count(*) AS next_count;")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
