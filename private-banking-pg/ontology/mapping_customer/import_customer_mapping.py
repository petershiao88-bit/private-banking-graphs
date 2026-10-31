"""Add only mapping Customer and owned edges to the already selected Aura."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from import_aura_snapshot import credentials, selected_aura
from import_ontology_neo4j import Neo4j

KEY = 'pb_shared:customer:customer'
ORIGIN = 'mapping_customer_v1'
PARAMS = dict(key=KEY, origin=ORIGIN, ns='pb_shared')


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def rows(db, query, params=None):
    return db.query(query, params)['data']['values']


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def protected_snapshot(db):
    nodes = rows(db, 'MATCH (n) WHERE coalesce(n.key,\'\') <> $key RETURN elementId(n),labels(n),properties(n) ORDER BY elementId(n)', PARAMS)
    for node in nodes:
        node[1].sort()
    edges = rows(db, 'MATCH (a)-[r]->(b) WHERE coalesce(r.origin,\'\') <> $origin OR coalesce(r.ontologyId,\'\') <> $ns RETURN elementId(r),elementId(a),type(r),elementId(b),properties(r) ORDER BY elementId(r)', PARAMS)
    return dict(nodes=len(nodes), relationships=len(edges), sha256=digest([nodes, edges]))


def customer_state(db):
    return dict(nodes=rows(db, 'MATCH (c {key:$key}) RETURN elementId(c),labels(c),properties(c)', PARAMS),
                edges=rows(db, 'MATCH (a)-[r]->(b) WHERE r.origin=$origin AND r.ontologyId=$ns RETURN elementId(r),a.key,type(r),b.key,properties(r) ORDER BY elementId(r)', PARAMS))


def preflight(db, plan):
    ensure(plan['ontologyId'] == 'pb_shared' and plan['rootKey'] == KEY and plan['version'] == ORIGIN, 'Invalid extension namespace')
    ensure(len(plan['nodes']) == 1 and plan['nodes'][0]['key'] == KEY, 'Only the mapping Customer may be added')
    node = plan['nodes'][0]
    ensure(node['labels'] == ['BusinessDimension', 'MappingCustomer'], 'Customer label mismatch')
    ensure(node['properties']['key'] == KEY and node['properties']['ontologyId'] == 'pb_shared', 'Invalid customer properties')
    ensure(all(isinstance(v, (str, list)) and (not isinstance(v, list) or all(isinstance(x, str) for x in v)) for v in node['properties'].values()), 'Unsupported property type')
    refs = plan['externalReferences']
    ensure(len(refs) == 14 and len({r['key'] for r in refs}) == 14, 'Unexpected external references')
    matches = rows(db, 'UNWIND $refs AS ref OPTIONAL MATCH (n {key:ref.key}) RETURN ref.key,ref.label,count(n),collect(labels(n))', {'refs': refs})
    ensure(all(n == 1 and label in labels[0] and 'PBConcept' not in labels[0] for _, label, n, labels in matches), 'Missing, ambiguous or cross-graph external endpoint')
    by_key = {r['key']: r['label'] for r in refs}
    edges = plan['relationships']
    ensure(len(edges) == 14 and len({(e['source'], e['type'], e['target']) for e in edges}) == 14, 'Unexpected extension edges')
    for edge in edges:
        ensure(re.fullmatch('[A-Z_]+', edge['type']) and edge['properties']['origin'] == ORIGIN and edge['properties']['ontologyId'] == 'pb_shared', 'Invalid owned edge')
        if edge['type'] == 'MEASURES_CUSTOMER':
            ensure(edge['target'] == KEY and by_key.get(edge['source']) == 'BusinessMetric', 'Invalid metric edge')
        else:
            ensure(edge['type'] == 'HAS_DOMAIN_DIMENSION' and edge['source'] == KEY and by_key.get(edge['target']) == 'BusinessDimension', 'Invalid dimension edge')
    state = customer_state(db)
    ensure(len(state['nodes']) <= 1, 'Duplicate customer key')
    for _, labels, props in state['nodes']:
        ensure(sorted(labels) == sorted(node['labels']) and props == node['properties'], 'Existing Customer differs; no overwrite allowed')
    planned = {(e['source'], e['type'], e['target']): e['properties'] for e in edges}
    ensure(len({tuple(e[1:4]) for e in state['edges']}) == len(state['edges']), 'Duplicate owned edge')
    ensure(all(planned.get(tuple(e[1:4])) == e[4] for e in state['edges']), 'Unexpected owned edge')
    adjacent = rows(db, 'MATCH (c {key:$key})-[r]-() RETURN count(r)', PARAMS)[0][0]
    ensure(adjacent == len(state['edges']), 'Unexpected external Customer relationships')
    cross = rows(db, 'MATCH (a:PBConcept)-[r]-(b) WHERE NOT b:PBConcept RETURN count(r)')[0][0]
    ensure(cross == 0, 'Pre-existing cross-graph relationship')
    return dict(existingCustomerNodes=len(state['nodes']), existingCustomerRelationships=len(state['edges']), externalReferences=14)


def merge(db, plan):
    # One transaction for the Customer and all 14 edges; no changes to external nodes.
    query = '''CALL {
      WITH $props AS props
      MERGE (c:MappingCustomer {key:props.key})
      SET c:BusinessDimension, c = props
      RETURN count(c) AS customerCount
    }
    CALL {
      UNWIND $metrics AS edge
      MATCH (m:BusinessMetric {key:edge.source}), (c:MappingCustomer {key:edge.target})
      MERGE (m)-[r:MEASURES_CUSTOMER]->(c)
      SET r = edge.properties
      RETURN count(r) AS metricCount
    }
    CALL {
      UNWIND $dimensions AS edge
      MATCH (c:MappingCustomer {key:edge.source}), (d:BusinessDimension {key:edge.target})
      MERGE (c)-[r:HAS_DOMAIN_DIMENSION]->(d)
      SET r = edge.properties
      RETURN count(r) AS dimensionCount
    }
    RETURN customerCount,metricCount,dimensionCount'''
    result = rows(db, query, dict(props=plan['nodes'][0]['properties'],
                  metrics=[e for e in plan['relationships'] if e['type'] == 'MEASURES_CUSTOMER'],
                  dimensions=[e for e in plan['relationships'] if e['type'] == 'HAS_DOMAIN_DIMENSION']))
    ensure(result == [[1, 12, 2]], 'Incomplete atomic merge')


def verify(db, plan):
    preflight(db, plan)
    state = customer_state(db)
    ensure(len(state['nodes']) == 1 and len(state['edges']) == 14, 'Customer extension incomplete')
    graph_query = (HERE / 'view_mapping_customer.cypher').read_text(encoding='utf-8')
    visible = rows(db, graph_query)
    ensure(len(visible) == 12, 'Not all twelve metrics visible')
    # The graph-view query returns relationship paths; no root traversal is required.
    direct = rows(db, 'MATCH (m:BusinessMetric)-[:MEASURES_CUSTOMER]->(c:MappingCustomer {key:$key}) RETURN m.key,m.name ORDER BY m.key', PARAMS)
    securities = rows(db, "MATCH (p:SharedProduct {ontologyId:'pb_shared',code:'securities_fund'})-[:MEASURED_BY_AUM]->(m:BusinessMetric)-[:MEASURES_CUSTOMER]->(c:MappingCustomer {key:$key}) RETURN p.code,m.key,c.key", PARAMS)
    ensure(securities == [['securities_fund', 'aum:metric:aum_securities_month_end', KEY]], 'Securities Customer lookup requires/went through a total')
    query = (HERE / 'view_mapping_with_customer.cypher').read_text(encoding='utf-8')
    rendered = rows(db, query)
    ensure(rendered and any(row[-1] for row in rendered), 'Full mapping query omitted Customer')
    from verify_mapping_view import verify as verify_view
    view_check = verify_view(db)
    customer_keys = {e[3] for e in state['edges'] if e[2] == 'HAS_DOMAIN_DIMENSION'}
    ensure(customer_keys == {'aum:dimension:customer', 'income:dimension:customer'}, 'Domain Customer metadata missing')
    return dict(customerNodes=1, customerRelationships=14, directMetricLinks=12,
                domainDimensionLinks=2, metrics=direct, securitiesFundDirectPath=securities,
                fullMappingQueryRows=len(rendered), exactViewBaselinePreserved=view_check['originalFourPathsExactlyPreserved'],
                noTotalRequiredForCustomer=True,
                conceptGraphCrossEdges=0, customerStateSha256=digest(state))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    creds = credentials(args.credentials)
    ensure(urlparse(creds['NEO4J_URI']).hostname == '4bb479b2.databases.neo4j.io', 'Unexpected Aura target')
    db = Neo4j(selected_aura(creds['NEO4J_URI']), 'neo4j', creds['NEO4J_USERNAME'], creds['NEO4J_PASSWORD'])
    plan = json.loads((HERE / 'graph_plan.json').read_text(encoding='utf-8'))
    check = preflight(db, plan)
    before = protected_snapshot(db)
    if args.check_only:
        print(json.dumps(dict(checkOnly='passed', host='4bb479b2.databases.neo4j.io', protected=before, **check)))
        return
    backup = dict(verifiedAt=datetime.now(timezone.utc).isoformat(), protected=before, customerBefore=customer_state(db))
    (HERE / 'before.json').write_text(json.dumps(backup, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    db.query('CREATE CONSTRAINT MappingCustomer_key_unique IF NOT EXISTS FOR (c:MappingCustomer) REQUIRE c.key IS UNIQUE')
    merge(db, plan)
    first = verify(db, plan)
    ensure(protected_snapshot(db) == before, 'Original graph changed')
    merge(db, plan)
    second = verify(db, plan)
    after = protected_snapshot(db)
    ensure(first == second and before == after, 'Idempotent rerun or protected graph check failed')
    report = dict(verifiedAt=datetime.now(timezone.utc).isoformat(), host='4bb479b2.databases.neo4j.io', database='neo4j',
                  before=before, after=after, existingGraphPreserved=True, idempotentRerun=True, **second)
    (HERE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
