CALL {
UNWIND $selectedPaths AS selection
UNWIND selection.productCodes AS productCode
MATCH (p:SharedProduct {ontologyId:'pb_shared',code:productCode})
WITH DISTINCT p,selection,null AS measure
CALL (p,selection,measure) {
 OPTIONAL MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(stage:StagingOutput)
 WHERE stage.ontologyId=selection.domain
  AND ((selection.domain='aum' AND type(mapping)='AUM_IMPLEMENTED_BY') OR
       (selection.domain='income' AND type(mapping) IN ['INCOME_IMPLEMENTED_BY','INCOME_DECLARED_BY']))

 WITH p,selection,measure,mapping,stage,
 'candidate_bridge' AS bindingStatus
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
RETURN selection.pathKey AS pathKey,p.key AS bindingConceptKey,p.code AS productCode,p.name AS productName,selection.domain AS domain,
 CASE WHEN selection.domain='income' AND p.incomeMappingActive=false THEN 'pending_confirmation' ELSE p.status END AS status,mappings


UNION ALL
UNWIND $selectedPaths AS selection
UNWIND selection.productCodes AS productCode
MATCH (p:MappingDraftProduct {code:productCode})
WHERE p.key='draft:pb:20261012:product:'+productCode
MATCH (p)-[measure:MEASURED_BY_AUM|MEASURED_BY_INCOME]->(metric:MappingDraftMetric)
WHERE type(measure)=CASE WHEN selection.domain='aum' THEN 'MEASURED_BY_AUM' ELSE 'MEASURED_BY_INCOME' END
 AND metric.key='draft:pb:20261012:metric:'+CASE head(selection.metricCodes)
 WHEN 'aum_deposit' THEN 'aum_deposit_month_end'
 WHEN 'aum_bank_investment' THEN 'aum_bank_investment_month_end'
 WHEN 'aum_securities' THEN 'aum_securities_month_end'
 WHEN 'aum_insurance' THEN 'aum_insurance_month_end'
 ELSE head(selection.metricCodes) END
 AND metric.key STARTS WITH 'draft:pb:20261012:metric:'
MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY]->(source:MappingDraftTable)
WHERE type(mapping)=CASE WHEN selection.domain='aum' THEN 'AUM_IMPLEMENTED_BY' ELSE 'INCOME_IMPLEMENTED_BY' END
 AND mapping.mappingRole='base_source' AND source.tableRole='source'
 AND source.key STARTS WITH 'draft:pb:20261012:table:'
CALL (mapping,source) {
 MATCH (dependency:MappingDraftTable)
 WHERE dependency.tableRole='source' AND dependency.key STARTS WITH 'draft:pb:20261012:table:'
  AND (dependency.name IN coalesce(mapping.dependencySourceTables,[]) OR dependency=source)
 RETURN collect({key:dependency.key,labels:labels(dependency),properties:properties(dependency)}) AS sourceTables
}
CALL {
 MATCH (a)-[r]->(b)
 WHERE a.key STARTS WITH 'draft:pb:20261012:'
  AND (a:MappingDraftEntity OR a:MappingDraftOrganization OR a:MappingDraftMetric)
  AND b.key STARTS WITH 'draft:pb:20261012:'
  AND (b:MappingDraftEntity OR b:MappingDraftOrganization OR b:MappingDraftTable)
  AND type(r) IN ['ASSIGNED_TO','SCOPED_TO','IDENTIFIED_IN']
 RETURN collect({id:elementId(r),from:a.key,to:b.key,type:type(r),properties:properties(r),
  sourceNode:{key:a.key,labels:labels(a),properties:properties(a)},
  targetNode:{key:b.key,labels:labels(b),properties:properties(b)}}) AS dimensionEvidence
}
WITH p,selection,metric,measure,mapping,source,sourceTables,dimensionEvidence ORDER BY source.name
RETURN selection.pathKey AS pathKey,p.key AS bindingConceptKey,p.code AS productCode,p.name AS productName,selection.domain AS domain,
 'mapping_draft_rules' AS status,
 collect({mappingFormat:'mapping_draft_rules',mappingKey:mapping.draftEdgeKey,
  implementation:{from:p.key,to:source.key,type:type(mapping),properties:properties(mapping)},
  measurement:{id:elementId(measure),from:p.key,to:metric.key,type:type(measure),properties:properties(measure)},
  sourceTables:sourceTables,dimensionEvidence:dimensionEvidence,
  calculationAuthorized:false}) AS mappings
}
RETURN *
ORDER BY productCode,domain