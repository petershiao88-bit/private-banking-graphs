const body=$input.first().json,context=$('Jev - Prepare Concept Paths').first().json;
const conceptPathScores=context.conceptPathCandidates.map(path=>scored({pathKey:path.pathKey,domain:path.domain,productCodes:path.productCodes,metricCodes:path.metricCodes},body.answers[path.pathKey]));
const selectedConceptPaths=context.conceptPathCandidates.filter(path=>body.answers[path.pathKey].choice==='included');
const {decisionRequest,...rest}=context;
return [{json:{...rest,conceptPathScores,selectedConceptPaths,selectedPaths:selectedConceptPaths.map(({pathKey,domain,productCodes,metricCodes})=>({pathKey,domain,productCodes,metricCodes})),
 conceptDecision:decisionEvidence(body,'concept_path_selection')}}];
