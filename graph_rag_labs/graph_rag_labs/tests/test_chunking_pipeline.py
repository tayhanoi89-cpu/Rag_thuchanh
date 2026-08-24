from pathlib import Path

import chunking_pipeline


def test_build_chunks_creates_hierarchy_and_next_links():
    data_dir = Path(__file__).resolve().parents[1] / "kb+hops"
    documents = chunking_pipeline.build_chunks_from_csv(data_dir)

    assert documents, "Expected at least one document chunk"
    first_document = documents[0]
    assert first_document["type"] == "document"
    assert first_document["title"]
    assert first_document["children"], "Expected at least one child chunk"

    first_chapter = first_document["children"][0]
    assert first_chapter["type"] == "chapter"
    assert first_chapter["children"], "Expected chapter to contain article chunks"

    first_article = first_chapter["children"][0]
    assert first_article["type"] == "article"
    assert first_article["children"], "Expected article to contain clause chunks"

    first_clause = first_article["children"][0]
    assert first_clause["type"] == "clause"
    assert first_clause["text"]
    assert first_clause["parent_id"] == first_article["id"]


def test_build_chunks_assigns_ids_to_all_descendants():
    data_dir = Path(__file__).resolve().parents[1] / "kb+hops"
    documents = chunking_pipeline.build_chunks_from_csv(data_dir)

    def walk(node):
        if node.get("type") == "clause":
            assert "id" in node
            assert node["parent_id"]
        for child in node.get("children", []):
            walk(child)

    for document in documents:
        walk(document)
