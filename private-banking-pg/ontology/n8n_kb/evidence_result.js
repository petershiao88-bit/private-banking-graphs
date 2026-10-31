const body=$input.first().json;
const conceptChoice=$('Concept Decision Result').first().json;
const choice=$('Route Decision Result').first().json,context=$('Concept Routes').first().json;
const rows=body.data.values.map(row=>Object.fromEntries(body.data.fields.map((k,i)=>[k,row[i]])));
const edgeKey=r=>r.properties?.lineageEdgeId || [r.from,r.type,r.to,r.properties?.statementKey].join('|');
function formatMapping(mapping){
 const graph=mapping.sqlEvidence,tables=graph.tables;
 const statements=new Map(tables.flatMap(t=>t.statements).map(s=>[s.statementKey,s]));
 const edges=new Map(graph.paths.flatMap(p=>p.relationships).map(r=>[edgeKey(r),r]));
 const sqlEvidence={maxDepth:graph.maxDepth,statements:[...statements.values()],
  tables:tables.map(({statements,requiredIncoming,...t})=>({...t,statementKeys:statements.map(s=>s.statementKey),
   requiredIncoming:requiredIncoming.map(r=>({from:r.from,to:r.to,type:r.type,statementKey:r.properties.statementKey,lineageEdgeId:r.properties.lineageEdgeId}))})),
  relationships:[...edges.values()].map(r=>{const {sql,ruleSteps,inputSteps,...properties}=r.properties;return {from:r.from,to:r.to,type:r.type,properties};}),
  paths:graph.paths.map(p=>({tableKeys:p.tableKeys,relationshipIds:p.relationships.map(edgeKey)}))};
 return {...mapping,lineage:mapping.lineage.map(p=>({...p,rules:p.rules.map(({ruleSteps,inputSteps,...r})=>r)})),sqlEvidence,
  requiredBaseTables:tables.filter(t=>t.properties.tableKind==='external_source').map(t=>t.properties.physicalName || t.properties.name).sort()};
}
const products=choice.selections.map(selection=>{
 const concept=context.products.find(p=>p.productCode===selection.productCode);
 const paths=choice.selectedConceptPaths.filter(p=>p.anchorConceptKeys.includes(selection.conceptKey)&&p.domain===selection.domain);
 const mappings=paths.flatMap(path=>rows.filter(r=>r.pathKey===path.pathKey&&r.queryMetricKey===path.queryMetricKey&&r.bindingConceptKey===selection.conceptKey&&r.domain===selection.domain)
  .flatMap(row=>row.mappings.map(m=>({...formatMapping(m),selectedPathKey:path.pathKey,queryMetricKey:path.queryMetricKey,queryMetricCode:path.queryMetricCode}))));
 const score=conceptChoice.candidateScores.find(c=>c.objectKey===selection.objectKey);
 return {productCode:selection.productCode,productName:concept.productName,domain:selection.domain,objectKey:selection.objectKey,
  probability:score.probability,probabilities:score.probabilities,judgement:score.judgement,
  definition:concept.definition,definitionStatus:concept[`${selection.domain}Status`],metrics:concept[`${selection.domain}Metrics`],
  matchedMetricCodes:[...new Set(paths.map(p=>p.queryMetricCode))],conceptEvidence:{...concept.conceptEvidence,domain:selection.domain,paths},mappings};
});
return [{json:{contractVersion:'pb_kb_lazy_routes_v4',metricCodes:context.metricCodes,domains:context.domains,
 candidateScores:conceptChoice.candidateScores,pathScores:choice.pathScores,selectedConcepts:conceptChoice.selectedConcepts,
 selectedConceptPaths:choice.selectedConceptPaths,routeRetrieval:context.routeRetrieval,
 queryPlan:{anchorConceptKeys:[...new Set(conceptChoice.selectedConcepts.map(c=>c.conceptKey))],selectedPathKeys:choice.selectedConceptPaths.map(p=>p.pathKey)},
 decision:{model:choice.pathDecision.model,concept:conceptChoice.conceptDecision,path:choice.pathDecision,method:'concept_then_lazy_routes_then_mapping'},products}}];

