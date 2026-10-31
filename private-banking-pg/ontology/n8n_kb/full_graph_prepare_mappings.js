const context=$('Concept Path Result').first().json,rows=graphRows($input.first().json);
const mappingsByKey=new Map(),candidatesByKey=new Map(),tablesByKey=new Map(),statementsByKey=new Map(),edgesById=new Map();
const edgeId=edge=>edge.properties.lineageEdgeId||stableKey('sql-edge',[edge.from,edge.type,edge.to,edge.properties.statementKey]);
for(const row of rows)for(const mapping of row.mappings||[]){
 const mappingKey=stableKey('mapping',[row.productCode,row.domain,mapping.implementation,mapping.stage.key,mapping.targetTableKey]);
 const previous=mappingsByKey.get(mappingKey);
 const conceptPathKeys=[...new Set([...(previous?.conceptPathKeys||[]),row.pathKey])];
 mappingsByKey.set(mappingKey,{...mapping,mappingKey,productCode:row.productCode,productName:row.productName,domain:row.domain,conceptPathKeys});
 for(const table of mapping.sqlEvidence.tables){
  const previousTable=tablesByKey.get(table.key);
  tablesByKey.set(table.key,{key:table.key,labels:table.labels,properties:table.properties,
   statementKeys:[...new Set([...(previousTable?.statementKeys||[]),...table.statements.map(statement=>statement.statementKey)])],
   requiredIncoming:uniqueBy([...(previousTable?.requiredIncoming||[]),...table.requiredIncoming],edge=>edgeId(edge))});
  for(const statement of table.statements)statementsByKey.set(statement.statementKey,statement);
 }
 for(const path of mapping.sqlEvidence.paths)for(const edge of path.relationships)edgesById.set(edgeId(edge),{...edge,id:edgeId(edge)});
 // Each external-source-to-target path is a candidate; shared SQL dependencies remain attached to its implementation.
 for(const path of mapping.sqlEvidence.paths.filter(path=>mapping.sqlEvidence.tables.find(table=>table.key===path.tableKeys[0])?.properties.tableKind==='external_source')){
  const relationshipIds=path.relationships.map(edgeId);
  const mappingPathKey=stableKey('mapping-path',[mappingKey,path.tableKeys,relationshipIds]);
  const old=candidatesByKey.get(mappingPathKey);
  candidatesByKey.set(mappingPathKey,{mappingPathKey,mappingKey,conceptPathKeys:[...new Set([...(old?.conceptPathKeys||[]),row.pathKey])],productCode:row.productCode,productName:row.productName,domain:row.domain,
   implementation:mapping.implementation,stageKey:mapping.stage.key,targetTableKey:mapping.targetTableKey,productScope:mapping.productScope,
   tableKeys:path.tableKeys,relationshipIds,statementKeys:[...new Set(path.relationships.map(edge=>edge.properties.statementKey).filter(Boolean))]});
 }
}
const mappingPathCandidates=[...candidatesByKey.values()],mappingCandidates=[...mappingsByKey.values()];
const sqlEvidence={tables:[...tablesByKey.values()].map(table=>({...table,requiredIncoming:table.requiredIncoming.map(edge=>({from:edge.from,to:edge.to,type:edge.type,relationshipId:edgeId(edge),statementKey:edge.properties.statementKey}))})),
 statements:[...statementsByKey.values()],relationships:[...edgesById.values()].map(edge=>{const {sql,inputSteps,ruleSteps,...properties}=edge.properties;return {...edge,properties};})};
const decisionRules='根據已選概念路徑及 question，查閱 technicalGraph 的表、關係、原始 SQL、範圍、日期、估值、JOIN／彙總／UNION 依據，判斷實體路徑是否需要。保留第一輪的業務範圍；多個來源可以共同實作同一概念。SQL 同一 UNION 或 JOIN 所需的來源都可納入；歷史初始化與月更新可能是不同適用階段，依原始 SQL 及問題判斷。僅有表名相似不構成對應理由。';
const questions=Object.fromEntries(mappingPathCandidates.map(path=>[path.mappingPathKey,{type:'choice',
 instructions:`依 state.decisionRules 評估 mappingPaths 中 mappingPathKey=${path.mappingPathKey} 的完整實體路徑。`,
 criteria:{included:'能實作已選概念或是所需依賴，且符合問題口徑。',uncertain:'可能對應，但映射或 SQL 不足以確定適用性。',excluded:'不對應已選概念，或資料範圍／計算口徑不符。'}}]));
// Local references reduce repeated lineage hashes and parser-derived expressions.
// Every candidate, dependency edge and original SQL statement remains in the request.
const tableRefs=new Map(sqlEvidence.tables.map((table,i)=>[table.key,`T${i+1}`]));
const statementRefs=new Map(sqlEvidence.statements.map((statement,i)=>[statement.statementKey,`S${i+1}`]));
const edgeRefs=new Map(sqlEvidence.relationships.map((edge,i)=>[edge.id,`E${i+1}`]));
const mappingRefs=new Map(mappingCandidates.map((mapping,i)=>[mapping.mappingKey,`M${i+1}`]));
const ref=(refs,key)=>refs.get(key)||key;
const technicalGraph={
 tables:sqlEvidence.tables.map(table=>({id:ref(tableRefs,table.key),name:table.properties.physicalName||table.properties.name,
  kind:table.properties.tableKind,definitionStatus:table.properties.definitionStatus,statements:table.statementKeys.map(key=>ref(statementRefs,key)),
  requiredIncoming:table.requiredIncoming.map(edge=>ref(edgeRefs,edge.relationshipId))})),
 statements:sqlEvidence.statements.map(statement=>({id:ref(statementRefs,statement.statementKey),file:statement.properties.file,lineStart:statement.properties.lineStart,
  lineEnd:statement.properties.lineEnd,status:statement.properties.status,sourceRole:statement.properties.sourceRole,type:statement.properties.statementType,
  requiredTables:statement.requiredTableKeys.map(key=>ref(tableRefs,key)),sql:statement.properties.sql})),
 relationships:sqlEvidence.relationships.map(edge=>({id:ref(edgeRefs,edge.id),from:ref(tableRefs,edge.from),to:ref(tableRefs,edge.to),type:edge.type,
  statement:ref(statementRefs,edge.properties.statementKey),unionBranchOrders:edge.properties.unionBranchOrders,unionBranchCounts:edge.properties.unionBranchCounts,
  joinInputRoles:edge.properties.joinInputRoles,status:edge.properties.status}))};
const conceptNodeKeys=new Set(context.selectedConceptPaths.flatMap(path=>path.nodeKeys));
const conceptRelationshipIds=new Set(context.selectedConceptPaths.flatMap(path=>path.relationshipIds));
const businessGraph={nodes:context.conceptGraph.nodes.filter(node=>conceptNodeKeys.has(node.key)),relationships:context.conceptGraph.relationships.filter(edge=>conceptRelationshipIds.has(edge.id))};
const mappingPaths=mappingPathCandidates.map(path=>({mappingPathKey:path.mappingPathKey,implementation:ref(mappingRefs,path.mappingKey),conceptPathKeys:path.conceptPathKeys,
 tables:path.tableKeys.map(key=>ref(tableRefs,key)),relationships:path.relationshipIds.map(key=>ref(edgeRefs,key)),statements:path.statementKeys.map(key=>ref(statementRefs,key))}));
const implementations=mappingCandidates.map(mapping=>({id:ref(mappingRefs,mapping.mappingKey),productCode:mapping.productCode,productName:mapping.productName,domain:mapping.domain,
 conceptPathKeys:mapping.conceptPathKeys,mappingType:mapping.mappingType,productScope:mapping.productScope,status:mapping.mappingStatus,
 note:mapping.implementation.properties.note,stage:mapping.stage.properties.name,target:ref(tableRefs,mapping.targetTableKey)}));
return [{json:{...context,mappingCandidates,mappingPathCandidates,sqlEvidence,
 decisionRequest:{model:'typesafe/jev-1.13',state:{question:context.question,decisionRules,businessGraph,
  selectedConceptPaths:context.selectedConceptPaths.map(({nodes,relationships,...path})=>path),mappingPaths,implementations,technicalGraph},questions}}}];
