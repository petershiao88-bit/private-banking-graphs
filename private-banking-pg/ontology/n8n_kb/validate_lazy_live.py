"""Verify catalog→selected concepts→paths→selected paths→mappings, read-only."""
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_aura_snapshot import credentials,selected_aura
from import_ontology_neo4j import Neo4j
from lazy_queries import CATALOG,PATHS,MAPPINGS,REGISTRY
HERE=Path(__file__).resolve().parent
def fixture(payload):return json.loads(subprocess.check_output(['node',str(HERE/'lazy_fixture.cjs')],input=json.dumps(payload).encode('utf-8')))
def write(name,v):(HERE/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--credentials',type=Path,required=True);a=p.parse_args()
 c=credentials(a.credentials);db=Neo4j(selected_aura(c['NEO4J_URI']),'neo4j',c['NEO4J_USERNAME'],c['NEO4J_PASSWORD'])
 cases={'deposit_aum':(['aum'],['aum_deposit_month_end'],['deposit']),
 'deposit_income':(['income'],['deposit_interest_income'],['deposit']),
 'securities_aum':(['aum'],['aum_securities_month_end'],['securities_fund']),
 'deposit_both':(['aum','income'],['aum_deposit_month_end','deposit_interest_income'],['deposit']),
 'securities_compare':(['aum'],['aum_securities_month_end'],['securities_fund','securities_bond'])}
 report={}
 for name,(domains,metricCodes,products) in cases.items():
  request={'question':'唯讀圖查詢驗證', 'domains':domains,'metricCodes':metricCodes}
  catalog=db.query(CATALOG,request)
  if any(k in catalog['data']['fields'] for k in ['businessPath','conceptEvidence','aumPaths','incomePaths']):raise RuntimeError('第一輪載入了路徑。')
  first=fixture({'catalog':catalog,'request':request,'products':products})
  selections=first['choice']['selectedConcepts']
  paths=db.query(PATHS,{'selectedConcepts':selections,'metricCodes':metricCodes})
  if any(row[paths['data']['fields'].index('requestedConceptKey')] not in {s['conceptKey'] for s in selections} for row in paths['data']['values']):raise RuntimeError('查詢回傳未選概念的路徑。')
  second=fixture({'catalog':catalog,'request':request,'products':products,'paths':paths})
  selectedPaths=second['choice']['selectedPaths']
  mapping=db.query(MAPPINGS,{'selectedPaths':selectedPaths})
  write(f'lazy_live_{name}.json',{'request':request,'catalog':catalog,'paths':paths,'mapping':mapping})
  reversed_paths=[{**s,'nodeKeys':list(reversed(s['nodeKeys']))} for s in selectedPaths]
  if db.query(MAPPINGS,{'selectedPaths':reversed_paths})['data']['values']:raise RuntimeError('接受反向路徑。')
  report[name]={'catalogRows':len(catalog['data']['values']),'selectedConcepts':len(selections),'pathRows':len(paths['data']['values']),'mappingRows':len(mapping['data']['values']),'reversedPathsRejected':True}
 empty=db.query(PATHS,{'selectedConcepts':[],'metricCodes':['aum_securities_month_end']})
 if empty['data']['values']:raise RuntimeError('無選定概念時仍回傳路徑。')
 write('lazy_live_registry.json',db.query(REGISTRY))
 write('lazy_graph_validation.json',{'readOnly':True,'liveGraph':True,'liveJev':False,'syntheticDecisions':True,'catalogContainsNoPaths':True,'unselectedConceptsNotExpanded':True,'emptySelectionHasNoPaths':True,'cases':report})
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
