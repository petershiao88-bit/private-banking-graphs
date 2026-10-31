"""Scoped adapter for the ontology skill's cross-ontology graph plan.

Existing endpoints must exist exactly once with the expected label. No
external node properties are modified. Replaces only this trial's obsolete
direct-to-total relationships, retaining original ontology relationships.
"""
import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from import_ontology_neo4j import Neo4j

HERE = Path(__file__).resolve().parent
NS = 'pb_shared'


def validate(plan, db):
    assert plan['ontologyId'] == NS
    nodes = plan['nodes']
    keys = [n['key'] for n in nodes]
    assert len(set(keys)) == len(keys)
    refs = plan['externalReferences']
    rkeys = [r['key'] for r in refs]
    assert len(set(rkeys)) == len(rkeys) and not set(keys).intersection(rkeys)
    for n in nodes:
        assert n['key'].startswith(NS + ':product:')
        assert n['labels'] == ['ProductCategory', 'SharedProduct']
        assert n['properties']['ontologyId'] == NS
        for value in n['properties'].values():
            assert isinstance(value, (str, int, float, bool, list))
            if isinstance(value, list):
                assert all(isinstance(x, str) for x in value)
    for ref in refs:
        assert ref['label'] in ('StagingOutput', 'BusinessMetric')
    data = db.query('UNWIND $refs AS ref OPTIONAL MATCH (n {key:ref.key}) '
                    'RETURN ref.key, ref.label, count(n), collect(labels(n))', {'refs': refs})['data']['values']
    bad = [row for row in data if row[2] != 1 or row[1] not in row[3][0]]
    if bad:
        raise ValueError(f'Missing/ambiguous external references: {bad}')
    collisions = db.query('UNWIND $keys AS key MATCH (n {key:key}) '
                          'RETURN key, count(n), collect(n.ontologyId)', {'keys': keys})['data']['values']
    assert all(row[1] == 1 and row[2] == [NS] for row in collisions), collisions
    seen = set()
    for r in plan['relationships']:
        assert r['target'] in rkeys
        if r['type'].endswith('_ROLLS_UP_TO'):
            assert r['source'] in rkeys
            assert r['source'].split(':')[0] == r['target'].split(':')[0]
            assert all(refs[rkeys.index(k)]['label'] == 'BusinessMetric' for k in [r['source'], r['target']])
        else:
            assert r['source'] in keys
        assert r['type'] in ('MEASURED_BY_AUM', 'MEASURED_BY_INCOME', 'INCOME_DEFINITION_PENDING',
                             'AUM_IMPLEMENTED_BY', 'INCOME_IMPLEMENTED_BY', 'INCOME_DECLARED_BY',
                             'AUM_ROLLS_UP_TO', 'INCOME_ROLLS_UP_TO')
        assert re.fullmatch('[A-Z_]+', r['type'])
        triple = (r['source'], r['type'], r['target'])
        assert triple not in seen
        seen.add(triple)
    return {'checkOnly': True, 'nodes': len(nodes), 'relationships': len(seen), 'externalReferences': len(refs)}


def counts(db):
    queries = {
        'sharedNodes': "MATCH (p:SharedProduct {ontologyId:$ns}) RETURN count(p)",
        'sharedRelations': "MATCH ()-[r]->() WHERE r.ontologyId=$ns AND r.origin='shared_product_trial' RETURN count(r)",
        'aumMappings': "MATCH (:SharedProduct {ontologyId:$ns})-[:MEASURED_BY_AUM]->(:BusinessMetric) RETURN count(*)",
        'incomeMappings': "MATCH (:SharedProduct {ontologyId:$ns})-[:MEASURED_BY_INCOME]->(:BusinessMetric) RETURN count(*)",
        'pendingIncomeMappings': "MATCH (:SharedProduct {ontologyId:$ns})-[:INCOME_DEFINITION_PENDING]->(:BusinessMetric) RETURN count(*)",
        'reverseMetricEdges': "MATCH (:BusinessMetric)-[]->(:SharedProduct {ontologyId:$ns}) RETURN count(*)",
        'isolatedSharedProducts': "MATCH (p:SharedProduct {ontologyId:$ns}) WHERE NOT (p)-[:MEASURED_BY_AUM]->() OR NOT (p)-[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->() RETURN count(p)",
        'duplicateRelations': "MATCH (p)-[r]->(t) WHERE r.ontologyId=$ns AND r.origin='shared_product_trial' WITH p,t,type(r) AS kind,count(r) AS c WHERE c>1 RETURN count(*)",
        'aumHierarchyEdges': "MATCH ()-[r:AUM_ROLLS_UP_TO]->() WHERE r.ontologyId=$ns RETURN count(r)",
        'incomeHierarchyEdges': "MATCH ()-[r:INCOME_ROLLS_UP_TO]->() WHERE r.ontologyId=$ns RETURN count(r)",
        'directToTotalEdges': "MATCH (:SharedProduct {ontologyId:$ns})-[r:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(m) WHERE m.key IN ['aum:metric:aum_total_month_end','income:metric:income_total_customer_month'] RETURN count(r)",
        'missingAumRootPath': "MATCH (p:SharedProduct {ontologyId:$ns}) WHERE NOT (p)-[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO*1..5]->(:BusinessMetric {key:'aum:metric:aum_total_month_end'}) RETURN count(p)",
        'missingIncomeRootPath': "MATCH (p:SharedProduct {ontologyId:$ns}) WHERE NOT (p)-[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->(:BusinessMetric {key:'income:metric:income_total_customer_month'}) RETURN count(p)",
    }
    return {key: db.query(q, {'ns': NS})['data']['values'][0][0] for key, q in queries.items()}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    plan = json.loads((HERE / 'Shared_product_graph_plan.json').read_text(encoding='utf-8'))
    db = Neo4j('http://127.0.0.1:7474', 'neo4j', 'neo4j', os.environ['NEO4J_PASSWORD'])
    report = validate(plan, db)
    if args.check_only:
        print(json.dumps(report))
        return
    before = counts(db)
    # Presentation labels retain BusinessMetric so existing queries work.
    db.query("MATCH (m:BusinessMetric {ontologyId:'aum'}) SET m:AUMMetric")
    db.query("MATCH (m:BusinessMetric {ontologyId:'income'}) SET m:IncomeMetric")
    db.rows('UNWIND $rows AS row MERGE (p:ProductCategory:SharedProduct {key:row.key}) '
            'SET p += row.properties', plan['nodes'])
    groups = defaultdict(list)
    for r in plan['relationships']:
        groups[r['type']].append(r)
    for kind, rows in groups.items():
        db.rows(f'UNWIND $rows AS row MATCH (p {{key:row.source}}) '
                f'MATCH (target {{key:row.target}}) MERGE (p)-[r:{kind}]->(target) '
                'SET r += row.properties', rows)
    # The previous trial's direct-to-total edges were inspected before this
    # migration. Their ownership is checked again at deletion time.
    db.query("MATCH (p:SharedProduct {ontologyId:$ns})-[r:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(m:BusinessMetric) "
             "WHERE p.key IN $keys AND r.ontologyId=$ns AND r.origin='shared_product_trial' "
             "AND m.key IN ['aum:metric:aum_total_month_end','income:metric:income_total_customer_month'] DELETE r",
             {'ns': NS, 'keys': [n['key'] for n in plan['nodes']]})
    report = counts(db)
    report['idempotentRerun'] = before == report and before['sharedNodes'] == len(plan['nodes'])
    assert report['sharedNodes'] == len(plan['nodes'])
    assert report['sharedRelations'] == len(plan['relationships'])
    assert report['aumMappings'] == 15 and report['incomeMappings'] == 14 and report['pendingIncomeMappings'] == 1
    assert report['reverseMetricEdges'] == report['isolatedSharedProducts'] == report['duplicateRelations'] == 0
    assert report['aumHierarchyEdges'] == 5 and report['incomeHierarchyEdges'] == 6
    assert report['directToTotalEdges'] == report['missingAumRootPath'] == report['missingIncomeRootPath'] == 0
    report['representativeBusinessPaths'] = db.query(
        "MATCH a=(p:SharedProduct {ontologyId:$ns})-[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO*1..5]->(:BusinessMetric {key:'aum:metric:aum_total_month_end'}) "
        "MATCH i=(p)-[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->(:BusinessMetric {key:'income:metric:income_total_customer_month'}) "
        "RETURN p.code,[n IN nodes(a) | n.name],[n IN nodes(i) | n.name]", {'ns': NS})['data']['values']
    paths = db.query("MATCH (p:SharedProduct {ontologyId:$ns})-[r:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(s:StagingOutput) "
                     "OPTIONAL MATCH (s)-[:DEPENDS_ON|REFRESHED_FROM*0..8]->(derived:StagingOutput)-[:DESCRIBED_BY]->(t:Term) "
                     "RETURN p.code,type(r),s.key,count(DISTINCT t)", {'ns': NS})['data']['values']
    report['stageEvidencePaths'] = paths
    assert all(row[3] > 0 for row in paths), 'Missing ontology term evidence'
    (HERE / 'Shared_product_graph_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('stageEvidencePaths','representativeBusinessPaths')}))


if __name__ == '__main__':
    run()
