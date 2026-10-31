import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8-sig'))
def normalized(value):
    if isinstance(value, str):
        return value.replace('\r\n', '\n').strip()
    if isinstance(value, list):
        return [normalized(item) for item in value]
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items()}
    return value

report = {}
for stem, count in [('PB_AUM_Income_KB', 9), ('main', 32)]:
    saved = read(stem + '.full_graph.saved.json')
    ready = read(stem + '.full_graph.ready.json')
    expected = {node['name']: node for node in ready['nodes']}
    assert len(saved['nodes']) == count
    assert {node['name'] for node in saved['nodes']} == set(expected)
    differences = []
    for node in saved['nodes']:
        for field in ['parameters', 'credentials', 'type', 'typeVersion']:
            if normalized(node.get(field)) != normalized(expected[node['name']].get(field)):
                differences.append([node['name'], field])
    assert not differences, differences
    assert saved['connections'] == ready['connections']
    assert not saved.get('pinData')
    report[stem] = {'nodes': count, 'parametersMatch': True, 'credentialsMatch': True,
                    'connectionsMatch': True, 'noPinnedTestData': True}
native = {}
for case in ['securities_fund', 'securities_all', 'deposit_both']:
    result = read('full_graph.native_' + case + '.json')[0]
    assert result['contractVersion'] == 'pb_kb_full_graph_mapping_paths_v1'
    assert len(result['conceptPathScores']) == 30
    for phase, scores, key in [('concept', 'conceptPathScores', 'pathKey'), ('mapping', 'mappingPathScores', 'mappingPathKey')]:
        decision = result['decision'][phase]
        assert decision['requestId'].startswith('gen-dec-')
        assert decision['model'].startswith('typesafe/jev-1.13')
        for score in result[scores]:
            assert score['probabilities'] == decision['answers'][score[key]]['probabilities']
            assert score['choice'] == decision['answers'][score[key]]['choice']
    native[case] = {'conceptCandidates': len(result['conceptPathScores']),
                    'selectedConceptPaths': len(result['selectedConceptPaths']),
                    'mappingCandidates': len(result['mappingPathScores']),
                    'selectedMappingPaths': len(result['selectedMappingPaths']),
                    'conceptRequestId': result['decision']['concept']['requestId'],
                    'mappingRequestId': result['decision']['mapping']['requestId'],
                    'mappingInputTokens': result['decision']['mapping']['usage']['input_tokens']}
report.update(contractVersion='pb_kb_full_graph_mapping_paths_v1', nativeJev=native,
              published=False, fullMainQueryTested=False, sqlExecuted=False)
(HERE / 'full_graph.deployment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
