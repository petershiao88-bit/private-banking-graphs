UNWIND $selectedPaths AS selection
WITH DISTINCT selection
MATCH businessPath=(start:SharedProduct)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|AUM_ROLLS_UP_TO|INCOME_ROLLS_UP_TO*1..8]->(:BusinessMetric)
WHERE [n IN nodes(businessPath)|n.key]=selection.nodeKeys
 AND [r IN relationships(businessPath)|type(r)]=selection.relationshipTypes
 AND [r IN relationships(businessPath)|properties(r)]=selection.relationshipProperties
 AND any(n IN nodes(businessPath) WHERE n.key=selection.queryMetricKey AND n.code=selection.queryMetricCode)
 AND all(n IN nodes(businessPath) WHERE n:SharedProduct OR (n:BusinessMetric AND n.ontologyId=selection.domain))
UNWIND [n IN nodes(businessPath) WHERE n:SharedProduct AND n.key IN selection.anchorConceptKeys] AS p
WITH DISTINCT p,selection,[r IN relationships(businessPath) WHERE startNode(r).key=p.key AND type(r) IN ['MEASURED_BY_AUM','MEASURED_BY_INCOME','INCOME_DEFINITION_PENDING']] AS measures
WITH p,selection,head(measures) AS measure
CALL (p,selection,measure) {
 OPTIONAL MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(stage:StagingOutput)
 WHERE stage.ontologyId=selection.domain
  AND ((selection.domain='aum' AND type(mapping)='AUM_IMPLEMENTED_BY') OR
       (selection.domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))
  AND (mapping.metricKey IS NULL OR mapping.metricKey=endNode(measure).key)
  AND (measure.scope IS NULL OR mapping.scope IS NULL OR measure.scope=mapping.scope)
 WITH p,selection,measure,mapping,stage,
 CASE WHEN size([(p)-[r:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(m:BusinessMetric)
 WHERE m.ontologyId=selection.domain AND (mapping.metricKey IS NULL OR mapping.metricKey=m.key)
 AND (mapping.scope IS NULL OR r.scope IS NULL OR mapping.scope=r.scope)|r])=1
 THEN CASE WHEN mapping.metricKey=endNode(measure).key THEN 'explicit_metric'
 WHEN measure.scope IS NOT NULL AND mapping.scope=measure.scope THEN 'explicit_scope'
 ELSE 'unambiguous_legacy_measurement' END
 ELSE 'ambiguous_anchor_bridge' END AS bindingStatus
 OPTIONAL MATCH (stage)-[bridge:REPRESENTS_SQL_TABLE]->(target:SqlTable)
 OPTIONAL MATCH path=(upstream:SqlTable)-[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*0..16]->(target)
 WHERE all(r IN relationships(path) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
 WITH p,selection,mapping,stage,bridge,target,bindingStatus,collect(DISTINCT path) AS paths
 WITH *,reduce(acc=[],path IN paths | acc+nodes(path)) AS tableNodes
 CALL (tableNodes) {
  UNWIND tableNodes AS t
  WITH DISTINCT t
  OPTIONAL MATCH (s:SqlStatement)-[:TARGETS_TABLE]->(t)
  WHERE s.status='active_sql' AND s.sourceRole='primary_reference'
  OPTIONAL MATCH (s)-[:READS_TABLE]->(source:SqlTable)
  WITH t,s,collect(DISTINCT source.key) AS requiredTableKeys
  WITH t,collect(DISTINCT CASE WHEN s IS NULL THEN null ELSE
   {statementKey:s.key,properties:properties(s),requiredTableKeys:requiredTableKeys} END) AS statements
  OPTIONAL MATCH (incoming:SqlTable)-[r:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM]->(t)
  WHERE r.status='active_sql' AND r.sourceRole='primary_reference'
  WITH t,statements,collect(DISTINCT CASE WHEN r IS NULL THEN null ELSE
   {from:incoming.key,to:t.key,type:type(r),properties:properties(r)} END) AS requiredIncoming
  RETURN collect({key:t.key,labels:labels(t),properties:properties(t),statements:statements,requiredIncoming:requiredIncoming}) AS tables
 }
 WITH p,selection,mapping,stage,bridge,target,bindingStatus,paths,tables,
 [path IN paths WHERE head(nodes(path)).tableKind='external_source' | {
  baseTable:head(nodes(path)).name,tablePath:[n IN nodes(path)|n.name],
  rules:[r IN relationships(path)|{operation:type(r),statementKey:r.statementKey,lineageEdgeId:r.lineageEdgeId,
   operationTypes:r.operationTypes,whereConditions:r.whereConditions,joinConditions:r.joinConditions,
   groupExpressions:r.groupExpressions,aggregateExpressions:r.aggregateExpressions,selectExpressions:r.selectExpressions,
   caseExpressions:r.caseExpressions,unionBranchOrders:r.unionBranchOrders,unionBranchCounts:r.unionBranchCounts,
   unionDeduplication:r.unionDeduplication,joinTypes:r.joinTypes,joinInputRoles:r.joinInputRoles,
   havingConditions:r.havingConditions,inputSteps:r.inputSteps,ruleSteps:r.ruleSteps,
   file:r.file,lineStart:r.lineStart,lineEnd:r.lineEnd,status:r.status,sourceRole:r.sourceRole,sqlTextKind:r.sqlTextKind,sql:r.sql}]
 }] AS lineage
 RETURN collect(DISTINCT CASE WHEN stage IS NULL THEN null ELSE {
  mappingType:type(mapping),mappingStatus:mapping.status,productScope:mapping.scope,
  bindingConceptKey:p.key,bindingStatus:bindingStatus,
  implementation:{from:p.key,to:stage.key,type:type(mapping),properties:properties(mapping)},
  stage:{key:stage.key,labels:labels(stage),properties:properties(stage)},
  bridge:CASE WHEN bridge IS NULL THEN null ELSE {from:stage.key,to:target.key,type:type(bridge),properties:properties(bridge)} END,
  outputTable:stage.outputObject,sqlTable:target.name,targetTableKey:target.key,
  lineageStatus:CASE WHEN size(lineage)=0 THEN 'missing_evidence' ELSE 'traced' END,lineage:lineage,
  sqlEvidence:{maxDepth:16,tables:tables,
   paths:[path IN paths|{tableKeys:[n IN nodes(path)|n.key],relationships:[r IN relationships(path)|
    {from:startNode(r).key,to:endNode(r).key,type:type(r),properties:properties(r)}]}]}
 } END) AS mappings
}
RETURN selection.pathKey AS pathKey,selection.queryMetricKey AS queryMetricKey,
 selection.queryMetricCode AS queryMetricCode,p.key AS bindingConceptKey,p.code AS productCode,p.name AS productName,selection.domain AS domain,
 CASE WHEN selection.domain='income' AND p.incomeMappingActive=false THEN 'pending_confirmation' ELSE p.status END AS status,mappings
ORDER BY productCode,domain
