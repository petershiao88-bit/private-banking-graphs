MATCH a=(p:PBConcept:PBConceptProduct)-[:PB_AUM_MEASURED_BY]->(:PBConcept:PBConceptMetric:PBConceptAUM)
  -[:PB_AUM_ROLLS_UP_TO*0..4]->(:PBConcept:PBConceptMetric:PBConceptAUM {metricCode:'aum_total_month_end'})
MATCH i=(p)-[:PB_INCOME_MEASURED_BY|PB_INCOME_PENDING]->(:PBConcept:PBConceptMetric:PBConceptIncome)
  -[:PB_INCOME_ROLLS_UP_TO*0..4]->(:PBConcept:PBConceptMetric:PBConceptIncome {metricCode:'income_total_customer_month'})
RETURN p.productCode AS productCode, p.name AS productName,
  p.definition AS definition, p.status AS status,
  p.aumStatus AS aumStatus, p.incomeStatus AS incomeStatus,
  [m IN tail(nodes(a)) | {metricCode:m.metricCode, name:m.name, definition:m.definition, status:m.status}] AS aumMetrics,
  [m IN tail(nodes(i)) | {metricCode:m.metricCode, name:m.name, definition:m.definition, status:m.status}] AS incomeMetrics
ORDER BY productCode
