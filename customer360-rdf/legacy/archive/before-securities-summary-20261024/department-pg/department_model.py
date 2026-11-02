"""Department categories and metric adoption metadata; no instances or calculations."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('department_common', HERE / 'advisory_income_model.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
FH, BANK = common.FH, common.BANK
require, keys, canonical_json = common.require, common.keys, common.canonical_json
LABELS = common.LABELS
RELATIONSHIPS = {**common.RELATIONSHIPS,
    'USES_METRIC': ('BusinessConcept', 'BusinessConcept'),
    'HAS_PARENT_CLASS_REFERENCE': ('OntologyClassReference', 'OntologyClassReference'),
    'HAS_DOMAIN_CLASS': ('OntologyObjectPropertyReference', 'OntologyClassReference'),
    'HAS_RANGE_CLASS': ('OntologyObjectPropertyReference', 'OntologyClassReference')}
DEPARTMENT_ID = 'bank.private_banking'
APPROVED_METRICS = frozenset({
    'bank.product_fee_income',
    'bank.twd_deposit_aum', 'bank.foreign_currency_deposit_aum', 'bank.structured_deposit_aum',
    'bank.overseas_stock_aum', 'bank.overseas_bond_trust_aum', 'bank.offshore_structured_aum',
    'bank.overseas_bond_proprietary_aum',
    'bank.domestic_structured_si_fee_income', 'bank.offshore_structured_fee_income',
    'bank.overseas_stock_fee_income', 'bank.domestic_structured_eli_fee_income',
    'bank.domestic_structured_fci_fee_income', 'bank.dci_fee_income',
    'bank.fund_aum', 'bank.fund_fee_income', 'bank.etf_aum', 'bank.etf_fee_income',
    'bank.collective_account_aum', 'bank.insurance_aum', 'bank.insurance_fee_income',
    'bank.planned_trust_aum', 'bank.planned_trust_fee_income',
    'bank.trust_custody_aum', 'bank.trust_custody_fee_income',
    'bank.fx_fee_income', 'bank.lc_fee_income', 'bank.gold_fee_income',
    'bank.loan_lum', 'bank.loan_income', 'bank.deposit_interest_income',
    'bank.overseas_bond_trust_fee_income', 'bank.overseas_bond_proprietary_fee_income',
    'securities.bond_aum', 'securities.structured_aum', 'securities.fund_aum',
    'securities.foreign_stock_aum', 'securities.taiwan_stock_aum',
    'securities.bond_fee_income', 'securities.structured_fee_income',
    'securities.fund_fee_income', 'securities.foreign_stock_fee_income',
})


def validate_model(model, metric_concepts=None):
    keys(model, {'schema_version', 'ontology_version', 'status', 'scope', 'inference',
                 'instance_mapping', 'access_policy_status', 'department', 'relation_definition', 'metric_ids'},
         'departments')
    require((model['schema_version'], model['ontology_version'], model['status'], model['scope']) ==
            ('1.0.0', '0.16.0', 'active', 'metadata_only'), 'Expected active v0.16.0 department metadata')
    require(model['inference'] is False and model['instance_mapping'] is False and
            model['access_policy_status'] == 'deferred_by_user', 'No organization instances or access decisions')
    d = model['department']
    keys(d, {'id', 'name', 'definition', 'class_uri', 'subsidiary', 'department_owner', 'source_data_owner'},
         'private banking department')
    require((d['id'], d['name'], d['class_uri'], d['subsidiary']) ==
            (DEPARTMENT_ID, '私銀', BANK + 'PrivateBankingDepartment', 'bank'), 'Unexpected department scope')
    require(d['department_owner'] is None and d['source_data_owner'] is None,
            'Metric adoption does not establish source ownership')
    require(isinstance(d['definition'], str) and d['definition'].strip(), 'Missing department definition')
    r = model['relation_definition']
    keys(r, {'id', 'name', 'property_uri', 'domain_uri', 'range_uri'}, 'adoption relation')
    require((r['id'], r['name'], r['property_uri'], r['domain_uri'], r['range_uri']) ==
            (DEPARTMENT_ID + '.uses_metric', '私銀採用指標', FH + 'usesMetric', FH + 'Department', FH + 'Metric'),
            'Use Department -> Metric semantics; product, ownership and advisor relations stay separate')
    ids = model['metric_ids']
    require(isinstance(ids, list) and all(isinstance(cid, str) for cid in ids) and
            len(ids) == len(APPROVED_METRICS) and set(ids) == APPROVED_METRICS,
            'Expected exactly the 42 approved existing metrics, without duplicates or pending scope')
    if metric_concepts is not None:
        require(set(metric_concepts) == APPROVED_METRICS, 'Department scope must match all active metric concepts')
        allowed = {BANK + n for n in ('BankAUM', 'BankFeeIncome', 'BankLUM', 'BankInterestIncome')} | {
            'https://example.org/ontology/securities#' + n for n in ('SecuritiesAUM', 'SecuritiesFeeIncome')}
        for cid in ids:
            c = metric_concepts[cid]
            subsidiary = cid.split('.')[0]
            require(c['class_uri'] in allowed and 'table_sources' in c and c['subsidiary'] == subsidiary,
                    'Adoption target must remain an active metric with its original source subsidiary')
            prefix = '私銀－' + {'bank': '銀行', 'securities': '證券'}[subsidiary]
            require(c['name'].startswith(prefix) and len(c['name']) > len(prefix), 'Missing private metric display scope')


def load_model(path=None):
    model = json.loads((HERE / 'departments.json' if path is None else Path(path)).read_text(encoding='utf-8'))
    validate_model(model)
    return model


def build_graph(model, metric_concepts):
    validate_model(model, metric_concepts)
    nodes, edges = {}, {}

    def node(nid, label, **props):
        nodes[nid] = {'id': nid, 'label': label, 'properties': {'scope': 'metadata_only', **props}}

    def edge(source, kind, target):
        eid = source + '|' + kind + '|' + target
        edges[eid] = {'id': eid, 'type': kind, 'source': source, 'target': target}

    d, r = model['department'], model['relation_definition']
    mid, cid, rid = 'department-pg.departments', d['id'], r['id']
    node(mid, 'MetadataModule', ontology_version=model['ontology_version'], schema_version=model['schema_version'],
         status='active', access_policy_status=model['access_policy_status'],
         metric_ids_json=canonical_json(sorted(model['metric_ids'])),
         relation_definition_json=canonical_json(r))
    node(cid, 'BusinessConcept', name=d['name'], definition=d['definition'], subsidiary=d['subsidiary'],
         department_owner_json='null', source_data_owner_json='null', concept_kind='department')
    for uri in (d['class_uri'], FH + 'Department', FH + 'Metric'):
        node(uri, 'OntologyClassReference', uri=uri)
    node(r['property_uri'], 'OntologyObjectPropertyReference', uri=r['property_uri'],
         domain_uri=r['domain_uri'], range_uri=r['range_uri'])
    node(rid, 'BusinessRelationDefinition', name=r['name'], status='metadata_only')
    edge(mid, 'HAS_CONCEPT', cid)
    edge(cid, 'REFERS_TO_CLASS', d['class_uri'])
    # Mirror the declared RDF parent as a reference; perform no PG classification inference.
    edge(d['class_uri'], 'HAS_PARENT_CLASS_REFERENCE', FH + 'Department')
    edge(cid, 'HAS_RELATION_DEFINITION', rid)
    edge(rid, 'REFERS_TO_OBJECT_PROPERTY', r['property_uri'])
    edge(rid, 'HAS_TARGET_CLASS', FH + 'Metric')
    edge(r['property_uri'], 'HAS_DOMAIN_CLASS', FH + 'Department')
    edge(r['property_uri'], 'HAS_RANGE_CLASS', FH + 'Metric')
    for metric_id in sorted(model['metric_ids']):
        edge(cid, 'USES_METRIC', metric_id)
    # Target metric nodes belong to their original modules and are merged by the builder.
    return {'nodes': sorted(nodes.values(), key=lambda n: n['id']),
            'relationships': sorted(edges.values(), key=lambda e: e['id'])}
