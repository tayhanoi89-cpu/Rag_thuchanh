"""RBAC helper module for Buổi 17.

Reuses RBAC validation from Buổi 14/16 with Role Normalization:
- HR -> HR_Manager
- Risk_Manager -> Risk_Officer
- Staff -> Employee
- Unknown Role -> Default Deny
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "rbac_policy.json"

ROLE_ALIASES = {
    "HR": "HR_Manager",
    "Risk_Manager": "Risk_Officer",
    "Staff": "Employee",
}

VALID_ROLES = {"Admin", "Risk_Officer", "Employee", "HR_Manager", "Guest"}


def normalize_role(role: str) -> str:
    """Normalize input role against aliases and valid role set."""
    clean_role = role.strip()
    return ROLE_ALIASES.get(clean_role, clean_role)


def normalize_roles(roles: Iterable[str]) -> list[str]:
    """Normalize a list of input roles."""
    return [normalize_role(r) for r in roles]


def is_role_authorized(user_role: str, allowed_roles: Iterable[str]) -> bool:
    """Check if normalized user role is present in allowed_roles."""
    norm_role = normalize_role(user_role)
    if norm_role not in VALID_ROLES:
        return False
    return norm_role in set(allowed_roles)
