const response=$input.first().json;
const normalized=$('Normalize SQL Result').first().json;
const scores=normalized.candidateScores || [],pathScores=normalized.pathScores || [];
const escape=s=>String(s).replace(/[|\r\n]/g,' ');
const rows=scores.map(c=>`| ${escape(c.productName)} | ${c.domain==='aum'?'AUM':'Income'} | ${c.probability} |`);
const table=rows.length?'\n\n候選產品的納入機率（0～1）：\n\n| 產品 | 領域 | 機率 |\n|---|---|---|\n'+rows.join('\n'):'';
const routes=pathScores.map(p=>`| ${escape(p.pathKey)} | ${escape(p.queryMetricCode)} | ${p.probability} | ${escape(p.judgement)} |`);
const pathTable=routes.length?'\n\n完整概念路徑的納入機率（0～1）：\n\n| 路徑 | 查詢指標 | 機率 | 判斷 |\n|---|---|---|---|\n'+routes.join('\n'):'';
return [{json:{...response,text:String(response.text || response.output || '')+table+pathTable,
 candidateScores:scores,pathScores,selectedConcepts:normalized.selectedConcepts,selectedConceptPaths:normalized.selectedConceptPaths,decision:normalized.decision}}];
