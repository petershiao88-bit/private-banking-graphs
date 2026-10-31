"""Add an isolated business graph. Never writes to the existing mapping graph.

Uses the existing repository's standard-library Query API client. Credentials
are read at runtime, never copied to deliverables. No databases are provisioned.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from import_ontology_neo4j import Neo4j
from import_aura_snapshot import credentials

from concept_model import (LABELS, KEY_FIELDS, TYPES, PRODUCT_FIELDS, METRIC_FIELDS,
                           CUSTOMER_FIELDS, PRODUCT_OUTPUT_FIELDS, TECHNICAL,
                           key, validate_plan, business_paths, product_catalog)

OUTPUT_FIELDS = PRODUCT_OUTPUT_FIELDS


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rows(db, query, params=None):
    return db.query(query, params)['data']['values']



def existing_fingerprint(db):
    ns = rows(db, 'MATCH (n) WHERE NOT n:PBConcept RETURN elementId(n), labels(n), properties(n) ORDER BY elementId(n)')
    for row in ns:
        row[1].sort()
    rs = rows(db, 'MATCH (a)-[r]->(b) WHERE NOT a:PBConcept OR NOT b:PBConcept RETURN elementId(r),elementId(a),type(r),elementId(b),properties(r) ORDER BY elementId(r)')
    return dict(nodes=len(ns), relationships=len(rs), sha256=digest([ns, rs]))


def concept_snapshot(db):
    return dict(
        nodes=rows(db, 'MATCH (n:PBConcept) RETURN elementId(n),labels(n),properties(n) ORDER BY elementId(n)'),
        relationships=rows(db, 'MATCH (a:PBConcept)-[r]->(b:PBConcept) RETURN elementId(r),elementId(a),type(r),elementId(b),properties(r) ORDER BY elementId(r)'),
    )


def verify_existing_concepts_preserved(before, after):
    for section in ('nodes', 'relationships'):
        current = {row[0]: row for row in after[section]}
        ensure(all(current.get(row[0]) == row for row in before[section]), 'Existing concept IDs/content changed')


def preflight(db, mapping, plan):
    validate_plan(plan)
    actual = rows(db, 'MATCH (n) WHERE any(l IN labels(n) WHERE l IN $labels) RETURN elementId(n),labels(n),properties(n)',
                  {'labels': sorted({l for ls in LABELS.values() for l in ls})})
    expected = {key(n['properties']): n for n in plan['nodes']}
    seen = set()
    for ident, labels, props in actual:
        code = key(props)
        ensure(code in expected and code not in seen, 'Concept label/code collision')
        ensure(sorted(labels) == sorted(LABELS[expected[code]['kind']]), 'Concept shares existing mapping labels')
        ensure(props == expected[code]['properties'], 'Existing concept content differs; review before overwriting')
        seen.add(code)
    ensure(rows(db, 'MATCH (c:PBConcept)-[r]-(x) WHERE NOT x:PBConcept RETURN count(r)') == [[0]], 'Cross-graph relationship detected')
    edges = rows(db, 'MATCH (a:PBConcept)-[r]->(b:PBConcept) RETURN coalesce(a.productCode,a.metricCode,a.conceptCode),type(r),coalesce(b.productCode,b.metricCode,b.conceptCode),properties(r)')
    planned = {(r['source'], r['type'], r['target']): r['properties'] for r in plan['relationships']}
    ensure(len({tuple(r[:3]) for r in edges}) == len(edges), 'Duplicate concept relationships')
    ensure(all(tuple(r[:3]) in planned and r[3] == planned[tuple(r[:3])] for r in edges), 'Unexpected concept relationship')
    routes = plan.get('mappingRoutes')
    if routes is None:
        routes = [{'productCode': r['source'], 'domain': 'aum' if r['type'].startswith('PB_AUM_') else 'income', 'sourceGraph': 'shared_product_sql'}
                  for r in plan['relationships'] if r['type'] in ('PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY')]
    wanted = {(r['source'], 'aum' if r['type'].startswith('PB_AUM_') else 'income') for r in plan['relationships']
              if r['type'] in ('PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY')}
    ensure(len(routes) == len(wanted) and {(r['productCode'], r['domain']) for r in routes} == wanted, 'Mapping routes differ from declared measurements')
    for route in routes:
        ensure(route['sourceGraph'] in ('shared_product_sql', 'mapping_draft_rules'), 'Unknown mapping source')
    shared = [r for r in routes if r['sourceGraph'] == 'shared_product_sql']
    draft = [r for r in routes if r['sourceGraph'] == 'mapping_draft_rules']
    if shared:
        matches = rows(mapping, """UNWIND $routes AS route
OPTIONAL MATCH (p:SharedProduct {ontologyId:'pb_shared',code:route.productCode})
OPTIONAL MATCH (p)-[r:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY]->(s:StagingOutput)
WHERE s.ontologyId=route.domain AND type(r)=CASE WHEN route.domain='aum' THEN 'AUM_IMPLEMENTED_BY' ELSE 'INCOME_IMPLEMENTED_BY' END
RETURN route.productCode,route.domain,count(DISTINCT p),count(DISTINCT s)""", {'routes': shared})
        ensure(len(matches) == len(shared) and all(p == 1 and stages > 0 for _, _, p, stages in matches), 'Shared mapping missing or ambiguous')
    if draft:
        ensure(all(isinstance(r.get('productKey'), str) and r['productKey'].startswith('draft:pb:20261012:product:')
                   and isinstance(r.get('metricKey'), str) and r['metricKey'].startswith('draft:pb:20261012:metric:') for r in draft), 'Invalid draft mapping binding')
        matches = rows(mapping, """UNWIND $routes AS route
OPTIONAL MATCH (p:MappingDraftProduct {key:route.productKey,code:route.productCode})
OPTIONAL MATCH (p)-[m:MEASURED_BY_AUM|MEASURED_BY_INCOME]->(metric:MappingDraftMetric {key:route.metricKey})
WHERE type(m)=CASE WHEN route.domain='aum' THEN 'MEASURED_BY_AUM' ELSE 'MEASURED_BY_INCOME' END
OPTIONAL MATCH (p)-[r:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY]->(s:MappingDraftTable)
WHERE type(r)=CASE WHEN route.domain='aum' THEN 'AUM_IMPLEMENTED_BY' ELSE 'INCOME_IMPLEMENTED_BY' END
 AND r.mappingRole='base_source' AND s.tableRole='source'
RETURN route.productCode,route.domain,count(DISTINCT p),count(DISTINCT metric),count(DISTINCT s)""", {'routes': draft})
        ensure(len(matches) == len(draft) and all(p == 1 and metric == 1 and sources > 0 for _, _, p, metric, sources in matches), 'Draft mapping missing or ambiguous')
    return dict(existingConceptNodes=len(actual), existingConceptRelationships=len(edges), mappingProductCodes=len({r['productCode'] for r in routes}), mappingRoutes=len(routes))


def merge(db, plan):
    validate_plan(plan)
    present = {n['kind'] for n in plan['nodes']}
    constraints = sorted({(LABELS[kind][1], KEY_FIELDS[kind]) for kind in present})
    for label, field in constraints:
        db.query(f'CREATE CONSTRAINT {label}_code_unique IF NOT EXISTS FOR (n:{label}) REQUIRE n.{field} IS UNIQUE')
    parts, params, returns = [], {}, []
    for kind in LABELS:
        if kind not in present:
            continue
        labels, field = LABELS[kind], KEY_FIELDS[kind]
        params[kind] = [n['properties'] for n in plan['nodes'] if n['kind'] == kind]
        count = kind + 'Count'
        parts.append(f'CALL {{ UNWIND ${kind} AS props MERGE (n:{":".join(labels)} {{{field}:props.{field}}}) SET n = props RETURN count(*) AS {count} }}')
        returns.append(count)
    kinds = {key(n['properties']): n['kind'] for n in plan['nodes']}
    groups = {}
    for edge in plan['relationships']:
        groups.setdefault((edge['type'], kinds[edge['source']], kinds[edge['target']]), []).append(edge)
    for index, ((typ, source_kind, target_kind), edges) in enumerate(sorted(groups.items())):
        param, count = 'edges' + str(index), 'edgeCount' + str(index)
        params[param] = edges
        sl, sf = LABELS[source_kind][1], KEY_FIELDS[source_kind]
        tl, tf = LABELS[target_kind][1], KEY_FIELDS[target_kind]
        parts.append(f'CALL {{ UNWIND ${param} AS edge MATCH (a:PBConcept:{sl} {{{sf}:edge.source}}), (b:PBConcept:{tl} {{{tf}:edge.target}}) MERGE (a)-[r:{typ}]->(b) SET r = edge.properties RETURN count(*) AS {count} }}')
        returns.append(count)
    return db.query('\n'.join(parts) + '\nRETURN ' + ','.join(returns), params)


def verify_concepts(db, plan):
    ns = rows(db, 'MATCH (n:PBConcept) RETURN elementId(n),labels(n),properties(n)')
    expected = {key(n['properties']): [sorted(LABELS[n['kind']]), n['properties']] for n in plan['nodes']}
    actual = {key(p): [sorted(ls), p] for _, ls, p in ns}
    ensure(len(ns) == len(expected) and actual == expected, 'Concept nodes differ')
    es = rows(db, 'MATCH (a:PBConcept)-[r]->(b:PBConcept) RETURN coalesce(a.productCode,a.metricCode,a.conceptCode),type(r),coalesce(b.productCode,b.metricCode,b.conceptCode),properties(r)')
    expected_edges = sorted([[r['source'], r['type'], r['target'], r.get('properties', {})] for r in plan['relationships']])
    ensure(sorted(es) == expected_edges, 'Concept edges differ')
    ensure(rows(db, 'MATCH (c:PBConcept)-[r]-(n) WHERE NOT n:PBConcept RETURN count(r)') == [[0]], 'Cross graph edge')
    return dict(nodes=len(ns), relationships=len(es), nodeIds=sorted(n[0] for n in ns), contentSha256=digest([actual, sorted(es)]))


def verify_queries(db, mapping, plan, output_dir=None):
    result = db.query((HERE / '01_list_concepts.cypher').read_text(encoding='utf-8'))['data']
    expected_catalog = product_catalog(plan)
    ensure(result['fields'] == OUTPUT_FIELDS and len(result['values']) == len(expected_catalog), 'First query schema/count mismatch')
    products = [{k: v for k, v in zip(result['fields'], row) if v is not None} for row in result['values']]
    ensure(not TECHNICAL.search(json.dumps(products, ensure_ascii=False)), 'First query leaked technical text')
    expected = {p['productCode']: p for p in expected_catalog}
    ensure(len({p['productCode'] for p in products}) == len(products), 'Duplicate returned product')
    for p in products:
        wanted = expected[p['productCode']]
        for field in OUTPUT_FIELDS:
            if field.endswith('Metrics'):
                ensure({m['metricCode']: m for m in p[field]} == {m['metricCode']: m for m in wanted[field]}, 'Measurement coverage mismatch')
            else:
                ensure(p.get(field) == wanted.get(field), 'Business product field mismatch')
    routes = plan.get('mappingRoutes', [{'productCode': r['source'], 'domain': 'aum' if r['type'].startswith('PB_AUM_') else 'income', 'sourceGraph': 'shared_product_sql'}
                  for r in plan['relationships'] if r['type'] in ('PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY')])
    checks, examples = [], {}
    for route in routes:
        query = '03_lookup_mapping_draft.cypher' if route['sourceGraph'] == 'mapping_draft_rules' else '02_lookup_mapping.cypher'
        params = {k: route[k] for k in ('productCode', 'domain', 'productKey', 'metricKey') if k in route}
        out = mapping.query((HERE / query).read_text(encoding='utf-8'), params)['data']
        ensure(len(out['values']) == 1, 'Second query must return one supported offering')
        record = dict(zip(out['fields'], out['values'][0]))
        ensure(record['productCode'] == route['productCode'] and record['domain'] == route['domain'], 'Routing mismatch')
        ensure(record['calculationAuthorized'] is False and record['mappings'], 'Invalid mapping evidence')
        if route['sourceGraph'] == 'shared_product_sql':
            ensure(all(m['lineageStatus'] == 'traced' and m['lineage'] for m in record['mappings']), 'Missing legacy source evidence')
            expected_stages=rows(mapping,"MATCH (p:SharedProduct {ontologyId:'pb_shared',code:$productCode})-[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(s:StagingOutput) WHERE s.ontologyId=$domain RETURN DISTINCT s.outputObject",params)
            ensure(sorted(m['outputTable'] for m in record['mappings'])==sorted(v[0] for v in expected_stages),'A mapping implementation was dropped')
            ensure(all(p['baseTable']==p['tablePath'][0] and p['tablePath'][-1]==m['sqlTable'] and p['rules'] for m in record['mappings'] for p in m['lineage']),'Incomplete legacy lineage')
        else:
            ensure(all(m['mappingFormat'] == 'mapping_draft_rules' and m['sourceTable'] and m['calculationRules'] for m in record['mappings']), 'Missing draft source rules')
        checks.append({'productCode': route['productCode'], 'domain': route['domain'], 'sourceGraph': route['sourceGraph'], 'mappingCount': len(record['mappings'])})
        examples[route['productCode'] + '_' + route['domain']] = record
    legacy_query=(HERE/'02_lookup_mapping.cypher').read_text(encoding='utf-8')
    negative=[{'productCode':"' MATCH (n) RETURN n //",'domain':'income'}, {'productCode':'bank_insurance','domain':'all'}, {'productCode':'unknown','domain':'aum'}]
    for params in negative:
        ensure(mapping.query(legacy_query,params)['data']['values']==[],'Unexpected invalid-parameter mapping result')
    customer_query = (HERE / 'lookup_customer_dimension.cypher').read_text(encoding='utf-8')
    customer_checks = []
    for n in plan['nodes']:
        if n['kind'] in ('aum', 'income'):
            code = n['properties']['metricCode']
            values = rows(db, customer_query, {'metricCode': code})
            ensure(len(values) == 1 and values[0][0] == code and values[0][2]['conceptCode'] == 'customer', 'Direct customer lookup failed')
            customer_checks.append(code)
    ensure(rows(db, customer_query, {'metricCode': 'unknown'}) == [], 'Unknown metric accepted')
    graph, paths = rows(db, (HERE / 'full_concept_graph_with_customer.cypher').read_text(encoding='utf-8'))[0]
    ensure(len(graph['nodes']) == len(plan['nodes']) and len(graph['relationships']) == len(plan['relationships']) and len(paths) == len(business_paths(plan)), 'Full graph/path count differs')
    ensure(all(n['key'] for n in graph['nodes']) and all(r['from'] and r['to'] for r in graph['relationships']), 'Null concept key')
    ensure(all(all(code not in {'customer', 'advisor', 'private_banking'} for code in p['nodeKeys']) for p in paths), 'Business context entered calculation path')
    target = Path(output_dir or HERE)
    target.mkdir(parents=True, exist_ok=True)
    for name, value in [('customer_graph.output.json', {'conceptGraph': graph, 'businessPaths': paths}), ('01_output.json', {'products': products}), ('02_output_examples.json', examples)]:
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'firstQueryRows': len(products), 'firstQueryWhitelistPassed': True, 'technicalTextLeaks': 0,
            'allProductDomainPairs': checks, 'invalidParameterChecksPassed':len(negative), 'directCustomerMetricChecks': customer_checks, 'fullGraphBusinessPathCount': len(paths), 'customerIsNotCalculationRoot': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials', type=Path)
    parser.add_argument('--uri')
    parser.add_argument('--database', default='neo4j')
    parser.add_argument('--mapping-database', default='neo4j')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--plan', type=Path, default=HERE / 'concept_graph.json')
    parser.add_argument('--mapping-routes', type=Path, help='Explicit local binding registry; does not modify mapping nodes')
    parser.add_argument('--validate-only', action='store_true', help='Local checks only; no credentials or network')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8-sig'))
    if args.mapping_routes:
        plan['mappingRoutes']=json.loads(args.mapping_routes.read_text(encoding='utf-8-sig'))['routes']
    validate_plan(plan)
    if args.validate_only:
        print(json.dumps({'localValidation': 'passed', 'nodes': len(plan['nodes']), 'relationships': len(plan['relationships']), 'businessPaths': len(business_paths(plan)), 'networkUsed': False}))
        return
    ensure(args.check_only or plan.get('importReady') is not False, 'Review draft is not an approved import plan; use --validate-only')
    creds = credentials(args.credentials) if args.credentials else os.environ
    uri = args.uri or creds.get('NEO4J_URI')
    parsed = urlparse(uri or '')
    ensure(parsed.scheme in ['https', 'http', 'neo4j+s', 'bolt+s'] and parsed.hostname, 'Explicit URI required')
    ensure(parsed.scheme != 'http' or parsed.hostname in ['127.0.0.1', 'localhost'], 'Remote connections require TLS')
    if args.uri and creds.get('NEO4J_URI'):
        ensure(parsed.hostname == urlparse(creds['NEO4J_URI']).hostname, 'Credential host mismatch')
    ensure(not parsed.username and not parsed.password and not parsed.query and parsed.path in ['', '/'], 'Invalid URI')
    base = uri.rstrip('/') if parsed.scheme in ['http', 'https'] else 'https://' + parsed.hostname
    for name in [args.database, args.mapping_database]:
        ensure(bool(re.fullmatch(r'[A-Za-z0-9_.-]+', name)), 'Invalid database name')
    db = Neo4j(base, args.database, creds.get('NEO4J_USERNAME', 'neo4j'), creds['NEO4J_PASSWORD'])
    mapping = Neo4j(base, args.mapping_database, creds.get('NEO4J_USERNAME', 'neo4j'), creds['NEO4J_PASSWORD'])
    check = preflight(db, mapping, plan)
    before = existing_fingerprint(mapping)
    target_before = existing_fingerprint(db) if args.database != args.mapping_database else before
    if args.check_only:
        print(json.dumps(dict(checkOnly='passed', host=parsed.hostname, database=args.database, mapping=before, **check)))
        return
    old_ids = {r[0] for r in rows(db, 'MATCH (n) WHERE NOT n:PBConcept RETURN elementId(n)')}
    concepts_before = concept_snapshot(db)
    (HERE / 'customer_update.before.json').write_text(json.dumps(concepts_before, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    merge(db, plan)
    first = verify_concepts(db, plan)
    ensure(not old_ids.intersection(first['nodeIds']), 'An original node was reused')
    ensure(existing_fingerprint(mapping) == before and existing_fingerprint(db) == target_before, 'Existing graph changed')
    query_checks = verify_queries(db, mapping, plan)
    merge(db, plan)
    second = verify_concepts(db, plan)
    ensure(first == second, 'Idempotent rerun failed')
    after = existing_fingerprint(mapping)
    ensure(after == before and existing_fingerprint(db) == target_before, 'Existing graph changed on rerun')
    verify_existing_concepts_preserved(concepts_before, concept_snapshot(db))
    report = dict(verifiedAt=datetime.now(timezone.utc).isoformat(), host=parsed.hostname,
                  conceptDatabase=args.database, mappingDatabase=args.mapping_database,
                  isolation='separate_databases' if args.database != args.mapping_database else 'disjoint_nodes_same_database',
                  arbitraryCypherIsNotBlocked=args.database == args.mapping_database,
                  before=before, after=after, conceptGraph=second,
                  reusedOriginalNodeCount=0, crossGraphRelationshipCount=0,
                  originalGraphPreserved=True, existingConceptGraphPreserved=True,
                  conceptNodesBefore=len(concepts_before['nodes']), conceptRelationshipsBefore=len(concepts_before['relationships']),
                  idempotentRerun=True, **query_checks)
    (HERE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ['allProductDomainPairs', 'conceptGraph']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
