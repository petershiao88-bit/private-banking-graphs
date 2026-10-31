"""Apply the approved concept relation changes, scoped and atomic."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from import_concepts import (Neo4j, credentials, ensure, rows, validate_plan,
                             verify_concepts, verify_queries, concept_snapshot, existing_fingerprint)
from import_aura_snapshot import selected_aura

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'deliverables/concept_relations/20261009'


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    c = credentials(args.credentials)
    host = selected_aura(c['NEO4J_URI'])
    ensure(host == 'https://4bb479b2.databases.neo4j.io', 'Unexpected host')
    db = Neo4j(host, 'neo4j', c['NEO4J_USERNAME'], c['NEO4J_PASSWORD'])
    old = json.loads((OUT / 'local_before/concept_graph.json').read_text(encoding='utf-8-sig'))
    new = json.loads((HERE / 'concept_graph.json').read_text(encoding='utf-8'))
    ensure(new == json.loads((OUT / 'concept_graph.proposed.json').read_text(encoding='utf-8')), 'Plan differs from approved migration')
    ensure(old['nodes'] == new['nodes'], 'Node content changes are not in scope')
    validate_plan(new)
    before = concept_snapshot(db)
    mapping_before = existing_fingerprint(db)
    try:
        verify_concepts(db, old)
        state = 'previous'
    except RuntimeError:
        verify_concepts(db, new)
        state = 'approved'
    write('preflight.json', {'state': state, 'conceptNodes': len(before['nodes']), 'conceptRelationships': len(before['relationships']), 'mapping': mapping_before})
    if args.check_only:
        print(json.dumps({'checkOnly':'passed','state':state,'nodes':len(before['nodes']),'relationships':len(before['relationships']),'mapping':mapping_before}))
        return
    if state == 'previous':
        ensure(not (OUT / 'live_before.json').exists() or json.loads((OUT / 'live_before.json').read_text(encoding='utf-8')) == before, 'Conflicting baseline')
        write('live_before.json', before)
        definitions = json.loads((HERE / 'relationship_dictionary.json').read_text(encoding='utf-8'))
        normal, renamed, pending = [], [], []
        for ident, a, typ, b, props in before['relationships']:
            item = {'id':ident,'source':a,'target':b,'type':typ,'before':props}
            if typ == 'PB_INCOME_PENDING':
                pending.append(item)
            elif typ == 'PB_MEASURES_CUSTOMER':
                item['after'] = {'definition': definitions['PB_HAS_MEASUREMENT_SUBJECT']}
                renamed.append(item)
            else:
                item['after'] = {'definition': definitions[typ]}
                normal.append(item)
        ensure((len(normal),len(renamed),len(pending)) == (39,12,1), 'Unexpected relation migration scope')
        params = {'nodes':[{'id':i,'labels':ls,'props':p} for i,ls,p in before['nodes']],
                  'relations':normal+renamed+pending,'normal':normal,'renamed':renamed,'pending':pending}
        query = '''CALL { MATCH (n:PBConcept) RETURN collect(n) AS ns }
CALL { MATCH (a:PBConcept)-[r]->(b:PBConcept)
       RETURN collect({edge:r,source:elementId(a),target:elementId(b)}) AS rs }
WITH ns,rs
WHERE size(ns)=size($nodes) AND size(rs)=size($relations)
 AND all(item IN $nodes WHERE any(n IN ns WHERE elementId(n)=item.id AND properties(n)=item.props AND labels(n)=item.labels))
 AND all(item IN $relations WHERE any(v IN rs WHERE elementId(v.edge)=item.id AND type(v.edge)=item.type AND properties(v.edge)=item.before AND v.source=item.source AND v.target=item.target))
CALL { UNWIND $normal AS item MATCH (:PBConcept)-[r]->(:PBConcept)
       WHERE elementId(r)=item.id SET r = item.after RETURN count(r) AS described }
CALL { UNWIND $renamed AS item MATCH (m:PBConcept:PBConceptMetric)-[r:PB_MEASURES_CUSTOMER]->(c:PBConcept:PBConceptCustomer)
       WHERE elementId(r)=item.id CREATE (m)-[replacement:PB_HAS_MEASUREMENT_SUBJECT]->(c)
       SET replacement = item.after DELETE r RETURN count(replacement) AS renamed }
CALL { UNWIND $pending AS item MATCH (:PBConcept:PBConceptProduct)-[r:PB_INCOME_PENDING]->(:PBConcept:PBConceptMetric)
       WHERE elementId(r)=item.id DELETE r RETURN count(*) AS removed }
RETURN described,renamed,removed'''
        ensure(rows(db, query, params) == [[39,12,1]], 'Atomic migration precondition failed')
    after = concept_snapshot(db)
    verified = verify_concepts(db, new)
    ensure(before['nodes'] == after['nodes'], 'Concept node identities/content changed')
    mapping_after = existing_fingerprint(db)
    ensure(mapping_before == mapping_after, 'Mapping graph changed')
    if state == 'previous':
        retained = {r[0]:r for r in after['relationships']}
        for r in before['relationships']:
            if r[2] not in ('PB_INCOME_PENDING','PB_MEASURES_CUSTOMER'):
                ensure(r[0] in retained and retained[r[0]][:4] == r[:4], 'Unchanged relation identity or endpoint changed')
        ensure(sum(r[0] in retained for r in before['relationships']) == 39, 'Unexpected old relationship retention')
    write('live_after.json', after)
    report = {'verifiedAt':datetime.now(timezone.utc).isoformat(),'target':'4bb479b2/neo4j','migrationApplied':state=='previous',
              'conceptGraph':verified,'conceptNodesPreserved':True,'normalRelationIdsPreserved':39,
              'customerRelationsRenamed':12,'pendingRelationsRemoved':1,'relationDefinitions':51,
              'mappingBefore':mapping_before,'mappingAfter':mapping_after,'mappingGraphPreserved':True,'crossGraphRelationships':0}
    write('validation.json', report)
    checks = verify_queries(db, db, new)
    ensure(verified == verify_concepts(db, new) and mapping_before == existing_fingerprint(db), 'Graph changed during verification')
    report.update(queryChecks=checks,approvedStateRerunPassed=True)
    write('validation.json', report)
    if state == 'previous':
        write('validation.applied.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('queryChecks','conceptGraph')}))


if __name__ == '__main__':
    main()
