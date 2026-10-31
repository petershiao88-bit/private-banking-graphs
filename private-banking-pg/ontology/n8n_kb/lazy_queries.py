"""Concept catalog first; expand routes only for concepts selected by Jev."""
from evidence_queries import MAPPINGS as PREVIOUS_MAPPINGS,REGISTRY

CATALOG = """MATCH (c:PBConcept:PBConceptProduct)
CALL (c) {
 MATCH (c)-[:PB_AUM_MEASURED_BY]->(:PBConcept:PBConceptMetric)
  -[:PB_AUM_ROLLS_UP_TO*0..8]->(m:PBConcept:PBConceptMetric)
 WHERE 'aum' IN $domains AND m.metricCode IN $metricCodes
 RETURN collect(DISTINCT {domain:'aum',metricCode:m.metricCode}) AS aumScopes
}
CALL (c) {
 MATCH (c)-[:PB_INCOME_MEASURED_BY|PB_INCOME_PENDING]->(:PBConcept:PBConceptMetric)
  -[:PB_INCOME_ROLLS_UP_TO*0..8]->(m:PBConcept:PBConceptMetric)
 WHERE 'income' IN $domains AND m.metricCode IN $metricCodes
 RETURN collect(DISTINCT {domain:'income',metricCode:m.metricCode}) AS incomeScopes
}
WITH c,aumScopes+incomeScopes AS matchedScopes
WHERE size(matchedScopes)>0
OPTIONAL MATCH (p:SharedProduct {ontologyId:'pb_shared',code:c.productCode})
RETURN p.key AS conceptKey,c.productCode AS productCode,c.name AS productName,
 c.definition AS definition,c.status AS status,c.aumStatus AS aumStatus,c.incomeStatus AS incomeStatus,
 matchedScopes
ORDER BY productCode"""

PATHS = """UNWIND $selectedConcepts AS selection
MATCH (p:SharedProduct {key:selection.conceptKey,ontologyId:'pb_shared'})
WHERE p.code=selection.productCode
MATCH path=(p)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|AUM_ROLLS_UP_TO|INCOME_ROLLS_UP_TO*1..8]->(root:BusinessMetric)
WHERE root.key=CASE WHEN selection.domain='aum' THEN 'aum:metric:aum_total_month_end' ELSE 'income:metric:income_total_customer_month' END
 AND all(r IN relationships(path) WHERE type(r) IN CASE WHEN selection.domain='aum' THEN ['MEASURED_BY_AUM','AUM_ROLLS_UP_TO'] ELSE ['MEASURED_BY_INCOME','INCOME_DEFINITION_PENDING','INCOME_ROLLS_UP_TO'] END)
 AND all(n IN nodes(path) WHERE n:SharedProduct OR (n:BusinessMetric AND n.ontologyId=selection.domain))
 AND any(n IN nodes(path) WHERE n:BusinessMetric AND n.code IN $metricCodes)
WITH DISTINCT selection,p,path
RETURN selection.conceptKey AS requestedConceptKey,selection.domain AS domain,
 {identity:{conceptProductCode:p.code,sharedProductCode:p.code,sharedProductKey:p.key},
  sharedProduct:{key:p.key,labels:labels(p),properties:properties(p)}} AS conceptEvidence,
 {nodes:[n IN nodes(path)|{key:n.key,labels:labels(n),properties:properties(n)}],
  relationships:[r IN relationships(path)|{type:type(r),from:startNode(r).key,to:endNode(r).key,properties:properties(r)}]} AS businessPath
ORDER BY requestedConceptKey,domain"""

# Explicit metric/scope annotations are preferred. A legacy product bridge is usable
# only when the selected measurement relationship is unambiguous, never because
# each product is assumed to have one route. Roll-up alternatives remain separate.
MAPPINGS = PREVIOUS_MAPPINGS.replace(
 "MATCH (p:SharedProduct {ontologyId:'pb_shared',code:selection.productCode})\nMATCH businessPath=(p)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(:BusinessMetric)\n -[:AUM_ROLLS_UP_TO|INCOME_ROLLS_UP_TO*0..4]->(:BusinessMetric)",
 "MATCH businessPath=(start:SharedProduct)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|AUM_ROLLS_UP_TO|INCOME_ROLLS_UP_TO*1..8]->(:BusinessMetric)")
MAPPINGS=MAPPINGS.replace(
 " AND all(n IN tail(nodes(businessPath)) WHERE n.ontologyId=selection.domain)\n AND nodes(businessPath)[1].key=CASE WHEN selection.domain='aum' THEN p.aumMetricKey ELSE p.incomeMetricKey END\nWITH DISTINCT p,selection\nCALL (p,selection) {",
 " AND all(n IN nodes(businessPath) WHERE n:SharedProduct OR (n:BusinessMetric AND n.ontologyId=selection.domain))\n"
 "UNWIND [n IN nodes(businessPath) WHERE n:SharedProduct AND n.key IN selection.anchorConceptKeys] AS p\n"
 "WITH DISTINCT p,selection,[r IN relationships(businessPath) WHERE startNode(r).key=p.key AND type(r) IN ['MEASURED_BY_AUM','MEASURED_BY_INCOME','INCOME_DEFINITION_PENDING']] AS measures\n"
 "WITH p,selection,head(measures) AS measure\n"
 "CALL (p,selection,measure) {")
MAPPINGS=MAPPINGS.replace(
 "       (selection.domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))",
 "       (selection.domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))\n"
 "  AND (mapping.metricKey IS NULL OR mapping.metricKey=endNode(measure).key)\n"
 "  AND (measure.scope IS NULL OR mapping.scope IS NULL OR measure.scope=mapping.scope)\n"
 " WITH p,selection,measure,mapping,stage,\n"
 " CASE WHEN size([(p)-[r:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(m:BusinessMetric)\n"
 " WHERE m.ontologyId=selection.domain AND (mapping.metricKey IS NULL OR mapping.metricKey=m.key)\n"
 " AND (mapping.scope IS NULL OR r.scope IS NULL OR mapping.scope=r.scope)|r])=1\n"
 " THEN CASE WHEN mapping.metricKey=endNode(measure).key THEN 'explicit_metric'\n"
 " WHEN measure.scope IS NOT NULL AND mapping.scope=measure.scope THEN 'explicit_scope'\n"
 " ELSE 'unambiguous_legacy_measurement' END\n"
 " ELSE 'ambiguous_anchor_bridge' END AS bindingStatus")
MAPPINGS=MAPPINGS.replace("WITH p,selection,mapping,stage,bridge,target,collect", "WITH p,selection,mapping,stage,bridge,target,bindingStatus,collect")
MAPPINGS=MAPPINGS.replace("WITH p,selection,mapping,stage,bridge,target,paths,tables,", "WITH p,selection,mapping,stage,bridge,target,bindingStatus,paths,tables,")
MAPPINGS=MAPPINGS.replace("mappingType:type(mapping),mappingStatus:mapping.status,productScope:mapping.scope,", "mappingType:type(mapping),mappingStatus:mapping.status,productScope:mapping.scope,\n  bindingConceptKey:p.key,bindingStatus:bindingStatus,")
MAPPINGS=MAPPINGS.replace("selection.queryMetricCode AS queryMetricCode,p.code", "selection.queryMetricCode AS queryMetricCode,p.key AS bindingConceptKey,p.code")
