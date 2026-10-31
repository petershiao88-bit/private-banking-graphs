from build_full_graph_workflow import HERE

# Preserve the established evidence normalization, without a second decision request.
prepare = (HERE/'full_graph_prepare_mappings.js').read_text(encoding='utf-8')
prepare = prepare[:prepare.index("const decisionRules=")]
prepare = prepare.replace('// Each external-source-to-target path is a candidate; shared SQL dependencies remain attached to its implementation.', '// Return every external-source-to-target path and every shared SQL dependency of the mapped implementation.')
result = (HERE/'full_graph_result.js').read_text(encoding='utf-8')
products = result[result.index('const products='):result.index('return [{json:')]
products = products.replace('selectedMappings.filter', 'mappingCandidates.filter').replace('selectedMappingPathKeys:selectedMappingPaths.filter', 'mappingPathKeys:mappingPathCandidates.filter')
final = """return [{json:{contractVersion:'pb_kb_full_graph_single_jev_v1',question:context.question,domains:context.domains,metricCodes:context.metricCodes,
 conceptGraph:context.conceptGraph,conceptPathScores:context.conceptPathScores,selectedConceptPaths:context.selectedConceptPaths,
 mappingPaths:mappingPathCandidates,sqlEvidence,products,
 queryPlan:{selectedConceptPathKeys:context.selectedConceptPaths.map(path=>path.pathKey),mappingPathKeys:mappingPathCandidates.map(path=>path.mappingPathKey)},
 decision:{model:context.conceptDecision.model,concept:context.conceptDecision,method:'full_concept_graph_then_direct_mapping'},
 mappingResolution:{method:'graph_relationships',mappingCount:mappingCandidates.length,pathCount:mappingPathCandidates.length}}}];
"""
(HERE/'single_jev_result.js').write_text(prepare+products+final, encoding='utf-8')
normalize = (HERE/'full_graph_normalize_result.js').read_text(encoding='utf-8').replace('mappingPathScores:kb.mappingPathScores', 'mappingPaths:kb.mappingPaths').replace('selectedMappingPaths:kb.selectedMappingPaths', 'mappingResolution:kb.mappingResolution')
(HERE/'single_jev_normalize_result.js').write_text(normalize,encoding='utf-8')
retain = (HERE/'full_graph_retain_probability.js').read_text(encoding='utf-8')
retain = retain.replace(',mappingPathScores=normalized.mappingPathScores||[]','')
retain = '\n'.join(line for line in retain.splitlines() if not line.startswith('const mappingRows=') and not line.startswith('const mappingTable='))
retain = retain.replace('+conceptTable+mappingTable','+conceptTable').replace('conceptPathScores,mappingPathScores,','conceptPathScores,mappingPaths:normalized.mappingPaths,').replace('selectedMappingPaths:normalized.selectedMappingPaths','mappingResolution:normalized.mappingResolution')
(HERE/'single_jev_retain_probability.js').write_text(retain+'\n',encoding='utf-8')
prompt = (HERE/'full_graph_sql_evidence_prompt.txt').read_text(encoding='utf-8')
old = prompt[prompt.index('KB 合約為'):prompt.index('\n\nconceptGraph')]
prompt = prompt.replace(old, 'KB 合約為 pb_kb_full_graph_single_jev_v1。Jev 讀完整概念圖並選概念路徑；接著 KB 沿圖上的關係取回所有對應映射、資料血緣及原始 SQL。mappingPaths 是圖查詢取得的實體路徑，不含第二輪 AI 判斷或機率。沿 selectedConceptPaths 與 mappingPaths 的 conceptPathKeys、mappingKey 理解對應，可同時包含多條路徑。conceptPathScores 的機率原樣保留，不是金額或加權，也不跨候選正規化。')
prompt = prompt.replace('selectedMappingPathKeys 表示原生 Jev 納入的實體路徑', 'mappingPathKeys 表示此實作查回的所有實體路徑')
prompt = prompt.replace('一條實體路徑被納入後，KB 仍保留該實作的全部必要依賴', 'KB 取回每個對應實作的全部必要依賴')
prompt = prompt.replace('不得因只選一條底表路徑就刪掉必要依賴', '不得因路徑重疊就刪掉必要依賴')
(HERE/'single_jev_sql_evidence_prompt.txt').write_text(prompt,encoding='utf-8')
