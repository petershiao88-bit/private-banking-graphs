UNWIND $selectedConcepts AS selection
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
ORDER BY requestedConceptKey,domain
