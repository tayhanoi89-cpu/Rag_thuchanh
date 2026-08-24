"""Shared configuration for the Buoi 15 RBAC exercises."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_ENV_PATH = PROJECT_ROOT / ".env"

ROLES = (
    "Admin",
    "HR_Manager",
    "Risk_Officer",
    "Employee",
    "Guest",
)
VALID_ROLES = frozenset(ROLES)

load_dotenv(DATABASE_ENV_PATH)


def get_neo4j_config() -> dict[str, str]:
    """Return Neo4j settings loaded from the local .env file."""
    required_keys = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise RuntimeError(f"Missing Neo4j settings in {DATABASE_ENV_PATH}: {missing}")

    return {
        "uri": os.environ["NEO4J_URI"],
        "user": os.environ["NEO4J_USER"],
        "password": os.environ["NEO4J_PASSWORD"],
        "database": os.environ["NEO4J_DATABASE"],
    }


def validate_roles(roles: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Validate and normalize a collection of RBAC roles."""
    invalid_roles = sorted(set(roles) - VALID_ROLES)
    if invalid_roles:
        raise ValueError(f"Unknown roles: {', '.join(invalid_roles)}")
    return tuple(dict.fromkeys(roles))