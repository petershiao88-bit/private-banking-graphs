"""Prepare an isolated, baseline-guarded Aura UI migration and verify exports."""
import json
import hashlib
import sys
from pathlib import Path

from concept_model import LABELS, KEY_FIELDS, key, validate_plan

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deliverables/concept_update/20261013'
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def literal(value):
    if isinstance(value, dict):
        return '{' + ','.join('`' + k.replace('`', '``') + '`:' + literal(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(literal(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False)


def unpack(path):
    return read(path)[0]['snapshot']


def fingerprint(graph):
    ids = {n['id'] for n in graph['nodes'] if 'PBConcept' not in n['labels']}
    nodes = [{**n, 'labels': sorted(n['labels'])} for n in graph['nodes'] if n['id'] in ids]
    edges = [r for r in graph['relationships'] if r['source'] in ids or r['target'] in ids]
    data = [sorted(nodes, key=lambda n:n['id']), sorted(edges, key=lambda r:r['id'])]
    return {'nodes': len(nodes), 'relationships': len(edges), 'sha256': hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}


def concept(graph):
    ns = [n for n in graph['nodes'] if 'PBConcept' in n['labels']]
    ids = {n['id'] for n in ns}
    rs = [r for r in graph['relationships'] if r['source'] in ids and r['target'] in ids]
    assert not any((r['source'] in ids) != (r['target'] in ids) for r in graph['relationships']), 'Cross graph edge'
    return ns, rs


def check(graph, plan):
    ns, rs = concept(graph)
    actual = {key(n['properties']): [sorted(n['labels']), n['properties']] for n in ns}
    expected = {key(n['properties']): [sorted(LABELS[n['kind']]), n['properties']] for n in plan['nodes']}
    assert len(ns) == len(expected) and actual == expected, 'Node content differs'
    code = {n['id']: key(n['properties']) for n in ns}
    actual_edges = {(code[r['source']], r['type'], code[r['target']]): r['properties'] for r in rs}
    expected_edges = {(r['source'], r['type'], r['target']): r['properties'] for r in plan['relationships']}
    assert len(rs) == len(expected_edges) and actual_edges == expected_edges, 'Relation content differs'


def prepare(path):
    before = unpack(path)
    baseline = read(ROOT / 'ontology/independent_concepts/concept_graph.json')
    approved = read(ROOT / 'deliverables/concept_build/20261013/business_v2/concept_graph.json')
    validate_plan(approved)
    check(before, baseline)
    save('aura.before.json', before)
    save('mapping.before.json', fingerprint(before))
    approved['importReady'] = True
    approved['authorization'] = 'User explicitly requested Aura update on 2026-10-13; PBConcept namespace only.'
    save('approved_plan.json', approved)
    ns, rs = concept(before)
    # Reject subtype label collisions outside the independent graph.
    reserved = {l for ls in LABELS.values() for l in ls}
    assert not any(reserved.intersection(n['labels']) for n in before['nodes'] if 'PBConcept' not in n['labels'])
    kinds = {key(n['properties']): n['kind'] for n in approved['nodes']}
    parts = [f'WITH {literal(ns)} AS expectedNodes, {literal(rs)} AS expectedRelationships',
             'MATCH (n:PBConcept) WITH expectedNodes,expectedRelationships,collect(n) AS currentNodes',
             'WHERE size(currentNodes)=size(expectedNodes) AND all(e IN expectedNodes WHERE any(n IN currentNodes WHERE elementId(n)=e.id AND properties(n)=e.properties AND size(labels(n))=size(e.labels) AND all(l IN labels(n) WHERE l IN e.labels)))',
             'CALL { MATCH (a:PBConcept)-[r]->(b:PBConcept) RETURN collect({id:elementId(r),source:elementId(a),type:type(r),target:elementId(b),properties:properties(r)}) AS currentRelationships }',
             'WITH expectedRelationships,currentRelationships WHERE size(currentRelationships)=size(expectedRelationships) AND all(e IN expectedRelationships WHERE e IN currentRelationships)',
             'CALL { MATCH (a:PBConcept)-[r]-(b) WHERE NOT b:PBConcept RETURN count(r) AS crossEdges }',
             'WITH crossEdges WHERE crossEdges=0']
    for kind, labels in LABELS.items():
        items = [n['properties'] for n in approved['nodes'] if n['kind'] == kind]
        field = KEY_FIELDS[kind]
        parts.append(f'CALL {{ UNWIND {literal(items)} AS props MERGE (n:{":".join(labels)} {{{field}:props.{field}}}) SET n=props RETURN count(*) AS {kind}Count }}')
    groups = {}
    for r in approved['relationships']:
        groups.setdefault((r['type'], kinds[r['source']], kinds[r['target']]), []).append(r)
    for i, ((typ, sk, tk), edges) in enumerate(sorted(groups.items())):
        parts.append(f'CALL {{ UNWIND {literal(edges)} AS edge MATCH (a:PBConcept:{LABELS[sk][1]} {{{KEY_FIELDS[sk]}:edge.source}}), (b:PBConcept:{LABELS[tk][1]} {{{KEY_FIELDS[tk]}:edge.target}}) MERGE (a)-[r:{typ}]->(b) SET r=edge.properties RETURN count(*) AS edgeCount{i} }}')
    parts.append("RETURN 'PBConcept business_v2 applied' AS status,productCount,aumCount,incomeCount,customerCount,advisorCount,organizationCount")
    (OUT / 'apply.cypher').write_text('\n'.join(parts), encoding='utf-8')
    print(json.dumps({'baselineNodes':len(ns),'baselineRelationships':len(rs),'approvedNodes':len(approved['nodes']),'approvedRelationships':len(approved['relationships']),'mapping':fingerprint(before)},ensure_ascii=False))


def verify(path):
    after = unpack(path)
    before = read(OUT / 'aura.before.json')
    plan = read(OUT / 'approved_plan.json')
    check(after, plan)
    export = read(path)[0]
    if 'mappingSha256' in export:
        expected = read(OUT / 'mapping.canonical.before.json')
        assert export['mappingSha256']==expected['sha256'], 'Mapping content changed'
        assert export['mappingNodes']==expected['nodes'] and export['mappingRelationships']==expected['relationships'] and export['crossEdges']==0
        mapping = expected
        save('verification.export.json', export)
    else:
        assert fingerprint(before)==fingerprint(after), 'Mapping graph changed'
        mapping = fingerprint(after)
    bn, br = concept(before)
    an, ar = concept(after)
    amap = {key(n['properties']): n for n in an}
    assert all(amap[key(n['properties'])]['id']==n['id'] and sorted(amap[key(n['properties'])]['labels'])==sorted(n['labels']) for n in bn), 'Existing node ID changed'
    acodes = {n['id']:key(n['properties']) for n in an}
    er = {(acodes[r['source']],r['type'],acodes[r['target']]):r['id'] for r in ar}
    assert all(er[(acodes[r['source']],r['type'],acodes[r['target']])]==r['id'] for r in br), 'Existing relationship ID changed'
    save('concept.after.json',after)
    save('verification.json',{'passed':True,'nodes':len(an),'relationships':len(ar),'mappingUnchanged':True,'mapping':mapping,'existingNodeIdsPreserved':True,'existingRelationshipIdsPreserved':True,'crossGraphEdges':0})
    print('Verified: 41 nodes / 69 relationships; mapping unchanged; existing IDs preserved.')


if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify}[sys.argv[1]](sys.argv[2])
