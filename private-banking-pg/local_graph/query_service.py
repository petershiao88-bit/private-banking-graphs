"""Token-authenticated local graph bridge with three fixed read-only operations.
It accepts query PARAMETERS, never arbitrary Cypher or database credentials.
"""
import argparse,hmac,json,secrets,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from runtime import ROOT,STATE,query

V7=ROOT/'deliverables/single_turn_qa/rag_v1/graph_retrieval_v7'
def operations():
    w=json.loads((V7/'workflow.saved.live.json').read_text(encoding='utf-8-sig'))
    n=next(n for n in w['nodes'] if n['name']=='Aura - Full Concept Graph')
    body=n['parameters']['jsonBody'];at=body.index('statement:')+len('statement:')
    full,_=json.JSONDecoder().raw_decode(body[at:])
    return {'full_concept_graph':full,'candidate_paths':(V7/'candidate_paths.cypher').read_text(encoding='utf-8'),'mapping_paths':(V7/'mapping_subgraph.cypher').read_text(encoding='utf-8')}
OPS=operations()
QUERY_SLOTS=threading.BoundedSemaphore(4)
class BridgeServer(ThreadingHTTPServer):
    request_queue_size=128
def token():
    STATE.mkdir(parents=True,exist_ok=True);p=STATE/'bridge-token.txt'
    if not p.exists():p.write_text(secrets.token_urlsafe(40),encoding='utf-8')
    return p.read_text(encoding='utf-8').strip()

def execute(operation,parameters):
    if operation not in OPS:raise ValueError('Unknown operation; arbitrary Cypher is not accepted.')
    if not isinstance(parameters,dict):raise ValueError('parameters must be an object')
    allowed={'full_concept_graph':set(),'candidate_paths':{'specs'},'mapping_paths':{'conceptGraph'}}[operation]
    if set(parameters)!=allowed:raise ValueError('Invalid parameter keys for this operation.')
    with QUERY_SLOTS:
        return query(OPS[operation],parameters)

class Handler(BaseHTTPRequestHandler):
    server_version='PBGraphBridge/1'
    def log_message(self,fmt,*args):pass  # Never log request bodies or authorization headers.
    def send_json(self,status,value):
        raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/health':self.send_json(200,{'service':'PBGraphBridge','status':'ready','readOnlyOperations':3})
        else:self.send_json(404,{'error':'not found'})
    def do_POST(self):
        if self.path!='/query':return self.send_json(404,{'error':'not found'})
        expected='Bearer '+self.server.bridge_token
        if not hmac.compare_digest(self.headers.get('Authorization',''),expected):return self.send_json(401,{'error':'unauthorized'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_000_000:return self.send_json(413,{'error':'request size limit'})
            request=json.loads(self.rfile.read(size))
            if set(request)-{'operation','parameters'}:raise ValueError('Only operation and parameters are accepted.')
            result=execute(request.get('operation'),request.get('parameters',{}))
            self.send_json(200,result)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:self.send_json(400,{'error':str(e)[:300]})
        except Exception as e:self.send_json(502,{'error':'Local graph query failed','detail':str(e)[:600]})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=18780);args=parser.parse_args()
    server=BridgeServer(('127.0.0.1',args.port),Handler);server.bridge_token=token()
    print(json.dumps({'service':'PBGraphBridge','bind':'127.0.0.1','port':args.port,'readOnlyOperations':list(OPS),'publicExposureEnabled':False}),flush=True)
    server.serve_forever()
