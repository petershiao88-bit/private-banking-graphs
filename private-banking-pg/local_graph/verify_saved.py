"""Verify native n8n export privately, then publish a credential-redacted copy."""
import copy,json,sys
from pathlib import Path
from runtime import ROOT,STATE
P=ROOT/'deliverables/single_turn_qa/rag_v1/graph_retrieval_v8'
saved=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
expected=json.loads((STATE/'workflow.bridge-single.json').read_text(encoding='utf-8'))
by=lambda w:{n['name']:n for n in w['nodes']}
actual_by,wanted=by(saved),by(expected)
assert set(actual_by)==set(wanted)
for name,n in wanted.items():
    for field in ['parameters','type','typeVersion','credentials']:
        actual,want=copy.deepcopy(actual_by[name].get(field)),copy.deepcopy(n.get(field))
        if field=='parameters' and name.startswith('Local Graph - '):
            actual.setdefault('authentication','none');want.setdefault('authentication','none')
        assert actual==want,(name,field)
assert saved['connections']==expected['connections']
assert not saved['active'] and len(saved['nodes'])==14
(STATE/'workflow.saved.live.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
public=copy.deepcopy(saved)
for n in public['nodes']:
    if n['name'].startswith('Local Graph - '):
        n['parameters']['headerParameters']['parameters']=[{'name':'Authorization','value':'Bearer BRIDGE_TOKEN_REQUIRED'}]
        n['parameters']['url']='https://APPROVED-BRIDGE-HOST/query'
(P/'workflow.saved.sanitized.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
out={'workflowId':saved['id'],'name':saved['name'],'nodes':14,'allNodeParametersMatch':True,'normalization':'n8n omits default authentication=none','allConnectionsMatch':True,'active':False,'singleQuestionRestored':True,'graphOperations':3,'bridgeSecretStoredOnlyPrivately':True,'publicExportRedacted':True}
(P/'saved-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
