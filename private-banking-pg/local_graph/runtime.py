"""Local Neo4j bootstrap and authenticated Query API client.
Secrets stay in .local_runtime/ and are never printed or sent to a cloud service.
"""
import base64,json,secrets,subprocess,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.local_runtime'/'graph'
CONTAINER='pb-graphrag-neo4j'
IMAGE='neo4j:2026.09.0'
URL='http://127.0.0.1:17474/db/neo4j/query/v2'

def docker(*args,check=True):
    p=subprocess.run(['docker',*args],capture_output=True,text=True,encoding='utf-8')
    if check and p.returncode:raise RuntimeError(p.stderr.strip()[:1000])
    return p

def config():
    p=STATE/'connection.json'
    if not p.exists():raise RuntimeError('Run local_graph/bootstrap.py first.')
    return json.loads(p.read_text(encoding='utf-8'))

def query(statement,parameters=None):
    c=config();token=base64.b64encode((c['user']+':'+c['password']).encode()).decode()
    payload=json.dumps({'statement':statement,'parameters':parameters or {}},ensure_ascii=False).encode()
    request=urllib.request.Request(URL,data=payload,headers={'Authorization':'Basic '+token,'Content-Type':'application/json','Accept':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=180) as response:body=json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError('Local Neo4j HTTP '+str(e.code)+': '+e.read().decode()[:600]) from None
    if body.get('errors'):raise RuntimeError(json.dumps(body['errors'],ensure_ascii=False)[:1200])
    return body

def rows(statement,parameters=None):return query(statement,parameters)['data']['values']

def bootstrap():
    STATE.mkdir(parents=True,exist_ok=True)
    state=STATE/'connection.json'
    if not state.exists():
        state.write_text(json.dumps({'url':URL,'user':'neo4j','password':secrets.token_urlsafe(30),'container':CONTAINER},indent=2),encoding='utf-8')
    c=config()
    env=STATE/'neo4j.env'
    env.write_text('NEO4J_AUTH=neo4j/'+c['password']+'\nNEO4J_server_memory_heap_initial__size=256m\nNEO4J_server_memory_heap_max__size=1G\nNEO4J_server_memory_pagecache_size=256m\n',encoding='utf-8')
    result=docker('inspect',CONTAINER,check=False)
    if result.returncode:
        docker('image','inspect',IMAGE)
        docker('run','-d','--name',CONTAINER,'--restart','unless-stopped','--memory','2g','--publish','127.0.0.1:17474:7474','--publish','127.0.0.1:17687:7687','--env-file',str(env),'--volume','pb_graphrag_data:/data',IMAGE)
    else:
        existing=json.loads(result.stdout)[0]
        assert existing['Config']['Image']==IMAGE,'Existing project container has a different image.'
        docker('start',CONTAINER)
    for _ in range(40):
        try:
            if rows('RETURN 1')[0][0]==1:
                print(json.dumps({'container':CONTAINER,'browser':'http://127.0.0.1:17474/browser/','queryApi':URL,'ready':True,'credentialsFile':str(state)},ensure_ascii=False));return
        except (OSError,RuntimeError):time.sleep(1)
    raise RuntimeError('Neo4j did not become ready. Inspect the project container logs.')

if __name__=='__main__':bootstrap()
