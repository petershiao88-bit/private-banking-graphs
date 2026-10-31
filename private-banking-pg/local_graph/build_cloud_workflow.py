"""Prepare n8n's three graph calls for the authenticated local bridge.
Public deliverables contain placeholders. With a real URL, secret-bearing files
are written only under .local_runtime/graph and must never be committed/shared.
"""
import argparse,copy,html,json
from pathlib import Path
from runtime import ROOT,STATE
from query_service import token
P=ROOT/'deliverables/single_turn_qa/rag_v1/graph_retrieval_v8'
def build(source,url,secret):
    w=copy.deepcopy(source)
    renames={'Aura - Full Concept Graph':'Local Graph - Full Concept Graph','Aura - 候選路徑查詢':'Local Graph - 候選路徑查詢','Aura - Mapping Paths':'Local Graph - Mapping Paths'}
    for n in w['nodes']:
        op={'Aura - Full Concept Graph':'full_concept_graph','Aura - 候選路徑查詢':'candidate_paths','Aura - Mapping Paths':'mapping_paths'}.get(n['name'])
        if not op:continue
        p=n['parameters'];p['url']=url.rstrip('/')+'/query';p['authentication']='none'
        p.pop('genericAuthType',None);p.pop('nodeCredentialType',None);n.pop('credentials',None)
        p['sendHeaders']=True;p['headerParameters']={'parameters':[{'name':'Authorization','value':'Bearer '+secret}]}
        if op=='full_concept_graph':p['jsonBody']=json.dumps({'operation':op,'parameters':{}})
        elif op=='candidate_paths':p['jsonBody']='={{ {operation:"candidate_paths",parameters:$json.candidateQueryParameters} }}'
        else:p['jsonBody']='={{ {operation:"mapping_paths",parameters:Object.fromEntries([["conceptGraph",$json.conceptGraph]])} }}'
    for n in w['nodes']:
        n['name']=renames.get(n['name'],n['name'])
        if 'jsCode' in n['parameters']:
            for old,new in renames.items():n['parameters']['jsCode']=n['parameters']['jsCode'].replace("$('"+old+"')","$('"+new+"')")
    connections={}
    for name,channels in w['connections'].items():
        for outputs in channels.values():
            for links in outputs:
                for link in links:link['node']=renames.get(link['node'],link['node'])
        connections[renames.get(name,name)]=channels
    w['connections']=connections
    return w
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bridge-url');args=parser.parse_args()
    out=STATE if args.bridge_url else P;out.mkdir(parents=True,exist_ok=True)
    for filename,label in [('workflow.updated.json','single'),('workflow.graph-tests.json','tests')]:
        src=json.loads((P/filename).read_text(encoding='utf-8'))
        w=build(src,args.bridge_url or 'https://APPROVED-BRIDGE-HOST',token() if args.bridge_url else 'BRIDGE_TOKEN_REQUIRED')
        (out/('workflow.bridge-'+label+'.json')).write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
        payload=json.dumps({'nodes':w['nodes'],'connections':w['connections']},ensure_ascii=False)
        html_out=out/'import' if args.bridge_url else out
        html_out.mkdir(parents=True,exist_ok=True)
        (html_out/('workflow.bridge-'+label+'.import.html')).write_text('<!doctype html><meta charset="utf-8"><title>Local graph bridge workflow</title><textarea readonly style="width:95vw;height:80vh">'+html.escape(payload)+'</textarea>',encoding='utf-8')
    print(json.dumps({'prepared':True,'liveUrlConfigured':bool(args.bridge_url),'outputsContainCredentials':bool(args.bridge_url),'outputDirectory':str(out)},ensure_ascii=False))
