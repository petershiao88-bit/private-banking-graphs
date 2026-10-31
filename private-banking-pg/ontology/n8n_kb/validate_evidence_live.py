"""Validate read-only Aura queries without copying credentials into output files."""
import argparse,json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_aura_snapshot import credentials,selected_aura
from import_ontology_neo4j import Neo4j
from evidence_queries import CONCEPTS,MAPPINGS,REGISTRY
HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--credentials',type=Path,required=True);a=p.parse_args()
 c=credentials(a.credentials);db=Neo4j(selected_aura(c['NEO4J_URI']),'neo4j',c['NEO4J_USERNAME'],c['NEO4J_PASSWORD'])
 cases={'deposit_aum':({'metricCodes':['aum_deposit_month_end'],'domains':['aum']},[{'productCode':'deposit','domain':'aum'}]),
        'deposit_income':({'metricCodes':['deposit_interest_income'],'domains':['income']},[{'productCode':'deposit','domain':'income'}]),
        'securities_aum':({'metricCodes':['aum_securities_month_end'],'domains':['aum']},[{'productCode':'securities_fund','domain':'aum'}])}
 report={}
 for name,(params,selections) in cases.items():
  concept=db.query(CONCEPTS,params)
  selected=json.loads(subprocess.check_output(['node',str(HERE/'fixture_paths.cjs')],input=json.dumps({'concept':concept,'request':{'question':'唯讀查詢驗證',**params},'productCode':selections[0]['productCode']}).encode('utf-8')))
  mapping=db.query(MAPPINGS,{'selectedPaths':selected})
  (HERE/f'evidence_live_{name}.json').write_text(json.dumps({'concept':concept,'mapping':mapping},ensure_ascii=False,indent=2),encoding='utf-8')
  report[name]={'conceptRows':len(concept['data']['values']),'mappingRows':len(mapping['data']['values'])}
  invalid=[{**path,'nodeKeys':list(reversed(path['nodeKeys']))} for path in selected]
  rejected=db.query(MAPPINGS,{'selectedPaths':invalid})
  if rejected['data']['values']:raise RuntimeError('映射查詢接受了錯誤方向的概念路徑。')
  report[name]['reversedPathsRejected']=True
 registry=db.query(REGISTRY);(HERE/'evidence_live_registry.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'cases':report,'registryRows':len(registry['data']['values']),'readOnly':True}))
if __name__=='__main__':main()
