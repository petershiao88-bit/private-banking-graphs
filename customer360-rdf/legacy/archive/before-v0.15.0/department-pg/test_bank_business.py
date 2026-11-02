"""Source-backed service scopes and safe separation of fees, P&L and lending income."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from test_product_fees import source_path, workbook_cells

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC = importlib.util.spec_from_file_location('bank_business_test_builder', HERE / 'build_cypher.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
business = builder.bank_business
FH, BANK = Namespace(builder.FH), Namespace(business.BANK)


class BankBusinessTests(unittest.TestCase):
    def setUp(self):
        self.model = business.load_model()
        self.concepts = {c['id']: c for c in self.model['concepts']}
        self.rdf = Graph().parse(ROOT / 'customer360-ontology.ttl', format='turtle')

    def test_six_existing_business_scopes_are_covered_by_eight_metrics_with_table_only_sources(self):
        private = json.loads(source_path(self.model['evidence']['private_products']).read_text(encoding='utf-8'))
        codes = {n['properties']['productCode'] for n in private['nodes'] if n['kind'] == 'product'}
        expected = {'bank_planned_trust', 'bank_trust_custody', 'bank_fx', 'bank_lc', 'bank_gold', 'loan'}
        self.assertEqual({c['product_code'] for c in self.concepts.values()}, expected)
        self.assertTrue(expected <= codes)
        self.assertEqual(len(self.concepts), 8)
        self.assertEqual(sum(len(c['fields']) for c in self.concepts.values()), 67)
        graph = business.build_graph(self.model)
        edges = {(e['source'], e['type'], e['target']) for e in graph['relationships']}
        for c in self.concepts.values():
            for f in c['fields']:
                self.assertEqual((f['status'], f['table'], f['column'], f['candidates']), ('pending', None, None, []))
            for row in c['table_sources']['tables']:
                self.assertIn((c['id'], 'HAS_SOURCE_TABLE', 'source:' + row['table']), edges)
                self.assertNotIn((c['business_scope_class_uri'], 'HAS_SOURCE_TABLE', 'source:' + row['table']), edges)
            self.assertIn((c['id'], 'HAS_BUSINESS_SCOPE', c['business_scope_class_uri']), edges)
        self.assertFalse(any(e[1] == 'CANDIDATE_SOURCE' for e in edges))
        self.assertTrue(all(v is None for v in self.model['execution'].values()))

    def test_service_classification_and_relation_domains_do_not_turn_services_into_products(self):
        self.assertNotIn(FH.FinancialProduct, set(self.rdf.transitive_objects(FH.FinancialService, RDFS.subClassOf)))
        for cls in ('PlannedTrustService', 'TrustCustodyService', 'ForeignExchangeService', 'LetterOfCreditService'):
            self.assertEqual(set(self.rdf.objects(BANK[cls], RDFS.subClassOf)), {FH.FinancialService})
        for cls in ('GoldProduct', 'LoanProduct'):
            self.assertEqual(set(self.rdf.objects(BANK[cls], RDFS.subClassOf)), {FH.FinancialProduct})
        for prop, domain in ((FH.measuresService, FH.AUM), (FH.feeIncomeFromService, FH.FeeIncome)):
            self.assertEqual(set(self.rdf.objects(prop, RDFS.domain)), {domain})
            self.assertEqual(set(self.rdf.objects(prop, RDFS.range)), {FH.FinancialService})
        for c in self.concepts.values():
            ancestors = set(self.rdf.transitive_objects(URIRef(c['class_uri']), RDFS.subClassOf))
            self.assertIn(FH.Metric, ancestors)
            for f in c['fields']:
                prop = self.model['field_definitions'][f['field']]['property_uri']
                if prop:
                    entity = self.model['field_definitions'][f['field']]['entity_class_uri']
                    applicable = set(self.rdf.transitive_objects(URIRef(entity), RDFS.subClassOf)) if entity else ancestors
                    self.assertIn(self.rdf.value(URIRef(prop), RDFS.domain), applicable)

    def test_pnl_and_lending_are_generic_metrics_without_fee_only_properties_or_advisor_relations(self):
        relations = {r['id'] for r in self.model['relation_definitions']}
        for cid in ('bank.fx_trading_pnl', 'bank.gold_trading_pnl', 'bank.loan_income'):
            c = self.concepts[cid]
            self.assertEqual(c['class_uri'], str(FH.Metric))
            self.assertNotIn(cid + '.advisor', relations)
            self.assertNotIn(cid + '.scope', relations)
            self.assertFalse(set(business.common.FEE_ELEMENTS) & {f['field'] for f in c['fields']})
        self.assertIn('毛利', self.concepts['bank.loan_income']['observations']['amount_observation'])
        self.assertIn('聯行息', self.concepts['bank.loan_income']['observations']['amount_observation'])
        self.assertIn('累計', self.concepts['bank.planned_trust_fee_income']['observations']['amount_observation'])
        self.assertIn('DCD', ' '.join(self.concepts['bank.fx_trading_pnl']['observations']['gaps']))
        self.assertFalse(any(c['id'] in {'bank.loan_aum', 'bank.gold_aum'} for c in self.model['concepts']))

    def test_income_nature_and_scope_are_supported_by_exact_metadata_cells_and_original_sql(self):
        for record in self.model['evidence'].values():
            if 'cells' in record:
                cells = workbook_cells(source_path(record), record['sheet'])
                for cell, value in record['cells'].items():
                    self.assertEqual(cells[cell], value)
        for eid, tokens in {
            'trust_aum': ('AUM_020', 'AUM_021', 'PresentAmt', 'MarketValueTWD'),
            'custody_aum': ('AUM_022', 'PB_PMS_AUM'),
            'trust_fee': ('INCOME_046', 'INCOME_047', '累計', 'SecuritiesBrwFee', 'fee+createfee'),
            'custody_fee': ('INCOME_048', 'sum(FEE)'),
            'fx_pnl': ('INCOME_043', 'INCOME_044', "pcc_code like '2E%'", "not in  ('DCD','Cash Bond')"),
            'lc_fee': ('INCOME_045', 'FEE_END_DATE', 'sysdate', 'FEE_AMT'),
            'gold_pnl': ('INCOME_049', 'PLAMT_TWD'),
            'loan_income': ('INCOME_067', 'GROSS_INCM', 'INT_INCM - CB_INT_AMT', 'UNION ALL'),
            'trust_aum_summary': ('AUM_020', 'AUM_021', 'AUM_022', '規劃型信託', '信託保管'),
            'trust_income_summary': ('INCOME_046', 'INCOME_047', 'INCOME_048', '規劃型信託'),
            'loan_income_summary': ('INCOME_067', '放款', '利收'),
        }.items():
            record = self.model['evidence'][eid]
            start, end = record['lines']
            text = '\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
            for token in tokens:
                self.assertIn(token.upper(), text.upper())

    def test_existing_active_models_and_securities_deferred_scope_are_preserved(self):
        before = ROOT / 'archive/before-v0.14.0'
        for name in ('model', 'deposits', 'advisory-income', 'product-fees', 'product-aum', 'investment-metrics'):
            old = json.loads((before / 'department-pg' / (name + '.json')).read_text(encoding='utf-8'))
            current = json.loads((HERE / (name + '.json')).read_text(encoding='utf-8'))
            current['ontology_version'] = old['ontology_version']
            self.assertEqual(old, current)
        for name in ('holding-core.ttl', 'bank-deposit.ttl', 'bank-common.ttl',
                     'bank-investment-products.ttl', 'securities-common.ttl'):
            old = Graph().parse(before / name, format='turtle')
            current = Graph().parse(ROOT / name, format='turtle')
            for g in (old, current):
                for ontology in list(g.subjects(RDF.type, OWL.Ontology)):
                    g.remove((ontology, None, None))
                g.remove((FH.metricAmount, SKOS.definition, None))
            subjects = set(old.subjects())
            self.assertEqual(set(old), {t for t in current if t[0] in subjects})
        current = builder.investment_metrics.load_model()
        self.assertEqual({p['id'] for p in current['pending_scope']},
                         {'securities.taiwan_stock_fee_income', 'bank.collective_account_fee_income'})

    def test_wrong_metric_types_field_mapping_sources_and_execution_are_rejected(self):
        for change in ('fee_type', 'service_as_product', 'column', 'candidate', 'source', 'role', 'sql',
                       'fee_property', 'duplicate_field', 'extra_relation', 'database_verified'):
            changed = copy.deepcopy(self.model)
            c = next(c for c in changed['concepts'] if c['id'] == 'bank.fx_trading_pnl')
            if change == 'fee_type': c['class_uri'] = str(BANK.BankFeeIncome)
            elif change == 'service_as_product': c['business_scope_kind'] = 'product'
            elif change == 'column': c['fields'][0]['column'] = 'UNAPPROVED'
            elif change == 'candidate': c['fields'][0]['candidates'] = [{'column': 'UNAPPROVED'}]
            elif change == 'source': c['table_sources']['tables'][0]['table'] = 'STAGING.INCOME_044'
            elif change == 'role': c['table_sources']['tables'][0]['role'] = 'date_lookup_only'
            elif change == 'sql': changed['execution']['sql'] = 'SELECT 1'
            elif change == 'fee_property': changed['field_definitions']['incomePeriod']['property_uri'] = str(FH.incomePeriodStart)
            elif change == 'duplicate_field': c['fields'][0] = copy.deepcopy(c['fields'][1])
            elif change == 'extra_relation': changed['relation_definitions'].append(copy.deepcopy(changed['relation_definitions'][0]))
            else: changed['sources'][0]['database_verified'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                business.build_graph(changed)

    def test_projection_is_deterministic_when_new_module_arrays_are_reordered(self):
        changed = copy.deepcopy(self.model)
        changed['concepts'].reverse()
        changed['sources'].reverse()
        changed['relation_definitions'].reverse()
        for c in changed['concepts']:
            c['fields'].reverse()
            c['observations']['evidence'].reverse()
            c['table_sources']['tables'].reverse()
            for row in c['table_sources']['tables']: row['evidence'].reverse()
        for s in changed['sources']: s['evidence'].reverse()
        self.assertEqual(builder.render_combined_cypher(), builder.render_combined_cypher(business_model=changed))


if __name__ == '__main__':
    unittest.main()
