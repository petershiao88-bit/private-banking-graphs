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

LABELS = {
    'product': ['PBConcept', 'PBConceptProduct'],
    'aum': ['PBConcept', 'PBConceptMetric', 'PBConceptAUM'],
    'income': ['PBConcept', 'PBConceptMetric', 'PBConceptIncome'],
    'customer': ['PBConcept', 'PBConceptCustomer'],
}
TYPES = ['PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY', 'PB_INCOME_PENDING',
         'PB_AUM_ROLLS_UP_TO', 'PB_INCOME_ROLLS_UP_TO', 'PB_MEASURES_CUSTOMER']
PRODUCT_FIELDS = {'productCode', 'name', 'definition', 'status', 'aumStatus', 'incomeStatus'}
METRIC_FIELDS = {'metricCode', 'name', 'definition', 'status'}
CUSTOMER_FIELDS = {'conceptCode', 'name', 'definition', 'status',
                   'customerId', 'customerName', 'customerNumber'}
OUTPUT_FIELDS = ['productCode', 'productName', 'definition', 'status', 'aumStatus',
                 'incomeStatus', 'aumMetrics', 'incomeMetrics']
# Defense in depth in addition to exact field and value comparisons.
TECHNICAL = re.compile(r'(?i)\b(?:SQL|CASE|SELECT|WHERE|JOIN|STAGE|FH_TYP|SUB_TYPE|CUST_ID|AMT|PROD_TYPE|CFEE|ABFEE|TSSN)\b|(?:AUM|INCOME)_[0-9]|DSPMS\.|\b\w+\.\w+\b')


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rows(db, query, params=None):
    return db.query(query, params)['data']['values']


def key(props):
    return props.get('productCode', props.get('metricCode', props.get('conceptCode')))


def validate_plan(plan):
    keys = set()
    for n in plan['nodes']:
        ensure(n['kind'] in LABELS, 'Unexpected node kind')
        props = n['properties']
        fields = PRODUCT_FIELDS if n['kind'] == 'product' else CUSTOMER_FIELDS if n['kind'] == 'customer' else METRIC_FIELDS
        ensure(set(props) == fields, 'Non-business property')
        ensure(all(isinstance(v, str) and v for v in props.values()), 'Invalid property value')
        ensure(not TECHNICAL.search(json.dumps(props, ensure_ascii=False)), 'Technical text in concept')
        ensure(key(props) not in keys, 'Duplicate concept code')
        keys.add(key(props))
    edges = [(r['source'], r['type'], r['target']) for r in plan['relationships']]
    ensure(len(set(edges)) == len(edges), 'Duplicate edge')
    ensure(all(a in keys and b in keys and t in TYPES for a, t, b in edges), 'External endpoint or unexpected relationship')
    ensure(len(keys) == 28 and len(edges) == 52, 'Unexpected graph size')
    ensure(sum(t == 'PB_INCOME_PENDING' for a, t, b in edges) == 1, 'Missing pending relationship')
    kinds = {key(n['properties']): n['kind'] for n in plan['nodes']}
    ensure(list(kinds.values()).count('customer') == 1 and kinds.get('customer') == 'customer', 'Unexpected customer concept')
    metrics = {code for code, kind in kinds.items() if kind in ('aum', 'income')}
    ensure({(a, b) for a, t, b in edges if t == 'PB_MEASURES_CUSTOMER'} ==
           {(code, 'customer') for code in metrics}, 'Each metric must directly measure Customer')
    for a, t, b in edges:
        if t == 'PB_MEASURES_CUSTOMER':
            continue
        ensure(kinds[b] in ('aum', 'income'), 'Non-metric measurement or rollup target')
        ensure(kinds[a] in ('aum', 'income') if t.endswith('ROLLS_UP_TO') else kinds[a] == 'product', 'Invalid relationship source')
        ensure(kinds[b] == ('aum' if t.startswith('PB_AUM_') else 'income'), 'Cross-domain relationship')


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
    planned = {(r['source'], r['type'], r['target']) for r in plan['relationships']}
    ensure(len({tuple(r[:3]) for r in edges}) == len(edges), 'Duplicate concept relationships')
    ensure(all(tuple(r[:3]) in planned and r[3] == {} for r in edges), 'Unexpected concept relationship')
    codes = [key(n['properties']) for n in plan['nodes'] if n['kind'] == 'product']
    matches = rows(mapping, "UNWIND $codes AS code OPTIONAL MATCH (p:SharedProduct {ontologyId:'pb_shared',code:code}) RETURN code,count(p)", {'codes': codes})
    ensure(len(matches) == 15 and all(count == 1 for code, count in matches), 'Existing mapping product missing or ambiguous')
    return dict(existingConceptNodes=len(actual), existingConceptRelationships=len(edges), mappingProductCodes=len(matches))


def merge(db, plan):
    # Constraints apply only to new concept labels. The entire data write is atomic.
    for label, field in [('PBConceptProduct', 'productCode'), ('PBConceptMetric', 'metricCode'), ('PBConceptCustomer', 'conceptCode')]:
        db.query(f'CREATE CONSTRAINT {label}_code_unique IF NOT EXISTS FOR (n:{label}) REQUIRE n.{field} IS UNIQUE')
    parts = []
    params = {}
    for kind, labels in LABELS.items():
        field = 'productCode' if kind == 'product' else 'conceptCode' if kind == 'customer' else 'metricCode'
        params[kind] = [n['properties'] for n in plan['nodes'] if n['kind'] == kind]
        parts.append(f'CALL {{ UNWIND ${kind} AS props MERGE (n:{":".join(labels)} {{{field}:props.{field}}}) SET n = props RETURN count(*) AS {kind}Count }}')
    for index, kind in enumerate(TYPES):
        param = 'edges' + str(index)
        params[param] = [r for r in plan['relationships'] if r['type'] == kind]
        source_label, source_field = ('PBConceptMetric', 'metricCode') if kind.endswith('ROLLS_UP_TO') or kind == 'PB_MEASURES_CUSTOMER' else ('PBConceptProduct', 'productCode')
        target_label, target_field = ('PBConceptCustomer', 'conceptCode') if kind == 'PB_MEASURES_CUSTOMER' else ('PBConceptMetric', 'metricCode')
        parts.append(f'CALL {{ UNWIND ${param} AS edge MATCH (a:PBConcept:{source_label} {{{source_field}:edge.source}}), (b:PBConcept:{target_label} {{{target_field}:edge.target}}) MERGE (a)-[:{kind}]->(b) RETURN count(*) AS edgeCount{index} }}')
    db.query('\n'.join(parts) + '\nRETURN productCount,aumCount,incomeCount,customerCount', params)


def verify_concepts(db, plan):
    ns = rows(db, 'MATCH (n:PBConcept) RETURN elementId(n),labels(n),properties(n)')
    expected = {key(n['properties']): [sorted(LABELS[n['kind']]), n['properties']] for n in plan['nodes']}
    actual = {key(p): [sorted(ls), p] for _, ls, p in ns}
    ensure(len(ns) == len(expected) and actual == expected, 'Concept nodes differ')
    es = rows(db, 'MATCH (a:PBConcept)-[r]->(b:PBConcept) RETURN coalesce(a.productCode,a.metricCode,a.conceptCode),type(r),coalesce(b.productCode,b.metricCode,b.conceptCode),properties(r)')
    expected_edges = sorted([[r['source'], r['type'], r['target'], {}] for r in plan['relationships']])
    ensure(sorted(es) == expected_edges, 'Concept edges differ')
    ensure(rows(db, 'MATCH (c:PBConcept)-[r]-(n) WHERE NOT n:PBConcept RETURN count(r)') == [[0]], 'Cross graph edge')
    return dict(nodes=len(ns), relationships=len(es), nodeIds=sorted(n[0] for n in ns), contentSha256=digest([actual, sorted(es)]))


def verify_queries(db, mapping, plan):
    q1 = (HERE / '01_list_concepts.cypher').read_text(encoding='utf-8')
    q2 = (HERE / '02_lookup_mapping.cypher').read_text(encoding='utf-8')
    result = db.query(q1)['data']
    ensure(result['fields'] == OUTPUT_FIELDS and len(result['values']) == 15, 'First query schema/count mismatch')
    products = [dict(zip(result['fields'], row)) for row in result['values']]
    ensure(not TECHNICAL.search(json.dumps(products, ensure_ascii=False)), 'First query leaked technical text')
    ensure(len({p['productCode'] for p in products}) == 15, 'Duplicate returned product')
    for p in products:
        for domain in ['aum', 'income']:
            ensure(bool(p[domain + 'Metrics']), 'Missing metric path')
            for m in p[domain + 'Metrics']:
                ensure(set(m) == METRIC_FIELDS, 'Non-whitelisted metric fields')
    pending = next(p for p in products if p['productCode'] == 'bank_collective_account')
    ensure(pending['incomeStatus'] == 'pending_confirmation', 'Pending Income lost')
    checks, examples = [], {}
    for p in products:
        for domain in ['aum', 'income']:
            out = mapping.query(q2, dict(productCode=p['productCode'], domain=domain))['data']
            ensure(len(out['values']) == 1, 'Second query must return exactly one product')
            record = dict(zip(out['fields'], out['values'][0]))
            ensure(record['productCode'] == p['productCode'] and record['domain'] == domain, 'Routing mismatch')
            ensure(record['calculationAuthorized'] is False, 'Lineage is not calculation approval')
            expected_stages = rows(mapping, "MATCH (p:SharedProduct {ontologyId:'pb_shared',code:$productCode})-[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(s:StagingOutput) WHERE s.ontologyId=$domain RETURN DISTINCT s.outputObject", dict(productCode=p['productCode'], domain=domain))
            ensure(sorted(m['outputTable'] for m in record['mappings']) == sorted(r[0] for r in expected_stages), 'A mapping stage was dropped')
            ensure(all(m['lineageStatus'] == 'traced' and m['lineage'] for m in record['mappings']), 'Missing base table evidence')
            ensure(all(l['baseTable'] == l['tablePath'][0] and l['tablePath'][-1] == m['sqlTable'] and l['rules'] for m in record['mappings'] for l in m['lineage']), 'Incomplete lineage')
            if p['productCode'] == 'bank_collective_account' and domain == 'income':
                ensure(record['status'] == 'pending_confirmation' and record['mappingActive'] is False, 'Pending mapping marked active')
                ensure(all(m['mappingType'] == 'INCOME_DECLARED_BY' for m in record['mappings']), 'Pending mapped as implemented')
            checks.append(dict(productCode=p['productCode'], domain=domain, stageCount=len(record['mappings']),
                               baseTables=sorted({l['baseTable'] for m in record['mappings'] for l in m['lineage']}), status=record['status']))
            if p['productCode'] in ['bank_insurance', 'bank_collective_account']:
                examples[p['productCode'] + '_' + domain] = record
    # Query parameters remain values even for invalid/adversarial input.
    negative = [dict(productCode="' MATCH (n) RETURN n //", domain='income'),
                dict(productCode='bank_insurance', domain='all'), dict(productCode='unknown', domain='aum')]
    for params in negative:
        ensure(mapping.query(q2, params)['data']['values'] == [], 'Unexpected invalid-parameter result')
    customer_query = (HERE / 'lookup_customer_dimension.cypher').read_text(encoding='utf-8')
    customer_checks = []
    for node in plan['nodes']:
        if node['kind'] not in ('aum', 'income'):
            continue
        code = node['properties']['metricCode']
        values = rows(db, customer_query, {'metricCode': code})
        ensure(len(values) == 1 and values[0][0] == code and values[0][2]['conceptCode'] == 'customer', 'Direct customer lookup failed')
        customer_checks.append(code)
    ensure(rows(db, customer_query, {'metricCode': 'unknown'}) == [], 'Unknown metric accepted')
    full = rows(db, (HERE / 'full_concept_graph_with_customer.cypher').read_text(encoding='utf-8'))
    graph, paths = full[0]
    ensure(len(graph['nodes']) == 28 and len(graph['relationships']) == 52 and len(paths) == 30, 'Full graph/path count changed unexpectedly')
    ensure(all(n['key'] for n in graph['nodes']) and all(e['from'] and e['to'] for e in graph['relationships']), 'Null concept key')
    ensure(all('customer' not in p['nodeKeys'] for p in paths), 'Customer dimension became a calculation root')
    (HERE / 'customer_graph.output.json').write_text(json.dumps({'conceptGraph': graph, 'businessPaths': paths}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / '01_output.json').write_text(json.dumps({'products': products}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / '02_output_examples.json').write_text(json.dumps(examples, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dict(firstQueryRows=len(products), firstQueryWhitelistPassed=True, technicalTextLeaks=0,
                allProductDomainPairs=checks, invalidParameterChecksPassed=len(negative),
                directCustomerMetricChecks=customer_checks, fullGraphBusinessPathCount=len(paths),
                customerIsNotCalculationRoot=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials', type=Path)
    parser.add_argument('--uri')
    parser.add_argument('--database', default='neo4j')
    parser.add_argument('--mapping-database', default='neo4j')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
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
    plan = json.loads((HERE / 'concept_graph.json').read_text(encoding='utf-8'))
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
