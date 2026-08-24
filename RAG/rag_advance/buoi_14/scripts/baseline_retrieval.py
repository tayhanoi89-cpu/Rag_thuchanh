"""Run and compare BM25-only and dense-only retrieval baselines."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.bm25_retriever import BM25Retriever
from src.corpus import load_corpus
from src.dense_retriever import DenseRetriever, MODEL_NAME


def print_results(title: str, rows: list[dict[str, object]]) -> None:
    print(f"\n{title}")
    for row in rows:
        print(f"{row['rank']}. {row['chunk_id']} score={row['retrieval_score']:.6f}")
        print(f"   citation: {row['citation']}")
        print(f"   text: {str(row['text'])[:240].replace(chr(10), ' ')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    rows = load_corpus()
    bm25_results = BM25Retriever(rows).search(args.query, args.top_k)
    print_results("BM25 RESULTS", bm25_results)
    print(f"\nDENSE MODEL: {MODEL_NAME}")
    dense_results = DenseRetriever(rows).search(args.query, args.top_k)
    print_results("DENSE RESULTS", dense_results)


if __name__ == "__main__":
    main()