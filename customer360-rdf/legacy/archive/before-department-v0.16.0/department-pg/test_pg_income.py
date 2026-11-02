"""Approved SQL dictionary expansion: source behavior, preservation and no execution."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

from test_bank_business import builder
from test_product_fees import source_path, workbook_cells
from review_contract_pg_income import historical_income_model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BEFORE = ROOT / 'archive/before-pg-income-extension-20261024'
NEW = {'bank.deposit_interest_income', 'bank.overseas_bond_trust_fee_income',
       'bank.overseas_bond_proprietary_fee_income'}


def observed(model, eid):
    r = model['evidence'][eid]
    start, end = r['lines']
    return '\n'.join(source_path(r).read_text(encoding=r['encoding']).splitlines()[start-1:end]).upper()


class PGIncomeTests(unittest.TestCase):
    def test_only_approved_concepts_and_metadata_change_and_all_rdf_bytes_stay_identical(self):
        for file in ('holding-core.ttl', 'bank-deposit.ttl', 'bank-common.ttl',
                     'bank-investment-products.ttl', 'securities-common.ttl',
                     'customer360-ontology.ttl', 'customer360-ontology.owl', 'build-config.json', 'catalog-v001.xml'):
            self.assertEqual((ROOT / file).read_bytes(), (BEFORE / file).read_bytes(), file)
        for name in ('model', 'deposits', 'advisory-income', 'product-aum'):
            self.assertEqual((HERE / (name+'.json')).read_bytes(), (BEFORE / 'department-pg' / (name+'.json')).read_bytes())
        for name in ('product-fees', 'investment-metrics'):
            current = json.loads((HERE / (name+'.json')).read_text(encoding='utf-8'))
            old = json.loads((BEFORE / 'department-pg' / (name+'.json')).read_text(encoding='utf-8'))
            self.assertEqual(historical_income_model(current), old)
            by_id = {c['id']: c for c in current['concepts']}
            for c in old['concepts']:
                self.assertEqual(c['fields'], by_id[c['id']]['fields'])
        business = builder.bank_business.load_model()
        old = json.loads((BEFORE / 'department-pg/bank-business-metrics.json').read_text(encoding='utf-8'))
        self.assertEqual({c['id'] for c in business['concepts']} - {c['id'] for c in old['concepts']}, NEW)
        for key in ('concepts','sources','relation_definitions'):
            index = 'table' if key == 'sources' else 'id'
            current = {c[index]: c for c in business[key]}
            for item in old[key]: self.assertEqual(item, current[item[index]])
        for eid, record in old['evidence'].items(): self.assertEqual(record, business['evidence'][eid])
        products=json.loads(source_path(business['evidence']['private_products']).read_text(encoding='utf-8'))
        codes={n['properties']['productCode'] for n in products['nodes'] if n['kind']=='product'}
        for c in business['concepts']:
            self.assertIn(c['product_code'],codes)

    def test_deposit_interest_preserves_actual_current_history_and_monthly_scope_differences(self):
        model = builder.bank_business.load_model()
        c = next(c for c in model['concepts'] if c['id']=='bank.deposit_interest_income')
        self.assertEqual(c['class_uri'], builder.bank_business.BANK+'BankInterestIncome')
        self.assertEqual(c['business_scope_class_uri'], builder.bank_business.BANK+'DepositProduct')
        self.assertEqual({r['table'] for r in c['table_sources']['tables']}, {
            'DSDEP.DEP_NT_ACCT_HS','DSDEP.DEP_FN_ACCT_HS','DSDEP.EMP_DEP_NT_ACCT_HS','DSDEP.DEP_FN_ACCT'})
        h, cur, month = [observed(model,e) for e in ('deposit_income_history','deposit_income_current','deposit_income_monthly')]
        for token in ('GROSS_INCM', "YYYYMM>'202505'", 'PRFT_CNTR_CD', 'UNION ALL'): self.assertIn(token,h)
        self.assertIn('DSDEP.DEP_FN_ACCT@',cur)
        self.assertNotIn('FROM DSDEP.DEP_NT_ACCT@',cur)
        self.assertIn('INCOME_066_TMP01',cur)
        self.assertIn('GROSS_INCM',observed(model,'deposit_income_monthly_job'))
        self.assertIn('UNION',month)
        self.assertNotIn('UNION ALL',month)
        self.assertNotIn('WHERE TRIM(PRFT_CNTR_CD)',month)  # Ignore commented SELECT examples.
        self.assertIn('SYSDATE',month)
        self.assertIn("'利收'",observed(model,'deposit_income_summary'))
        relations={r['id']:r for r in model['relation_definitions']}
        self.assertNotIn(c['id']+'.advisor',relations)
        self.assertNotIn('employeeId',{f['field'] for f in c['fields']})

    def test_bond_income_preserves_components_absolute_value_and_existing_product_scope(self):
        model=builder.bank_business.load_model()
        trust=observed(model,'bond_trust_income')
        own=observed(model,'bond_proprietary_income')
        for token in ('BRHREBATEAMT+(WKR028/100)',"FHID='CB'","LIKE '%2E%'"): self.assertIn(token,trust)
        for token in ('SUM(ABS(INC_AMT_NT))','DSWTR.BOND_TXN',"LIKE '2E%'"): self.assertIn(token,own)
        self.assertIn("'手收'",observed(model,'bond_income_summary'))
        graph=builder.bank_business.build_graph(model)
        edges={(e['source'],e['type'],e['target']) for e in graph['relationships']}
        for cid in NEW-{'bank.deposit_interest_income'}:
            c=next(c for c in model['concepts'] if c['id']==cid)
            self.assertEqual(set(c['product_class_uris']),{builder.bank_business.BANK+p for p in ('BondProduct','OverseasFinancialProduct')})
            for uri in c['product_class_uris']:
                self.assertIn((cid,'HAS_BUSINESS_SCOPE',uri),edges)
                self.assertIn((cid+'.scope','HAS_TARGET_CLASS',uri),edges)
            self.assertIn((cid+'.advisor','REFERS_TO_OBJECT_PROPERTY',builder.bank_business.BANK+'attributedToAdvisor'),edges)

    def test_dci_tmu_and_fx_keep_distinct_sql_product_branches(self):
        fees=builder.product_fees.load_model()
        c=next(c for c in fees['concepts'] if c['id']=='bank.dci_fee_income')
        self.assertEqual(c['name'],'銀行 DCI 手收')
        self.assertEqual({t['table'] for t in c['table_sources']['tables']}, {
            'DSDEP.DCI_PERFO_RPT','DSDEP.DCI_PERFO_RPT_HS','DSTAS.FO108_W'})
        text=observed(fees,'sql_dci_tmu')
        self.assertIn("TRIM(PRODUCT)='DCD'",text)
        self.assertIn('SUM(TMUPROFIT)',text)
        self.assertIn('INCOME_037',observed(fees,'sql_dci_summary'))
        self.assertIn('INCOME_038',observed(fees,'sql_dci_summary'))
        self.assertIn("NOT IN  ('DCD','CASH BOND')",observed(builder.bank_business.load_model(),'fx_pnl'))
        graph=builder.build_combined_graph()
        self.assertEqual(sum(n['id']=='source:DSTAS.FO108_W' for n in graph['nodes']),1)

    def test_insurance_monthly_sources_keep_contribution_meaning_date_shift_and_union_observation(self):
        model=builder.investment_metrics.load_model()
        c=next(c for c in model['concepts'] if c['id']=='bank.insurance_fee_income')
        self.assertEqual(c['name'],'銀行保險手收')
        text=observed(model,'insurance_contribution_sql')
        for token in ('SUM(PS)','ADD_MONTHS','PS IS NOT NULL',"OPEN_ACCOUNT='Y'"): self.assertIn(token,text)
        for eid in ('insurance_contribution_iu_metadata','insurance_contribution_ofi_metadata'):
            r=model['evidence'][eid]
            cells=workbook_cells(source_path(r),r['sheet'])
            for cell,expected in r['cells'].items(): self.assertEqual(cells[cell],expected)
        summary=observed(model,'insurance_income_summary')
        for token in ('INCOME_028','INCOME_029','INCOME_030','UNION',"'手收'"): self.assertIn(token,summary)
        self.assertIn('客戶貢獻度',c['observations']['valuation_observation'])
        self.assertTrue(any('重疊' in s and '去重' in s for s in c['observations']['gaps']))

    def test_new_fields_stay_empty_and_wrong_class_sources_qualifiers_or_execution_are_rejected(self):
        model=builder.bank_business.load_model()
        for c in model['concepts']:
            if c['id'] in NEW:
                for f in c['fields']:
                    self.assertEqual((f['status'],f['table'],f['column'],f['candidates']),('pending',None,None,[]))
        for change in ('class','table','qualifier','mapping','execution'):
            altered=copy.deepcopy(model)
            c=next(c for c in altered['concepts'] if c['id']=='bank.overseas_bond_trust_fee_income')
            if change=='class': c['class_uri']=builder.bank_business.BANK+'BankAUM'
            elif change=='table': c['table_sources']['tables'][0]['table']='DSWTR.BOND_POS_DAY'
            elif change=='qualifier': c['product_class_uris']=[builder.bank_business.BANK+'BondProduct']
            elif change=='mapping': c['fields'][0]['column']='UNAPPROVED'
            else: altered['execution']['sql']='SELECT 1'
            with self.subTest(change=change),self.assertRaises(ValueError): builder.bank_business.build_graph(altered)
        for m in (model,builder.product_fees.load_model(),builder.investment_metrics.load_model()):
            self.assertTrue(all(v is None for v in m['execution'].values()))

    def test_review_evidence_hashes_sources_and_new_scope_determinism(self):
        review=json.loads((HERE/'history/pg-income-extension-20261024.json').read_text(encoding='utf-8'))
        self.assertEqual(set(review['new_concepts']),NEW)
        self.assertFalse(review['rdf_changed'])
        for r in review['source_evidence'].values():
            self.assertEqual(hashlib.sha256(source_path(r).read_bytes()).hexdigest(),r['sha256'])
        hashes=json.loads((BEFORE/'source-readonly-sha256.json').read_text(encoding='utf-8'))
        self.assertEqual(len(hashes),24)
        for rel,digest in hashes.items(): self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest)
        m=builder.bank_business.load_model()
        for c in m['concepts']:
            if 'product_class_uris' in c: c['product_class_uris'].reverse()
        self.assertEqual(builder.render_combined_cypher(),builder.render_combined_cypher(business_model=m))


if __name__=='__main__': unittest.main()
