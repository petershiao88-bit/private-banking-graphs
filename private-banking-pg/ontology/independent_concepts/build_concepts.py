"""Build isolated concepts from explicit dictionaries or a business review draft."""
import argparse
import copy
import json
from pathlib import Path
from concept_model import current_plan, validate_plan

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def build(dictionary=None, relationships=None, output=None):
    source = read(dictionary or HERE / 'business_dictionary.json')
    if isinstance(source, dict) and 'nodes' in source and 'relationships' in source:
        plan = {'nodes': copy.deepcopy(source['nodes']), 'relationships': copy.deepcopy(source['relationships'])}
        if source.get('documentType') == 'business_concept_review':
            plan.update(modelVersion=source['version'], importReady=False, reviewSource=str(Path(dictionary).resolve()))
        else:
            for field in ('modelVersion', 'importReady', 'mappingRoutes'):
                if field in source:
                    plan[field] = copy.deepcopy(source[field])
    else:
        nodes = source
        relation_source = read(relationships or HERE / 'relationship_dictionary.json')
        if isinstance(relation_source, dict) and 'relationships' in relation_source:
            edges = copy.deepcopy(relation_source['relationships'])
        elif isinstance(relation_source, list):
            edges = copy.deepcopy(relation_source)
        else:
            # A legacy type dictionary uses only the exact canonical edge list.
            canonical = read(HERE / 'concept_graph.json')
            node_key = lambda n: n['properties'].get('productCode', n['properties'].get('metricCode', n['properties'].get('conceptCode')))
            if {node_key(n) for n in nodes} != {node_key(n) for n in canonical['nodes']}:
                raise RuntimeError('New concepts require an explicit relationship dictionary')
            edges = copy.deepcopy(canonical['relationships'])
            for edge in edges:
                edge['properties'] = {'definition': relation_source[edge['type']]}
        plan = {'nodes': copy.deepcopy(nodes), 'relationships': edges}
        if isinstance(relation_source, dict) and 'relationships' in relation_source:
            for field in ('modelVersion', 'importReady', 'mappingRoutes'):
                if field in relation_source:
                    plan[field] = copy.deepcopy(relation_source[field])
    plan = current_plan(plan)
    validate_plan(plan)
    target = Path(output or HERE / 'concept_graph.json')
    if plan.get('importReady') is False and target.resolve() == (HERE / 'concept_graph.json').resolve():
        raise RuntimeError('Review draft requires a separate output path')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'nodes': len(plan['nodes']), 'relationships': len(plan['relationships']), 'reviewDraft': plan.get('importReady') is False}))
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', type=Path)
    parser.add_argument('--relationships', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    build(args.dictionary, args.relationships, args.output)
