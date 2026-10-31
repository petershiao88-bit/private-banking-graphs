MATCH (p:SharedProduct {ontologyId:'pb_shared', code:$productCode})
WHERE $domain IN ['aum','income']
MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(stage:StagingOutput)
WHERE stage.ontologyId=$domain
  AND (($domain='aum' AND type(mapping)='AUM_IMPLEMENTED_BY')
    OR ($domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))
OPTIONAL MATCH (stage)-[:REPRESENTS_SQL_TABLE]->(target:SqlTable)
OPTIONAL MATCH path=(source:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->(target)
WHERE source.tableKind='external_source'
  AND all(r IN relationships(path) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
WITH p, mapping, stage, target, source, path
ORDER BY stage.outputObject, source.name, [n IN nodes(path) | n.name]
WITH p, mapping, stage, target,
  collect(DISTINCT CASE WHEN path IS NULL THEN null ELSE {
    baseTable:source.name, tablePath:[n IN nodes(path) | n.name],
    rules:[r IN relationships(path) | {
      operation:type(r), operationTypes:r.operationTypes,
      whereConditions:r.whereConditions, joinConditions:r.joinConditions,
      groupExpressions:r.groupExpressions, aggregateExpressions:r.aggregateExpressions,
      selectExpressions:r.selectExpressions, caseExpressions:r.caseExpressions,
      unionBranchOrders:r.unionBranchOrders, unionDeduplication:r.unionDeduplication,
      file:r.file, lineStart:r.lineStart, lineEnd:r.lineEnd, status:r.status, sql:r.sql
    }]
  } END) AS lineage
ORDER BY stage.outputObject
RETURN p.code AS productCode, p.name AS productName, $domain AS domain,
  CASE WHEN $domain='income' AND p.incomeMappingActive=false THEN 'pending_confirmation'
       ELSE p.status END AS status,
  CASE WHEN $domain='income' AND p.incomeMappingActive=false THEN false ELSE true END AS mappingActive,
  false AS calculationAuthorized,
  collect({mappingType:type(mapping), mappingStatus:mapping.status, productScope:mapping.scope,
    outputTable:stage.outputObject, sqlTable:target.name,
    lineageStatus:CASE WHEN size(lineage)=0 THEN 'missing_evidence' ELSE 'traced' END,
    lineage:lineage}) AS mappings
