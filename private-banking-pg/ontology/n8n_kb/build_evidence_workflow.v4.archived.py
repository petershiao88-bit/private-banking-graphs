"""Build graph-evidence contracts from the last deployed Jev workflows."""
import json,csv,uuid
from pathlib import Path
from copy import deepcopy
from evidence_queries import CONCEPTS,MAPPINGS,REGISTRY
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def write(name,value):(HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def code(name):return (HERE/name).read_text(encoding='utf-8')
def request(query,params):
 return '={{ (() => { '+params+' return {statement:'+json.dumps(query,ensure_ascii=False)+',parameters}; })() }}'
def code_node(name,file,position):
 return {'id':str(uuid.uuid4()),'name':name,'type':'n8n-nodes-base.code','typeVersion':2,'position':position,'parameters':{'jsCode':code(file)}}
def gate_node(name,expression,position):
 return {'id':str(uuid.uuid4()),'name':name,'type':'n8n-nodes-base.if','typeVersion':2.2,'position':position,'parameters':{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':str(uuid.uuid4()),'leftValue':expression,'rightValue':'','operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}}}
def connect(w,source,*targets):
 w['connections'][source]={'main':[[{'node':t,'type':'main','index':0}] for t in targets]}
def build():
 for current,backup in [('PB_AUM_Income_KB.deployed.json','PB_AUM_Income_KB.before_evidence.json'),('main.jev.deployed.json','main.before_evidence.json')]:
  if not (HERE/backup).exists():write(backup,read(current))
 w=read('PB_AUM_Income_KB.before_paths.live.json');by={n['name']:n for n in w['nodes']}
 by['Aura - Concepts']['parameters']['jsonBody']=request(CONCEPTS,"const parameters={metricCodes:Array.isArray($json.metricCodes)?$json.metricCodes:[$json.metricCodes],domains:Array.isArray($json.domains)?$json.domains:[$json.domains]};")
 by['Aura - Concepts']['notes']='同時保留 PBConcept 辨識目錄與 SharedProduct → BusinessMetric → 上層指標的完整業務證據；以 productCode 明確連接。'
 for name,file in [('Concept Catalog','concept_catalog.js'),('Jev - Prepare Objects','jev_prepare.js'),('Jev - Evaluate Objects','jev_evaluate.js'),('KB Result','evidence_result.js')]:by[name]['parameters']['jsCode']=code(file)
 by['Jev - Decisions API'].update(retryOnFail=True,maxTries=3,waitBetweenTries=1500)
 w['nodes'] += [code_node('Concept Paths','concept_paths.js',[720,300]),gate_node('Concept Route Ready',"={{ $json.status === 'selected' && $json.pathStatus === 'confirmed' && $json.selectedConceptPaths.length > 0 }}",[1680,300]),code_node('Selected Paths','selected_paths.js',[1920,220])]
 order=['KB Input','Aura - Concepts','Concept Catalog','Concept Paths','Jev - Prepare Objects','Jev - Decisions API','Jev - Evaluate Objects','Concept Route Ready','Selected Paths','Aura - Mappings','KB Result']
 positions={name:[i*240,300] for i,name in enumerate(order)}
 for n in w['nodes']:n['position']=positions[n['name']]
 connect(w,'Concept Catalog','Concept Paths');connect(w,'Concept Paths','Jev - Prepare Objects');connect(w,'Jev - Evaluate Objects','Concept Route Ready')
 connect(w,'Concept Route Ready','Selected Paths','KB Result');connect(w,'Selected Paths','Aura - Mappings')
 by['Aura - Mappings']['parameters']['jsonBody']=request(MAPPINGS,"if($json.status!=='selected' || $json.pathStatus!=='confirmed' || !$json.selectedPaths?.length) throw new Error('未確認完整業務路徑。'); const parameters={selectedPaths:$json.selectedPaths};")
 by['Aura - Mappings']['notes']='先核對已選完整業務路徑的節點、關係方向及屬性，再沿明確的產品指標對應查 staging 與完整 SQL 依賴；回傳 pathKey 及 queryMetricKey。'
 by['Jev - Prepare Objects']['notes']='先逐 object 評估，再評估完整業務路徑（path choice）；state 僅含業務定義，不含技術映射。'
 by['KB Result']['notes']='pb_kb_path_evidence_v2：只回傳已确认概念路徑及其綁定映射；object/path 各自保留原生機率。SQL 證據完整性獨立檢查。'
 for k in ['activeVersion','activeVersionId','versionId','versionCounter','meta']:w.pop(k,None)
 w['pinData']={}
 for name in ['PB_AUM_Income_KB.evidence.ready.json','PB_AUM_Income_KB.jev.ready.json','PB_AUM_Income_KB.ready.json','PB_AUM_Income_KB.json']:write(name,w)
 (HERE/'lookup_concepts.cypher').write_text(CONCEPTS+'\n',encoding='utf-8');(HERE/'lookup_mappings.cypher').write_text(MAPPINGS+'\n',encoding='utf-8')
 (HERE/'kb_result.js').write_text(code('evidence_result.js'),encoding='utf-8')
 test=deepcopy(w);test['pinData']={'KB Input':[{'json':{'question':'請查2026年9月全體客戶的存款利收，以新臺幣呈現。','domains':['income'],'metricCodes':['deposit_interest_income']}}]}
 write('PB_AUM_Income_KB.evidence.test.json',test)
 m=read('main.before_paths.live.json');b={n['name']:n for n in m['nodes']}
 registry=b['Get row(s)'];registry.update(type='n8n-nodes-base.httpRequest',typeVersion=4.2)
 registry['parameters']=deepcopy(by['Aura - Concepts']['parameters']);registry['parameters']['jsonBody']=request(REGISTRY,'const parameters={};')
 registry['credentials']=deepcopy(by['Aura - Concepts']['credentials']);registry['notes']='從 Neo4j 讀取 AUM／Income 12 個概念指標；不修改原 AUM Data Table。'
 aliases={}
 with (HERE.parents[1]/'deliverables/metrics/router_postgresql_v0.4/AUM_Metric_Router_Registry_PostgreSQL_v0.4.csv').open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):aliases[row['metric_code']]=json.loads(row['aliases'])
 aggregate=b['Aggregate'];aggregate.update(type='n8n-nodes-base.code',typeVersion=2)
 aggregate['parameters']={'jsCode':"const b=$input.first().json; if(b.errors?.length || !b.data?.fields || !Array.isArray(b.data.values)) throw new Error('指標目錄查詢失敗。'); const aliases="+json.dumps(aliases,ensure_ascii=False)+"; const metrics=b.data.values.map(row=>{const m=Object.fromEntries(b.data.fields.map((k,i)=>[k,row[i]])); if(!['aum','income'].includes(m.domain) || !m.metric_code) throw new Error('指標領域無效。'); return {...m,aliases:[...new Set([...(m.aliases || []),...(aliases[m.metric_code] || [])])]};}); if(new Set(metrics.map(m=>m.metric_code)).size!==metrics.length) throw new Error('指標代碼重複。'); return [{json:{metrics}}];"}
 classifier=b['Basic LLM Chain']['parameters']['messages']['messageValues'][0]
 classifier['message']=classifier['message'].replace('你是私銀 AUM 智能查詢','你是私銀 AUM／Income 智能查詢')
 classifier['message']=classifier['message'].replace('本主流程目前 registry 只含 AUM。要求 Income 數值時 route=unsupported，說明尚未配置 Income metric 路由；不得將 Income 當成 AUM。','本次 registry 同時含 AUM 與 Income。AUM 是資產衡量，Income 是收入；依使用者要求分流，兩者並查時完整保留。Income 月份必須能確定年份與月份。業務月底取數規則由 KB 證據決定，不假設每位客戶各自取最新日。')
 router=b['metric router']['parameters']['messages']['messageValues'][0]
 router['message']=router['message'].replace('你是 AUM Metric Router','你是 AUM／Income Metric Router')+' AUM 與 Income 分別選本次 registry 中對應 domain 的代碼；存款利收選 deposit_interest_income。兩領域並查時保留兩領域指標。'
 kb=b['Product Concept KB'];kb['parameters']['workflowInputs']['value']['domains']="={{ (() => { const codes=$('metric router').item.json.output.selected_metric_codes; const metrics=$('Aggregate').first().json.metrics; for(const c of codes) if(!metrics.some(m=>m.metric_code===c)) throw new Error('選取指標不在本次 registry。'); const domains=[...new Set(codes.map(c=>metrics.find(m=>m.metric_code===c).domain))]; return domains.length?domains:['aum','income']; })() }}"
 sql=b['SQL Reasoning Agent']['parameters']
 sql['text']=code('sql_evidence_prompt.txt')
 guard=b['Execute a SQL query']['parameters']['query']
 marker="if ($('Product Concept KB').first().json.status !== 'selected') return \"SELECT 'KB_PRODUCT_OR_DEFINITION_UNRESOLVED' AS error_message;\";"
 assert marker in guard
 guard=guard.replace(marker,marker+"\nif ($('Product Concept KB').first().json.canGenerateSql !== true) return \"SELECT 'KB_EVIDENCE_INCOMPLETE' AS error_message;\";\n"+code('readonly_sql_guard.js'))
 b['Execute a SQL query']['parameters']['query']=guard
 b['Normalize SQL Result']['parameters']['jsCode']=code('normalize_evidence_result.js')
 b['保留候選機率']['parameters']['jsCode']=code('retain_probability.js')
 m['nodes'] += [gate_node('KB Route and Evidence Ready',"={{ $json.status === 'selected' && $json.pathStatus === 'confirmed' && $json.canGenerateSql === true }}",[1380,0]),
  {'id':str(uuid.uuid4()),'name':'KB Not Ready','type':'n8n-nodes-base.code','typeVersion':2,'position':[1620,180],'parameters':{'jsCode':"const kb=$input.first().json; return [{json:{error_message:kb.status==='selected'?'KB_EVIDENCE_INCOMPLETE':'KB_PRODUCT_OR_DEFINITION_UNRESOLVED'}}];"}}]
 connect(m,'metric router','Product Concept KB');connect(m,'Product Concept KB','KB Route and Evidence Ready')
 connect(m,'KB Route and Evidence Ready','Available Source Metadata','KB Not Ready');connect(m,'KB Not Ready','Normalize SQL Result')
 connect(m,'Available Source Metadata','SQL Reasoning Agent')
 b['Response']['parameters']['text']+='\nstatus=evidence_incomplete：說明已辨識產品，但計算依據仍有缺口，不能報金額。依原因說明缺口，勿將它當成產品辨識歧義。\nstatus=no_match：說明支援範圍內沒有符合產品，不能報金額。\n選品：{{ $json.kbStatus }}\n證據狀態：{{ $json.evidenceStatus }}'
 for k in ['activeVersion','activeVersionId','versionId','versionCounter','meta']:m.pop(k,None)
 m['pinData']={}
 for name in ['main.evidence.ready.json','main.jev.ready.json','main.copy.ready.json']:write(name,m)
 print(json.dumps({'kbNodes':len(w['nodes']),'mainNodes':len(m['nodes']),'contract':'pb_kb_path_evidence_v2','registry':'AUM + Income'},ensure_ascii=False))
if __name__=='__main__':build()
