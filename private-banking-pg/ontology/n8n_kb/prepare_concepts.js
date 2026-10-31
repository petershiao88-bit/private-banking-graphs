const body=$input.first().json,raw=$('KB Input').first().json;
const list=v=>(Array.isArray(v)?v:[v]).map(x=>typeof x==='string'?x.trim():x);
const question=raw.question,domains=list(raw.domains),metricCodes=list(raw.metricCodes);
const products=body.data.values.map(row=>Object.fromEntries(body.data.fields.map((k,i)=>[k,row[i]])));
const candidates=products.flatMap(p=>[...new Set(p.matchedScopes.map(s=>s.domain))].map(domain=>({
 objectKey:`${p.productCode}::${domain}`,conceptKey:p.conceptKey,productCode:p.productCode,productName:p.productName,domain,
 definition:p.definition,definitionStatus:p[`${domain}Status`],matchedMetricCodes:[...new Set(p.matchedScopes.filter(s=>s.domain===domain).map(s=>s.metricCode))]})));
const questions={};
for(const c of candidates)questions[c.objectKey]={type:'choice',instructions:`本題只判斷 question 是否要求概念「${c.productName}」（${c.productCode}）的 ${c.domain.toUpperCase()}。定義：${c.definition}。不判斷路徑或實現方式。只問基金時不要因共用投資／證券指標而纳入股票、債券、ETF 或結構型商品。`,criteria:{
 included:`明確要求「${c.productName}」且產品種類、通路與領域相符；或明確要求其所屬完整類別的所有產品。`,
 uncertain:'產品可能符合，但缺通路或領域等資訊，無法區分概念。',excluded:'未要求此概念，或產品種類、通路、領域不符；同屬 metric 不構成納入理由。'}};
return [{json:{question,domains,metricCodes,products,candidates,unmatchedMetricCodes:metricCodes.filter(code=>!products.some(p=>p.matchedScopes.some(s=>s.metricCode===code))),
 decisionRequest:{model:'typesafe/jev-1.13',state:{question,domains,metricCodes,candidates},questions}}}];
