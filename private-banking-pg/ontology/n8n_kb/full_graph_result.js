const body=$input.first().json,context=$('Jev - Prepare Mapping Paths').first().json;
const mappingPathScores=context.mappingPathCandidates.map(path=>scored({mappingPathKey:path.mappingPathKey,mappingKey:path.mappingKey,conceptPathKeys:path.conceptPathKeys,productCode:path.productCode,domain:path.domain},body.answers[path.mappingPathKey]));
const selectedMappingPaths=context.mappingPathCandidates.filter(path=>body.answers[path.mappingPathKey].choice==='included');
const mappingKeys=new Set(selectedMappingPaths.map(path=>path.mappingKey));
const selectedMappings=context.mappingCandidates.filter(mapping=>mappingKeys.has(mapping.mappingKey));
const tables=uniqueBy(selectedMappings.flatMap(mapping=>mapping.sqlEvidence.tables),table=>table.key);
const statements=uniqueBy(tables.flatMap(table=>table.statements),statement=>statement.statementKey);
const tableKeys=new Set(tables.map(table=>table.key)),statementKeys=new Set(statements.map(statement=>statement.statementKey));
const sqlEvidence={tables:context.sqlEvidence.tables.filter(table=>tableKeys.has(table.key)),statements:context.sqlEvidence.statements.filter(statement=>statementKeys.has(statement.statementKey)),
 relationships:context.sqlEvidence.relationships.filter(edge=>tableKeys.has(edge.from)&&tableKeys.has(edge.to))};
const products=uniqueBy(context.selectedConceptPaths.flatMap(path=>path.productCodes.map(productCode=>({productCode,domain:path.domain}))),selection=>`${selection.productCode}::${selection.domain}`).map(selection=>{
 const node=context.conceptGraph.nodes.find(node=>node.properties.productCode===selection.productCode);
 const paths=context.selectedConceptPaths.filter(path=>path.domain===selection.domain&&path.productCodes.includes(selection.productCode));
 const mappings=selectedMappings.filter(mapping=>mapping.productCode===selection.productCode&&mapping.domain===selection.domain).map(mapping=>{
  const {sqlEvidence:rawEvidence,lineage,...metadata}=mapping;
  return {...metadata,lineage:lineage.map(path=>({...path,rules:path.rules.map(({sql,inputSteps,ruleSteps,...rule})=>rule)})),
  sqlEvidence:{tableKeys:rawEvidence.tables.map(table=>table.key),statementKeys:[...new Set(rawEvidence.tables.flatMap(table=>table.statements.map(statement=>statement.statementKey)))],
   paths:rawEvidence.paths.map(path=>({tableKeys:path.tableKeys,relationshipIds:path.relationships.map(edge=>edge.properties.lineageEdgeId||stableKey('sql-edge',[edge.from,edge.type,edge.to,edge.properties.statementKey]))}))},
  selectedMappingPathKeys:selectedMappingPaths.filter(path=>path.mappingKey===mapping.mappingKey).map(path=>path.mappingPathKey),
  requiredBaseTables:rawEvidence.tables.filter(table=>table.properties.tableKind==='external_source').map(table=>table.properties.physicalName||table.properties.name)};});
 return {...selection,productName:node.properties.name,definition:node.properties.definition,definitionStatus:node.properties[`${selection.domain}Status`],
  matchedMetricCodes:[...new Set(paths.flatMap(path=>path.metricCodes))],conceptEvidence:{paths},mappings};
});
return [{json:{contractVersion:'pb_kb_full_graph_mapping_paths_v1',question:context.question,domains:context.domains,metricCodes:context.metricCodes,
 conceptGraph:context.conceptGraph,conceptPathScores:context.conceptPathScores,selectedConceptPaths:context.selectedConceptPaths,
 mappingPathScores,selectedMappingPaths,sqlEvidence,products,
 queryPlan:{selectedConceptPathKeys:context.selectedConceptPaths.map(path=>path.pathKey),selectedMappingPathKeys:selectedMappingPaths.map(path=>path.mappingPathKey)},
 decision:{model:body.model,concept:context.conceptDecision,mapping:decisionEvidence(body,'mapping_path_selection'),method:'full_concept_graph_then_mapping_paths'}}}];
