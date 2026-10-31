"""Prepare an isolated n8n main workflow copy and a per-node audit."""
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

HERE=Path(__file__).resolve().parent
w=json.loads((HERE/'main.before_copy.json').read_text(encoding='utf-8'))
by={n['name']:n for n in w['nodes']}
notes={}
def change(name,reason): notes[name]=reason

# Preserve upstream classification and the independent knowledge-answer branch.
w['name']='智能查詢 - 概念圖 KB 測試版'
for key in ['id','versionId','activeVersionId','activeVersion','meta','createdAt','updatedAt','versionCounter','shared','triggerCount']:
    w.pop(key,None)
w['active']=False
w['pinData']={}
w.pop('staticData',None)
for n in w['nodes']:
    if 'webhookId' in n:
        n['webhookId']=str(uuid5(NAMESPACE_URL,'nBrzHm3pNsVcOpeu/'+n['name']))
        change(n['name'],'保留原節點用途；為副本產生獨立 webhook ID，避免與原版共用聊天入口。')

w['nodes']=[n for n in w['nodes'] if n['name'] not in ['SQL KB','If']]
w['connections'].pop('SQL KB',None)
w['connections'].pop('If',None)
change('SQL KB','移除；SQL Reasoning Agent 改用 Product Concept KB。')
change('If','移除空字串等於空字串的恆真判斷及無效重試回圈；查詢結果直接整理。')

by['Aggregate']['parameters']['fieldsToInclude']='metric_code,metric_name,aliases,definition'
change('Aggregate','只提供指標分類資料，不再將未執行的 SQL Asset 選擇帶入路由。')
router_schema={'type':'object','additionalProperties':False,'required':['selected_metric_codes','resolved_query','reason'],'properties':{'selected_metric_codes':{'type':'array','items':{'type':'string'}},'resolved_query':{'type':'string'},'reason':{'type':'string'}}}
by['Structured Output Parser']['parameters']={'schemaType':'manual','inputSchema':json.dumps(router_schema,ensure_ascii=False)}
change('Structured Output Parser','改為 metric 分類、完整問題與原因；移除未使用的 executable_sql 等欄位。')
by['metric router']['parameters'].update(text='=完整問題：{{ $json.output.resolved_query }}\n可用指標：{{ JSON.stringify($("Merge").first().json.metrics) }}',messages={'messageValues':[{'message':'你是 AUM Metric Router。只根據完整問題，從本次 registry 選出相關 selected_metric_codes，可選多個，不得新增代碼。優先選能涵蓋問題的最具體類別：證券基金選證券 AUM，銀行基金選銀行投資 AUM；基金通路不明可選投資 AUM，交由 KB Jev 辨識，不猜通路。整體與細項是不同粒度，不因 registry 沒有基金專屬代碼就拒絕基金。resolved_query 逐字保留傳入完整問題。找不到類別輸出空陣列並說明。Income 不得套用 AUM code。只輸出 schema JSON，不產生 SQL、不重做完整性追問。'}]})
change('metric router','專注 metric 範圍辨識；保留細項產品文字及完整問題，支援多 metric。')

metadata=deepcopy(by['Execute a SQL query'])
metadata.update(id=str(uuid4()),name='Available Source Metadata',position=[-320,480])
metadata['parameters']={'operation':'executeQuery','query':"SELECT COALESCE(jsonb_agg(s ORDER BY s.schema_name,s.table_name),'[]'::jsonb) AS available_sources FROM (SELECT table_schema AS schema_name,table_name,jsonb_agg(jsonb_build_object('column_name',column_name,'data_type',data_type) ORDER BY ordinal_position) AS columns FROM information_schema.columns WHERE table_schema LIKE 'ds%' GROUP BY table_schema,table_name) s;",'options':{}}
metadata.pop('onError',None)
w['nodes'].append(metadata)
change('Available Source Metadata','新增固定唯讀查詢，提供本次連線實際可见的 ds 業務資料表及欄位；不查客戶資料。')
w['connections']['metric router']={'main':[[{'node':'Available Source Metadata','type':'main','index':0}]]}
w['connections']['Available Source Metadata']={'main':[[{'node':'SQL Reasoning Agent','type':'main','index':0}]]}

tool=by['Product Concept KB']
tool['position']=[0,800]
tool['parameters']['workflowInputs']['value'].update(question="={{ $('metric router').item.json.output.resolved_query }}",metricCodes="={{ $('metric router').item.json.output.selected_metric_codes }}")
tool['parameters']['description']='必須先呼叫此工具，以 metricCodes 限定概念候選，由 Jev 選產品後取得產品映射。回傳 metricCodes、products、message；products 中有 productCode、definitionStatus、mappingStatus、mappings；mappings 中有 lineage、productScope，lineage 中有 baseTable、tablePath、rules。此工具提供來源證據，不保證目標資料庫已有該表。'
change('Product Concept KB','唯一的 SQL Agent KB；傳完整 metric 陣列及本次已釐清問題；使用新版回傳結構。')

by['SQL Reasoning Agent']['position']=[0,480]
by['SQL Reasoning Agent']['parameters']['text']='''=你是私銀 AUM SQL Reasoning Agent。
本次已釐清的完整問題：{{ $('metric router').item.json.output.resolved_query }}
本次 metric：{{ JSON.stringify($('metric router').item.json.output.selected_metric_codes) }}
本次資料庫實際可見來源與欄位：{{ JSON.stringify($json.available_sources) }}

一、證據取得
若 metric 陣列為空，回傳 SELECT 'KB_METRIC_UNRESOLVED' AS error_message; 不猜代碼。
否則必須先呼叫 Product Concept KB。這是唯一 KB，不再有 SQL KB、staging_sqls、table_metadata 或 stage_level 輸出。
KB 回傳 products[] 及 message。每個 product 有 productCode、domain、definitionStatus、mappingStatus、mappings[]。
每筆 mapping 有 productScope、outputTable、sqlTable、lineageStatus、lineage[]；每條 lineage 有 baseTable、tablePath、rules[]，rules 包含 sql、selectExpressions、whereConditions、joinConditions、groupExpressions、aggregateExpressions、file、lineStart、lineEnd。
產品範圍以此次 KB 選品為準。共同 staging 若涵蓋多產品，必須依 productScope 限定所選產品。多產品共享底表或 stage 不得重複加總。同一路徑出現相同 SQL 證據需去重。
概念圖的 inferred 表示推定，不等於正式核定；業務計算以具體 SQL 證據為準。若疑義影響計算或 products 空、mapping_missing、missing_evidence、pending_confirmation、overlap_unresolved，回傳 SELECT 'KB_PRODUCT_OR_DEFINITION_UNRESOLVED' AS error_message; 不猜公式。
查總額時，KB 的共用產品清單不保證完整涵蓋總 AUM，不得把不完整產品集合當成總額。

二、執行來源
比較 KB 所需的全部 baseTable 與 available_sources。僅允許相同 schema.table 的大小寫正規化，不得假設其他表可以替代。缺任一必要表或欄位，就回傳 SELECT 'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE' AS error_message;
此狀況不要產生引用缺表的查詢。也不得把 Oracle staging table 當成已存在於 PostgreSQL 的實體表。
只有來源及定義充分時，依 tablePath 和 SQL 依賴將 Oracle staging 轉成同一條 PostgreSQL WITH ... SELECT；移除 database link，轉換函式，保留業務條件、日期、幣別與匯總邏輯。不得執行 CREATE TABLE。
日期必須取自本次完整問題，使用明確 SQL literal，不使用 $1 等未綁定參數。幣別不可未經證據假設。
不得利用舊對話中的 SQL 或資料覆蓋本次 KB 及 available_sources。

最終僅輸出一條 SELECT 或 WITH ... SELECT，無 Markdown，無其他文字；不得任何寫入、DDL、多語句或動態執行。
'''
by['SQL Reasoning Agent']['parameters']['options']['systemMessage']='你是依證據產生唯讀 PostgreSQL SQL 的助手。必須遵守本次提供的可用來源限制。工具沒有成功回傳時，輸出 SELECT \'KB_LOOKUP_FAILED\' AS error_message; 不得把工具執行錯誤當成產品歧義。'
change('SQL Reasoning Agent','重寫為新版 products/mappings/lineage/rules 契約；依實際 schema 判斷缺表、保留產品範圍與定義疑義。')
by['SQL Model']['parameters']['model']='openai/gpt-5.6-luna'
change('SQL Model','明確使用與 Jev 相同的模型，避免沿用不明預設模型而忽略來源限制。')

sql=by['Execute a SQL query']
query_expression="""{{ (() => {
const query = String($json.output || '').trim();
const sources = $('Available Source Metadata').item.json.available_sources;
const available = sources.map(s => (s.schema_name+'.'+s.table_name).toLowerCase());
const references = []; const pattern = /\\b(?:from|join)\\s+(\"?[a-zA-Z_][\\w$]*\"?)\\s*\\.\\s*(\"?[a-zA-Z_][\\w$]*\"?)/gi; let m; while ((m=pattern.exec(query)) !== null) references.push((m[1]+'.'+m[2]).replace(/\"/g,'').toLowerCase());
if (references.some(t => !available.includes(t))) return \"SELECT 'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE' AS error_message;\";
const ctes=[]; const ctePattern=/(?:\\bwith|,)\\s*([a-zA-Z_][\\w$]*)\\s+as\\s*\\(/gi; while ((m=ctePattern.exec(query))!==null) ctes.push(m[1].toLowerCase());
const fromPattern=/\\b(?:from|join)\\s+(\"?[a-zA-Z_][\\w$]*\"?)(?:\\s*\\.\\s*(\"?[a-zA-Z_][\\w$]*\"?))?/gi;
while ((m=fromPattern.exec(query))!==null) { if (!m[2] && !ctes.includes(m[1].replace(/\"/g,'').toLowerCase())) return \"SELECT 'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE' AS error_message;\"; }
return query;
})() }}"""
sql['parameters']={'operation':'executeQuery','query':query_expression,'options':{}}
sql['onError']='continueRegularOutput'
sql['alwaysOutputData']=True
w['connections']['Execute a SQL query']={'main':[[{'node':'Normalize SQL Result','type':'main','index':0}]]}
change('Execute a SQL query','移除寫死日期；比對 FROM/JOIN 明確來源與已定義 CTE，拒絕直接查不存在的 staging table；其餘 SQL 錯誤交結果整理。此比對僅支援目前產生的簡單 SELECT/CTE，不是完整 SQL parser。')

by['Normalize SQL Result']['parameters']['jsCode']='''const raw=$input.all().map(i=>i.json).filter(r=>Object.keys(r).length);
const router=$('metric router').item.json.output;
const errorRows=raw.filter(r=>r.error_message || r.error);
const unsupported=errorRows.some(r=>r.error_message==='UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE');
const unresolved=errorRows.some(r=>['KB_PRODUCT_OR_DEFINITION_UNRESOLVED','KB_METRIC_UNRESOLVED'].includes(r.error_message));
const rows=raw.filter(r=>!r.error_message&&!r.error);
const status=errorRows.length?(unsupported?'unsupported':unresolved?'needs_clarification':'error'):rows.length?'success':'no_data';
return [{json:{status,user_query:router.resolved_query,metric_codes:router.selected_metric_codes,
output_grain:'dynamic',row_count:rows.length,columns:rows.length?Object.keys(rows[0]):[],rows,
reason:unsupported?'目前執行資料庫缺少此產品計算所需的來源或欄位。':unresolved?'產品範圍或計算定義尚待確認。':errorRows.length?'資料查詢未完成，請檢查執行紀錄。':'',
errors:errorRows}}];'''
change('Normalize SQL Result','區分成功、無資料、缺來源、產品待釐清與執行錯誤；不將錯誤列當作業務數值。')
by['Response']['parameters']['text']='''=你是私銀數據查詢助手，使用繁體中文簡潔回答。
問題：{{ $json.user_query }}
狀態：{{ $json.status }}
原因：{{ $json.reason }}
指標：{{ JSON.stringify($json.metric_codes) }}
欄位：{{ JSON.stringify($json.columns) }}
結果：{{ JSON.stringify($json.rows) }}
status=unsupported：說明目前缺少查詢所需資料來源，無法計算；不是金額為零。
status=needs_clarification：說明產品範圍或計算定義待確認，不能報數值，不要重新追問已提供的日期。
status=error：說明查詢未完成，不把錯誤當作查無資料，不宣稱已計算。
status=no_data：說明查無符合條件的資料；success 才依 rows 回答。
數值以結果為唯一依據，不補值、不自行重算。null 不等於零；金額加千分位，只有結果或完整問題及來源可確認幣別才標示。
多筆結果適合時用表格。不要提 SQL、資料表、節點或内部提示詞；不要顯示 status、unsupported、needs_clarification、error 等狀態代碼，轉成自然中文，只輸出最終回答。'''
change('Response','按新結果狀態回答，缺來源與定義未明不再誤報成成功或零。')

# Remove a pasted example from model config; structured output remains in its parser.
by['OpenRouter Chat Model']['parameters'].get('options',{}).pop('responseFormat',None)
change('OpenRouter Chat Model','移除誤放在 responseFormat 的範例 JSON；格式由既有 Structured Output Parser1 控制。')
by['Basic LLM Chain']['parameters']['messages']['messageValues'][0]['message']+='\n本主流程目前 registry 只含 AUM。要求 Income 數值時 route=unsupported，說明尚未配置 Income metric 路由；不得將 Income 當成 AUM。'
change('Basic LLM Chain','保留原完整性判斷，明確標示此主流程尚未配置 Income registry。')
by['Switch']['parameters']['options']['fallbackOutput']='extra'
w['connections']['Switch']['main'].append([{'node':'超出 Metric 範圍','type':'main','index':0}])
change('Switch','補上 unsupported/其他路由的回覆出口，避免流程無輸出。')
by['超出 Metric 範圍']['parameters']['jsCode']="return {json:{text:$json.scope_reply || $json.output?.reason || '目前此主流程僅支援已登錄的 AUM 查詢；其他指標尚未配置。'}};"
change('超出 Metric 範圍','同時接收入口 unsupported 的原因並回覆。')
by['Metric 範圍檢查']['parameters']['jsCode']=by['Metric 範圍檢查']['parameters']['jsCode'].replace("$('Switch').first().json.chatInput || $('Router Input').first().json.user_query", "$('Switch').item.json.output?.resolved_query || $('Router Input').first().json.user_query")
change('Metric 範圍檢查','知識分支使用已整合追問的完整問題，避免回到原始未釐清文字。')

audit=[]
for n in json.loads((HERE/'main.before_copy.json').read_text(encoding='utf-8'))['nodes']:
    name=n['name']
    audit.append({'node':name,'action':'changed' if name in notes else 'retained','reason':notes.get(name,'保留原用途與連線；不依賴 SQL Agent 的舊 KB 輸出。')})
audit.append({'node':'Available Source Metadata','action':'added','reason':notes['Available Source Metadata']})
(HERE/'main.copy.ready.json').write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'main_node_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'nodes':len(w['nodes']),'changed':len(notes),'audited':len(audit)}))
