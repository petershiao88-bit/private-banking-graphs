"""Read-only checks of the fixed KB queries against the intended Aura database."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from import_ontology_neo4j import Neo4j
from import_aura_snapshot import credentials, selected_aura

creds = credentials(Path.home()/'Downloads'/'Neo4j-4bb479b2-Created-2026-10-06.txt')
base = selected_aura(creds['NEO4J_URI'])
assert base == 'https://4bb479b2.databases.neo4j.io'
db = Neo4j(base,'neo4j',creds['NEO4J_USERNAME'],creds['NEO4J_PASSWORD'])
workflow = json.loads((HERE/'PB_AUM_Income_KB.json').read_text(encoding='utf-8'))
q1 = (HERE/'lookup_concepts.cypher').read_text(encoding='utf-8')
q2 = (HERE/'lookup_mappings.cypher').read_text(encoding='utf-8')

def records(query, parameters=None):
    data = db.query(query,parameters)['data']
    return [dict(zip(data['fields'],r)) for r in data['values']]

catalog = records(q1,{'metricCodes':['aum_total_month_end','income_total_customer_month'],'domains':['aum','income']})
assert len(catalog)==15
assert all(set(p)=={'matchedScopes','productCode','productName','definition','status','aumStatus','incomeStatus','aumMetrics','incomeMetrics'} for p in catalog)
scope_cases = {
 'deposit':(['aum_deposit_month_end'],['aum'],{'deposit'}),
 'securities':(['aum_securities_month_end'],['aum'],{'securities_bond','securities_foreign_stock','securities_fund','securities_structured'}),
 'insurance':(['aum_insurance_month_end'],['aum'],{'bank_insurance'}),
 'multiple_metrics':(['aum_deposit_month_end','aum_insurance_month_end'],['aum'],{'deposit','bank_insurance'}),
 'unknown':(['not_a_metric'],['aum'],set()),
 'wrong_domain':(['aum_securities_month_end'],['income'],set()),
 'injection':(["aum_total_month_end' MATCH(n) RETURN n"],['aum'],set()),
 'income_bank':(['bank_fee_income'],['income'],{p['productCode'] for p in catalog if p['productCode'].startswith('bank_')}),
}
scope_outputs = {}
for name,(codes,domains,expected) in scope_cases.items():
 result=records(q1,{'metricCodes':codes,'domains':domains})
 assert {p['productCode'] for p in result}==expected, name
 assert all(s['metricCode'] in codes and s['domain'] in domains for p in result for s in p['matchedScopes'])
 scope_outputs[name]=result
cases = {
    'empty':[],
    'single':[{'productCode':'bank_insurance','domain':'income'}],
    'multiple':[{'productCode':'bank_fund','domain':'aum'},{'productCode':'bank_etf','domain':'income'}],
    'pending':[{'productCode':'bank_collective_account','domain':'income'}],
    'duplicate':[{'productCode':'bank_insurance','domain':'income'}]*2,
    'both_domains':[{'productCode':'bank_insurance','domain':d} for d in ['aum','income']],
}
outputs = {name:records(q2,{'selections':value}) for name,value in cases.items()}
assert outputs['empty']==[]
assert len(outputs['single'])==1 and len(outputs['single'][0]['mappings'])==3
assert {(p['productCode'],p['domain']) for p in outputs['multiple']}=={('bank_fund','aum'),('bank_etf','income')}
assert outputs['pending'][0]['status']=='pending_confirmation'
assert len(outputs['duplicate'])==1
assert len(outputs['both_domains'])==2
assert all('calculationAuthorized' not in p and 'mappingActive' not in p for values in outputs.values() for p in values)
report = {'verifiedAt':datetime.now(timezone.utc).isoformat(),'endpoint':db.url,'catalogProducts':len(catalog),
          'scopeCases':{name:len(rows) for name,rows in scope_outputs.items()},
          'cases':{name:{'selected':len(cases[name]),'returned':len(result)} for name,result in outputs.items()}}
(HERE/'query_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'test_fixtures.json').write_text(json.dumps({'catalog':catalog,'outputs':outputs,'scopeOutputs':scope_outputs},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
