import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def normalized(value):
    if isinstance(value,str):return value.replace('\r\n','\n').strip()
    if isinstance(value,list):return [normalized(v) for v in value]
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    return value
report={}
for stem,count in [('PB_AUM_Income_KB',7),('main',32)]:
    saved=read(stem+'.single_jev.saved.json');ready=read(stem+'.single_jev.ready.json')
    expected={n['name']:n for n in ready['nodes']}
    assert len(saved['nodes'])==count
    assert {n['name'] for n in saved['nodes']}==set(expected)
    differences=[]
    for node in saved['nodes']:
        for field in ['parameters','credentials','type','typeVersion']:
            if normalized(node.get(field))!=normalized(expected[node['name']].get(field)):differences.append([node['name'],field])
    assert not differences,differences
    assert saved['connections']==ready['connections']
    assert not saved.get('pinData')
    report[stem]={'nodes':count,'parametersMatch':True,'credentialsMatch':True,'connectionsMatch':True,'noPinnedTestData':True}
result=read('single_jev.native_securities_all.json')[0]
assert result['contractVersion']=='pb_kb_full_graph_single_jev_v1'
assert len(result['conceptPathScores'])==30
assert len(result['selectedConceptPaths'])==4
assert len(result['mappingPaths'])==17
decision=result['decision']['concept']
assert decision['requestId'].startswith('gen-dec-')
assert decision['model'].startswith('typesafe/jev-1.13')
for score in result['conceptPathScores']:
    assert score['probabilities']==decision['answers'][score['pathKey']]['probabilities']
    assert score['choice']==decision['answers'][score['pathKey']]['choice']
assert 'mapping' not in result['decision'] and 'mappingPathScores' not in result
assert any('cust_id' in s['properties']['sql'].lower() for s in result['sqlEvidence']['statements'])
report.update(contractVersion=result['contractVersion'],nativeJev={'conceptCandidates':30,'selectedConceptPaths':4,'mappingPaths':17,'requestId':decision['requestId'],'usage':decision['usage']},published=False,fullMainQueryTested=False,sqlExecuted=False,graphModified=False)
(HERE/'single_jev.deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
