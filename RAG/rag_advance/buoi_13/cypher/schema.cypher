// Run once in the target Neo4j database.
CREATE CONSTRAINT ruirro_id_unique IF NOT EXISTS
FOR (node:RuiRo) REQUIRE node.id IS UNIQUE;

CREATE CONSTRAINT kiemsoat_id_unique IF NOT EXISTS
FOR (node:KiemSoat) REQUIRE node.id IS UNIQUE;

CREATE CONSTRAINT sukienruiro_id_unique IF NOT EXISTS
FOR (node:SuKienRuiRo) REQUIRE node.id IS UNIQUE;