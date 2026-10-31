"""Read-only live Aura verification. Decisions here are explicitly synthetic."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_aura_snapshot import credentials, selected_aura
from import_ontology_neo4j import Neo4j
from build_full_graph_workflow import GRAPH, mapping_query, write

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', required=True, type=Path)
    args = parser.parse_args()
    credential = credentials(args.credentials)
    db = Neo4j(selected_aura(credential['NEO4J_URI']), 'neo4j', credential['NEO4J_USERNAME'], credential['NEO4J_PASSWORD'])
    graph = db.query(GRAPH)
    write('full_graph.live.json', graph)
    cases = {'deposit_aum':[('deposit','aum')], 'deposit_income':[('deposit','income')],
             'securities_fund':[('securities_fund','aum')],
             'securities_all':[(code,'aum') for code in ['securities_bond','securities_fund','securities_foreign_stock','securities_structured']],
             'deposit_both':[('deposit','aum'),('deposit','income')]}
    report = {}
    for name, selections in cases.items():
        request = {'question':'唯讀圖查詢與資料合約驗證','domains':sorted({domain for _,domain in selections}),'metricCodes':[]}
        payload = {'request':request,'graph':graph,'select':[{'productCode':code,'domain':domain} for code,domain in selections]}
        decision = json.loads(subprocess.check_output(['node',str(HERE/'full_graph_fixture.cjs')],input=json.dumps(payload).encode('utf-8')))
        mappings = db.query(mapping_query(), {'selectedPaths':decision['choice']['selectedPaths']})
        write(f'full_graph.live_{name}.json', {**payload, 'mappings':mappings})
        report[name] = {'conceptCandidates':len(decision['prepared']['conceptPathCandidates']),
                        'selectedConceptPaths':len(decision['choice']['selectedConceptPaths']),
                        'mappingRows':len(mappings['data']['values'])}
    node_index = graph['data']['fields'].index('conceptGraph')
    graph_data = graph['data']['values'][0][node_index]
    write('full_graph.query_validation.json', {'readOnly':True,'liveAura':True,'liveJev':False,'syntheticDecisions':True,
         'nodes':len(graph_data['nodes']),'relationships':len(graph_data['relationships']),'cases':report})
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
