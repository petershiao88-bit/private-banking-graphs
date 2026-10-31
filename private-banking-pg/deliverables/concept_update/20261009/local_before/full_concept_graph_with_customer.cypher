// Customer is dimension context; existing 30 product-to-total calculation paths remain unchanged.
CALL {
 MATCH (n:PBConcept)
 RETURN collect({key:coalesce(n.productCode,n.metricCode,n.conceptCode),labels:labels(n),properties:n{.productCode,.metricCode,.conceptCode,.name,.definition,.status,.aumStatus,.incomeStatus,.customerId,.customerName,.customerNumber}}) AS conceptNodes
}
CALL {
 MATCH (a:PBConcept)-[r]->(b:PBConcept)
 RETURN collect({id:elementId(r),from:coalesce(a.productCode,a.metricCode,a.conceptCode),to:coalesce(b.productCode,b.metricCode,b.conceptCode),type:type(r),properties:r{.name,.scope,.status,.note}}) AS conceptRelationships
}
CALL {
 MATCH path=(leaf:PBConcept)-[:PB_AUM_MEASURED_BY|PB_INCOME_MEASURED_BY|PB_INCOME_PENDING|PB_AUM_ROLLS_UP_TO|PB_INCOME_ROLLS_UP_TO*1..]->(root:PBConcept)
 WHERE NOT EXISTS { MATCH (:PBConcept)-[:PB_AUM_MEASURED_BY|PB_INCOME_MEASURED_BY|PB_INCOME_PENDING|PB_AUM_ROLLS_UP_TO|PB_INCOME_ROLLS_UP_TO]->(leaf) }
  AND NOT EXISTS { MATCH (root)-[:PB_AUM_MEASURED_BY|PB_INCOME_MEASURED_BY|PB_INCOME_PENDING|PB_AUM_ROLLS_UP_TO|PB_INCOME_ROLLS_UP_TO]->(:PBConcept) }
  AND all(n IN nodes(path) WHERE n:PBConcept)
  AND (all(r IN relationships(path) WHERE type(r) IN ['PB_AUM_MEASURED_BY','PB_AUM_ROLLS_UP_TO'])
   OR all(r IN relationships(path) WHERE type(r) IN ['PB_INCOME_MEASURED_BY','PB_INCOME_PENDING','PB_INCOME_ROLLS_UP_TO']))
 RETURN collect(DISTINCT {domain:CASE WHEN root:PBConceptAUM THEN 'aum' ELSE 'income' END,
  nodeKeys:[n IN nodes(path)|coalesce(n.productCode,n.metricCode,n.conceptCode)],relationshipIds:[r IN relationships(path)|elementId(r)]}) AS businessPaths
}
RETURN {nodes:conceptNodes,relationships:conceptRelationships} AS conceptGraph,businessPaths
