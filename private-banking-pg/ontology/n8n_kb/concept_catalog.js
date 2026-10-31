const body = $input.first().json;
if (body.errors?.length || !body.data?.fields || !Array.isArray(body.data.values)) {
  throw new Error('Aura 概念查詢失敗，請檢查連線或執行紀錄。');
}
const metric = m => ({metricCode:m.metricCode,name:m.name,definition:m.definition,status:m.status});
const products = body.data.values.map(row => {
  const p = Object.fromEntries(body.data.fields.map((key,i)=>[key,row[i]]));
  return {productCode:p.productCode,productName:p.productName,definition:p.definition,
    status:p.status,aumStatus:p.aumStatus,incomeStatus:p.incomeStatus,matchedScopes:p.matchedScopes,
    aumMetrics:(p.aumMetrics || []).map(metric),incomeMetrics:(p.incomeMetrics || []).map(metric),
    conceptEvidence:p.conceptEvidence || null};
});
const raw = $('KB Input').first().json;
const normalize = value => (Array.isArray(value) ? value : [value]).map(v => typeof v === 'string' ? v.trim() : v);
const request = {...raw, domains:normalize(raw.domains), metricCodes:normalize(raw.metricCodes)};
if (typeof request.question !== 'string' || !request.question.trim() || !request.domains.length || !request.domains.every(d=>['aum','income'].includes(d)) || !request.metricCodes.every(c=>typeof c==='string'&&c)) throw new Error('KB 輸入無效。');
const unmatchedMetricCodes = request.metricCodes.filter(code=>!products.some(p=>p.matchedScopes.some(s=>s.metricCode===code)));
return [{json:{question:request.question,domains:request.domains,metricCodes:request.metricCodes,unmatchedMetricCodes,products}}];
