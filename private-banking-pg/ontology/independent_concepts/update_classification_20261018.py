"""Prepare and verify the authorized property-only Aura classification update."""
import copy
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from concept_model import LABELS, business_paths, key, validate_plan

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'deliverables/concept_update/20261018_classification'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def literal(value):
    if isinstance(value, dict):
        return '{' + ','.join('`' + k.replace('`', '``') + '`:' + literal(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(literal(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False)


def unpack(path):
    value = read(path)
    return value[0] if isinstance(value, list) else value


def check(snapshot, plan):
    nodes = snapshot['nodes']
    assert len(nodes) == len(plan['nodes'])
    actual = {key(n['properties']): (sorted(n['labels']), n['properties']) for n in nodes}
    expected = {key(n['properties']): (sorted(LABELS[n['kind']]), n['properties']) for n in plan['nodes']}
    assert actual == expected, 'Concept node content differs from the canonical plan'
    codes = {n['id']: key(n['properties']) for n in nodes}
    actual_edges = {(codes[r['source']], r['type'], codes[r['target']]): r['properties'] for r in snapshot['relationships']}
    expected_edges = {(r['source'], r['type'], r['target']): r['properties'] for r in plan['relationships']}
    assert len(snapshot['relationships']) == len(expected_edges) and actual_edges == expected_edges


def prepare(path):
    assert not OUT.exists(), 'Use the existing migration folder instead of replacing its backup'
    before = unpack(path)
    baseline = read(HERE / 'concept_graph.json')
    validate_plan(baseline)
    check(before['snapshot'], baseline)
    assert before['crossEdges'] == 0
    plan = copy.deepcopy(baseline)
    products = {key(n['properties']): n for n in plan['nodes'] if n['kind'] == 'product'}
    assert len(products) == 25
    patches = {c: {'subsidiary': '證券' if c.startswith('securities_') else '銀行'} for c in products}
    for c, form in [('bank_fund', '基金'), ('bank_etf', 'ETF'), ('securities_fund', '基金')]:
        patches[c]['fundType'] = form
    for c in ['bank_overseas_stock', 'securities_foreign_stock', 'bank_bond_trust', 'bank_bond_proprietary', 'securities_bond']:
        patches[c]['marketRegion'] = '海外'
    patches['securities_taiwan_stock']['marketRegion'] = '台灣'
    for c, mode in [('bank_bond_trust', '信託'), ('bank_bond_proprietary', '自營'), ('securities_bond', '複委託'), ('securities_foreign_stock', '複委託'), ('securities_structured', '複委託')]:
        patches[c]['dealingMode'] = mode
    patches['deposit_twd']['currencyType'] = '台幣'
    patches['deposit_foreign']['currencyType'] = '外幣'
    patches['deposit_structured']['structureType'] = '結構型'
    live = {key(n['properties']): n for n in before['snapshot']['nodes']}
    changes = []
    for c, patch in sorted(patches.items()):
        props = products[c]['properties']
        assert not (set(props) & set(patch)), 'Existing classification requires explicit reconciliation'
        changes.append({'id': live[c]['id'], 'productCode': c, 'before': copy.deepcopy(props), 'patch': patch})
        props.update(patch)
    validate_plan(plan)
    assert business_paths(plan) == business_paths(baseline), 'Classification changed monetary paths'
    OUT.mkdir(parents=True)
    shutil.copy2(path, OUT / 'aura.before.export.json')
    for filename in ['concept_graph.json', 'business_dictionary.json', 'concept_model.py', '01_list_concepts.cypher', 'full_concept_graph_with_customer.cypher']:
        shutil.copy2(HERE / filename, OUT / ('before.' + filename))
    save('approved_plan.json', plan)
    save('patches.json', changes)
    save('preflight.json', {'passed': True, 'nodes': 41, 'relationships': 69, 'targetProducts': len(patches), 'addedProperties': sum(map(len, patches.values())), 'fields': dict(Counter(k for p in patches.values() for k in p)), 'businessPaths': len(business_paths(plan)), 'mapping': {k: v for k, v in before.items() if k != 'snapshot'}})
    query = '\n'.join([
        'WITH ' + literal(changes) + ' AS changes',
        'MATCH (n:PBConcept:PBConceptProduct) WITH changes,collect(n) AS products',
        "CALL apoc.util.validate(size(products)<>25 OR any(e IN changes WHERE size([n IN products WHERE n.productCode=e.productCode AND elementId(n)=e.id AND (properties(n)=e.before OR properties(n)=apoc.map.merge(e.before,e.patch))])<>1), 'Classification baseline differs; no update applied', [])",
        'WITH changes,products UNWIND changes AS e UNWIND [n IN products WHERE n.productCode=e.productCode AND elementId(n)=e.id] AS n',
        'WITH n,e,size([k IN keys(e.patch) WHERE n[k] IS NULL OR n[k]<>e.patch[k]]) AS delta',
        'FOREACH (_ IN CASE WHEN delta>0 THEN [1] ELSE [] END | SET n += e.patch)',
        "RETURN '商品分類已更新' AS status,count(*) AS targetNodes,sum(CASE WHEN delta>0 THEN 1 ELSE 0 END) AS changedNodes,sum(delta) AS changedProperties"
    ])
    (OUT / 'apply.cypher').write_text(query + '\n', encoding='utf-8')
    shutil.copy2(ROOT / 'deliverables/concept_update/20261013/verify.cypher', OUT / 'verify.cypher')
    print(json.dumps(read(OUT / 'preflight.json'), ensure_ascii=False))


def verify(path):
    after = unpack(path)
    before = unpack(OUT / 'aura.before.export.json')
    plan = read(OUT / 'approved_plan.json')
    check(after['snapshot'], plan)
    assert {k: v for k, v in before.items() if k != 'snapshot'} == {k: v for k, v in after.items() if k != 'snapshot'}, 'Mapping graph changed'
    bn = {key(n['properties']): n for n in before['snapshot']['nodes']}
    an = {key(n['properties']): n for n in after['snapshot']['nodes']}
    assert all(an[c]['id'] == n['id'] and sorted(an[c]['labels']) == sorted(n['labels']) for c, n in bn.items())
    assert sorted(before['snapshot']['relationships'], key=lambda r: r['id']) == sorted(after['snapshot']['relationships'], key=lambda r: r['id'])
    shutil.copy2(path, OUT / 'aura.after.export.json')
    save('verification.json', {'passed': True, 'nodes': len(an), 'relationships': len(after['snapshot']['relationships']), 'nodeIdsPreserved': True, 'relationshipsUnchanged': True, 'mappingUnchanged': True, 'crossEdges': after['crossEdges'], 'businessPaths': len(business_paths(plan))})
    (HERE / 'concept_graph.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'business_dictionary.json').write_text(json.dumps(plan['nodes'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(read(OUT / 'verification.json'), ensure_ascii=False))


if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify}[sys.argv[1]](sys.argv[2])
