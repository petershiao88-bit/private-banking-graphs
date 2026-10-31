"""Read-only graph queries; retain business paths and complete dependency evidence."""
CONCEPTS = """MATCH a=(c:PBConcept:PBConceptProduct)-[:PB_AUM_MEASURED_BY]->(:PBConcept:PBConceptMetric:PBConceptAUM)
 -[:PB_AUM_ROLLS_UP_TO*0..4]->(:PBConcept:PBConceptMetric:PBConceptAUM {metricCode:'aum_total_month_end'})
MATCH i=(c)-[:PB_INCOME_MEASURED_BY|PB_INCOME_PENDING]->(:PBConcept:PBConceptMetric:PBConceptIncome)
 -[:PB_INCOME_ROLLS_UP_TO*0..4]->(:PBConcept:PBConceptMetric:PBConceptIncome {metricCode:'income_total_customer_month'})
WITH c,a,i,
 [m IN tail(nodes(a)) WHERE 'aum' IN $domains AND m.metricCode IN $metricCodes | {metricCode:m.metricCode,domain:'aum'}] +
 [m IN tail(nodes(i)) WHERE 'income' IN $domains AND m.metricCode IN $metricCodes | {metricCode:m.metricCode,domain:'income'}] AS matchedScopes
WHERE size(matchedScopes)>0
OPTIONAL MATCH (p:SharedProduct {ontologyId:'pb_shared',code:c.productCode})
CALL (p) {
 OPTIONAL MATCH path=(p)-[:MEASURED_BY_AUM]->(:BusinessMetric)
  -[:AUM_ROLLS_UP_TO*0..4]->(:BusinessMetric {key:'aum:metric:aum_total_month_end'})
 RETURN collect(DISTINCT CASE WHEN path IS NULL THEN null ELSE {
  nodes:[n IN nodes(path) | {key:n.key,labels:labels(n),properties:properties(n)}],
  relationships:[r IN relationships(path) | {type:type(r),from:startNode(r).key,to:endNode(r).key,properties:properties(r)}]
 } END) AS aumPaths
}
CALL (p) {
 OPTIONAL MATCH path=(p)-[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(:BusinessMetric)
  -[:INCOME_ROLLS_UP_TO*0..4]->(:BusinessMetric {key:'income:metric:income_total_customer_month'})
 RETURN collect(DISTINCT CASE WHEN path IS NULL THEN null ELSE {
  nodes:[n IN nodes(path) | {key:n.key,labels:labels(n),properties:properties(n)}],
  relationships:[r IN relationships(path) | {type:type(r),from:startNode(r).key,to:endNode(r).key,properties:properties(r)}]
 } END) AS incomePaths
}
RETURN matchedScopes,c.productCode AS productCode,c.name AS productName,c.definition AS definition,
 c.status AS status,c.aumStatus AS aumStatus,c.incomeStatus AS incomeStatus,
 [m IN tail(nodes(a)) | {metricCode:m.metricCode,name:m.name,definition:m.definition,status:m.status}] AS aumMetrics,
 [m IN tail(nodes(i)) | {metricCode:m.metricCode,name:m.name,definition:m.definition,status:m.status}] AS incomeMetrics,
 {identity:{conceptProductCode:c.productCode,sharedProductCode:p.code,sharedProductKey:p.key},
  sharedProduct:CASE WHEN p IS NULL THEN null ELSE {key:p.key,labels:labels(p),properties:properties(p)} END,
  aumPaths:aumPaths,incomePaths:incomePaths} AS conceptEvidence
ORDER BY productCode"""

MAPPINGS = """UNWIND $selectedPaths AS selection
WITH DISTINCT selection
MATCH (p:SharedProduct {ontologyId:'pb_shared',code:selection.productCode})
MATCH businessPath=(p)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(:BusinessMetric)
 -[:AUM_ROLLS_UP_TO|INCOME_ROLLS_UP_TO*0..4]->(:BusinessMetric)
WHERE [n IN nodes(businessPath)|n.key]=selection.nodeKeys
 AND [r IN relationships(businessPath)|type(r)]=selection.relationshipTypes
 AND [r IN relationships(businessPath)|properties(r)]=selection.relationshipProperties
 AND any(n IN nodes(businessPath) WHERE n.key=selection.queryMetricKey AND n.code=selection.queryMetricCode)
 AND all(n IN tail(nodes(businessPath)) WHERE n.ontologyId=selection.domain)
 AND nodes(businessPath)[1].key=CASE WHEN selection.domain='aum' THEN p.aumMetricKey ELSE p.incomeMetricKey END
WITH DISTINCT p,selection
CALL (p,selection) {
 OPTIONAL MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(stage:StagingOutput)
 WHERE stage.ontologyId=selection.domain
  AND ((selection.domain='aum' AND type(mapping)='AUM_IMPLEMENTED_BY') OR
       (selection.domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))
 OPTIONAL MATCH (stage)-[bridge:REPRESENTS_SQL_TABLE]->(target:SqlTable)
 OPTIONAL MATCH path=(upstream:SqlTable)-[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*0..16]->(target)
 WHERE all(r IN relationships(path) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
 WITH p,selection,mapping,stage,bridge,target,collect(DISTINCT path) AS paths
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
 WITH p,selection,mapping,stage,bridge,target,paths,tables,
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
 selection.queryMetricCode AS queryMetricCode,p.code AS productCode,p.name AS productName,selection.domain AS domain,
 CASE WHEN selection.domain='income' AND p.incomeMappingActive=false THEN 'pending_confirmation' ELSE p.status END AS status,mappings
ORDER BY productCode,domain"""

REGISTRY = """MATCH (m:PBConcept:PBConceptMetric)
WITH m,CASE WHEN m:PBConceptAUM THEN 'aum' ELSE 'income' END AS domain
OPTIONAL MATCH (original:BusinessMetric {ontologyId:domain,code:m.metricCode})
RETURN m.metricCode AS metric_code,m.name AS metric_name,[m.name,m.metricCode] AS aliases,
 coalesce(original.definition,m.definition) AS definition,domain,m.status AS metric_status
ORDER BY domain,metric_code"""
