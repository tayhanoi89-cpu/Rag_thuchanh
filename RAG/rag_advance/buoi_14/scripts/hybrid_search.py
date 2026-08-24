"""Run Hybrid Search and print RRF-ranked candidates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hybrid_retriever import HybridRetriever


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=20)
    args = parser.parse_args()

    results = HybridRetriever().search(args.query, top_k=args.top_k, candidate_k=args.candidate_k)
    print("HYBRID RESULTS")
    print("Rank | Chunk | BM25 rank | Dense rank | RRF | Citation")
    for row in results:
        print(
            f"{row['final_rank']} | {row['chunk_id']} | {row['bm25_rank'] or '-'} | "
            f"{row['dense_rank'] or '-'} | {row['rrf_score']:.8f} | {row['citation']}"
        )
    print(f"candidate_k={args.candidate_k}, rrf_k=60, top_k={args.top_k}")


if __name__ == "__main__":
    main()