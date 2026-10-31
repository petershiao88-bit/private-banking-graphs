const context=$input.first().json;
const pick=(p,keys)=>Object.fromEntries(keys.filter(k=>p?.[k]!==undefined).map(k=>[k,p[k]]));
const businessPaths=context.pathCandidates.map(p=>({...pick(p,['pathKey','domain','anchorConceptKeys','queryMetricCode','queryMetricKey']),
 nodes:p.nodes.map(n=>({key:n.key,labels:n.labels,properties:pick(n.properties,['code','name','definition','dateRule','intendedGrain','status','aumFilter','incomeFilter','aumValuationBasis','incomeAmountBasis','directionStatus'])})),
 relationships:p.relationships.map(r=>({...pick(r,['from','to','type']),properties:pick(r.properties,['name','scope','status','rootDefinitionStatus','note'])}))}));
const questions={};
for(const p of businessPaths)questions[`path::${p.pathKey}`]={type:'choice',instructions:`唯一對象是 businessPaths 中 pathKey=${p.pathKey} 的有方向完整路徑；目標是 ${p.queryMetricCode}。沿 nodes／relationships 依序判斷衡量定義、scope、dateRule、粒度與方向是否符合 question。中間概念只是路徑成員，不需要逐一重新選 object。依業務意圖決定是否納入此路徑；同一概念的其他支線不能代替本路徑。draft/inferred 本身不是選路歧義，SQL 證據稍後另處理。`,criteria:{
 included:'此完整路徑符合問題，是回答所需路徑之一；允許多條路徑共享節點或共同構成方案。',
 uncertain:'可能符合，但業務口徑、方向或競爭支線尚無法確定。',excluded:'此完整路徑的業務定義或方向不符合問題，或不是所需方案的一部分。'}};
return [{json:{...context,decisionRequest:{model:'typesafe/jev-1.13',state:{question:context.question,domains:context.domains,metricCodes:context.metricCodes,selectedConcepts:context.selectedConcepts,businessPaths},questions}}}];
