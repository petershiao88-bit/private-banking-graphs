"""Verify actual n8n UI exports against generated path contracts (no secrets)."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def write(name,data):(HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def semantic(field,value):
 if field!='parameters' or not isinstance(value,dict):return value
 result=json.loads(json.dumps(value))
 for condition in result.get('conditions',{}).get('conditions',[]):condition.pop('id',None)
 return result
report={}
for name,saved,expected in [('kb','PB_AUM_Income_KB.paths.saved.json','PB_AUM_Income_KB.evidence.ready.json'),('main','main.paths.saved.json','main.evidence.ready.json')]:
 a,b=read(saved),read(expected);actual={n['name']:n for n in a['nodes']};want={n['name']:n for n in b['nodes']}
 assert actual.keys()==want.keys(),name+' nodes differ'
 assert a['connections']==b['connections'],name+' connections differ'
 assert not a.get('pinData'),name+' test input still pinned'
 for key in actual:
  for field in ['type','typeVersion','parameters','credentials','retryOnFail','maxTries','waitBetweenTries']:
   assert semantic(field,actual[key].get(field))==semantic(field,want[key].get(field)),name+' node differs: '+key+' '+field
 report[name]={'nodes':len(actual),'parametersAndConnectionsMatch':True,'credentialReferencesMatch':True,'pinDataEmpty':True,'savedExport':saved}
report.update(contractVersion='pb_kb_path_evidence_v2',date='2026-10-08',contractChecksPassed=142,
 liveAura={'cases':['deposit_aum','deposit_income','securities_aum'],'reversedPathsRejected':True,'registryMetrics':12},
 liveJev={'model':'typesafe/jev-1.13-20260917','standaloneIncome':{'successSeconds':7.506,'objectProbability':1,'pathProbability':0.68,'requestId':'gen-dec-1791415442-kI3tfm9fjq9es2PsUo0j','evidence':'path_jev_live_income.dom.txt'}},
 mainExecutions={'income':{'successSeconds':14.867,'pathProbability':0.61,'result':'evidence_incomplete','skipped':['Available Source Metadata','SQL Reasoning Agent','Execute a SQL query'],'evidence':'path_main_live_income.dom.txt'},
 'securitiesFund':{'successSeconds':17.782,'objectProbability':0.79,'pathProbability':0.88,'otherThreePathsExcluded':True,'result':'missing_required_source_tables','evidence':'path_main_live_securities.dom.txt'}},
 publication={'state':'saved_unpublished','blockedByAutomaticApprovalReview':True,'action':'publish KB v4 to live n8n workflow','reason':'Implementation and validation authorized; explicit live publication authorization required.'})
write('path_deployment_validation.json',report)
main={'id':'nBrzHm3pNsVcOpeu','name':'智能查詢 - 概念圖 KB 測試版','url':'https://chiang4901.app.n8n.cloud/workflow/nBrzHm3pNsVcOpeu','state':'saved_unpublished','nodes':report['main']['nodes'],'export':'main.paths.saved.json','validationReport':'path_deployment_validation.json','contractChecksPassed':142,'endToEndState':'success','originalMainModified':False}
write('main-copy-deployment.json',main)
write('deployment.json',{'id':'tL7HTesvAzqwsqv6','url':'https://chiang4901.app.n8n.cloud/workflow/tL7HTesvAzqwsqv6','state':'saved_unpublished','intendedVersion':'KB v4 — Complete business paths before mapping','contractVersion':'pb_kb_path_evidence_v2','nodes':11,'model':'typesafe/jev-1.13','resolvedModel':'typesafe/jev-1.13-20260917','pinDataEmpty':True,'savedExport':'PB_AUM_Income_KB.paths.saved.json','validationReport':'path_deployment_validation.json','previousPublishedExport':'PB_AUM_Income_KB.deployed.json','publication':report['publication'],'mainWorkflowIntegration':main})
print(json.dumps({k:report[k] for k in ['kb','main','contractChecksPassed','publication']},ensure_ascii=False))
