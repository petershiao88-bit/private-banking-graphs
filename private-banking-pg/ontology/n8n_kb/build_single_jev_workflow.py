"""Build the seven-node draft from the current saved workflows."""
from copy import deepcopy
from build_full_graph_workflow import HERE, read, write, GRAPH, request


def build():
    workflow = read('PB_AUM_Income_KB.single_jev.saved.json')
    workflow['nodes'] = [node for node in workflow['nodes'] if node['name'] not in
                         ['Jev - Prepare Mapping Paths', 'Jev - Mapping Path Decisions API']]
    nodes = {node['name']: node for node in workflow['nodes']}
    nodes['Aura - Full Concept Graph']['parameters']['jsonBody'] = request(GRAPH, '{}')
    mapping_request = request((HERE/'lookup_full_mapping_paths.cypher').read_text(encoding='utf-8').strip(), '{selectedPaths:$json.selectedPaths||[]}')
    nodes['Aura - Mapping Paths']['parameters']['jsonBody'] = mapping_request.replace('return {statement:', 'return JSON.stringify({statement:').replace(',parameters};', ',parameters});')
    nodes['Jev - Prepare Concept Paths']['parameters']['jsCode'] = (HERE/'full_graph_common.js').read_text(encoding='utf-8')+'\n'+(HERE/'full_graph_prepare_concepts.js').read_text(encoding='utf-8')
    nodes['KB Result']['parameters']['jsCode'] = (HERE/'full_graph_common.js').read_text(encoding='utf-8')+'\n'+(HERE/'single_jev_result.js').read_text(encoding='utf-8')
    workflow['connections'] = {}
    for index, node in enumerate(workflow['nodes']):
        node['position'] = [index*240, 180]
        if index < len(workflow['nodes'])-1:
            workflow['connections'][node['name']] = {'main': [[{'node': workflow['nodes'][index+1]['name'], 'type': 'main', 'index': 0}]]}
    workflow['pinData'] = {}
    for key in ['activeVersion', 'activeVersionId', 'versionId', 'versionCounter', 'meta', 'staticData']:
        workflow.pop(key, None)
    write('PB_AUM_Income_KB.single_jev.ready.json', workflow)
    test = deepcopy(workflow)
    test['pinData'] = {'KB Input':[{'json':{'question':'請查2026年9月全體客戶的月底證券AUM，以新臺幣呈現。','domains':['aum'],'metricCodes':['aum_securities']}}]}
    write('PB_AUM_Income_KB.single_jev.test.json', test)
    main = read('main.before_single_jev.saved.json')
    main_nodes = {node['name']:node for node in main['nodes']}
    for name, key, filename in [('SQL Reasoning Agent','text','single_jev_sql_evidence_prompt.txt'),('Normalize SQL Result','jsCode','single_jev_normalize_result.js'),('保留候選機率','jsCode','single_jev_retain_probability.js')]:
        main_nodes[name]['parameters'][key] = (HERE/filename).read_text(encoding='utf-8')
    for key in ['activeVersion', 'activeVersionId', 'versionId', 'versionCounter', 'meta', 'staticData']:
        main.pop(key, None)
    write('main.single_jev.ready.json', main)
    print({'kbNodes':len(workflow['nodes']),'mainNodes':len(main['nodes']),'jevCalls':1})


if __name__ == '__main__':
    build()
