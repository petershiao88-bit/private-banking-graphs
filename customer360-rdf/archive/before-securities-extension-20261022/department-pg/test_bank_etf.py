"""ETF keeps independent classification, table-only lineage and original fund scope."""
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import RDFS
from test_product_fees import source_path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('etf_builder_tests', HERE / 'build_cypher.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BankETFTests(unittest.TestCase):
    def test_etf_directly_inherits_financial_product_and_metrics_keep_table_only_lineage(self):
        bank = Namespace(builder.investment_metrics.BANK)
        fh = Namespace(builder.FH)
        rdf = Graph().parse(HERE.parent / 'customer360-ontology.ttl', format='turtle')
        self.assertEqual(set(rdf.objects(bank.ETFProduct, RDFS.subClassOf)), {fh.FinancialProduct})
        self.assertNotIn(bank.FundProduct, set(rdf.transitive_objects(bank.ETFProduct, RDFS.subClassOf)))
        model = builder.investment_metrics.load_model()
        concepts = {c['id']: c for c in model['concepts']}
        graph = builder.build_combined_graph()
        edges = {(e['source'], e['type'], e['target']) for e in graph['relationships']}
        for kind, count, table, prop in (
            ('aum', 8, 'DSFND.PB_FUND_MONTH', 'measuresProduct'),
            ('fee_income', 11, 'DSFND.PB_FUND_SPREAD_DAILY', 'feeIncomeFromProduct'),
        ):
            cid = 'bank.etf_' + kind
            concept = concepts[cid]
            self.assertEqual(concept['product_class_uris'], [str(bank.ETFProduct)])
            self.assertEqual(concept['product_code'], 'bank_etf')
            self.assertEqual(len(concept['fields']), count)
            for field in concept['fields']:
                self.assertEqual((field['status'], field['table'], field['column'], field['candidates']),
                                 ('pending', None, None, []))
            self.assertIn((cid, 'HAS_SOURCE_TABLE', 'source:' + table), edges)
            self.assertIn((cid + '.product', 'REFERS_TO_OBJECT_PROPERTY', str(fh[prop])), edges)
            self.assertNotIn((str(bank.ETFProduct), 'HAS_SOURCE_TABLE', 'source:' + table), edges)
        self.assertIn(('bank.etf_fee_income.advisor', 'REFERS_TO_OBJECT_PROPERTY', str(bank.attributedToAdvisor)), edges)
        self.assertNotIn('bank.etf', {p['id'] for p in model['pending_scope']})
        self.assertTrue(all(v is None for v in model['execution'].values()))

    def test_shared_source_evidence_does_not_broaden_fund_scope_or_resolve_etf_aum_classification(self):
        model = builder.investment_metrics.load_model()
        concepts = {c['id']: c for c in model['concepts']}
        before = json.loads((HERE.parent / 'archive/before-v0.12.0/department-pg/investment-metrics.json').read_text(encoding='utf-8'))
        for original in before['concepts']:
            self.assertEqual(original, concepts[original['id']])
        aum = concepts['bank.etf_aum']['observations']
        self.assertIn('尚未驗證 ETF 實際分類取值', aum['classification_observation'])
        self.assertIn('不自動合計', aum['valuation_observation'])
        record = model['evidence']['bank_fund_fee']
        start, end = record['lines']
        sql = '\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
        self.assertIn("when TRIM(FHID) ='YB' then 'ETF'", sql)
        self.assertIn('DSFND.PB_FUND_SPREAD_DAILY', sql)
        generic = builder.advisory_income.load_model()['concepts'][1]['table_sources']
        self.assertEqual(generic['status'], 'partial_scope')
        self.assertIn('ETF', generic['coverage'])


if __name__ == '__main__':
    unittest.main()
