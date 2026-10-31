const body=$input.first().json,context=$('Jev - Prepare Concepts').first().json;
const candidateScores=context.candidates.map(c=>{
 const a=body.answers[c.objectKey];
 return {...c,probability:a.probabilities.included,probabilities:a.probabilities,confidence:a.confidence,judgement:a.choice};
});
const selectedConcepts=candidateScores.filter(c=>c.judgement==='included')
 .map(({conceptKey,objectKey,productCode,productName,domain,matchedMetricCodes})=>({conceptKey,objectKey,productCode,productName,domain,matchedMetricCodes}));
const {decisionRequest,...rest}=context;
return [{json:{...rest,selectedConcepts,candidateScores,conceptDecision:decisionEvidence(body,'concept_selection')}}];

