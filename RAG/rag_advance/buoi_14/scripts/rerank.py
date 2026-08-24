"""Run Hybrid candidate retrieval followed by Cross-Encoder reranking."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.hybrid_retriever import HybridRetriever
from src.reranker import CandidateReranker


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    candidates = HybridRetriever().search(args.query, top_k=args.candidate_k, candidate_k=args.candidate_k)
    reranker = CandidateReranker()
    results = reranker.rerank(args.query, candidates, args.top_k)
    print(f"RERANKER: {reranker.mode}")
    print("\nBEFORE RERANK")
    for candidate in candidates[:args.top_k]:
        print(f"{candidate['final_rank']}. {candidate['chunk_id']} RRF={candidate['rrf_score']:.8f}")
    print("\nAFTER RERANK")
    for result in results:
        print(
            f"{result['final_rank']}. {result['chunk_id']} "
            f"hybrid_rank={result['hybrid_rank']} rerank={result['rerank_score']:.8f} "
            f"citation={result['citation']}"
        )


if __name__ == "__main__":
    main()