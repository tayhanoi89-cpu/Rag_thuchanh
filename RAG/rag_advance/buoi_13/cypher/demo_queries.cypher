// A. View the complete MVP graph.
MATCH (source)-[relationship]->(target)
RETURN source, relationship, target
ORDER BY source.id, type(relationship), target.id;

// B. Find controls mitigating one risk. Replace $risk_id when running.
MATCH (control:KiemSoat)-[relationship:MITIGATES]->(risk:RuiRo {id: $risk_id})
RETURN control.id AS control_id, control.name AS control_name,
       relationship, risk.id AS risk_id, risk.name AS risk_name;

// C. Find observed events for one risk. Replace $risk_id when running.
MATCH (risk:RuiRo {id: $risk_id})-[relationship:OBSERVED_AS]->(event:SuKienRuiRo)
RETURN risk.id AS risk_id, risk.name AS risk_name,
       relationship, event.id AS event_id, event.name AS event_name;

// D. Traverse KiemSoat -> RuiRo -> SuKienRuiRo.
MATCH (control:KiemSoat)-[:MITIGATES]->(risk:RuiRo)-[:OBSERVED_AS]->(event:SuKienRuiRo)
RETURN control.id AS control_id, control.name AS control_name,
       risk.id AS risk_id, risk.name AS risk_name,
       event.id AS event_id, event.name AS event_name;

// E. Find risks without a mitigating control.
MATCH (risk:RuiRo)
WHERE NOT EXISTS {
    MATCH (:KiemSoat)-[:MITIGATES]->(risk)
}
RETURN risk.id AS risk_id, risk.name AS risk_name;

// F. Find relationships that are not VERIFIED.
MATCH (source)-[relationship]->(target)
WHERE coalesce(relationship.verification_status, '') <> 'VERIFIED'
RETURN source.id AS source_id, type(relationship) AS relationship_type,
       target.id AS target_id, relationship.verification_status AS verification_status,
       relationship.evidence_quote AS evidence_quote;