"""Prepare a reversible, property-only Aura update and verify the exported result."""
import json
import shutil
import sys
from pathlib import Path

from concept_model import business_paths, current_plan, key, validate_plan
from update_classification_20261018 import check, literal, unpack

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'deliverables/concept_update/20261018_remove_offering_type'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(path):
    assert not (OUT / 'aura.before.export.json').exists(), 'Preserve the original live backup'
    before = unpack(path)
    baseline = read(OUT / 'local.before/ontology/independent_concepts/concept_graph.json')
    check(before['snapshot'], baseline)
    assert before['crossEdges'] == 0
    expected = current_plan(baseline)
    validate_plan(expected)
    assert business_paths(expected) == business_paths(baseline)
    products = [n for n in before['snapshot']['nodes'] if 'PBConceptProduct' in n['labels']]
    assert len(products) == 25 and all('offeringType' in n['properties'] for n in products)
    shutil.copy2(path, OUT / 'aura.before.export.json')
    save('approved_plan.json', expected)
    save('preflight.json', {'passed': True, 'products': 25, 'propertiesToRemove': 25, 'nodes': len(expected['nodes']), 'relationships': len(expected['relationships']), 'businessPaths': len(business_paths(expected)), 'mapping': {k: v for k, v in before.items() if k != 'snapshot'}})
    guard = '\n'.join([
        'WITH ' + literal(products) + ' AS expected',
        'MATCH (n:PBConcept:PBConceptProduct) WITH expected,collect(n) AS products',
        "CALL apoc.util.validate(size(products)<>size(expected) OR any(e IN expected WHERE size([n IN products WHERE elementId(n)=e.id AND (properties(n)=e.properties OR properties(n)=apoc.map.removeKeys(e.properties,['offeringType']))])<>1), 'Offering field baseline differs; no update applied', [])",
        'WITH products UNWIND products AS n',
        'WITH n,n.offeringType IS NOT NULL AS present',
        'FOREACH (_ IN CASE WHEN present THEN [1] ELSE [] END | REMOVE n.offeringType)',
        "RETURN 'offeringType 已移除' AS status,count(*) AS targetNodes,sum(CASE WHEN present THEN 1 ELSE 0 END) AS removedProperties"
    ])
    (OUT / 'apply.cypher').write_text(guard + '\n', encoding='utf-8')
    restore = [f"MATCH (n:PBConcept:PBConceptProduct {{productCode:{literal(n['properties']['productCode'])}}}) WHERE elementId(n)={literal(n['id'])} SET n.offeringType={literal(n['properties']['offeringType'])};" for n in products]
    (OUT / 'restore.cypher').write_text('// Recovery only: restore the backed-up property values.\n' + '\n'.join(restore) + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'deliverables/concept_update/20261013/verify.cypher', OUT / 'verify.cypher')
    print(json.dumps(read(OUT / 'preflight.json'), ensure_ascii=False))


def verify(path):
    before = unpack(OUT / 'aura.before.export.json')
    after = unpack(path)
    expected = read(OUT / 'approved_plan.json')
    check(after['snapshot'], expected)
    assert {k: v for k, v in before.items() if k != 'snapshot'} == {k: v for k, v in after.items() if k != 'snapshot'}, 'Mapping graph changed'
    old = {n['id']: n for n in before['snapshot']['nodes']}
    new = {n['id']: n for n in after['snapshot']['nodes']}
    assert set(old) == set(new), 'Concept identities changed'
    for node_id, node in old.items():
        properties = dict(node['properties'])
        if 'PBConceptProduct' in node['labels']:
            properties.pop('offeringType', None)
        assert properties == new[node_id]['properties'] and sorted(node['labels']) == sorted(new[node_id]['labels'])
    assert sorted(before['snapshot']['relationships'], key=lambda r: r['id']) == sorted(after['snapshot']['relationships'], key=lambda r: r['id'])
    assert not any('offeringType' in n['properties'] for n in after['snapshot']['nodes'])
    assert read(HERE / 'concept_graph.json') == expected
    assert read(HERE / 'business_dictionary.json') == expected['nodes']
    shutil.copy2(path, OUT / 'aura.after.export.json')
    report = {'passed': True, 'removedProperties': 25, 'remainingOfferingType': 0, 'nodes': len(new), 'relationships': len(after['snapshot']['relationships']), 'nodeIdsPreserved': True, 'otherPropertiesUnchanged': True, 'relationshipsUnchanged': True, 'mappingUnchanged': True, 'businessPaths': len(business_paths(expected)), 'crossEdges': after['crossEdges'], 'canonicalSourcesSynchronized': True}
    save('verification.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify}[sys.argv[1]](sys.argv[2])
