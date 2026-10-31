const body=$input.first().json,context=$('Concept Decision Result').first().json;
const rows=body.data.values.map(row=>Object.fromEntries(body.data.fields.map((k,i)=>[k,row[i]])));
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const hash=s=>{let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0).toString(16).padStart(8,'0');};
const paths=new Map();
for(const row of rows){
 const nodes=row.businessPath?.nodes || [],relationships=row.businessPath?.relationships || [];
 const nodeKeys=nodes.map(n=>n.key);
 const anchors=context.selectedConcepts.filter(c=>c.domain===row.domain&&nodeKeys.includes(c.conceptKey));
 for(const target of nodes.filter(n=>n.labels?.includes('BusinessMetric')&&context.metricCodes.includes(n.properties?.code))){
  const signature=JSON.stringify(canonical({domain:row.domain,queryMetricKey:target.key,nodes,relationships}));
  const pathKey=`route::${row.domain}::${target.properties.code}::${hash(signature)}`;
  const previous=paths.get(pathKey);
  const anchorConceptKeys=[...new Set([...(previous?.anchorConceptKeys || []),...anchors.map(c=>c.conceptKey)])].sort();
  const anchorObjectKeys=[...new Set([...(previous?.anchorObjectKeys || []),...anchors.map(c=>c.objectKey)])].sort();
  paths.set(pathKey,{pathKey,domain:row.domain,anchorConceptKeys,anchorObjectKeys,queryMetricCode:target.properties.code,queryMetricKey:target.key,
   nodeKeys,relationshipTypes:relationships.map(r=>r.type),relationshipProperties:relationships.map(r=>r.properties || {}),nodes,relationships});
 }
}
const products=context.products.filter(p=>context.selectedConcepts.some(c=>c.productCode===p.productCode)).map(p=>{
 const evidence=rows.find(r=>r.requestedConceptKey===p.conceptKey)?.conceptEvidence;
 const metrics=domain=>[...new Map(rows.filter(r=>r.domain===domain&&r.requestedConceptKey===p.conceptKey).flatMap(r=>r.businessPath.nodes).filter(n=>n.labels?.includes('BusinessMetric')).map(n=>[n.key,{metricCode:n.properties.code,name:n.properties.name,definition:n.properties.definition,status:n.properties.status}])).values()];
 return {...p,conceptEvidence:evidence || null,aumMetrics:metrics('aum'),incomeMetrics:metrics('income')};
});
return [{json:{...context,products,pathCandidates:[...paths.values()].sort((a,b)=>a.pathKey.localeCompare(b.pathKey)),
 routeRetrieval:{selectedConceptKeys:[...new Set(context.selectedConcepts.map(c=>c.conceptKey))],returnedRows:rows.length,maxBusinessDepth:8}}}];
