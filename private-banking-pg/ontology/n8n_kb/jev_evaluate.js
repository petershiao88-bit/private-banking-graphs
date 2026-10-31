const body = $input.first().json;
const context = $('Jev - Prepare Objects').first().json;
if (body.error || body.errors?.length || !body.answers || typeof body.answers !== 'object' || Array.isArray(body.answers)) throw new Error('Jev 決策 API 未回傳有效 answers。');
if (typeof body.model !== 'string' || !/^typesafe\/jev-1\.13(?:-|$)/.test(body.model)) throw new Error('Jev 回傳模型不符合指定版本，停止選品。');
const routes=context.pathCandidates || [];
const expected = ['scope', ...context.candidates.map(c => c.objectKey),...routes.map(p=>`path::${p.pathKey}`)];
if (Object.keys(body.answers).length !== expected.length || expected.some(k => !Object.hasOwn(body.answers,k))) throw new Error('Jev object 評估漏項或有額外項目。');
function validate(answer, labels) {
  const probabilities = answer?.probabilities;
  if (answer?.type !== 'choice' || !labels.includes(answer.choice) || !probabilities ||
      Object.keys(probabilities).length !== labels.length || labels.some(k => !Object.hasOwn(probabilities,k) ||
      typeof probabilities[k] !== 'number' || !Number.isFinite(probabilities[k]) || probabilities[k] < 0 || probabilities[k] > 1) ||
      Math.abs(labels.reduce((sum,k) => sum + probabilities[k],0)-1) > 0.02 ||
      probabilities[answer.choice] < Math.max(...Object.values(probabilities))) throw new Error('Jev 機率分布或選項無效。');
  if (answer.confidence !== undefined && (typeof answer.confidence !== 'number' || !Number.isFinite(answer.confidence) || answer.confidence < 0 || answer.confidence > 1)) throw new Error('Jev confidence 無效。');
  return answer;
}
const scope = validate(body.answers.scope, ['clear','ambiguous','none']);
const candidateScores = context.candidates.map(c => {
  const answer = validate(body.answers[c.objectKey], ['included','uncertain','excluded']);
  return {...c, probability:answer.probabilities.included, probabilities:answer.probabilities,
    confidence:answer.confidence ?? null, judgement:answer.choice};
});
// No uncalibrated numeric cutoff or top-1 truncation. Native typed decisions only.
const ambiguous = scope.choice === 'ambiguous' || candidateScores.some(c => c.judgement === 'uncertain');
const included = candidateScores.filter(c => c.judgement === 'included');
if (scope.choice === 'none' && included.length) throw new Error('Jev 範圍與 object 判斷互相矛盾。');
const allExcluded = candidateScores.every(c => c.judgement === 'excluded');
const pathScores=routes.map(p=>{const a=validate(body.answers[`path::${p.pathKey}`],['included','uncertain','excluded']);return {pathKey:p.pathKey,objectKey:p.objectKey,queryMetricCode:p.queryMetricCode,queryMetricKey:p.queryMetricKey,probability:a.probabilities.included,probabilities:a.probabilities,confidence:a.confidence ?? null,judgement:a.choice};});
const relevant=pathScores.filter(p=>included.some(c=>c.objectKey===p.objectKey));
const conflictingPaths=pathScores.filter(p=>p.judgement==='included' && !included.some(c=>c.objectKey===p.objectKey));
const routeIssues=conflictingPaths.map(p=>({code:'object_path_disagreement',pathKey:p.pathKey,objectKey:p.objectKey,detail:'完整路徑被納入，但起點 object 未被納入，停止映射。'}));
const missingRoute=included.some(c=>c.matchedMetricCodes.some(metricCode=>!relevant.some(p=>p.objectKey===c.objectKey && p.queryMetricCode===metricCode && p.judgement==='included')));
const routeAmbiguous=relevant.some(p=>p.judgement==='uncertain');
const status = conflictingPaths.length ? 'needs_clarification' : !context.candidates.length || allExcluded || scope.choice === 'none' ? 'no_match' : ambiguous || !included.length || routeAmbiguous || missingRoute ? 'needs_clarification' : 'selected';
const selections = status === 'selected' ? included.map(c => ({productCode:c.productCode,domain:c.domain})) : [];
const selectedConceptPaths=status==='selected'?routes.filter(p=>relevant.some(s=>s.pathKey===p.pathKey && s.judgement==='included')):[];
const possible = candidateScores.filter(c => c.judgement !== 'excluded').map(c => `${c.productName}（${c.domain}）`);
const message = status === 'needs_clarification' ? `產品或完整業務路徑尚未確定，需確認查詢口徑：${possible.join('、') || '目前尚無明確產品'}。` : status === 'no_match' ? '指定範圍沒有符合問題的候選產品。' : '已依 Jev 評估 object 及完整業務路徑，才可進入映射。';
return [{json:{status,selections,candidateScores,pathScores,selectedConceptPaths,routeIssues,pathStatus:status==='selected'?'confirmed':'unresolved',message,decision:{requestId:body.id ?? null,model:body.model,
  provider:body.provider ?? null,scope,answers:body.answers,usage:body.usage ?? null,
  policy:{method:'native_object_and_complete_path_choice_with_gate',numericThreshold:null,calibrated:false},
  probabilityMeaning:'Native P(included) independently for each object and each full business path; never normalized across candidates or multiplied together.'}}}];
