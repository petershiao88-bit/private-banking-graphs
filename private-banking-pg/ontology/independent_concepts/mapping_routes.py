"""Bind declared business measurements to existing, separate mapping graphs."""
from concept_model import ensure, validate_plan

METRIC_MAPPING_CODES = {
    'aum_total': 'aum_total_month_end', 'aum_deposit': 'aum_deposit_month_end',
    'aum_investment': 'aum_investment_month_end', 'aum_bank_investment': 'aum_bank_investment_month_end',
    'aum_securities': 'aum_securities_month_end', 'aum_insurance': 'aum_insurance_month_end',
    'income_total': 'income_total_customer_month', 'fee_income': 'fee_income', 'bank_fee_income': 'bank_fee_income',
    'securities_fee_income': 'securities_fee_income', 'interest_income': 'interest_income',
    'deposit_interest_income': 'deposit_interest_income', 'loan_interest_income': 'loan_interest_income',
}


def build_routes(plan, shared_plan, mapping_plan):
    validate_plan(plan)
    shared_codes = {n['properties']['code'] for n in shared_plan['nodes'] if n.get('label') == 'SharedProduct' or 'SharedProduct' in n.get('labels', [])}
    mapping_nodes = {n['key']: n for n in mapping_plan['nodes']}
    products = {}
    for n in mapping_plan['nodes']:
        if n['label'] == 'MappingDraftProduct':
            products.setdefault(n['properties']['code'], []).append(n)
    routes = []
    for edge in plan['relationships']:
        if edge['type'] not in ('PB_AUM_MEASURED_BY', 'PB_INCOME_MEASURED_BY'):
            continue
        code = edge['source']
        domain = 'aum' if edge['type'] == 'PB_AUM_MEASURED_BY' else 'income'
        route = {'productCode': code, 'domain': domain}
        if code in shared_codes:
            route['sourceGraph'] = 'shared_product_sql'
        else:
            ensure(len(products.get(code, [])) == 1, 'Missing or ambiguous MappingDraft product')
            product = products[code][0]
            mapped_code = METRIC_MAPPING_CODES.get(edge['target'])
            ensure(mapped_code, 'Metric requires an explicit mapping code')
            metric_key = 'draft:pb:20261012:metric:' + mapped_code
            ensure(mapping_nodes.get(metric_key, {}).get('label') == 'MappingDraftMetric', 'Missing mapping metric')
            measurement_type = 'MEASURED_BY_AUM' if domain == 'aum' else 'MEASURED_BY_INCOME'
            ensure(any(r['from'] == product['key'] and r['to'] == metric_key and r['type'] == measurement_type for r in mapping_plan['relationships']), 'Business measurement has no matching mapping evidence')
            implementation_type = 'AUM_IMPLEMENTED_BY' if domain == 'aum' else 'INCOME_IMPLEMENTED_BY'
            sources = [r for r in mapping_plan['relationships'] if r['from'] == product['key'] and r['type'] == implementation_type
                       and r['properties'].get('mappingRole') == 'base_source'
                       and mapping_nodes[r['to']]['label'] == 'MappingDraftTable'
                       and mapping_nodes[r['to']]['properties'].get('tableRole') == 'source']
            ensure(sources and all(r['properties'].get('calculationRules') for r in sources), 'Draft mapping has no source rules')
            route.update(sourceGraph='mapping_draft_rules', productKey=product['key'], metricKey=metric_key)
        routes.append(route)
    ensure(len({(r['productCode'], r['domain']) for r in routes}) == len(routes), 'Ambiguous measurement binding')
    return sorted(routes, key=lambda r: (r['productCode'], r['domain']))
