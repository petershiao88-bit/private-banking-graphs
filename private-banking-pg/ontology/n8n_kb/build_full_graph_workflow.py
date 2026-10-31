"""Build the approved nine-node concept-path then mapping-path draft."""
import json
import uuid
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPES = ['PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY', 'PB_INCOME_PENDING',
         'PB_AUM_ROLLS_UP_TO', 'PB_INCOME_ROLLS_UP_TO']
RELS = '|'.join(TYPES)
# Use the current reviewed graph query; keep the former two-Jev builder archived.
GRAPH = (HERE / 'lookup_full_concept_graph.cypher').read_text(encoding='utf-8').strip()

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))

def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def mapping_query():
    original = (HERE / 'lookup_mappings.cypher').read_text(encoding='utf-8')
    # PBConcept is isolated. Only the selected business product codes are bridged here.
    query = """UNWIND $selectedPaths AS selection
UNWIND selection.productCodes AS productCode
MATCH (p:SharedProduct {ontologyId:'pb_shared',code:productCode})
WITH DISTINCT p,selection,null AS measure
""" + original[original.index('CALL (p,selection,measure) {'):]
    query = query.replace("  AND (mapping.metricKey IS NULL OR mapping.metricKey=endNode(measure).key)\n  AND (measure.scope IS NULL OR mapping.scope IS NULL OR measure.scope=mapping.scope)", '')
    start = query.index(' CASE WHEN size([')
    end = query.index(' AS bindingStatus', start)
    query = query[:start] + " 'candidate_bridge'" + query[end:]
    query = query.replace('selection.queryMetricKey AS queryMetricKey,\n selection.queryMetricCode AS queryMetricCode,', '')
    return query

def request(query, parameters):
    query = query.replace('}}', '} }')
    return '={{ (() => { const parameters=' + parameters + '; return {statement:' + json.dumps(query, ensure_ascii=False) + ',parameters}; })() }}'

def build():
    workflow = read('PB_AUM_Income_KB.before_full_graph.saved.json')
    old = {node['name']: node for node in workflow['nodes']}
    common = (HERE / 'full_graph_common.js').read_text(encoding='utf-8')
    def clone(template, name):
        node = deepcopy(old[template])
        node.update(id=str(uuid.uuid5(uuid.NAMESPACE_URL, 'pb-full-graph:' + name)), name=name)
        for key in ['notes', 'notesInFlow', 'disabled', 'onError']:
            node.pop(key, None)
        return node
    def code(name, filename):
        return dict(id=str(uuid.uuid5(uuid.NAMESPACE_URL, 'pb-full-graph:' + name)), name=name,
                    type='n8n-nodes-base.code', typeVersion=2, parameters={'jsCode':common+'\n'+(HERE / filename).read_text(encoding='utf-8')})
    graph = clone('Aura - Concept Catalog', 'Aura - Full Concept Graph')
    graph['parameters']['jsonBody'] = request(GRAPH, '{}')
    mappings = clone('Aura - Mappings', 'Aura - Mapping Paths')
    mappings['parameters']['jsonBody'] = request(mapping_query(), '{selectedPaths:$json.selectedPaths}')
    concept_api = clone('Jev - Concept Decisions API', 'Jev - Concept Path Decisions API')
    mapping_api = clone('Jev - Path Decisions API', 'Jev - Mapping Path Decisions API')
    # An empty candidate collection has no typed questions. Keep the native API response;
    # final formatting naturally produces zero mapping selections without inventing a decision.
    mapping_api['parameters']['options']['response']['response']['neverError'] = True
    workflow['nodes'] = [deepcopy(old['KB Input']), graph,
        code('Jev - Prepare Concept Paths', 'full_graph_prepare_concepts.js'), concept_api,
        code('Concept Path Result', 'full_graph_concept_result.js'), mappings,
        code('Jev - Prepare Mapping Paths', 'full_graph_prepare_mappings.js'), mapping_api,
        code('KB Result', 'full_graph_result.js')]
    workflow['connections'] = {}
    for index, node in enumerate(workflow['nodes']):
        node['position'] = [index * 240, 180]
        if index < 8:
            workflow['connections'][node['name']] = {'main': [[{'node': workflow['nodes'][index+1]['name'], 'type': 'main', 'index': 0}]]}
    workflow['pinData'] = {}
    for key in ['activeVersion', 'activeVersionId', 'versionId', 'versionCounter', 'meta', 'staticData']:
        workflow.pop(key, None)
    write('PB_AUM_Income_KB.full_graph.ready.json', workflow)
    test = deepcopy(workflow)
    test['pinData'] = {'KB Input': [{'json': {'question':'請查2026年9月全體客戶的證券基金月底AUM，以新臺幣呈現。','domains':['aum'],'metricCodes':['aum_securities_month_end']}}]}
    write('PB_AUM_Income_KB.full_graph.test.json', test)
    (HERE / 'lookup_full_concept_graph.cypher').write_text(GRAPH+'\n', encoding='utf-8')
    (HERE / 'lookup_full_mapping_paths.cypher').write_text(mapping_query(), encoding='utf-8')
    main = read('main.simplified.saved.json')
    main_nodes = {node['name']: node for node in main['nodes']}
    main_nodes['SQL Reasoning Agent']['parameters']['text'] = (HERE / 'full_graph_sql_evidence_prompt.txt').read_text(encoding='utf-8')
    main_nodes['Normalize SQL Result']['parameters']['jsCode'] = (HERE / 'full_graph_normalize_result.js').read_text(encoding='utf-8')
    main_nodes['保留候選機率']['parameters']['jsCode'] = (HERE / 'full_graph_retain_probability.js').read_text(encoding='utf-8')
    main['pinData'] = {}
    for key in ['activeVersion', 'activeVersionId', 'versionId', 'versionCounter', 'meta', 'staticData']:
        main.pop(key, None)
    write('main.full_graph.ready.json', main)
    print(json.dumps({'nodes':len(workflow['nodes']),'model':'typesafe/jev-1.13','draft':True}))

if __name__ == '__main__':
    build()
