const context=$('Concept Path Result').first().json,allRows=graphRows($input.first().json);
const rows=allRows.map(row=>({...row,mappings:(row.mappings||[]).filter(m=>m.mappingFormat!=='mapping_draft_rules')}));
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
 // Return every external-source-to-target path and every shared SQL dependency of the mapped implementation.
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

// Current rule evidence supplements legacy SQL; it is never a second amount to sum.
const parseProperty=(value,fallback)=>{if(value==null)return fallback;if(typeof value!=='string')return value;try{return JSON.parse(value);}catch{throw new Error('Invalid mapping rule JSON');}};
const normalizedProperties=properties=>Object.fromEntries(Object.entries(properties||{}).map(([key,value])=>[key,['calculationRules','queryRules','reviewNotes','externalPreconditions','sourceEvidence','columns'].includes(key)?parseProperty(value,[]):value]));
const ruleMap=new Map(),dimensionMap=new Map();
for(const row of allRows)for(const mapping of row.mappings||[]){
 if(mapping.mappingFormat!=='mapping_draft_rules')continue;
 const implementation={...mapping.implementation,properties:normalizedProperties(mapping.implementation.properties)};
 if(!Array.isArray(implementation.properties.calculationRules)||!implementation.properties.calculationRules.length)throw new Error('Missing mapping rules');
 const key=mapping.mappingKey;
 if(!key||implementation.properties.mappingRole!=='base_source')throw new Error('Invalid mapping rule binding');
 const old=ruleMap.get(key);
 for(const edge of mapping.dimensionEvidence)dimensionMap.set(edge.id,{...edge,properties:normalizedProperties(edge.properties),sourceNode:{...edge.sourceNode,properties:normalizedProperties(edge.sourceNode.properties)},targetNode:{...edge.targetNode,properties:normalizedProperties(edge.targetNode.properties)}});
 ruleMap.set(key,{key,productCode:row.productCode,domain:row.domain,
  conceptPathKeys:[...new Set([...(old?.conceptPathKeys||[]),row.pathKey])],implementation,
  measurement:{...mapping.measurement,properties:normalizedProperties(mapping.measurement.properties)},
  sourceTables:mapping.sourceTables.map(table=>({...table,properties:normalizedProperties(table.properties)})),
  dimensionEvidenceKeys:mapping.dimensionEvidence.map(edge=>edge.id),
  calculationAuthorized:false});
}
const ruleEvidence=[...ruleMap.values()];
const dimensionEvidence=[...dimensionMap.values()];

const products=uniqueBy(context.selectedConceptPaths.flatMap(path=>path.productCodes.map(productCode=>({productCode,domain:path.domain}))),selection=>`${selection.productCode}::${selection.domain}`).map(selection=>{
 const node=context.conceptGraph.nodes.find(node=>node.properties.productCode===selection.productCode);
 const paths=context.selectedConceptPaths.filter(path=>path.domain===selection.domain&&path.productCodes.includes(selection.productCode));
 const mappings=mappingCandidates.filter(mapping=>mapping.productCode===selection.productCode&&mapping.domain===selection.domain).map(mapping=>{
  const {sqlEvidence:rawEvidence,lineage,...metadata}=mapping;
  return {...metadata,lineage:lineage.map(path=>({...path,rules:path.rules.map(({sql,inputSteps,ruleSteps,...rule})=>rule)})),
  sqlEvidence:{tableKeys:rawEvidence.tables.map(table=>table.key),statementKeys:[...new Set(rawEvidence.tables.flatMap(table=>table.statements.map(statement=>statement.statementKey)))],
   paths:rawEvidence.paths.map(path=>({tableKeys:path.tableKeys,relationshipIds:path.relationships.map(edge=>edge.properties.lineageEdgeId||stableKey('sql-edge',[edge.from,edge.type,edge.to,edge.properties.statementKey]))}))},
  mappingPathKeys:mappingPathCandidates.filter(path=>path.mappingKey===mapping.mappingKey).map(path=>path.mappingPathKey),
  requiredBaseTables:rawEvidence.tables.filter(table=>table.properties.tableKind==='external_source').map(table=>table.properties.physicalName||table.properties.name)};});
 const rules=ruleEvidence.filter(rule=>rule.productCode===selection.productCode&&rule.domain===selection.domain);
 for(const mapping of mappings){mapping.evidenceFormat='shared_product_sql';mapping.ruleEvidenceKeys=rules.map(rule=>rule.key);}
 if(!mappings.length&&rules.length)mappings.push(...rules.map(rule=>({mappingKey:rule.key,evidenceFormat:'mapping_draft_rules',mappingStatus:'mapping_draft_rules',
  implementation:rule.implementation,productScope:rule.measurement.properties,ruleEvidenceKeys:[rule.key],
  calculationAuthorized:false,lineage:[],sqlEvidence:{tableKeys:[],statementKeys:[],paths:[]},mappingPathKeys:[],
  requiredBaseTables:rule.sourceTables.map(table=>table.properties.name)})));
 const businessProperties=Object.fromEntries(['definition','productCategory','businessChannel','customerNeed','serviceDescription','aumDefinition','incomeDefinition','subsidiary','currencyType','structureType','depositorType','fundType','marketRegion','dealingMode'].filter(field=>node.properties[field]!=null).map(field=>[field,node.properties[field]]));
 return {...selection,productName:node.properties.name,definition:node.properties[`${selection.domain}Definition`],businessProperties,
  matchedMetricCodes:[...new Set(paths.flatMap(path=>path.metricCodes))],conceptEvidence:{paths},mappings};
});
const selectedScopes=new Set(products.map(p=>`${p.productCode}::${p.domain}`));
const overlappingProductScopes=context.conceptGraph.relationships.filter(edge=>edge.type==='PB_SUBCATEGORY_OF').flatMap(edge=>['aum','income'].filter(domain=>selectedScopes.has(`${edge.from}::${domain}`)&&selectedScopes.has(`${edge.to}::${domain}`)).map(domain=>({domain,parentProductCode:edge.to,childProductCode:edge.from,...edge.properties})));
const unresolvedSelections=products.filter(p=>!p.mappings.length).map(({productCode,domain})=>({productCode,domain}));
return [{json:{contractVersion:'pb_kb_full_graph_single_jev_v1',question:context.question,domains:context.domains,metricCodes:context.metricCodes,
 conceptGraph:context.conceptGraph,conceptPathScores:context.conceptPathScores,selectedConceptPaths:context.selectedConceptPaths,
 mappingPaths:mappingPathCandidates,sqlEvidence,ruleEvidence,dimensionEvidence,products,
 evidenceGuidance:{ruleEvidence:'Current MappingDraft calculationRules/queryRules and measurement constraints are shared evidence. Join by products[].mappings[].ruleEvidenceKeys. These are alternative descriptions of the same implementation, never extra amounts to add to SQL lineage.',
  dimensions:'AO/customer/private-banking context includes month-effective rules, source metadata and unvalidated cardinality. Do not assume a unique advisor or allocate amounts to every advisor.',
  execution:'Rules-only mappings do not contain original SQL or executable approval. Resolve externalPreconditions, all required source columns, date/version/grain and pending review notes before calculating. If rules and SQL differ, do not silently pick a version; report unresolved evidence.',
  aggregation:'Never add parent products and their subcategories, or sum rebuild and monthly-refresh variants. Trust classifications require source-level splitting.'},
 queryPlan:{selectedConceptPathKeys:context.selectedConceptPaths.map(path=>path.pathKey),mappingPathKeys:mappingPathCandidates.map(path=>path.mappingPathKey),overlappingProductScopes},
 decision:{model:context.conceptDecision.model,concept:context.conceptDecision,method:'full_concept_graph_then_direct_mapping'},
 mappingResolution:{method:'graph_relationships',mappingCount:new Set(products.flatMap(p=>p.mappings.map(m=>m.mappingKey))).size,sqlMappingCount:mappingCandidates.length,pathCount:mappingPathCandidates.length,complete:unresolvedSelections.length===0,unresolvedSelections,ruleEvidenceCount:ruleEvidence.length,evidenceCoverageOnly:true}}}];
