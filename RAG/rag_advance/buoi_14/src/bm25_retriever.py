"""BM25-only retriever over the shared normalized corpus."""

from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi

from .corpus import load_corpus, result


TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text) if not token.isspace()]


class BM25Retriever:
    def __init__(self, rows: list[dict[str, str]] | None = None) -> None:
        self.rows = rows or load_corpus()
        self.tokens = [tokenize(row["text"]) for row in self.rows]
        self.index = BM25Okapi(self.tokens)

    def search(self, question: str, top_k: int = 5) -> list[dict[str, Any]]:
        scores = self.index.get_scores(tokenize(question))
        ranked = sorted(enumerate(scores), key=lambda item: (-float(item[1]), item[0]))[:top_k]
        return [result(self.rows[index], float(score), "bm25", rank) for rank, (index, score) in enumerate(ranked, 1)]