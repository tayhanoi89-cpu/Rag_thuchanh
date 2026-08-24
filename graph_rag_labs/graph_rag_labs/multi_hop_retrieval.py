from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

from embedding_pipeline import MODEL_NAME
from neo4j_config import build_neo4j_config


@dataclass
class RetrievalChunk:
    chunk_id: str
    document_id: str
    document_title: str
    chunk_type: str
    chunk_title: str
    text: str
    score: float


@dataclass
class HopDocument:
    document_id: str
    document_title: str
    min_hop: int


def parse_relation_types(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class MultiHopRetriever:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        config = build_neo4j_config()
        self.driver = GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"]))
        self.database = config["database"]
        self.model = SentenceTransformer(model_name, device="cpu")

    def close(self) -> None:
        self.driver.close()

    def embed_question(self, question: str) -> list[float]:
        embedding = self.model.encode(question, normalize_embeddings=True, convert_to_numpy=True)
        return embedding.tolist()

    def vector_search_chunks(self, query_embedding: list[float], top_k: int) -> list[RetrievalChunk]:
        cypher = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document)
        WHERE c.embedding IS NOT NULL AND size(c.embedding) = size($query_embedding)
        WITH c, d,
             reduce(dot = 0.0, i IN range(0, size($query_embedding) - 1) |
                 dot + toFloat(c.embedding[i]) * toFloat($query_embedding[i])) AS dot,
             sqrt(reduce(acc = 0.0, i IN range(0, size(c.embedding) - 1) |
                 acc + toFloat(c.embedding[i]) * toFloat(c.embedding[i]))) AS c_norm,
             sqrt(reduce(acc = 0.0, i IN range(0, size($query_embedding) - 1) |
                 acc + toFloat($query_embedding[i]) * toFloat($query_embedding[i]))) AS q_norm
        WITH c, d,
             CASE
                 WHEN c_norm = 0.0 OR q_norm = 0.0 THEN 0.0
                 ELSE dot / (c_norm * q_norm)
             END AS score
        ORDER BY score DESC
        LIMIT $top_k
        RETURN c.id AS chunk_id,
               d.id AS document_id,
               d.title AS document_title,
               c.type AS chunk_type,
               c.title AS chunk_title,
               c.text AS text,
               score
        """

        with self.driver.session(database=self.database) as session:
            records = session.run(cypher, query_embedding=query_embedding, top_k=top_k)
            return [
                RetrievalChunk(
                    chunk_id=record["chunk_id"],
                    document_id=record["document_id"],
                    document_title=record["document_title"],
                    chunk_type=record["chunk_type"],
                    chunk_title=record["chunk_title"] or "",
                    text=record["text"] or "",
                    score=float(record["score"]),
                )
                for record in records
            ]

    def expand_multi_hop_documents(
        self,
        seed_document_ids: list[str],
        hops: int,
        relation_types: list[str],
        max_documents: int,
    ) -> list[HopDocument]:
        if hops <= 0 or not seed_document_ids:
            return []

        hop_depth = max(1, int(hops))

        cypher = f"""
        UNWIND $seed_document_ids AS seed_id
        MATCH (seed:Document {{id: seed_id}})
        MATCH p = (seed)-[rels:RELATIONSHIP*1..{hop_depth}]-(doc:Document)
        WHERE doc.id <> seed.id
          AND all(r IN rels WHERE size($relation_types) = 0 OR r.type IN $relation_types)
        WITH doc, min(length(p)) AS min_hop
        RETURN doc.id AS document_id,
               doc.title AS document_title,
               min_hop
        ORDER BY min_hop ASC, document_id ASC
        LIMIT $max_documents
        """

        with self.driver.session(database=self.database) as session:
            records = session.run(
                cypher,
                seed_document_ids=seed_document_ids,
                relation_types=relation_types,
                max_documents=max_documents,
            )
            return [
                HopDocument(
                    document_id=record["document_id"],
                    document_title=record["document_title"],
                    min_hop=int(record["min_hop"]),
                )
                for record in records
            ]

    def fetch_chunks_by_documents(self, document_ids: list[str], per_document_limit: int) -> list[RetrievalChunk]:
        if not document_ids:
            return []

        cypher = """
        UNWIND $document_ids AS doc_id
        MATCH (d:Document {id: doc_id})<-[:PART_OF]-(c:Chunk)
        WITH d, c
        ORDER BY c.type ASC, c.id ASC
        WITH d, collect(c)[0..$per_document_limit] AS top_chunks
        UNWIND top_chunks AS c
        RETURN c.id AS chunk_id,
               d.id AS document_id,
               d.title AS document_title,
               c.type AS chunk_type,
               c.title AS chunk_title,
               c.text AS text,
               0.0 AS score
        """

        with self.driver.session(database=self.database) as session:
            records = session.run(
                cypher,
                document_ids=document_ids,
                per_document_limit=per_document_limit,
            )
            return [
                RetrievalChunk(
                    chunk_id=record["chunk_id"],
                    document_id=record["document_id"],
                    document_title=record["document_title"],
                    chunk_type=record["chunk_type"],
                    chunk_title=record["chunk_title"] or "",
                    text=record["text"] or "",
                    score=0.0,
                )
                for record in records
            ]

    def search_context(
        self,
        question: str,
        top_k: int,
        hops: int,
        relation_types: list[str],
        max_hop_documents: int,
        hop_chunk_limit: int,
    ) -> dict[str, Any]:
        query_embedding = self.embed_question(question)
        direct_chunks = self.vector_search_chunks(query_embedding=query_embedding, top_k=top_k)

        seed_document_ids = list(dict.fromkeys(chunk.document_id for chunk in direct_chunks))
        hop_documents = self.expand_multi_hop_documents(
            seed_document_ids=seed_document_ids,
            hops=hops,
            relation_types=relation_types,
            max_documents=max_hop_documents,
        )

        hop_document_ids = [doc.document_id for doc in hop_documents]
        hop_chunks = self.fetch_chunks_by_documents(
            document_ids=hop_document_ids,
            per_document_limit=hop_chunk_limit,
        )

        return {
            "question": question,
            "params": {
                "top_k": top_k,
                "hops": hops,
                "relation_types": relation_types,
                "max_hop_documents": max_hop_documents,
                "hop_chunk_limit": hop_chunk_limit,
            },
            "direct_chunks": [chunk.__dict__ for chunk in direct_chunks],
            "seed_document_ids": seed_document_ids,
            "hop_documents": [doc.__dict__ for doc in hop_documents],
            "hop_chunks": [chunk.__dict__ for chunk in hop_chunks],
        }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vector retrieval + multi-hop document expansion in Neo4j.")
    parser.add_argument("--question", required=True, help="User question to retrieve context for.")
    parser.add_argument("--k", type=int, default=5, help="Top-k chunks from vector search.")
    parser.add_argument("--hops", type=int, default=1, help="Maximum number of document hops.")
    parser.add_argument(
        "--relation-types",
        default="CAN_CU,THAY_THE,HOP_NHAT",
        help="Comma-separated RELATIONSHIP.type filters. Empty string means all relation types.",
    )
    parser.add_argument(
        "--max-hop-documents",
        type=int,
        default=20,
        help="Maximum expanded documents returned from multi-hop traversal.",
    )
    parser.add_argument(
        "--hop-chunk-limit",
        type=int,
        default=2,
        help="Number of chunks collected per expanded document.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    relation_types = parse_relation_types(args.relation_types)

    retriever = MultiHopRetriever()
    try:
        result = retriever.search_context(
            question=args.question,
            top_k=args.k,
            hops=args.hops,
            relation_types=relation_types,
            max_hop_documents=args.max_hop_documents,
            hop_chunk_limit=args.hop_chunk_limit,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
