"""CLI demo for unified retrieval and direct Graph RAG hints."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph_hints import direct_graph_hints
from src.unified_retriever import retrieve


METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--method", choices=METHODS, default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    results = retrieve(args.query, args.method, args.top_k)
    print(f"QUERY: {args.query}")
    print(f"METHOD: {args.method}")
    print("\nRESULTS")
    for row in results:
        print(f"{row['rank']}. {row['chunk_id']} | score={row['score']:.6f}")
        print(f"   document_id: {row['document_id']}")
        print(f"   citation: {row['citation']}")
        if "hybrid_score" in row:
            print(f"   hybrid_score: {row['hybrid_score']:.8f} | rerank_score: {row['rerank_score']:.8f}")
        print(f"   text: {row['text'][:280].replace(chr(10), ' ')}")

    document_ids = list(dict.fromkeys(row["document_id"] for row in results))
    chunk_ids = list(dict.fromkeys(row["chunk_id"] for row in results))
    hints, error = direct_graph_hints(document_ids)
    print("\nGRAPH HINTS")
    print(f"document_ids: {document_ids}")
    print(f"chunk_ids: {chunk_ids}")
    if error:
        print(error)
    elif hints:
        for hint in hints:
            print(
                f"{hint['source_id']} -[{hint['relationship_type']}]-> {hint['target_id']} "
                f"({hint.get('relationship_label') or 'no label'})"
            )
    else:
        print("No direct Buoi 14 relationships found for retrieved documents.")


if __name__ == "__main__":
    main()