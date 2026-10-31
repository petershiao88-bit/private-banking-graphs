"""Scoped in-place migration of the user-approved independent concepts.

Checks the exact previous or approved graph, saves a live backup, replaces only
properties on existing PBConcept nodes in one transaction, and preserves all
node/relationship identities. Never changes mapping nodes or SQL rules.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from import_concepts import (Neo4j, credentials, rows, key, ensure, LABELS,
                             validate_plan, verify_concepts, verify_queries,
                             existing_fingerprint, concept_snapshot, digest)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'deliverables/concept_update/20261009'


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials', required=True, type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    from import_aura_snapshot import selected_aura
    c = credentials(args.credentials)
    base = selected_aura(c['NEO4J_URI'])
    ensure(base == 'https://4bb479b2.databases.neo4j.io', 'Unexpected target host')
    db = Neo4j(base, 'neo4j', c['NEO4J_USERNAME'], c['NEO4J_PASSWORD'])
    old = json.loads((OUT / 'local_before/concept_graph.json').read_text(encoding='utf-8-sig'))
    new = json.loads((HERE / 'concept_graph.json').read_text(encoding='utf-8'))
    approved = json.loads((ROOT / 'deliverables/concept_review/20261009/concept_graph.proposed.json').read_text(encoding='utf-8'))
    ensure(new == approved, 'Source differs from approved graph')
    validate_plan(new)
    old_by = {key(n['properties']): n for n in old['nodes']}
    new_by = {key(n['properties']): n for n in new['nodes']}
    rename = {code: code.removesuffix('_month_end') if code.startswith('aum_') else 'income_total' if code == 'income_total_customer_month' else code for code in old_by}
    ensure({rename[k] for k in old_by} == set(new_by), 'Unexpected identity migration')
    ensure([{**r, 'source': rename[r['source']], 'target': rename[r['target']]} for r in old['relationships']] == new['relationships'], 'Relationship structure changed')
    before = concept_snapshot(db)
    mapping_before = existing_fingerprint(db)
    ensure(mapping_before['nodes'] == 1167 and mapping_before['relationships'] == 3664, 'Mapping graph size differs from reviewed snapshot')
    ensure(rows(db, 'MATCH (c:PBConcept)-[r]-(n) WHERE NOT n:PBConcept RETURN count(r)') == [[0]], 'Cross-graph relationship')
    actual = {key(p): p for _, _, p in before['nodes']}
    if actual == {k: n['properties'] for k, n in old_by.items()}:
        verify_concepts(db, old)
        state = 'previous'
    else:
        verify_concepts(db, new)
        state = 'approved'
    check = dict(target='4bb479b2/neo4j', state=state, conceptNodes=len(before['nodes']), conceptRelationships=len(before['relationships']), mapping=mapping_before, metricCodeRenames=7)
    write('preflight.json', check)
    if args.check_only:
        print(json.dumps({'checkOnly': 'passed', **check}))
        return
    if state == 'previous':
        # Persist the exact live baseline once, never overwrite it on rerun.
        backup = OUT / 'live_before.json'
        ensure(not backup.exists() or json.loads(backup.read_text(encoding='utf-8')) == before, 'Different live backup exists')
        write('live_before.json', before)
        items = [{'id': ident, 'before': props, 'after': new_by[rename[key(props)]]['properties']} for ident, labels, props in before['nodes']]
        query = '''MATCH (n:PBConcept)
WITH collect(n) AS concepts
WHERE size(concepts)=size($items)
  AND all(item IN $items WHERE any(n IN concepts WHERE elementId(n)=item.id AND properties(n)=item.before))
UNWIND $items AS item
MATCH (n:PBConcept) WHERE elementId(n)=item.id
SET n = item.after
RETURN count(n) AS updated'''
        ensure(rows(db, query, {'items': items}) == [[28]], 'Atomic migration precondition failed; no successful update')
    first = verify_concepts(db, new)
    after = concept_snapshot(db)
    ensure({row[0] for row in before['nodes']} == {row[0] for row in after['nodes']}, 'Concept node identities changed')
    ensure({row[0]: sorted(row[1]) for row in before['nodes']} == {row[0]: sorted(row[1]) for row in after['nodes']}, 'Concept labels changed')
    ensure(before['relationships'] == after['relationships'], 'Concept relationship identities/content changed')
    mapping_after = existing_fingerprint(db)
    ensure(mapping_before == mapping_after, 'Mapping graph changed')
    write('live_after.json', after)
    report = dict(verifiedAt=datetime.now(timezone.utc).isoformat(), target='4bb479b2/neo4j', migrationApplied=state == 'previous', conceptGraph=first,
                  conceptNodeIdsPreserved=True, conceptRelationshipIdsAndPropertiesPreserved=True,
                  mappingBefore=mapping_before, mappingAfter=mapping_after, mappingGraphPreserved=True, crossGraphRelationships=0)
    write('validation.json', report)
    checks = verify_queries(db, db, new)
    ensure(verify_concepts(db, new) == first and existing_fingerprint(db) == mapping_before, 'Graph changed during query verification')
    report.update(queryChecks=checks, approvedStateRerunPassed=True)
    write('validation.json', report)
    # Preserve earlier validation.json as historical evidence; new schema report is separate.
    print(json.dumps({k: v for k, v in report.items() if k not in ('queryChecks', 'conceptGraph')}))


if __name__ == '__main__':
    main()
