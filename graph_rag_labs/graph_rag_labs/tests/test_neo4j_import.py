import neo4j_import


def test_to_neo4j_compatible_serializes_metadata_and_keeps_embedding_arrays():
    metadata = {"title": "Sample", "nested": {"key": "value"}}
    embedding = [0.1, 0.2, 0.3]

    assert neo4j_import._to_neo4j_compatible(metadata) == '{"nested": {"key": "value"}, "title": "Sample"}'
    assert neo4j_import._to_neo4j_compatible(embedding) == embedding
