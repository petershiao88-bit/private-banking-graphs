"""Build two native Jev phases with selected-concept-only route retrieval."""
import json,uuid
from pathlib import Path
from copy import deepcopy
from lazy_queries import CATALOG,PATHS,MAPPINGS
HERE=Path(__file__).resolve().parent
def read(n):return json.loads((HERE/n).read_text(encoding='utf-8-sig'))
def code(n):return (HERE/n).read_text(encoding='utf-8')
def write(n,v):(HERE/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def node_id(n):return str(uuid.uuid5(uuid.NAMESPACE_URL,'pb-kb-lazy-routes:'+n))
def jsnode(name,file,native=False):
 return {'id':node_id(name),'name':name,'type':'n8n-nodes-base.code','typeVersion':2,'parameters':{'jsCode':(code('jev_response.js')+'\n' if native else '')+code(file)},'position':[0,0]}
def request(query,params):
 # n8n's expression delimiter recognizes }} even inside a quoted Cypher map.
 # Whitespace between map terminators preserves Cypher semantics.
 query=query.replace('}}','} }')
 return '={{ (() => { '+params+' return {statement:'+json.dumps(query,ensure_ascii=False)+',parameters}; })() }}'
def build():
 w=read('PB_AUM_Income_KB.before_simplify.live.json');old={n['name']:n for n in w['nodes']}
 def http(name,query,params):
  n=deepcopy(old['Aura - Concept Catalog']);n.update(id=node_id(name),name=name,position=[0,0]);n['parameters']['jsonBody']=request(query,params);return n
 def jev(name):
  n=deepcopy(old['Jev - Concept Decisions API']);n.update(id=node_id(name),name=name,position=[0,0]);return n
 w['nodes']=[deepcopy(old['KB Input']),
  http('Aura - Concept Catalog',CATALOG,"const input=$('KB Input').first().json; const parameters={metricCodes:input.metricCodes,domains:input.domains};"),
  jsnode('Jev - Prepare Concepts','prepare_concepts.js'),jev('Jev - Concept Decisions API'),jsnode('Concept Decision Result','concept_decision.js',True),
  http('Aura - Concept Paths',PATHS,"const parameters={selectedConcepts:$json.selectedConcepts,metricCodes:$json.metricCodes};"),
  jsnode('Concept Routes','concept_routes.js'),jsnode('Jev - Prepare Paths','prepare_routes.js'),jev('Jev - Path Decisions API'),jsnode('Route Decision Result','route_decision.js',True),
  http('Aura - Mappings',MAPPINGS,"const parameters={selectedPaths:$json.selectedPaths};"),jsnode('KB Result','evidence_result.js')]
 names=[n['name'] for n in w['nodes']]
 for i,n in enumerate(w['nodes']):
  # A single chain follows concept selection, route selection, then mapping.
  n['position']=[i*220,180]
  if n['name']=='Aura - Concept Catalog':n['notes']='只回傳候選概念識別、定義與允許的指標範圍，不載入業務路徑、staging 或 SQL。'
  elif n['name']=='Aura - Concept Paths':n['notes']='以第一輪選定 conceptKey 與領域查完整路徑，支援一個概念多條路徑。'
  elif n['name']=='Aura - Mappings':n['notes']='第二輪已選完整路徑才查技術實現；以路徑上的概念錨點與衡量關係綁定，支援多對多。'
  elif 'Decisions API' in n['name']:n['notes']='原生 typesafe/jev-1.13 Decisions API；此輪的候選機率獨立保留。'
  n.pop('notesInFlow',None)
 w['connections']={}
 def connect(source,*targets):w['connections'][source]={'main':[[{'node':t,'type':'main','index':0}] for t in targets]}
 for a,b in zip(names,names[1:]):connect(a,b)
 for key in ['activeVersion','activeVersionId','versionId','versionCounter','meta','staticData']:w.pop(key,None)
 w['pinData']={}
 for n in ['PB_AUM_Income_KB.lazy.ready.json','PB_AUM_Income_KB.evidence.ready.json','PB_AUM_Income_KB.jev.ready.json','PB_AUM_Income_KB.ready.json','PB_AUM_Income_KB.json']:write(n,w)
 test=deepcopy(w);test['pinData']={'KB Input':[{'json':{'question':'請查2026年9月全體客戶的證券基金月底AUM，以新臺幣呈現。','domains':['aum'],'metricCodes':['aum_securities_month_end']}}]};write('PB_AUM_Income_KB.lazy.test.json',test)
 for n,q in [('lookup_concepts.cypher',CATALOG),('lookup_concept_paths.cypher',PATHS),('lookup_mappings.cypher',MAPPINGS)]:(HERE/n).write_text(q+'\n',encoding='utf-8')
 (HERE/'kb_result.js').write_text(code('evidence_result.js'),encoding='utf-8')
 m=read('main.before_simplify.live.json');by={n['name']:n for n in m['nodes']}
 m['nodes']=[n for n in m['nodes'] if n['name'] not in ['KB Route and Evidence Ready','KB Not Ready']]
 m['connections'].pop('KB Route and Evidence Ready',None);m['connections'].pop('KB Not Ready',None)
 m['connections']['Product Concept KB']={'main':[[{'node':'Available Source Metadata','type':'main','index':0}]]}
 by['SQL Reasoning Agent']['parameters']['text']=code('sql_evidence_prompt.txt')
 by['Normalize SQL Result']['parameters']['jsCode']=code('normalize_evidence_result.js')
 by['保留候選機率']['parameters']['jsCode']=code('retain_probability.js')
 query=by['Execute a SQL query']['parameters']['query']
 by['Execute a SQL query']['parameters']['query']='\n'.join(line for line in query.split('\n') if "$('Product Concept KB').first().json.status" not in line and "$('Product Concept KB').first().json.canGenerateSql" not in line)
 for key in ['activeVersion','activeVersionId','versionId','versionCounter','meta','staticData']:m.pop(key,None)
 m['pinData']={}
 for n in ['main.lazy.ready.json','main.evidence.ready.json','main.jev.ready.json','main.copy.ready.json']:write(n,m)
 print(json.dumps({'kbNodes':len(w['nodes']),'mainNodes':len(m['nodes']),'contract':'pb_kb_lazy_routes_v4','jevPhases':2},ensure_ascii=False))
if __name__=='__main__':build()
