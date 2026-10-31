// Preserve the user baseline exactly; append Customer paths without multiplying rows.
MATCH aumPath=(p:SharedProduct {ontologyId:'pb_shared'})
  -[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key:'aum:metric:aum_total_month_end'})

MATCH incomePath=(p)
  -[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key:'income:metric:income_total_customer_month'})

OPTIONAL MATCH mappingPath=(p)
  -[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->
  (stage:StagingOutput)
  -[:REPRESENTS_SQL_TABLE]->
  (target:SqlTable)

OPTIONAL MATCH lineagePath=(source:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->
  (target)
WHERE source.tableKind='external_source'
  AND all(r IN relationships(lineagePath)
    WHERE r.status='active_sql'
      AND r.sourceRole='primary_reference')

CALL {
  WITH aumPath, incomePath
  MATCH customerPath=(metric:BusinessMetric)
    -[:MEASURES_CUSTOMER]->
    (customer:MappingCustomer {key:'pb_shared:customer:customer'})
  WHERE metric IN nodes(aumPath) OR metric IN nodes(incomePath)
  RETURN collect(DISTINCT customerPath) AS customerPaths
}
RETURN aumPath, incomePath, mappingPath, lineagePath, customerPaths;
