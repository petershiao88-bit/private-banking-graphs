import json,re
from pathlib import Path
p=Path(__file__).resolve().parent
downloads=Path('C:/Users/petershiao/Downloads')
for source,target,expected in [('私銀 AUM Income KB (5).json','PB_AUM_Income_KB.simplified.saved.json','PB_AUM_Income_KB.lazy.ready.json'),('智能查詢 - 概念圖 KB 測試版 (4).json','main.simplified.saved.json','main.lazy.ready.json')]:
 actual=json.loads((downloads/source).read_text(encoding='utf-8-sig'))
 desired=json.loads((p/expected).read_text(encoding='utf-8-sig'))
 assert not actual.get('pinData'),source
 # n8n clipboard import may assign new node IDs; compare functional definitions.
 shape=lambda w:{n['name']:{k:n.get(k) for k in ['type','typeVersion','parameters','credentials']} for n in w['nodes']}
 assert shape(actual)==shape(desired),source
 assert actual['connections']==desired['connections'],source
 (p/target).write_text(json.dumps(actual,ensure_ascii=False,indent=2),encoding='utf-8')
dom=(p/'simplified_kb_live_securities.dom.txt').read_text(encoding='utf-8')
assert 'pb_kb_lazy_routes_v4' in dom
requests=list(dict.fromkeys(re.findall(r'generic: (gen-dec-[^\s]+)',dom)))
assert len(requests)==2,requests
assert 'DSPBM.PB_FUNDPOSIT_SEC' in dom and 'DSPBM.PB_FUNDPOSIT_SEC_M' in dom
metadata={'contractVersion':'pb_kb_lazy_routes_v4','state':'saved_unpublished','kb':{'id':'tL7HTesvAzqwsqv6','nodes':12,'savedExport':'PB_AUM_Income_KB.simplified.saved.json','pinDataEmpty':True,'liveExecution':'success','durationSeconds':6.632,'nativeRequestIds':requests,'proof':'simplified_kb_live_securities.dom.txt'},'main':{'id':'nBrzHm3pNsVcOpeu','nodes':32,'savedExport':'main.simplified.saved.json','endToEndTestThisChange':False,'originalMainModified':False},'validation':'lazy_contract_validation.json','screenshot':'simplified-kb-draft.png'}
(p/'simplified_deployment.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
# The earlier copy attempt returned workflow clipboard text, not KB output.
(p/'simplified_kb_live_securities.json').write_text(json.dumps({'note':'Visible native output is saved in simplified_kb_live_securities.dom.txt','nativeRequestIds':requests},indent=2),encoding='utf-8')
print(json.dumps({'kbNodes':12,'mainNodes':32,'savedExportsMatch':True,'pinDataEmpty':True,'nativeRequests':len(requests)}))

