MATCH (c:PBConcept:PBConceptProduct)
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
ORDER BY productCode
