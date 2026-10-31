import json
from runtime import ROOT
from query_service import execute
OUT=ROOT/'deliverables/local_graph/20261020'
def fields(body):return dict(zip(body['data']['fields'],body['data']['values'][0]))
full=execute('full_concept_graph',{})
g=fields(full)['conceptGraph'];assert len(g['nodes'])==41 and len(g['relationships'])==69
assert len(fields(full)['businessPaths'])==39
(OUT/'full-concept-query.json').write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding='utf-8')
specs=[
 {'id':'etf','direction':'forward','startKeys':['bank_etf'],'targetKeys':[],'relationshipTypes':['PB_AUM_MEASURED_BY','PB_AUM_ROLLS_UP_TO']},
 {'id':'bank_composition','direction':'reverse','startKeys':[],'targetKeys':['aum_bank_investment'],'relationshipTypes':['PB_AUM_MEASURED_BY','PB_AUM_ROLLS_UP_TO']},
 {'id':'income_total','direction':'reverse','startKeys':[],'targetKeys':['income_total'],'relationshipTypes':['PB_INCOME_MEASURED_BY','PB_INCOME_ROLLS_UP_TO']},
 {'id':'property_only','direction':'identity','startKeys':['bank_gold'],'targetKeys':[],'relationshipTypes':[]},
]
raw=execute('candidate_paths',{'specs':specs});bundles={b['id']:b['paths'] for b in fields(raw)['bundles']}
assert sorted(len(p['relationships']) for p in bundles['etf'])==[1,2,3]
assert len(bundles['bank_composition'])==10
assert len(bundles['income_total'])==20
assert len(bundles['property_only'])==1 and not bundles['property_only'][0]['relationships']
(OUT/'candidate-path-query.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
etf=min(bundles['etf'],key=lambda p:len(p['relationships']))
mapping=execute('mapping_paths',{'conceptGraph':{'nodes':etf['nodes'],'relationships':etf['relationships']}})
m=fields(mapping)
assert len(m['legacyMappings'])==1 and len(m['draftMappings'])==1
assert not m['dimensionEvidence']
assert m['sqlTables'] and m['sqlStatements']
(OUT/'mapping-query.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
# Also exercise the same mapping Cypher against every prior selected graph.
v7=ROOT/'deliverables/single_turn_qa/rag_v1/graph_retrieval_v7'
old=json.loads((v7/'live.results.json').read_text(encoding='utf-8-sig'))[0]['json']['results']
replays=[]
for i,r in enumerate(old,1):
    out=fields(execute('mapping_paths',{'conceptGraph':r['conceptGraph']}))
    replays.append({'case':i,'legacyMappings':len(out['legacyMappings']),'draftMappings':len(out['draftMappings']),'sqlTables':len(out['sqlTables']),'sqlStatements':len(out['sqlStatements']),'unrequestedRoleEvidence':len(out['dimensionEvidence'])})
    assert not out['dimensionEvidence']
report={'status':'passed','conceptNodes':41,'conceptRelationships':69,'businessPaths':39,'candidateChecks':{'etfAllThreeEndpoints':True,'bankInvestmentCompositionPaths':10,'totalIncomeCompositionPaths':20,'propertyOnlyIdentity':True},'mappingWithSqlDependencies':True,'prior12MappingReplayedSuccessfully':replays,'cloudRerankNotCalled':True}
(OUT/'query-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
