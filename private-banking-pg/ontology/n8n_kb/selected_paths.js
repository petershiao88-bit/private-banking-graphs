const choice=$input.first().json;
if(choice.status!=='selected' || choice.pathStatus!=='confirmed' || !choice.selectedConceptPaths?.length)throw new Error('完整業務路徑未確認，不得查詢映射。');
const catalog=$('Concept Paths').first().json;
const selectedPaths=choice.selectedConceptPaths.map(p=>{
 const original=catalog.pathCandidates.find(c=>c.pathKey===p.pathKey);
 if(!original || JSON.stringify(original)!==JSON.stringify(p) ||
  choice.pathScores.find(s=>s.pathKey===p.pathKey)?.judgement!=='included' ||
  choice.candidateScores.find(s=>s.objectKey===p.objectKey)?.judgement!=='included')throw new Error('已選概念路徑不在本次 Jev 確認範圍。');
 return {pathKey:p.pathKey,productCode:p.productCode,domain:p.domain,queryMetricKey:p.queryMetricKey,queryMetricCode:p.queryMetricCode,
  nodeKeys:p.nodeKeys,relationshipTypes:p.relationshipTypes,relationshipProperties:p.relationshipProperties};
});
return [{json:{...choice,selectedPaths}}];
