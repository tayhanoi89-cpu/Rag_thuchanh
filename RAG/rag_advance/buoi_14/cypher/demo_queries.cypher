// A. View only Buoi 14 graph data.
MATCH (source {lab_session: 'buoi_14'})-[relationship]->(target {lab_session: 'buoi_14'})
RETURN source, relationship, target
LIMIT 100;

// B. View documents and their full-document clauses.
MATCH (document:VanBan {lab_session: 'buoi_14'})-[:CONTAINS]->(clause:DieuKhoan)
RETURN document, clause
LIMIT 50;

// C. NEXT is not created because the current corpus has full-document chunks,
// not verified article ordering. Use this query after verified article chunks exist.
MATCH (first:DieuKhoan {lab_session: 'buoi_14'})-[:NEXT]->(second:DieuKhoan {lab_session: 'buoi_14'})
RETURN first, second
LIMIT 50;

// D. View direct document relationships present in relationships.csv.
MATCH (source:VanBan {lab_session: 'buoi_14'})-[relationship]->(target:VanBan {lab_session: 'buoi_14'})
RETURN source.id AS source_id, type(relationship) AS relationship_type,
       relationship.relationship AS relationship_label,
       target.id AS target_id, relationship.source_file AS source_file
ORDER BY relationship_type, source_id, target_id;

// E. Find Buoi 14 nodes without an outgoing or incoming relationship.
MATCH (node {lab_session: 'buoi_14'})
WHERE NOT (node)--()
RETURN labels(node) AS labels, node.id AS id;