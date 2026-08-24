from __future__ import annotations

import os
from typing import Any


def build_neo4j_config() -> dict[str, Any]:
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "abcd1234"),
        "database": os.getenv("NEO4J_DATABASE", "kb-hops"),
    }


def print_connection_hint() -> None:
    config = build_neo4j_config()
    print("Neo4j connection settings")
    print(f"- URI: {config['uri']}")
    print(f"- User: {config['user']}")
    print(f"- Password: {config['password']}")
    print(f"- Database: {config['database']}")
