"""Collective-management AUM uses a product reference; fee semantics stay deferred."""
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS
from test_product_fees import source_path
from review_contract_pg_income import historical_income_concept

HERE = Path(__file__).resolve().parents[2] / "department-pg"
SPEC = importlib.util.spec_from_file_location('collective_builder_tests', HERE / 'build_cypher.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CollectiveManagementTests(unittest.TestCase):
    def test_collective_product_and_aum_have_table_only_lineage_without_account_instances(self):
        model = builder.investment_metrics.load_model()
        c = next(c for c in model['concepts'] if c['id'] == 'bank.collective_account_aum')
        bank, fh = Namespace(builder.investment_metrics.BANK), Namespace(builder.FH)
        rdf = Graph().parse(HERE.parent / 'customer360-ontology.ttl', format='turtle')
        self.assertEqual(set(rdf.objects(bank.CollectiveManagementProduct, RDFS.subClassOf)), {fh.FinancialProduct})
        for parent in (bank.FundProduct, bank.ETFProduct, bank.DepositProduct):
            self.assertNotIn(parent, set(rdf.transitive_objects(bank.CollectiveManagementProduct, RDFS.subClassOf)))
        self.assertNotIn(bank.Account, set(rdf.subjects(RDF.type, OWL.Class)))
        self.assertEqual(c['class_uri'], str(bank.BankAUM))
        self.assertEqual(c['product_class_uris'], [str(bank.CollectiveManagementProduct)])
        self.assertEqual(c['product_code'], 'bank_collective_account')
        self.assertEqual(len(c['fields']), 8)
        for f in c['fields']:
            self.assertEqual((f['status'], f['table'], f['column'], f['candidates']), ('pending', None, None, []))
        graph = builder.build_combined_graph()
        edges = {(e['source'], e['type'], e['target']) for e in graph['relationships']}
        self.assertIn((c['id'], 'HAS_SOURCE_TABLE', 'source:DSFND.PB_FUND_MONTH'), edges)
        self.assertIn((c['id']+'.product', 'REFERS_TO_OBJECT_PROPERTY', str(fh.measuresProduct)), edges)
        self.assertNotIn((str(bank.CollectiveManagementProduct), 'HAS_SOURCE_TABLE', 'source:DSFND.PB_FUND_MONTH'), edges)
        self.assertTrue(all(v is None for v in model['execution'].values()))

    def test_fee_is_deferred_with_original_case_order_and_previous_concepts_preserved(self):
        model = builder.investment_metrics.load_model()
        concepts = {c['id']: c for c in model['concepts']}
        before = json.loads((HERE.parent/'archive/before-v0.13.0/department-pg/investment-metrics.json').read_text(encoding='utf-8'))
        for c in before['concepts']:
            self.assertEqual(c, historical_income_concept(concepts[c['id']]))
        pending = next(p for p in model['pending_scope'] if p['id']=='bank.collective_account_fee_income')
        self.assertEqual(pending['status'], 'pending_business_semantics')
        self.assertNotIn(pending['id'], concepts)
        self.assertFalse(any(r['source_concept']==pending['id'] for r in model['relation_definitions']))
        for eid, expected in [('bank_fund_aum', "when trustprd ='集合' then '集合管理帳戶'"),
                              ('bank_fund_fee', "then '集合管理帳戶'")]:
            record=model['evidence'][eid]
            start,end=record['lines']
            text='\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
            self.assertIn(expected,text)
            if eid=='bank_fund_fee':
                self.assertLess(text.index("when FHID not in ('PS','CB','YB','SN')"), text.index("when FHID like 'TA%'"))
        private=json.loads(source_path(model['evidence']['private_products']).read_text(encoding='utf-8'))
        products=[]
        def collect(value):
            if isinstance(value,dict):
                if value.get('productCode')=='bank_collective_account' and 'definition' in value:
                    products.append(value)
                for item in value.values(): collect(item)
            elif isinstance(value,list):
                for item in value: collect(item)
        collect(private)
        self.assertEqual(len(products),1)
        self.assertEqual(products[0]['incomeDefinition'],'')


if __name__ == '__main__':
    unittest.main()
