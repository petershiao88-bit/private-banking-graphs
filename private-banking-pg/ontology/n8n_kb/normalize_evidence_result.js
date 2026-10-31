const raw=$input.all().map(i=>i.json).filter(r=>Object.keys(r).length);
const kb=$('Product Concept KB').first().json,router=$('metric router').item.json.output;
const errors=raw.filter(r=>r.error_message || r.error),rows=raw.filter(r=>!r.error_message && !r.error);
const unsupported=errors.some(r=>r.error_message==='UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE');
const status=errors.length?(unsupported?'unsupported':'error'):rows.length?'success':'no_data';
return [{json:{status,candidateScores:kb.candidateScores,pathScores:kb.pathScores,selectedConcepts:kb.selectedConcepts,
 selectedConceptPaths:kb.selectedConceptPaths,decision:kb.decision,user_query:router.resolved_query,metric_codes:router.selected_metric_codes,
 output_grain:'dynamic',row_count:status==='success'?rows.length:0,columns:status==='success'?Object.keys(rows[0]):[],rows:status==='success'?rows:[],
 reason:unsupported?'目前執行資料庫缺少此產品計算所需的來源或欄位。':errors.length?'資料查詢未完成，請檢查執行紀錄。':'',errors}}];

