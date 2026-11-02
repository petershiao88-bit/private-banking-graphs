"""SQL-classified bank product metrics, including LUM/interest; no execution or mapping."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('bank_business_common', HERE / 'advisory_income_model.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
FH, BANK = common.FH, common.BANK
require, keys, canonical_json = common.require, common.keys, common.canonical_json
LABELS = common.LABELS
RELATIONSHIPS = {**common.RELATIONSHIPS,
                 'HAS_BUSINESS_SCOPE': ('BusinessConcept', 'OntologyClassReference')}
# code, scope class, scope kind, metric kind, amount source tables
CONTRACT = {
    'bank.planned_trust_aum': ('bank_planned_trust', 'PlannedTrustProduct', 'product', 'aum',
        {'DSEBS.EBTS_ACT_CntAUMBal_PB', 'DSTAM.TRUCONTRACT_PB'}),
    'bank.planned_trust_fee_income': ('bank_planned_trust', 'PlannedTrustProduct', 'product', 'fee_income',
        {'DSEBS.EBTS_ACT_CntAUMBal_PB', 'DSTAM.TRUCONTRACT_PB'}),
    'bank.trust_custody_aum': ('bank_trust_custody', 'TrustCustodyProduct', 'product', 'aum',
        {'DSPMS.PB_PMS_AUM'}),
    'bank.trust_custody_fee_income': ('bank_trust_custody', 'TrustCustodyProduct', 'product', 'fee_income',
        {'DSPMS.PB_PMS_AUM'}),
    'bank.fx_fee_income': ('bank_fx', 'ForeignExchangeProduct', 'product', 'fee_income',
        {'DSWBS.PB_SPOT_Daily', 'DSWBS.PB_SPOT_Daily_HS', 'DSTAS.FO108_W'}),
    'bank.lc_fee_income': ('bank_lc', 'LetterOfCreditProduct', 'product', 'fee_income',
        {'DSWBS.IMPM007', 'DSWBS.IMPM007_HS'}),
    'bank.gold_fee_income': ('bank_gold', 'GoldProduct', 'product', 'fee_income',
        {'DSDEP.GD_PERFO_RPT', 'DSDEP.GD_PERFO_RPT_HS'}),
    'bank.loan_income': ('loan', 'LoanProduct', 'product', 'interest_income',
        {'DSLON.LN_NT_ACCT_HS', 'DSLON.LN_FN_ACCT_HS', 'DSLON.LN_FN_ACCT'}),
    'bank.loan_lum': ('loan', 'LoanProduct', 'product', 'lum',
        {'DSLON.LN_NT_ACCT', 'DSLON.LN_FN_ACCT', 'DSLON.LN_NT_ACCT_HS', 'DSLON.LN_FN_ACCT_HS'}),
}
EXECUTION = {'sql', 'join_rules', 'filter_rules', 'aggregation_rules', 'row_grain',
             'valuation_rules', 'snapshot_selection', 'currency_conversion', 'deduplication_rules',
             'recognition_rules', 'attribution_rules', 'period_basis'}
FIELD_SEMANTICS = {**common.FIELDS, **common.LUM_ELEMENTS, **common.INTEREST_ELEMENTS}
DEPARTMENT_CONTEXT = {'using_department': '私人銀行', 'definition_department': '私人銀行',
                      'source_data_owner': None}


def metric_class(kind):
    return BANK + {'aum': 'BankAUM', 'lum': 'BankLUM', 'fee_income': 'BankFeeIncome',
                   'interest_income': 'BankInterestIncome'}[kind]


def field_names(scope_kind, kind):
    fields = {'customerId', 'productId', 'amount', 'currency', 'snapshotDate'}
    if kind == 'aum':
        fields.update(common.AUM_ELEMENTS)
    elif kind == 'lum':
        fields.update(common.LUM_ELEMENTS)
    else:
        fields.add('incomePeriod')
        if kind == 'fee_income':
            fields.update(common.FEE_ELEMENTS)
            fields.add('employeeId')
        else:
            fields.update(common.INTEREST_ELEMENTS)
    return fields


def relation_contract(concepts):
    result = {}
    for c in concepts:
        cid, kind = c['id'], c['metric_kind']
        prop, domain = {'aum': ('measuresProduct', 'AUM'), 'lum': ('lumMeasuresProduct', 'LUM'),
                        'fee_income': ('feeIncomeFromProduct', 'FeeIncome'),
                        'interest_income': ('interestIncomeFromProduct', 'InterestIncome')}[kind]
        result[cid + '.scope'] = (cid, FH + prop, FH + domain, FH + 'FinancialProduct')
        if kind == 'fee_income':
            result[cid + '.advisor'] = (cid, BANK + 'attributedToAdvisor', BANK + 'BankFeeIncome',
                                        BANK + 'FinancialAdvisor')
    return result


def validate_model(model):
    keys(model, {'schema_version', 'ontology_version', 'status', 'scope', 'inference', 'instance_mapping',
                 'access_policy_status', 'execution', 'field_definitions', 'evidence', 'sources',
                 'concepts', 'relation_definitions', 'department_context'}, 'bank business metrics')
    require((model['schema_version'], model['ontology_version'], model['status'], model['scope']) ==
            ('1.0.0', '0.15.0', 'active', 'metadata_only'), 'Expected active v0.15.0 metadata')
    require(model['inference'] is False and model['instance_mapping'] is False and
            model['access_policy_status'] == 'deferred_by_user', 'No instances/inference/access decisions')
    require(model['department_context'] == DEPARTMENT_CONTEXT,
            'Private banking uses/defines metrics; source ownership remains unknown')
    keys(model['execution'], EXECUTION, 'execution')
    require(all(v is None for v in model['execution'].values()), 'No executable source rules')
    keys(model['field_definitions'], FIELD_SEMANTICS, 'field definitions')
    for field, semantics in FIELD_SEMANTICS.items():
        d = model['field_definitions'][field]
        keys(d, {'name', 'definition', 'data_type_hint', 'property_uri', 'entity_class_uri'}, 'field')
        require(tuple(d[k] for k in ('data_type_hint', 'property_uri', 'entity_class_uri')) == semantics,
                'Incorrect field semantic reference')
        require(all(isinstance(d[k], str) and d[k].strip() for k in ('name', 'definition')), 'Empty definition')
    evidence = model['evidence']
    require(isinstance(evidence, dict) and bool(evidence), 'Missing evidence')
    for record in evidence.values():
        require(isinstance(record, dict) and isinstance(record.get('file'), str) and
                record['file'].startswith('Ontology/私銀智能問答/') and '..' not in Path(record['file']).parts,
                'Invalid evidence path')

    def refs(values):
        require(isinstance(values, list) and bool(values) and all(isinstance(v, str) and v in evidence for v in values)
                and len(values) == len(set(values)), 'Invalid evidence references')

    sources = model['sources']
    require(isinstance(sources, list), 'Invalid sources')
    seen = set()
    for s in sources:
        keys(s, {'table', 'status', 'database_verified', 'evidence'}, 'source')
        require(isinstance(s['table'], str) and s['table'] not in seen and
                s['status'] == 'observed_in_files' and s['database_verified'] is False, 'Invalid source status')
        refs(s['evidence'])
        seen.add(s['table'])
    require(seen == set().union(*(c[4] for c in CONTRACT.values())), 'Incorrect source coverage')
    concepts = model['concepts']
    require(isinstance(concepts, list) and len(concepts) == len(CONTRACT), 'Incorrect metric coverage')
    seen = set()
    for c in concepts:
        keys(c, {'id', 'name', 'definition', 'subsidiary', 'department_owner', 'class_uri',
                 'specific_product_class_uri', 'metric_kind', 'product_code', 'business_scope_kind',
                 'business_scope_class_uri', 'fields', 'observations', 'table_sources'}, 'concept')
        cid = c['id']
        require(isinstance(cid, str) and cid in CONTRACT and cid not in seen, 'Unknown/duplicate metric')
        seen.add(cid)
        code, cls, scope_kind, kind, tables = CONTRACT[cid]
        require((c['product_code'], c['business_scope_class_uri'], c['business_scope_kind'], c['metric_kind'],
                 c['class_uri'], c['subsidiary'], c['department_owner'], c['specific_product_class_uri']) ==
                (code, BANK + cls, scope_kind, kind, metric_class(kind), 'bank', None, None),
                'Incorrect metric or product semantics')
        require(all(isinstance(c[k], str) and c[k].strip() for k in ('name', 'definition')), 'Missing metric meaning')
        common.validate_table_sources(c['table_sources'], evidence, sources, {(t, 'primary') for t in tables})
        require(c['table_sources']['unresolved_supporting_relations'] == [], 'No invented helper sources')
        expected = field_names(scope_kind, kind)
        require(isinstance(c['fields'], list) and len(c['fields']) == len(expected), 'Incorrect elements')
        fields = set()
        for f in c['fields']:
            keys(f, {'field', 'status', 'table', 'column', 'candidates'}, 'mapping')
            require(isinstance(f['field'], str) and f['field'] in expected and f['field'] not in fields,
                    'Unknown/duplicate element')
            fields.add(f['field'])
            require((f['status'], f['table'], f['column'], f['candidates']) == ('pending', None, None, []),
                    'New elements must be empty pending mappings')
        obs = c['observations']
        keys(obs, {'coverage', 'classification_observation', 'amount_observation', 'date_observation',
                   'gaps', 'evidence'}, 'observations')
        require(all(isinstance(obs[k], str) and obs[k].strip() for k in
                    ('coverage', 'classification_observation', 'amount_observation', 'date_observation')),
                'Missing observations')
        require(isinstance(obs['gaps'], list) and bool(obs['gaps']) and
                all(isinstance(v, str) and v.strip() for v in obs['gaps']), 'Missing unresolved scope')
        refs(obs['evidence'])
    relations = model['relation_definitions']
    expected = relation_contract(concepts)
    require(isinstance(relations, list) and len(relations) == len(expected), 'Incorrect relations')
    seen = set()
    for r in relations:
        keys(r, {'id', 'name', 'source_concept', 'property_uri', 'domain_uri', 'target_class_uri', 'fields'}, 'relation')
        require(isinstance(r['id'], str) and r['id'] in expected and r['id'] not in seen, 'Unknown/duplicate relation')
        seen.add(r['id'])
        require(tuple(r[k] for k in ('source_concept', 'property_uri', 'domain_uri', 'target_class_uri')) == expected[r['id']]
                and r['fields'] == [], 'Incorrect relationship semantics')
        require(isinstance(r['name'], str) and r['name'].strip(), 'Missing relation name')


def load_model(path=None):
    model = json.loads((HERE / 'bank-business-metrics.json' if path is None else Path(path)).read_text(encoding='utf-8'))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    model = copy.deepcopy(model)
    for c in model['concepts']:
        c['observations']['evidence'].sort()
    graph = common.project_graph(model, 'department-pg.bank-business-metrics')
    nodes = {n['id']: n for n in graph['nodes']}
    edges = {e['id']: e for e in graph['relationships']}
    nodes['department-pg.bank-business-metrics']['properties']['evidence_json'] = canonical_json(model['evidence'])
    nodes['department-pg.bank-business-metrics']['properties']['department_context_json'] = canonical_json(model['department_context'])
    for c in model['concepts']:
        cid, uri = c['id'], c['business_scope_class_uri']
        nodes[cid]['properties'].update(product_code=c['product_code'], metric_kind=c['metric_kind'],
            business_scope_kind=c['business_scope_kind'], observations_json=canonical_json(c['observations']),
            using_department=model['department_context']['using_department'],
            definition_department=model['department_context']['definition_department'])
        nodes[uri] = {'id': uri, 'label': 'OntologyClassReference', 'properties': {'scope': 'metadata_only', 'uri': uri}}
        eid = cid + '|HAS_BUSINESS_SCOPE|' + uri
        edges[eid] = {'id': eid, 'type': 'HAS_BUSINESS_SCOPE', 'source': cid, 'target': uri}
        rid = cid + '.scope'
        eid = rid + '|HAS_TARGET_CLASS|' + uri
        edges[eid] = {'id': eid, 'type': 'HAS_TARGET_CLASS', 'source': rid, 'target': uri}
    return {'nodes': sorted(nodes.values(), key=lambda n: n['id']),
            'relationships': sorted(edges.values(), key=lambda e: e['id'])}
