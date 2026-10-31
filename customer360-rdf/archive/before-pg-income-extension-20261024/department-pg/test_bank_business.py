"""Reviewed product scopes, SQL fee/interest classification and LUM sources."""
import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from test_product_fees import source_path, workbook_cells
from review_contract_v015 import normalize_reviewed_text

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

    def test_department_usage_does_not_claim_source_ownership_or_change_loan_advisor_scope(self):
        self.assertEqual(self.model['department_context'], {
            'using_department': '私人銀行', 'definition_department': '私人銀行', 'source_data_owner': None})
        graph = business.build_graph(self.model)
        nodes = {n['id']: n for n in graph['nodes']}
        for c in self.concepts.values():
            props = nodes[c['id']]['properties']
            self.assertEqual(props['using_department'], '私人銀行')
            self.assertEqual(props['definition_department'], '私人銀行')
            self.assertEqual(props['department_owner_json'], 'null')
            self.assertEqual(props['subsidiary'], 'bank')
        changed = copy.deepcopy(self.model)
        changed['department_context']['source_data_owner'] = '私人銀行'
        with self.assertRaises(ValueError): business.build_graph(changed)

    def test_original_source_files_are_unchanged_and_id_replacements_are_reviewable(self):
        hashes = json.loads((ROOT / 'archive/before-v0.15.0/source-readonly-sha256.json').read_text(encoding='utf-8'))
        for relative, digest in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest, relative)
        changes = json.loads((HERE / 'history/changes-v0.15.0.json').read_text(encoding='utf-8'))
        self.assertEqual(changes['concept_id_replacements'], {
            'bank.fx_trading_pnl': 'bank.fx_fee_income', 'bank.gold_trading_pnl': 'bank.gold_fee_income'})
        self.assertTrue(set(changes['concept_id_replacements'].values()) <= set(self.concepts))
        self.assertFalse(set(changes['concept_id_replacements']) & set(self.concepts))
        self.assertEqual(changes['retired_concept_ids'], ['securities.stock_pledge_aum'])

    def test_six_products_have_nine_metrics_with_table_only_sources(self):
        private = json.loads(source_path(self.model['evidence']['private_products']).read_text(encoding='utf-8'))
        codes = {n['properties']['productCode'] for n in private['nodes'] if n['kind'] == 'product'}
        expected = {'bank_planned_trust', 'bank_trust_custody', 'bank_fx', 'bank_lc', 'bank_gold', 'loan'}
        self.assertEqual({c['product_code'] for c in self.concepts.values()}, expected)
        self.assertTrue(expected <= codes)
        self.assertEqual(len(self.concepts), 9)
        self.assertEqual(sum(len(c['fields']) for c in self.concepts.values()), 85)
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

    def test_unified_products_and_four_metric_domains_resolve_without_service_references(self):
        for cls in ('PlannedTrustProduct', 'TrustCustodyProduct', 'ForeignExchangeProduct', 'LetterOfCreditProduct', 'GoldProduct', 'LoanProduct'):
            self.assertEqual(set(self.rdf.objects(BANK[cls], RDFS.subClassOf)), {FH.FinancialProduct})
        for uri in (FH.FinancialService, FH.measuresService, FH.feeIncomeFromService,
                    BANK.PlannedTrustService, BANK.TrustCustodyService, BANK.ForeignExchangeService, BANK.LetterOfCreditService):
            self.assertNotIn(uri, set(self.rdf.all_nodes()))
        for prop, domain in ((FH.measuresProduct, FH.AUM), (FH.lumMeasuresProduct, FH.LUM),
                             (FH.feeIncomeFromProduct, FH.FeeIncome), (FH.interestIncomeFromProduct, FH.InterestIncome)):
            self.assertEqual(set(self.rdf.objects(prop, RDFS.domain)), {domain})
            self.assertEqual(set(self.rdf.objects(prop, RDFS.range)), {FH.FinancialProduct})
        for cls, parent in ((FH.AUM, FH.Metric), (FH.LUM, FH.Metric), (FH.FeeIncome, FH.Metric), (FH.InterestIncome, FH.Metric),
                            (BANK.BankLUM, FH.LUM), (BANK.BankInterestIncome, FH.InterestIncome)):
            self.assertEqual(set(self.rdf.objects(cls, RDFS.subClassOf)), {parent})
        for c in self.concepts.values():
            ancestors = set(self.rdf.transitive_objects(URIRef(c['class_uri']), RDFS.subClassOf))
            self.assertIn(FH.Metric, ancestors)
            for f in c['fields']:
                definition = self.model['field_definitions'][f['field']]
                prop, entity = definition['property_uri'], definition['entity_class_uri']
                if prop:
                    applicable = set(self.rdf.transitive_objects(URIRef(entity), RDFS.subClassOf)) if entity else ancestors
                    self.assertIn(self.rdf.value(URIRef(prop), RDFS.domain), applicable)

    def test_sql_classified_fees_interest_lum_and_advisor_scope_are_separate(self):
        relations = {r['id']: r for r in self.model['relation_definitions']}
        fees = {'bank.planned_trust_fee_income', 'bank.trust_custody_fee_income', 'bank.fx_fee_income', 'bank.lc_fee_income', 'bank.gold_fee_income'}
        for cid in fees:
            c = self.concepts[cid]
            self.assertEqual(c['class_uri'], str(BANK.BankFeeIncome))
            self.assertEqual(relations[cid + '.scope']['property_uri'], str(FH.feeIncomeFromProduct))
            self.assertEqual(relations[cid + '.advisor']['property_uri'], str(BANK.attributedToAdvisor))
            self.assertIn('employeeId', {f['field'] for f in c['fields']})
        loan = self.concepts['bank.loan_income']
        self.assertEqual(loan['class_uri'], str(BANK.BankInterestIncome))
        self.assertEqual(relations[loan['id'] + '.scope']['property_uri'], str(FH.interestIncomeFromProduct))
        self.assertNotIn(loan['id'] + '.advisor', relations)
        self.assertFalse(set(business.common.FEE_ELEMENTS) & {f['field'] for f in loan['fields']})
        self.assertIn('毛利', loan['observations']['amount_observation'])
        self.assertIn('聯行息', loan['observations']['amount_observation'])
        lum = self.concepts['bank.loan_lum']
        self.assertEqual(lum['class_uri'], str(BANK.BankLUM))
        self.assertEqual({f['field'] for f in lum['fields']}, {'customerId', 'productId', 'amount', 'currency', 'snapshotDate', 'lumAsOfDate'})
        self.assertEqual(relations[lum['id'] + '.scope']['domain_uri'], str(FH.LUM))
        self.assertEqual(set(self.rdf.objects(FH.lumAsOfDate, RDFS.domain)), {FH.LUM})
        self.assertEqual(set(self.rdf.objects(FH.interestPeriodStart, RDFS.domain)), {FH.InterestIncome})
        self.assertEqual(set(self.rdf.objects(FH.incomePeriodStart, RDFS.domain)), {FH.FeeIncome})
        self.assertIn('累計', self.concepts['bank.planned_trust_fee_income']['observations']['amount_observation'])
        self.assertIn('DCD', ' '.join(self.concepts['bank.fx_fee_income']['observations']['gaps']))
        self.assertFalse(any(c['id'] in {'bank.loan_aum', 'bank.gold_aum', 'bank.fx_aum', 'bank.lc_aum'} for c in self.model['concepts']))
        self.assertEqual(str(self.rdf.value(FH.FeeIncome, RDFS.label)), '手收指標')
        self.assertIn('業務認列口徑', str(self.rdf.value(FH.FeeIncome, SKOS.definition)))
        self.assertIn('不限定為純客戶利息', str(self.rdf.value(FH.InterestIncome, SKOS.definition)))

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
            'loan_income_current': ('DSLON.LN_FN_ACCT', 'INT_INCM - CB_INT_AMT', 'data_dt'),
            'lum_current': ('DSLON.LN_NT_ACCT', 'DSLON.LN_FN_ACCT', 'LN_BAL', 'BAL_AMT'),
            'lum_history': ('DSLON.LN_NT_ACCT_HS', 'DSLON.LN_FN_ACCT_HS', 'YYYYMM'),
            'lum_summary': ('SUM(餘額)', '私人銀行一部', '1886', '應付保證'),
            'lum_roa': ('ROBA', 'LUM', 'ln_amt'),
            'income_scope_summary': ("'手收'", "'FX'", "'黃金'", "'利收'", "'放款'"),
        }.items():
            record = self.model['evidence'][eid]
            start, end = record['lines']
            text = '\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
            for token in tokens:
                self.assertIn(token.upper(), text.upper())

    def test_unrelated_models_and_source_evidence_survive_reviewed_retirement(self):
        before = ROOT / 'archive/before-v0.15.0'
        for name in ('model', 'deposits', 'advisory-income', 'product-fees', 'product-aum', 'investment-metrics'):
            old = json.loads((before / 'department-pg' / (name + '.json')).read_text(encoding='utf-8'))
            current = json.loads((HERE / (name + '.json')).read_text(encoding='utf-8'))
            current['ontology_version'] = old['ontology_version']
            if name == 'investment-metrics':
                old['concepts'] = [c for c in old['concepts'] if c['id'] != 'securities.stock_pledge_aum']
                old['relation_definitions'] = [r for r in old['relation_definitions'] if r['source_concept'] != 'securities.stock_pledge_aum']
                old['sources'] = [v for v in old['sources'] if v['table'] != 'DSCSD.PBCMS_REPORTA03']
                current['pending_scope'] = [v for v in current['pending_scope'] if v['id'] != 'securities.stock_pledge_lum']
            self.assertEqual(old, current)
        retired = {FH.FinancialService, FH.measuresService, FH.feeIncomeFromService,
                   BANK.PlannedTrustService, BANK.TrustCustodyService, BANK.ForeignExchangeService, BANK.LetterOfCreditService}
        for name in ('holding-core.ttl', 'bank-deposit.ttl', 'bank-common.ttl', 'bank-investment-products.ttl', 'securities-common.ttl'):
            old = Graph().parse(before / name, format='turtle')
            current = Graph().parse(ROOT / name, format='turtle')
            for g in (old, current):
                for ontology in list(g.subjects(RDF.type, OWL.Ontology)): g.remove((ontology, None, None))
                normalize_reviewed_text(g)
            for subject in retired: old.remove((subject, None, None))
            subjects = set(old.subjects())
            self.assertEqual(set(old), {t for t in current if t[0] in subjects})
        pending = {p['id'] for p in builder.investment_metrics.load_model()['pending_scope']}
        self.assertEqual(pending, {'securities.taiwan_stock_fee_income', 'bank.collective_account_fee_income', 'securities.stock_pledge_lum'})

    def test_wrong_metric_types_field_mapping_sources_and_execution_are_rejected(self):
        for change in ('fee_type', 'product_as_service', 'column', 'candidate', 'source', 'role', 'sql',
                       'fee_property', 'duplicate_field', 'extra_relation', 'database_verified'):
            changed = copy.deepcopy(self.model)
            c = next(c for c in changed['concepts'] if c['id'] == 'bank.fx_fee_income')
            if change == 'fee_type': c['class_uri'] = str(FH.Metric)
            elif change == 'product_as_service': c['business_scope_kind'] = 'service'
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
