"""Build a reviewed-direction trial graph from the two existing dictionaries.

External node properties are read-only. Scoped relationships also connect
existing submetrics to their parents in the user-confirmed direction.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS = 'pb_shared'
ROOTS = {'aum': 'aum:metric:aum_total_month_end',
         'income': 'income:metric:income_total_customer_month'}


def build():
    aum = json.loads((HERE / 'AUM_business_dictionary.json').read_text(encoding='utf-8'))
    income = json.loads((HERE / 'Income_business_dictionary.json').read_text(encoding='utf-8'))
    ap = {p['code']: p for p in aum['products']}
    ip = {p['code']: p for p in income['products']}
    specs = [
        ('deposit', '存款', ['deposit_twd', 'deposit_foreign', 'deposit_structured'], 'deposit_interest', None,
         "TYP='存款'", 'aggregate_scope', 'AUM保留台幣、外幣、結構型子分類；Income僅映射到存款總類。月更新SQL含台幣、外幣及員工台幣存款，未依產品代碼拆分；不可把總利收重複分配到各子類。'),
        ('bank_insurance', '銀行保險', ['insurance'], 'bank_insurance', None,
         "PROD='保險'", 'overlap_unresolved', 'AUM衡量原始投資金額；Income保留028、029、030三條来源。日檔及月檔重疊尚未證實，概念共用不代表可消除重複計入。'),
        ('bank_fund', '銀行基金', ['bank_trust_products'], 'bank_fund', None,
         "PROD='基金'", 'inferred', '由AUM銀行信託產品分類拆出；Income以FH_TYP基金分類。'),
        ('bank_etf', '銀行ETF', ['bank_trust_products'], 'bank_etf', None,
         "PROD='ETF'", 'inferred', '由AUM銀行信託產品分類拆出；Income以FH_TYP ETF分類。'),
        ('bank_overseas_stock', '銀行海外股票', ['bank_trust_products'], 'bank_overseas_stock', None,
         "PROD='海外股票'", 'inferred', '保留銀行通路，與證券複委託股票分開。'),
        ('bank_bond_trust', '海外債券（信託）', ['bank_trust_products'], 'bank_bond_trust', None,
         "PROD='海外債券(信託)'", 'inferred', '信託持有市值與信託收入來源共用概念。'),
        ('bank_bond_proprietary', '海外債券（自營）', ['bank_overseas_bond'], 'bank_bond_proprietary', None,
         "PROD='海外債券(自營)'", 'inferred', 'AUM海外債券自營與Income外國債券自營的對應為推論；Income保留ABS規則。'),
        ('bank_collective_account', '集合管理帳戶', ['bank_trust_products'], 'bank_collective_account', None,
         "PROD='集合管理帳戶'", 'metadata_sql_conflict', 'Income CASE先將TA/TB/TD/TE歸為基金，集合分類不可達；Income連線表示定義待確認，不表示獨立收入已計入。'),
        ('bank_structured_offshore', '銀行境外結構型商品', ['bank_trust_products'], 'bank_structured_offshore', None,
         "PROD='境外結構型商品'", 'inferred', '境內結構型、DCI及結構型存款均不併入此概念。'),
        ('bank_planned_trust', '規劃型信託', ['bank_planned_trust'], 'bank_planned_trust', ['INCOME_046', 'INCOME_047'],
         "PROD='規劃型信託'", 'inferred', 'Income舊分類含保管；此共用概念只連046、047，保管048另立概念。'),
        ('bank_trust_custody', '信託保管', ['bank_trust_custody'], 'bank_planned_trust', ['INCOME_048'],
         "PROD='信託保管'", 'inferred', '按DSPMS.PB_PMS_AUM的AUM與FEE拆出；Income的SUB_TYPE仍保留現行規劃型信託分類。'),
        ('securities_bond', '證券複委託債券', ['securities_bond'], 'securities_bond', None,
         "PROD='複委託債券'", 'inferred', '證券通路：部位估值與交易手續費共用概念。'),
        ('securities_structured', '證券複委託結構型商品', ['securities_structured'], 'securities_structured', None,
         "PROD='複委託結構型商品'", 'inferred', 'AUM以BOND的TSSN前綴區分，Income以FLG分類。'),
        ('securities_fund', '證券複委託基金', ['securities_fund'], 'securities_fund', None,
         "PROD='基金' AND COMP='證券'", 'inferred', '與銀行基金分開，保留證券持有及交易費來源。'),
        ('securities_foreign_stock', '證券複委託外國股票', ['securities_foreign_stock'], 'securities_foreign_stock', None,
         "PROD='外國股票' AND COMP='證券'", 'inferred', 'Income為CFEE減ABFEE乘匯率，保留可能負值。'),
    ]
    dictionary = {'id': NS, 'version': '0.2-with-hierarchy', 'directionStatus': 'user_confirmed',
                  'direction': '共用產品 -> 分類AUM -> 總AUM；共用產品 -> 分類Income -> 總Income',
                  'scope': '15個共用概念的試作；單側產品仍留在原圖。連線為業務映射，不執行金額計算。',
                  'status': 'inferred_business_dictionary', 'products': [],
                  'sourceFiles': ['ontology/AUM Ontology.json', 'ontology/Income Ontology.json',
                                  'ontology/AUM_business_dictionary.json', 'ontology/Income_business_dictionary.json',
                                  'sources/sql/1.AUM_DETAIL.sql', 'sources/sql/8.INCOME_DETAIL.sql',
                                  'sources/sql/9.INCOME_SMY.sql', 'sources/sql/X-INCOME_MOTHLY.sql',
                                  'sources/metadata/AUM_20250516.xlsx', 'sources/metadata/收入_20250527.xlsx']}
    plan = {'ontologyId': NS, 'version': 'external-reference-v1', 'nodes': [], 'externalReferences': [], 'relationships': []}
    refs = {}

    def reference(key, label):
        refs[key] = {'key': key, 'label': label}

    def relation(source, target, kind, **props):
        plan['relationships'].append({'source': source, 'target': target, 'type': kind,
                                     'properties': {'ontologyId': NS, 'origin': 'shared_product_trial', **props}})

    for root in ROOTS.values():
        reference(root, 'BusinessMetric')
    hierarchy = {
        'aum': [('aum_deposit_month_end', 'aum_total_month_end'),
                ('aum_investment_month_end', 'aum_total_month_end'),
                ('aum_bank_investment_month_end', 'aum_investment_month_end'),
                ('aum_securities_month_end', 'aum_investment_month_end'),
                ('aum_insurance_month_end', 'aum_bank_investment_month_end')],
        'income': [('interest_income', 'income_total_customer_month'),
                   ('fee_income', 'income_total_customer_month'),
                   ('securities_fee_income', 'fee_income'),
                   ('bank_fee_income', 'fee_income'),
                   ('loan_interest_income', 'interest_income'),
                   ('deposit_interest_income', 'interest_income')],
    }
    dictionary['metricHierarchy'] = hierarchy
    for side, pairs in hierarchy.items():
        for child, parent in pairs:
            source, target = f'{side}:metric:{child}', f'{side}:metric:{parent}'
            reference(source, 'BusinessMetric')
            reference(target, 'BusinessMetric')
            relation(source, target, f'{side.upper()}_ROLLS_UP_TO', name='歸入上層指標',
                     status='inferred', evidence='既有HAS_COMPONENT分類層級；以子指標指向父指標表示')
    for order, (code, name, acodes, icode, istages, afilter, status, note) in enumerate(specs, 1):
        aproducts, iproduct = [ap[c] for c in acodes], ip[icode]
        astages = sorted({s for p in aproducts for s in p['stages']})
        istages = istages or iproduct['stages']
        actual = iproduct['includedByCurrentSql']
        key = f'{NS}:product:{code}'
        ametrics = {p['parentMetric'] for p in aproducts}
        assert len(ametrics) == 1
        akey = f"aum:metric:{next(iter(ametrics))}"
        ikey = f"income:metric:{iproduct['parentMetric']}"
        reference(akey, 'BusinessMetric')
        reference(ikey, 'BusinessMetric')
        p = {'code': code, 'name': name, 'key': key, 'definition': note, 'status': status,
             'mappingStatus': 'inferred', 'aumMetricKey': akey, 'incomeMetricKey': ikey,
             'aumLegacyProducts': acodes, 'incomeLegacyProducts': [icode],
             'aumStages': astages, 'incomeStages': istages, 'aumFilter': afilter,
             'incomeFilter': iproduct.get('stageFilter', iproduct['classification']),
             'incomeMappingActive': actual,
             'aumValuationBasis': '; '.join(sorted({p.get('valuationBasis', 'balance') for p in aproducts})),
             'incomeAmountBasis': ('保管FEE' if code == 'bank_trust_custody' else
                                   '借券、管理、成立費；Fee+CreateFee' if code == 'bank_planned_trust' else iproduct['amountBasis'])}
        dictionary['products'].append(p)
        plan['nodes'].append({'key': key, 'labels': ['ProductCategory', 'SharedProduct'],
                              'properties': {**p, 'ontologyId': NS, 'role': 'shared_product',
                                             'displayOrder': order, 'directionStatus': 'user_confirmed'}})
        relation(key, akey, 'MEASURED_BY_AUM', status='inferred', scope=afilter,
                 rootDefinitionStatus='draft_metric_query', name='資產衡量')
        relation(key, ikey, 'MEASURED_BY_INCOME' if actual else 'INCOME_DEFINITION_PENDING',
                 status='inferred' if actual else 'metadata_sql_conflict',
                 name='收入衡量' if actual else '收入定義待確認', note=note)
        for side, stages in [('aum', astages), ('income', istages)]:
            for stage in stages:
                target = f'{side}:stage:{stage}'
                reference(target, 'StagingOutput')
                kind = f'{side.upper()}_IMPLEMENTED_BY'
                if side == 'income' and not actual:
                    kind = 'INCOME_DECLARED_BY'
                relation(key, target, kind, status='observed_in_sql' if actual or side == 'aum' else 'metadata_sql_conflict',
                         scope=afilter if side == 'aum' else p['incomeFilter'],
                         note=note)
    plan['externalReferences'] = list(refs.values())
    for name, data in [('Shared_product_business_dictionary.json', dictionary), ('Shared_product_graph_plan.json', plan)]:
        (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'products': len(plan['nodes']), 'relationships': len(plan['relationships']),
                      'externalReferences': len(refs)}))


if __name__ == '__main__':
    build()
