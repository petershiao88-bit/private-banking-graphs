const body=$input.first().json,context=$('Jev - Prepare Paths').first().json;
const pathScores=context.pathCandidates.map(p=>{
 const a=body.answers[`path::${p.pathKey}`];
 return {pathKey:p.pathKey,domain:p.domain,anchorConceptKeys:p.anchorConceptKeys,queryMetricCode:p.queryMetricCode,queryMetricKey:p.queryMetricKey,
  probability:a.probabilities.included,probabilities:a.probabilities,confidence:a.confidence,judgement:a.choice};
});
const selectedConceptPaths=context.pathCandidates.filter(p=>body.answers[`path::${p.pathKey}`].choice==='included');
const selectedPaths=selectedConceptPaths.map(p=>({pathKey:p.pathKey,domain:p.domain,anchorConceptKeys:p.anchorConceptKeys,
 queryMetricKey:p.queryMetricKey,queryMetricCode:p.queryMetricCode,nodeKeys:p.nodeKeys,relationshipTypes:p.relationshipTypes,relationshipProperties:p.relationshipProperties}));
return [{json:{selectedConcepts:context.selectedConcepts,candidateScores:context.candidateScores,pathScores,selectedConceptPaths,selectedPaths,
 selections:context.selectedConcepts.filter(c=>selectedConceptPaths.some(p=>p.domain===c.domain&&p.anchorConceptKeys.includes(c.conceptKey)))
  .map(c=>({conceptKey:c.conceptKey,objectKey:c.objectKey,productCode:c.productCode,domain:c.domain})),
 conceptDecision:context.conceptDecision,pathDecision:decisionEvidence(body,'route_selection')}}];

