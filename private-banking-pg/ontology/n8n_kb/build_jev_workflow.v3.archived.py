"""Build probability-preserving workflows from the backed-up live exports. No secrets."""
import json
from pathlib import Path
from copy import deepcopy
from uuid import uuid5, NAMESPACE_URL

HERE = Path(__file__).resolve().parent
def read(name): return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def write(name, obj): (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2),encoding='utf-8')
def code(name): return (HERE/name).read_text(encoding='utf-8')
def node(name, kind, parameters, x, y, version=2, **extra):
    return dict(name=name,id=str(uuid5(NAMESPACE_URL,'pb_jev_decisions/'+name)),type=kind,typeVersion=version,
                position=[x,y],parameters=parameters,**extra)
def link(name): return {'main':[[{'node':name,'type':'main','index':0}]]}

w=read('PB_AUM_Income_KB.before_jev_decisions.json')
old={n['name']:deepcopy(n) for n in w['nodes']}
catalog=old['Concept Catalog']['parameters']['jsCode']
catalog=catalog.replace("const request = $('KB Input').first().json;", """const raw = $('KB Input').first().json;
const normalize = value => (Array.isArray(value) ? value : [value]).map(v => typeof v === 'string' ? v.trim() : v);
const request = {...raw, domains:normalize(raw.domains), metricCodes:normalize(raw.metricCodes)};
if (typeof request.question !== 'string' || !request.question.trim() || !request.domains.length || !request.domains.every(d=>['aum','income'].includes(d)) || !request.metricCodes.length || !request.metricCodes.every(c=>typeof c==='string'&&c)) throw new Error('KB 輸入無效。');""")
old['Concept Catalog']['parameters']['jsCode']=catalog
concept=old['Aura - Concepts']['parameters']['jsonBody']
concept=concept.replace('const metricCodes = $json.metricCodes; const domains = $json.domains;', "const metricCodes = Array.isArray($json.metricCodes) ? $json.metricCodes : [$json.metricCodes]; const domains = Array.isArray($json.domains) ? $json.domains : [$json.domains];")
old['Aura - Concepts']['parameters']['jsonBody']=concept
result=old['KB Result']['parameters']['jsCode'].replace("$('Jev - Select Products').first().json.output", "$('Jev - Evaluate Objects').first().json")
result=result.replace('definition:concept.definition,definitionStatus:', 'probability:choice.candidateScores.find(c=>c.productCode===s.productCode&&c.domain===s.domain).probability,\n    definition:concept.definition,definitionStatus:')
result=result.replace('metricCodes:context.metricCodes,products,message:', 'metricCodes:context.metricCodes,status:choice.status,candidateScores:choice.candidateScores,decision:choice.decision,products,message:')
old['KB Result']['parameters']['jsCode']=result
old['KB Result']['notes']='回傳每個 object 的原始 Jev 機率、完整分布、決策證據與選定產品映射。未校準機率門檻；不執行底表 SQL。'
mapping=old['Aura - Mappings']['parameters']['jsonBody'].replace('const choice = $json.output;', 'const choice = $json;')
old['Aura - Mappings']['parameters']['jsonBody']=mapping
old['Aura - Mappings']['notes']='固定唯讀 Cypher。僅對明確選定的產品查映射；歧義保留全部機率並傳空 selections。'
request=node('Jev - Prepare Objects','n8n-nodes-base.code',{'jsCode':code('jev_prepare.js')},840,0)
http=node('Jev - Decisions API','n8n-nodes-base.httpRequest',{
    'method':'POST','url':'https://openrouter.ai/api/alpha/decisions',
    'authentication':'predefinedCredentialType','nodeCredentialType':'openRouterApi',
    'sendBody':True,'specifyBody':'json','jsonBody':'={{ $json.decisionRequest }}',
    'options':{'timeout':60000,'response':{'response':{'responseFormat':'json'}}}},1120,0,4.2,
    credentials=old['Jev Model']['credentials'],notes='直接呼叫 typesafe/jev-1.13 Decisions API，沿用既有 OpenRouter credential；不經 jev-router 或聊天模型。',notesInFlow=True)
evaluate=node('Jev - Evaluate Objects','n8n-nodes-base.code',{'jsCode':code('jev_evaluate.js')},1400,0,
    notes='逐 object 驗證完整分布，不重算機率或選 top-1；以原生 choice 分流歧義，numericThreshold=null、calibrated=false。')
w['nodes']=[old['KB Input'],old['Aura - Concepts'],old['Concept Catalog'],request,http,evaluate,old['Aura - Mappings'],old['KB Result']]
for i,n in enumerate(w['nodes']): n['position']=[i*280,0]
w['connections']={a['name']:link(b['name']) for a,b in zip(w['nodes'],w['nodes'][1:])}
w['pinData']={}
for k in ['activeVersion','activeVersionId','versionId','versionCounter','meta']: w.pop(k,None)
write('PB_AUM_Income_KB.jev.ready.json',w)
write('PB_AUM_Income_KB.json',w)
write('PB_AUM_Income_KB.ready.json',w)
(HERE/'concept_catalog.js').write_text(catalog,encoding='utf-8')
(HERE/'kb_result.js').write_text(result,encoding='utf-8')
# A separate import file supplies non-sensitive fixture data for editor-only testing.
test=deepcopy(w)
test['pinData']={'KB Input':[{'json':{'question':'請查2026年9月底全體客戶的證券基金 AUM，以新臺幣呈現。','domains':['aum'],'metricCodes':['aum_securities_month_end']}}]}
write('PB_AUM_Income_KB.jev.test.json',test)

m=read('main.before_jev_decisions.json')
by={n['name']:n for n in m['nodes']}
kb=by['Product Concept KB']
kb.update(type='n8n-nodes-base.executeWorkflow',typeVersion=1.3,position=[-160,480])
kb['parameters'].pop('description',None)
kb['parameters']['options']={'waitForSubWorkflow':True}
kb['notes']='主流程固定執行 KB，完整候選機率保留在標準節點輸出，不交給聊天模型決定是否呼叫。'
m['connections']['Available Source Metadata']=link('Product Concept KB')
m['connections']['Product Concept KB']=link('SQL Reasoning Agent')
agent=by['SQL Reasoning Agent']
agent.update(type='@n8n/n8n-nodes-langchain.chainLlm',typeVersion=1.9)
agent['parameters']['messages']={'messageValues':[{'message':agent['parameters'].get('options',{}).get('systemMessage','依證據產生唯讀 SQL。')}]}
agent['parameters'].pop('options',None)
agent['parameters']['batching']={}
t=agent['parameters']['text'].replace('$json.available_sources',"$('Available Source Metadata').first().json.available_sources")
t=t.replace('否則必須先呼叫 Product Concept KB。這是唯一 KB，不再有 SQL KB、staging_sqls、table_metadata 或 stage_level 輸出。', 'Product Concept KB 已由主流程固定執行。只使用以下本次 KB 結果，不自行重新選品：\n{{ JSON.stringify($json) }}\n若 KB.status 不是 selected，回傳 SELECT \'KB_PRODUCT_OR_DEFINITION_UNRESOLVED\' AS error_message; 不產生業務計算。\n候選機率屬於產品辨識，不能當成 AUM／Income 金額、加總權重或業務計算核准。')
agent['parameters']['text']=t
sql=by['Execute a SQL query']['parameters']['query']
sql=sql.replace("const query = String($json.output || '').trim();", "const query = String($json.output || '').trim();\nif ($('Product Concept KB').first().json.status !== 'selected') return \"SELECT 'KB_PRODUCT_OR_DEFINITION_UNRESOLVED' AS error_message;\";")
sql=sql.replace("String($json.output || '')", "String($json.text || $json.output || '')")
if not sql.startswith('='): sql='='+sql
by['Execute a SQL query']['parameters']['query']=sql
m['connections']['Postgres Chat Memory']['ai_memory']=[[c for c in conn if c['node']!='SQL Reasoning Agent'] for conn in m['connections']['Postgres Chat Memory'].get('ai_memory',[])]
m['connections']['Postgres Chat Memory']['ai_memory']=[conn for conn in m['connections']['Postgres Chat Memory']['ai_memory'] if conn]
if not m['connections']['Postgres Chat Memory']['ai_memory']: m['connections']['Postgres Chat Memory'].pop('ai_memory')
normalize=by['Normalize SQL Result']['parameters']['jsCode']
normalize=normalize.replace('const router=', "const kb=$('Product Concept KB').first().json;\nconst router=")
normalize=normalize.replace('status,user_query:', 'status,candidateScores:kb.candidateScores,decision:kb.decision,kbStatus:kb.status,kbMessage:kb.message,user_query:')
by['Normalize SQL Result']['parameters']['jsCode']=normalize
reply=node('保留候選機率','n8n-nodes-base.code',{'jsCode':"""const response=$input.first().json;
const normalized=$('Normalize SQL Result').first().json;
const scores=normalized.candidateScores || [];
const escape=s=>String(s).replace(/[|\\r\\n]/g,' ');
const rows=scores.map(c=>`| ${escape(c.productName)} | ${c.domain==='aum'?'AUM':'Income'} | ${c.probability} |`);
const table=rows.length?'\\n\\n候選產品的納入機率（0～1）：\\n\\n| 產品 | 領域 | 機率 |\\n|---|---|---|\\n'+rows.join('\\n'):'';
const clarification=normalized.kbStatus==='needs_clarification'?'\\n\\n'+normalized.kbMessage:'';
return [{json:{...response,text:String(response.text || response.output || '')+clarification+table,candidateScores:scores,decision:normalized.decision}}];"""},1020,480)
m['nodes'].append(reply)
m['connections']['Response']=link(reply['name'])
m['connections'][reply['name']]=link('送出查詢回答')
mx,my=by['Available Source Metadata']['position']
kb['position']=[mx+280,my]
for name in ['SQL Reasoning Agent','SQL Model','Execute a SQL query','Normalize SQL Result','Response','Response Model']:
    by[name]['position'][0]+=280
by['送出查詢回答']['position'][0]+=560
reply['position']=[by['Response']['position'][0]+280,by['Response']['position'][1]]
m['pinData']={}
for k in ['activeVersion','activeVersionId','versionId','versionCounter','meta']: m.pop(k,None)
write('main.jev.ready.json',m)
write('main.copy.ready.json',m)
print(json.dumps({'kbNodes':len(w['nodes']),'mainNodes':len(m['nodes']),'model':'typesafe/jev-1.13'},ensure_ascii=False))
