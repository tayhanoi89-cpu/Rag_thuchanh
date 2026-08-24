"""Secure Retrieval Module for Buổi 17.

Re-exports SecureRetrievalAdapter wrapping Buổi 14/16 SecureRetriever
with unified metadata and pre-filtering RBAC enforcement.
"""

from __future__ import annotations

import sys
from pathlib import Path

BUOI_17_ROOT = Path(__file__).resolve().parent.parent
if str(BUOI_17_ROOT) not in sys.path:
    sys.path.insert(0, str(BUOI_17_ROOT))

from scripts.secure_retrieval_adapter import SecureRetrievalAdapter

__all__ = ["SecureRetrievalAdapter"]
