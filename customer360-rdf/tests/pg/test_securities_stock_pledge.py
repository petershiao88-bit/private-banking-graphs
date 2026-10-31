"""Pledged-stock estimates remain evidence; active AUM is retired, LUM awaits a balance source."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

from test_product_fees import source_path, workbook_cells

HERE = Path(__file__).resolve().parents[2] / "department-pg"
SPEC = importlib.util.spec_from_file_location('pledge_metric_tests', HERE / 'build_cypher.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class SecuritiesStockPledgeTests(unittest.TestCase):
    def history(self):
        return json.loads((HERE.parent / 'archive/department-pg/history/stock-pledge-aum-retired-v0.15.0.json').read_text(encoding='utf-8'))

    def test_original_estimate_evidence_survives_without_being_reinterpreted_as_a_loan(self):
        history = self.history()
        model = builder.investment_metrics.load_model()
        before = json.loads((HERE.parent / 'archive/before-v0.15.0/department-pg/investment-metrics.json').read_text(encoding='utf-8'))
        old = next(c for c in before['concepts'] if c['id'] == 'securities.stock_pledge_aum')
        self.assertEqual(history['concept'], old)
        self.assertEqual(history['status'], 'retired_not_build_input')
        self.assertEqual(history['relation_definitions'], [r for r in before['relation_definitions'] if r['source_concept'] == old['id']])
        self.assertEqual(history['sources'], [s for s in before['sources'] if s['table'] == 'DSCSD.PBCMS_REPORTA03'])
        self.assertIs(history['sources'][0]['database_verified'], False)
        for eid, record in history['evidence'].items(): self.assertEqual(record, model['evidence'][eid])
        record = history['evidence']['stock_pledge_requirements']
        cells = workbook_cells(source_path(record), record['sheet'])
        self.assertEqual(cells['H28'], '證券_台股_AUM總量')
        self.assertEqual(cells['N28'], '股票設質：庫存股數 * 月底收盤價')
        self.assertEqual(cells['P28'], 'DSCSD.PBCMS_REPORTA03')
        record = history['evidence']['stock_pledge_summary']
        start, end = record['lines']
        text = '\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
        self.assertIn('from AUM_028', text)
        self.assertIn('不視為借款餘額或可融資額', old['observations']['valuation_observation'])

    def test_retired_metric_and_table_edges_are_absent_and_other_securities_metrics_survive(self):
        model = builder.investment_metrics.load_model()
        concepts = {c['id']: c for c in model['concepts']}
        self.assertNotIn('securities.stock_pledge_aum', concepts)
        self.assertNotIn('securities.stock_pledge_lum', concepts)
        self.assertNotIn('DSCSD.PBCMS_REPORTA03', {s['table'] for s in model['sources']})
        graph = builder.build_combined_graph()
        nodes = {n['id'] for n in graph['nodes']}
        self.assertNotIn('securities.stock_pledge_aum', nodes)
        self.assertNotIn('source:DSCSD.PBCMS_REPORTA03', nodes)
        self.assertFalse(any(e['source'].startswith('securities.stock_pledge_aum') for e in graph['relationships']))
        self.assertTrue(all(v is None for v in model['execution'].values()))
        before = json.loads((HERE.parent / 'archive/before-securities-extension-20261022/department-pg/investment-metrics.json').read_text(encoding='utf-8'))
        from review_contract_pg_income import historical_income_concept
        for old in before['concepts']: self.assertEqual(old, historical_income_concept(concepts[old['id']]))
        pending = {p['id']: p for p in model['pending_scope']}
        old_pending = {p['id']: p for p in before['pending_scope']}
        self.assertEqual(pending['securities.taiwan_stock_fee_income'], old_pending['securities.taiwan_stock_fee_income'])
        self.assertEqual(pending['securities.stock_pledge_lum']['status'], 'pending_source_definition')
        self.assertIn('股票估值', pending['securities.stock_pledge_lum']['reason'])
        self.assertIn('securities.taiwan_stock_aum', concepts)

    def test_active_validator_rejects_reinstating_the_retired_aum_or_renaming_its_estimate_as_lum(self):
        for cid in ('securities.stock_pledge_aum', 'securities.stock_pledge_lum'):
            changed = copy.deepcopy(builder.investment_metrics.load_model())
            concept = copy.deepcopy(self.history()['concept'])
            concept['id'] = cid
            changed['concepts'].append(concept)
            with self.subTest(cid=cid), self.assertRaises(ValueError):
                builder.investment_metrics.build_graph(changed)


if __name__ == '__main__':
    unittest.main()
