"""Business-only schemas and projections shared by local builders and checks."""
import copy
import json
import re

LABELS = {
    'product': ['PBConcept', 'PBConceptProduct'],
    'aum': ['PBConcept', 'PBConceptMetric', 'PBConceptAUM'],
    'income': ['PBConcept', 'PBConceptMetric', 'PBConceptIncome'],
    'customer': ['PBConcept', 'PBConceptCustomer'],
    'advisor': ['PBConcept', 'PBConceptAdvisor'],
    'organization': ['PBConcept', 'PBConceptOrganization'],
}
KEY_FIELDS = {kind: 'productCode' if kind == 'product' else 'metricCode' if kind in ('aum', 'income') else 'conceptCode' for kind in LABELS}
PRODUCT_FIELDS = {'productCode', 'name', 'aumDefinition', 'incomeDefinition'}
PRODUCT_BUSINESS_FIELDS = {'offeringType', 'definition', 'productCategory', 'businessChannel', 'customerNeed', 'serviceDescription'}
PRODUCT_CLASSIFICATION_FIELDS = {'subsidiary', 'currencyType', 'structureType', 'depositorType', 'fundType', 'marketRegion', 'dealingMode'}
METRIC_FIELDS = {'metricCode', 'name', 'definition'}
CUSTOMER_FIELDS = {'conceptCode', 'name', 'definition', 'customerId', 'customerName', 'customerNumber'}
ADVISOR_FIELDS = {'conceptCode', 'name', 'definition', 'roleResponsibilities', 'serviceDescription', 'advisorId', 'advisorName', 'employeeNumber'}
ORGANIZATION_FIELDS = {'conceptCode', 'name', 'definition', 'aliases', 'organizationType', 'businessPurpose', 'targetCustomer', 'serviceScope'}
FIELDS = {'product': PRODUCT_FIELDS | PRODUCT_BUSINESS_FIELDS | PRODUCT_CLASSIFICATION_FIELDS, 'aum': METRIC_FIELDS, 'income': METRIC_FIELDS,
          'customer': CUSTOMER_FIELDS | {'businessRole'}, 'advisor': ADVISOR_FIELDS, 'organization': ORGANIZATION_FIELDS}
REQUIRED = {**FIELDS, 'product': PRODUCT_FIELDS, 'customer': CUSTOMER_FIELDS}
NODE_FIELDS = sorted(set().union(*FIELDS.values()))
TYPES = ['PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY', 'PB_AUM_ROLLS_UP_TO', 'PB_INCOME_ROLLS_UP_TO',
         'PB_HAS_MEASUREMENT_SUBJECT', 'PB_SUBCATEGORY_OF', 'PB_ASSIGNED_TO', 'PB_SCOPED_TO']
CALCULATION_TYPES = set(TYPES[:4])
RELATION_FIELDS = {'definition', 'businessConstraint'}
PRODUCT_OUTPUT_FIELDS = ['productCode', 'productName', 'aumDefinition', 'incomeDefinition', 'offeringType', 'definition',
                         'productCategory', 'businessChannel', 'customerNeed', 'serviceDescription',
                         'subsidiary', 'currencyType', 'structureType', 'depositorType', 'fundType', 'marketRegion', 'dealingMode', 'aumMetrics', 'incomeMetrics']
TECHNICAL = re.compile(r'(?i)\b(?:SQL|CASE|SELECT|WHERE|JOIN|STAGE|FH_TYP|SUB_TYPE|CUST_ID|AMT|PROD_TYPE|CFEE|ABFEE|TSSN)\b|(?:AUM|INCOME)_[0-9]|DSPMS\.|\b\w+\.\w+\b')


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def key(props):
    return props.get('productCode', props.get('metricCode', props.get('conceptCode')))


def validate_plan(plan):
    ensure(isinstance(plan, dict) and isinstance(plan.get('nodes'), list) and isinstance(plan.get('relationships'), list), 'Invalid graph plan')
    nodes = {}
    for n in plan['nodes']:
        ensure(isinstance(n, dict) and n.get('kind') in LABELS and isinstance(n.get('properties'), dict), 'Unexpected node kind')
        props, kind = n['properties'], n['kind']
        ensure(REQUIRED[kind] <= set(props) <= FIELDS[kind], 'Non-business or missing property')
        for field, value in props.items():
            if field in {'aliases', 'roleResponsibilities'}:
                ensure(isinstance(value, list) and value and all(isinstance(v, str) and v for v in value), 'Invalid business list')
            else:
                ensure(isinstance(value, str) and (value or field in {'aumDefinition', 'incomeDefinition'}), 'Invalid property value')
        ensure(not TECHNICAL.search(json.dumps(props, ensure_ascii=False)), 'Technical text in concept')
        if kind == 'product' and 'offeringType' in props:
            ensure(props['offeringType'] in {'產品', '服務'}, 'Unexpected offering type')
        code = key(props)
        ensure(isinstance(code, str) and re.fullmatch(r'[a-z][a-z0-9_]*', code), 'Invalid concept code')
        ensure(code not in nodes, 'Duplicate concept code')
        nodes[code] = n
    ensure(nodes.get('customer', {}).get('kind') == 'customer' and sum(n['kind'] == 'customer' for n in nodes.values()) == 1, 'Unexpected customer concept')
    ensure(nodes.get('aum_total', {}).get('kind') == 'aum' and nodes.get('income_total', {}).get('kind') == 'income', 'Missing business totals')
    edges = set()
    measured = set()
    subjects = set()
    for r in plan['relationships']:
        ensure(isinstance(r, dict) and all(field in r for field in ('source', 'type', 'target', 'properties')), 'Invalid relationship')
        a, t, b = r['source'], r['type'], r['target']
        ensure(a in nodes and b in nodes and t in TYPES, 'External endpoint or unexpected relationship')
        ensure((a, t, b) not in edges and a != b, 'Duplicate or self relationship')
        edges.add((a, t, b))
        props = r['properties']
        ensure(isinstance(props, dict) and {'definition'} <= set(props) <= RELATION_FIELDS, 'Unexpected relationship properties')
        ensure(all(isinstance(v, str) and (v or f == 'businessConstraint') for f, v in props.items()), 'Invalid relationship property')
        ensure(not TECHNICAL.search(json.dumps(props, ensure_ascii=False)), 'Technical text in business relationship')
        ak, bk = nodes[a]['kind'], nodes[b]['kind']
        if t in CALCULATION_TYPES:
            domain = 'aum' if t.startswith('PB_AUM_') else 'income'
            ensure(bk == domain, 'Cross-domain relationship')
            if t.endswith('ROLLS_UP_TO'):
                ensure(ak == domain, 'Invalid rollup source')
            else:
                ensure(ak == 'product', 'Invalid measurement source')
                ensure(bool(nodes[a]['properties'][domain + 'Definition']), 'Blank definition cannot declare a measurement')
                measured.add((a, domain))
        elif t == 'PB_HAS_MEASUREMENT_SUBJECT':
            ensure(ak in ('aum', 'income') and b == 'customer', 'Invalid measurement subject')
            subjects.add(a)
        elif t == 'PB_SUBCATEGORY_OF':
            ensure(ak == bk == 'product', 'Invalid product classification')
        elif t == 'PB_ASSIGNED_TO':
            ensure(ak == 'customer' and bk == 'advisor', 'Invalid customer advisor relationship')
        elif t == 'PB_SCOPED_TO':
            ensure(ak in ('customer', 'advisor') and bk == 'organization', 'Invalid organization scope')
    metrics = {c for c, n in nodes.items() if n['kind'] in ('aum', 'income')}
    ensure(subjects == metrics, 'Each metric must directly measure Customer')
    for c, n in nodes.items():
        if n['kind'] == 'product':
            ensure(any((c, domain) in measured for domain in ('aum', 'income')), 'Offering has no declared measurement')
            for domain in ('aum', 'income'):
                ensure(bool(n['properties'][domain + 'Definition']) == ((c, domain) in measured), 'Definition and measurement coverage differ')
    if 'bank_collective_account' in nodes:
        ensure(nodes['bank_collective_account']['properties']['incomeDefinition'] == '' and ('bank_collective_account', 'income') not in measured, 'Unconfirmed collective account Income relationship')
    # Classification and service links do not become monetary paths.
    for typ in ('PB_AUM_ROLLS_UP_TO', 'PB_INCOME_ROLLS_UP_TO', 'PB_SUBCATEGORY_OF'):
        adjacency = {c: [] for c in nodes}
        for a, t, b in edges:
            if t == typ:
                adjacency[a].append(b)
        done = set()
        def visit(c, stack):
            ensure(c not in stack, 'Business hierarchy cycle')
            if c in done:
                return
            for b in adjacency[c]:
                visit(b, stack | {c})
            done.add(c)
        for c in nodes:
            visit(c, set())
    for c in metrics:
        domain = nodes[c]['kind']
        root = 'aum_total' if domain == 'aum' else 'income_total'
        todo, reachable = [c], set()
        while todo:
            current = todo.pop()
            if current in reachable:
                continue
            reachable.add(current)
            todo.extend(b for a, t, b in edges if a == current and t == f'PB_{domain.upper()}_ROLLS_UP_TO')
        ensure(root in reachable, 'Metric does not reach its business total')
    adjacency = {c: set() for c in nodes}
    for a, _, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    todo, seen = ['customer'], set()
    while todo:
        c = todo.pop()
        if c not in seen:
            seen.add(c)
            todo.extend(adjacency[c] - seen)
    ensure(seen == set(nodes), 'Disconnected business concept')
    return plan


def relationship_id(r):
    return f"business:{r['source']}:{r['type']}:{r['target']}"


def business_paths(plan):
    validate_plan(plan)
    by = {key(n['properties']): n for n in plan['nodes']}
    paths = []
    def extend(node_keys, rel_ids, domain):
        current = node_keys[-1]
        root = 'aum_total' if domain == 'aum' else 'income_total'
        if current == root:
            paths.append({'domain': domain, 'nodeKeys': node_keys, 'relationshipIds': rel_ids})
            return
        for r in plan['relationships']:
            if r['source'] == current and r['type'] == f'PB_{domain.upper()}_ROLLS_UP_TO':
                extend(node_keys + [r['target']], rel_ids + [relationship_id(r)], domain)
    for r in plan['relationships']:
        if r['type'] in {'PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY'}:
            domain = by[r['target']]['kind']
            extend([r['source'], r['target']], [relationship_id(r)], domain)
    return sorted(paths, key=lambda p: (p['nodeKeys'][0], p['domain'], p['nodeKeys']))


def project_graph(plan):
    validate_plan(plan)
    return {'nodes': [{'key': key(n['properties']), 'labels': LABELS[n['kind']], 'properties': copy.deepcopy(n['properties'])} for n in plan['nodes']],
            'relationships': [{'id': relationship_id(r), 'from': r['source'], 'to': r['target'], 'type': r['type'], 'properties': copy.deepcopy(r['properties'])} for r in plan['relationships']]}


def product_catalog(plan):
    validate_plan(plan)
    by = {key(n['properties']): n for n in plan['nodes']}
    paths = business_paths(plan)
    result = []
    for c, n in sorted(by.items()):
        if n['kind'] != 'product':
            continue
        props = n['properties']
        product = {'productCode': c, 'productName': props['name'], 'aumDefinition': props['aumDefinition'], 'incomeDefinition': props['incomeDefinition']}
        product.update({f: props[f] for f in sorted(PRODUCT_BUSINESS_FIELDS | PRODUCT_CLASSIFICATION_FIELDS) if f in props})
        for domain in ('aum', 'income'):
            codes = list(dict.fromkeys(metric for p in paths if p['nodeKeys'][0] == c and p['domain'] == domain for metric in p['nodeKeys'][1:]))
            product[domain + 'Metrics'] = [copy.deepcopy(by[metric]['properties']) for metric in codes]
        result.append(product)
    return result
