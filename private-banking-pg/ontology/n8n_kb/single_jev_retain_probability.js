const response=$input.first().json,normalized=$('Normalize SQL Result').first().json;
const conceptPathScores=normalized.conceptPathScores||[];
const escape=s=>String(s).replace(/[|\r\n]/g,' ');
const conceptRows=conceptPathScores.map(p=>`| ${escape(p.pathKey)} | ${escape(p.productCodes.join('、'))} | ${p.domain==='aum'?'AUM':'Income'} | ${p.probability} | ${escape(p.choice)} |`);
const conceptTable=conceptRows.length?'\n\n概念路徑的納入機率（0～1）：\n\n| 路徑 | 產品 | 領域 | 機率 | 判斷 |\n|---|---|---|---|---|\n'+conceptRows.join('\n'):'';
return [{json:{...response,text:String(response.text||response.output||'')+conceptTable,
 contractVersion:normalized.contractVersion,conceptPathScores,mappingPaths:normalized.mappingPaths,selectedConceptPaths:normalized.selectedConceptPaths,
 mappingResolution:normalized.mappingResolution,decision:normalized.decision}}];
