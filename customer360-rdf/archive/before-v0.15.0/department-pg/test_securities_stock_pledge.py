"""Source requirements resolve pledged-stock valuation, not lending or additive totals."""
import importlib.util
import json
import unittest
from pathlib import Path

from test_product_fees import source_path, workbook_cells

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('pledge_metric_tests',HERE/'build_cypher.py')
builder=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class SecuritiesStockPledgeTests(unittest.TestCase):
    def test_source_requirements_and_summary_support_stock_aum_without_lending_semantics(self):
        model=builder.investment_metrics.load_model()
        c=next(c for c in model['concepts'] if c['id']=='securities.stock_pledge_aum')
        record=model['evidence']['stock_pledge_requirements']
        cells=workbook_cells(source_path(record),record['sheet'])
        self.assertEqual(cells['H28'],'證券_台股_AUM總量')
        self.assertEqual(cells['N28'],'股票設質：庫存股數 * 月底收盤價')
        self.assertEqual(cells['P28'],'DSCSD.PBCMS_REPORTA03')
        record=model['evidence']['stock_pledge_summary']
        start,end=record['lines']
        sql='\n'.join(source_path(record).read_text(encoding=record['encoding']).splitlines()[start-1:end])
        self.assertIn("'證券'",sql)
        self.assertIn("'台股'",sql)
        self.assertIn('from AUM_028',sql)
        self.assertEqual(c['class_uri'],builder.investment_metrics.SEC+'SecuritiesAUM')
        self.assertEqual(c['product_class_uris'],[builder.investment_metrics.SEC+'StockProduct'])
        self.assertIn('不視為借款餘額或可融資額',c['observations']['valuation_observation'])
        self.assertIn('自動加總或去重規則',c['observations']['valuation_observation'])
        self.assertIn('APPLYDATE',c['observations']['date_observation'])

    def test_new_lineage_is_table_only_and_old_stock_metrics_and_domestic_fee_deferral_survive(self):
        model=builder.investment_metrics.load_model()
        concepts={c['id']:c for c in model['concepts']}
        c=concepts['securities.stock_pledge_aum']
        self.assertEqual(len(c['fields']),8)
        for f in c['fields']:
            self.assertEqual((f['status'],f['table'],f['column'],f['candidates']),('pending',None,None,[]))
        graph=builder.build_combined_graph()
        edges={(e['source'],e['type'],e['target']) for e in graph['relationships']}
        self.assertIn((c['id'],'HAS_SOURCE_TABLE','source:DSCSD.PBCMS_REPORTA03'),edges)
        self.assertIn((c['id']+'.product','REFERS_TO_OBJECT_PROPERTY',builder.FH+'measuresProduct'),edges)
        source=next(s for s in model['sources'] if s['table']=='DSCSD.PBCMS_REPORTA03')
        self.assertIs(source['database_verified'],False)
        self.assertTrue(all(v is None for v in model['execution'].values()))
        before=json.loads((HERE.parent/'archive/before-securities-extension-20261022/department-pg/investment-metrics.json').read_text(encoding='utf-8'))
        for old in before['concepts']:
            self.assertEqual(old,concepts[old['id']])
        pending={p['id']:p for p in model['pending_scope']}
        old_pending={p['id']:p for p in before['pending_scope']}
        self.assertNotIn('securities.stock_pledge',pending)
        self.assertEqual(pending['securities.taiwan_stock_fee_income'],old_pending['securities.taiwan_stock_fee_income'])
        self.assertNotIn('securities.taiwan_stock_fee_income',concepts)


if __name__=='__main__':
    unittest.main()
