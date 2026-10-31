// Full business context; calculation paths contain measurement and rollup links only.
CALL {
 MATCH (n:PBConcept)
 RETURN collect({key:coalesce(n.productCode,n.metricCode,n.conceptCode),labels:labels(n),properties:n{.advisorId,.advisorName,.aliases,.aumDefinition,.businessChannel,.businessPurpose,.businessRole,.conceptCode,.customerId,.customerName,.customerNeed,.customerNumber,.definition,.employeeNumber,.incomeDefinition,.metricCode,.name,.organizationType,.productCategory,.productCode,.roleResponsibilities,.serviceDescription,.serviceScope,.targetCustomer,.subsidiary,.currencyType,.structureType,.depositorType,.fundType,.marketRegion,.dealingMode}}) AS conceptNodes
}
CALL {
 MATCH (a:PBConcept)-[r]->(b:PBConcept)
 RETURN collect({id:elementId(r),from:coalesce(a.productCode,a.metricCode,a.conceptCode),to:coalesce(b.productCode,b.metricCode,b.conceptCode),type:type(r),properties:r{.definition,.businessConstraint}}) AS conceptRelationships
}
CALL {
 MATCH path=(leaf:PBConcept:PBConceptProduct)-[:PB_AUM_MEASURED_BY|PB_INCOME_MEASURED_BY|PB_AUM_ROLLS_UP_TO|PB_INCOME_ROLLS_UP_TO*1..]->(root:PBConcept:PBConceptMetric)
 WHERE all(n IN nodes(path) WHERE n:PBConcept)
  AND ((root:PBConceptAUM AND root.metricCode='aum_total' AND all(r IN relationships(path) WHERE type(r) IN ['PB_AUM_MEASURED_BY','PB_AUM_ROLLS_UP_TO']))
   OR (root:PBConceptIncome AND root.metricCode='income_total' AND all(r IN relationships(path) WHERE type(r) IN ['PB_INCOME_MEASURED_BY','PB_INCOME_ROLLS_UP_TO'])))
 RETURN collect(DISTINCT {domain:CASE WHEN root:PBConceptAUM THEN 'aum' ELSE 'income' END,
  nodeKeys:[n IN nodes(path)|coalesce(n.productCode,n.metricCode,n.conceptCode)],relationshipIds:[r IN relationships(path)|elementId(r)]}) AS businessPaths
}
RETURN {nodes:conceptNodes,relationships:conceptRelationships} AS conceptGraph,businessPaths
