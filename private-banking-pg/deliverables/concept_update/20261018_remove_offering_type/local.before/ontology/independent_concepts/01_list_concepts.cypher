// Start from offerings so income-only services and AUM-only products are retained.
MATCH (p:PBConcept:PBConceptProduct)
CALL {
 WITH p
 OPTIONAL MATCH path=(p)-[:PB_AUM_MEASURED_BY]->(:PBConcept:PBConceptMetric:PBConceptAUM)
   -[:PB_AUM_ROLLS_UP_TO*0..]->(:PBConcept:PBConceptMetric:PBConceptAUM {metricCode:'aum_total'})
 WITH collect(path) AS paths
 UNWIND CASE WHEN size(paths)=0 THEN [null] ELSE paths END AS path
 UNWIND CASE WHEN path IS NULL THEN [null] ELSE tail(nodes(path)) END AS metric
 RETURN collect(DISTINCT CASE WHEN metric IS NULL THEN null ELSE metric{.metricCode,.name,.definition} END) AS aumMetrics
}
CALL {
 WITH p
 OPTIONAL MATCH path=(p)-[:PB_INCOME_MEASURED_BY]->(:PBConcept:PBConceptMetric:PBConceptIncome)
   -[:PB_INCOME_ROLLS_UP_TO*0..]->(:PBConcept:PBConceptMetric:PBConceptIncome {metricCode:'income_total'})
 WITH collect(path) AS paths
 UNWIND CASE WHEN size(paths)=0 THEN [null] ELSE paths END AS path
 UNWIND CASE WHEN path IS NULL THEN [null] ELSE tail(nodes(path)) END AS metric
 RETURN collect(DISTINCT CASE WHEN metric IS NULL THEN null ELSE metric{.metricCode,.name,.definition} END) AS incomeMetrics
}
RETURN p.productCode AS productCode, p.name AS productName,
  p.aumDefinition AS aumDefinition, p.incomeDefinition AS incomeDefinition,
  p.offeringType AS offeringType, p.definition AS definition,
  p.productCategory AS productCategory, p.businessChannel AS businessChannel,
  p.customerNeed AS customerNeed, p.serviceDescription AS serviceDescription,
  p.subsidiary AS subsidiary, p.currencyType AS currencyType,
  p.structureType AS structureType, p.depositorType AS depositorType,
  p.fundType AS fundType, p.marketRegion AS marketRegion, p.dealingMode AS dealingMode,
  aumMetrics, incomeMetrics
ORDER BY productCode
