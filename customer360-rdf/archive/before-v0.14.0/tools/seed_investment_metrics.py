"""One-time v0.9 candidate catalog from inspected private-banking files; no SQL execution."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'department-pg/investment-metrics.json'
FH = 'https://example.org/ontology/holding#'
BANK = 'https://example.org/ontology/bank#'
SEC = 'https://example.org/ontology/securities#'
SQL = 'Ontology/私銀智能問答/sources/sql/'
META = 'Ontology/私銀智能問答/sources/metadata/'


def make_model():
    prior_aum = json.loads((ROOT / 'department-pg/product-aum.json').read_text(encoding='utf-8'))
    prior_fees = json.loads((ROOT / 'department-pg/product-fees.json').read_text(encoding='utf-8'))
    advisory = json.loads((ROOT / 'department-pg/advisory-income.json').read_text(encoding='utf-8'))
    evidence = {}
    for eid, filename, lines in [
        ('bank_fund_aum', '1.AUM_DETAIL.sql', [211, 230]),
        ('bank_fund_fee', '8.INCOME_DETAIL.sql', [62, 88]),
        ('sec_bond_aum', '1.AUM_DETAIL.sql', [316, 361]),
        ('sec_fund_aum', '1.AUM_DETAIL.sql', [364, 375]),
        ('sec_stock_aum', '1.AUM_DETAIL.sql', [376, 416]),
        ('sec_taiwan_aum', '1.AUM_DETAIL.sql', [418, 431]),
        ('stock_pledge_pending', '1.AUM_DETAIL.sql', [432, 438]),
        ('sec_bond_fee', '8.INCOME_DETAIL.sql', [329, 386]),
        ('sec_fund_fee', '8.INCOME_DETAIL.sql', [387, 427]),
        ('sec_stock_fee', '8.INCOME_DETAIL.sql', [429, 496]),
    ]:
        evidence[eid] = {'file': SQL + filename, 'lines': lines, 'encoding': 'cp950'}
    evidence['private_products'] = {
        'file': 'Ontology/私銀智能問答/ontology/independent_concepts/concept_graph.json',
        'selector': 'nodes with productCode', 'encoding': 'utf-8'}
    for eid, filename, sheet, cells in [
        ('meta_bank_fund', 'AUM_metadata.xlsx', 'DSFND.PB_FUND_MONTH',
         {'B8':'CURRENTTWDVALUE','E8':'台幣餘額','B12':'EXEDATE','E12':'執行日',
          'B19':'IDNO','E19':'客戶ID','B26':'TRUSTPRD','E26':'產品類別'}),
        ('meta_sec_fund_identity', 'AUM_metadata.xlsx', 'DSPBM.PB_FUNDPOSIT_SEC',
         {'B4':'WKB02','E4':'投資人帳號','B25':'WKB24','E25':'客戶身分證字號',
          'B24':'WKB23','E24':'收盤價','B29':'WKB28','E29':'基金單位數','B32':'WKB31','E32':'匯率'}),
        ('meta_sec_fund_fee', '收入_metadata.xlsx', 'DSPBM.PB_FUNDTRADM_SEC_M',
         {'B4':'WKA02','E4':'交易日期','B28':'WKA28','E28':'身分證字號',
          'B31':'WKA31','E31':'總手續費(台？)'}),
        ('meta_sec_stock_fee', '收入_metadata.xlsx', 'DSPBM.PB_STOCKTRADM_AM_SEC_M',
         {'B2':'ABFEE','E2':'上手手續費','B9':'CFEE','E9':'客戶手續費',
          'B10':'CLRDATE','E10':'結算日期','B18':'FXRATE','E18':'匯率','B19':'IDNO','E19':'身分證字號'}),
        ('meta_sec_taiwan', 'AUM_metadata.xlsx', 'DSPBM.PB_YTRMRBP_SEC',
         {'B5':'YTRMRB025','E5':'身分證號','B14':'YTRMRB110','E14':'集保庫存=目前庫存',
          'B18':'YTRMRB150','E18':'收盤價'}),
    ]:
        evidence[eid] = {'file': META + filename, 'sheet': sheet, 'cells': cells}
    model = {
        'schema_version':'1.0.0', 'ontology_version':'0.9.0', 'status':'active',
        'scope':'metadata_only', 'inference':False, 'instance_mapping':False,
        'access_policy_status':'deferred_by_user',
        'field_definitions':copy.deepcopy(advisory['field_definitions']),
        'execution':{k:None for k in (
            'sql','join_rules','filter_rules','aggregation_rules','row_grain',
            'valuation_rules','snapshot_selection','currency_conversion','deduplication_rules',
            'aum_recognition_rules','fee_recognition_rules','attribution_rules','period_basis')},
        'evidence':evidence, 'sources':[], 'concepts':[], 'relation_definitions':[],
        'pending_scope':[
            {'id':'securities.taiwan_stock_fee_income', 'status':'pending_source_definition',
             'reason':'原產品收入定義空白，提供的 SQL 未見台股手收分支；不推論現實業務沒有手收。',
             'evidence':['private_products']},
            {'id':'securities.stock_pledge', 'status':'pending_business_semantics',
             'reason':'原 SQL 有股票設質 Qty × Product_Price；尚不能定義為投資 AUM、貸款餘額或可融資金額，未建立 AUM 概念。',
             'evidence':['stock_pledge_pending']},
            {'id':'bank.etf', 'status':'outside_this_increment',
             'reason':'私銀將基金、ETF 分列；本輪基金不自動含 ETF，尚未新增 ETF 的 RDF 或 PG。',
             'evidence':['private_products','bank_fund_fee']},
        ]}
    model['field_definitions']['amount']['definition'] = '依所屬指標認列口徑形成的金額；估值組成欄位只是輸入，尚非核定 AUM 或手收。'
    sources = {}
    reused = {s['table']: s for m in (prior_aum, prior_fees) for s in m['sources']}

    def add_source(table, eid):
        if table not in sources:
            sources[table] = copy.deepcopy(reused.get(table, {
                'table':table, 'status':'observed_in_files', 'database_verified':False, 'evidence':[]}))
        if table not in reused and eid not in sources[table]['evidence']:
            sources[table]['evidence'].append(eid)

    def concept(cid, name, metric, product_code, products, inputs, eid, valuation, dates,
                classification, gaps, extra=()):
        subsidiary = cid.split('.')[0]
        ns = BANK if subsidiary == 'bank' else SEC
        fields = ['customerId','productId','amount','currency','snapshotDate']
        if metric == 'fee_income':
            fields.append('incomePeriod')
            if subsidiary == 'bank': fields.append('employeeId')
        mappings = []
        for field in fields:
            candidates = []
            for table, column, meaning in inputs.get(field, []):
                add_source(table,eid)
                refs = (['metadata_offshore'] if field == 'employeeId' or (field == 'productId' and subsidiary == 'bank')
                        else ['meta_sec_fund_identity'] if column == 'WKB24' else [eid])
                candidates.append({'table':table,'column':column,'meaning':meaning,'evidence':refs})
            status = {'amount':'pending_aum_recognition' if metric == 'aum' else 'pending_fee_recognition',
                      'customerId':'pending_identity_review','productId':'pending_product_identity',
                      'currency':'pending_currency','snapshotDate':'pending_time_semantics',
                      'incomePeriod':'pending_period_basis','employeeId':'pending_advisor_attribution'}[field]
            mappings.append({'field':field,'status':status,'table':None,'column':None,'candidates':candidates})
        c = {'id':cid, 'name':name, 'definition':name + '；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。',
             'subsidiary':subsidiary,'department_owner':None,
             'class_uri':ns + ('Bank' if subsidiary == 'bank' else 'Securities') + ('AUM' if metric == 'aum' else 'FeeIncome'),
             'specific_product_class_uri':None, 'product_class_uris':[ns+p for p in products],
             'metric_kind':metric, 'product_code':product_code,'fields':mappings,
             'observations':{'coverage':name,'classification_observation':classification,
                 'valuation_observation':valuation,'date_observation':dates,
                 'gaps':gaps,'evidence':[eid,'private_products',*extra]}}
        model['concepts'].append(c)
        model['relation_definitions'].append({
            'id':cid+'.product','name':'衡量金融商品' if metric == 'aum' else '手收來源商品',
            'source_concept':cid,'property_uri':FH+('measuresProduct' if metric=='aum' else 'feeIncomeFromProduct'),
            'domain_uri':FH+('AUM' if metric=='aum' else 'FeeIncome'),
            'target_class_uri':FH+'FinancialProduct','fields':[]})

    def pairs(tables, columns):
        return [(t,c,m) for t in tables for c,m in columns]

    fund='DSFND.PB_FUND_MONTH'
    concept('bank.fund_aum','銀行基金 AUM','aum','bank_fund',['FundProduct'],{
        'customerId':[(fund,'IDNO','客戶ID')], 'amount':[(fund,'CurrentTWDValue','metadata 台幣餘額；是否符合 AUM 認列另待核定')],
        'snapshotDate':[(fund,'EXEDATE','執行日；資產基準日語意待確認')]},'bank_fund_aum',
        'SQL 對 CurrentTWDValue 依客戶、執行日、PCCCODE 與 TRUSTPRD 加總；不自動再與其他 AUM 加總。',
        'EXEDATE 是 metadata 執行日；未核定快照選日規則。',
        'SQL 的 ELSE TRUSTPRD 保留原類別；私銀有 bank_fund，但尚未驗證底表基金類別完整取值，不能直接核定 TRUSTPRD 篩選。',
        ['基金與 ETF 在私銀分列，不能用表名 FUND 把全表都視為基金。','來源粒度、產品識別及去重待確認。'],['meta_bank_fund'])
    spread='DSFND.PB_FUND_SPREAD_DAILY'
    concept('bank.fund_fee_income','銀行基金手收','fee_income','bank_fund',['FundProduct'],{
        'customerId':[(spread,'IDNO','客戶識別候選')], 'amount':[(spread,'BRHREBATEAMT','分行手續費；幣別待確認')],
        'productId':[(spread,'FUNDID','基金代碼；與單一基金商品識別的映射尚待確認')],
        'incomePeriod':[(spread,'FEEDATE','手續費發生日；收入期間尚未核定')],
        'employeeId':[(spread,'BAOEMPID','所屬人員候選；不是已核定理專歸屬'),(spread,'SAOEMPID','服務人員候選；不是已核定理專歸屬')]},'bank_fund_fee',
        'SQL SUM(BRHREBATEAMT)；原分支含基金／ETF／海外股票等，只有分類為基金的範圍列為候選。',
        'FEEDATE 有民國日期轉換觀察；交易收入期間與資料快照分開，snapshotDate 沒有選定候選。',
        "SQL CASE 先以 FHID NOT IN ('PS','CB','YB','SN') 分成基金，再判 ETF／海外股票／集合；後方 TA/TB/TD/TE 可能已被先行基金條件攔截。保留順序，不自行修正為新版分類。",
        ['原 SQL 篩選 (BAOPCCCODE 或 SAOPCCCODE LIKE 2E%) 及 FEEDATE 下限只作觀察。','分類 CASE 順序、基金完整範圍、幣別及理專歸屬待確認。'],['metadata_offshore'])
    model['relation_definitions'].append({'id':'bank.fund_fee_income.advisor','name':'歸屬理專',
        'source_concept':'bank.fund_fee_income','property_uri':BANK+'attributedToAdvisor',
        'domain_uri':BANK+'BankFeeIncome','target_class_uri':BANK+'FinancialAdvisor','fields':[]})

    fx='DSDEP.FN_EXCH_RT'
    bondpos=['DSPBM.PB_BONDPOS_SEC_M','DSPBM.PB_BONDPOS_SEC']
    for suffix,label,code,products in [
        ('bond','複委託債券','securities_bond',['BondProduct','OverseasFinancialProduct']),
        ('structured','複委託結構型商品','securities_structured',['StructuredFinancialProduct'])]:
        concept('securities.'+suffix+'_aum','證券'+label+' AUM','aum',code,products,{
            'customerId':pairs(bondpos,[('IDNO','客戶識別候選')]),
            'amount':pairs(bondpos,[('NETQTY','估值輸入：數量'),('CPRICE','估值輸入：價格')])+[(fx,'EXCH_RT','估值輸入：匯率；不是可單獨選用的 AUM')],
            'snapshotDate':[(bondpos[0],'PRCS_DT','歷史 SQL 未加表別的 PRCS_DT 與 FX 表同名，需釐清來源'),(bondpos[1],'CLRDATE','current SQL 日期候選；尚未核定資產基準日'),(fx,'PRCS_DT','FX 日期輸入，歷史與部位同名需釐清')]},'sec_bond_aum',
            'SQL SUM(NETQTY / 100 * CPRICE * EXCH_RT)；所有金額候選為同一估值的組成輸入。',
            '歷史匯率取全體每月 MAX(PRCS_DT)，current 按 CLRDATE 與幣別連匯率；歷史/current UNION，快照、匯率連接與去重均未核定。',
            "SQL BOND LIKE 'TSSN%' 分成結構型，ELSE 為債券（含 SQL ELSE 的空值範圍，不能直接等同 NOT LIKE）。",
            ['折台為 SQL 意圖，幣別及匯率口徑待確認。','未核定 BOND 單一商品識別、理專與客戶跨系統識別。'])
    fundpos=['DSPBM.PB_FUNDPOSIT_SEC_M','DSPBM.PB_FUNDPOSIT_SEC']
    concept('securities.fund_aum','證券複委託基金 AUM','aum','securities_fund',['FundProduct'],{
        'customerId':pairs(fundpos,[('WKB02','SQL 當 cust_id；current metadata 為投資人帳號，不可直接認為客戶ID')])+[(fundpos[1],'WKB24','current metadata 客戶身分證字號；與 WKB02 對照關係未確認')],
        'amount':pairs(fundpos,[('WKB28','估值輸入：基金單位數，HS 定義未獨立確認'),('WKB23','估值輸入：收盤價，HS 定義未獨立確認'),('WKB31','估值輸入：匯率，HS 定義未獨立確認')]),
        'snapshotDate':pairs(fundpos,[('YYYYMMDD','原 SQL 日期欄位；基準日及選日待確認')])},'sec_fund_aum',
        'SQL SUM(WKB28 * WKB23 * WKB31)，歷史/current 聚合後 UNION；不是三個可替代金額。',
        'YYYYMMDD 尚未核定為快照日期；跨歷史/current 去重待確認。',
        '私銀 securities_fund 為複委託基金；不按表名擴成其他商品。',
        ['WKB02 是投資人帳號，WKB24 是客戶身分證字號；保留兩個不同角色，不核定客戶連接。','current metadata 不自動證明歷史表語意或計價幣別。'],['meta_sec_fund_identity'])
    stockpos=['DSPBM.PB_STOCKPOS_SEC_M','DSPBM.PB_STOCKPOS_SEC']
    concept('securities.foreign_stock_aum','證券複委託外國股票 AUM','aum','securities_foreign_stock',['StockProduct','OverseasFinancialProduct'],{
        'customerId':pairs(stockpos,[('IDNO','客戶識別候選')]),
        'amount':pairs(stockpos,[('NETQTY','估值輸入：數量'),('CPRICE','估值輸入：價格')])+[(fx,'EXCH_RT','估值輸入：匯率')],
        'snapshotDate':[(stockpos[1],'CLRDATE','current 部位日期候選'),(fx,'PRCS_DT','歷史輸出使用 FX PRCS_DT；不是證實部位快照日')]},'sec_stock_aum',
        'SQL SUM(NETQTY * CPRICE * EXCH_RT)。',
        '歷史取 FX 每月全體最大日期並以部位 YYYYMM 連接；current 以 CLRDATE 連 FX 日期；UNION 與快照口徑待確認。',
        '私銀 securities_foreign_stock 對應複委託海外股票；海外地域判定未另核定。',
        ['FX 日期、部位日期不可自動視為同義；幣別及去重待確認。'])
    taiwan=['DSPBM.PB_YTRMRBP_SEC_M','DSPBM.PB_YTRMRBP_SEC']
    concept('securities.taiwan_stock_aum','證券台股 AUM','aum','securities_taiwan_stock',['StockProduct'],{
        'customerId':pairs(taiwan,[('YTRMRB025','身分證號候選；歷史表定義未獨立確認')]),
        'amount':pairs(taiwan,[('YTRMRB110','估值輸入：集保庫存'),('YTRMRB150','估值輸入：收盤價')]),
        'snapshotDate':pairs(taiwan,[('YYYYMMDD','SQL 日期欄位；基準日待確認')])},'sec_taiwan_aum',
        'SQL 先投影客戶、日期、YTRMRB110 * YTRMRB150，UNION 後 SUM；可能去掉相同投影列，需確認原始粒度。',
        '日期與歷史/current 銜接待確認。', '私銀 securities_taiwan_stock，地域為台灣；未另造組合 OWL Class。',
        ['台股手收來源尚缺；不從 AUM 推導手收。','未核定合併、估值、幣別及去重。'],['meta_sec_taiwan'])
    fee_date='SQL 用 T_LAST_TWO_WORKDAYS 的 YM/LAST2_WD 將月底最後兩個工作天收入移至次月；YYYYMM||01 是歸屬月份標記，不是快照日。工作日曆、收入期間與 current 最大日期篩選均未核定。'
    bondtr=['DSPBM.PB_BONDTRADM_SEC_M','DSPBM.PB_BONDTRADM_SEC']
    for suffix,label,code,products in [
        ('bond','複委託債券','securities_bond',['BondProduct','OverseasFinancialProduct']),
        ('structured','複委託結構型商品','securities_structured',['StructuredFinancialProduct'])]:
        concept('securities.'+suffix+'_fee_income','證券'+label+'手收','fee_income',code,products,{
            'customerId':pairs(bondtr,[('IDNO','客戶識別候選')]),
            'amount':pairs(bondtr,[('CFEE','金額輸入：客戶手續費'),('FXRATE','金額輸入：匯率')]),
            'incomePeriod':pairs(bondtr,[('CLRDATE','結算日期；收入歸屬月份需另核定')])},'sec_bond_fee',
            'SQL SUM(CFEE * FXRATE)，不是單取其中一個金額；歷史/current 聚合後 UNION。',fee_date,
            "SQL BOND LIKE 'TSSN%' 為結構型，ELSE 為債券；不自行改成 NOT LIKE。",
            ['幣別、收入認列與證券端人員歸屬未核定；不套用銀行理專關係。'])
    fundtr=['DSPBM.PB_FUNDTRADM_SEC_M','DSPBM.PB_FUNDTRADM_SEC']
    concept('securities.fund_fee_income','證券複委託基金手收','fee_income','securities_fund',['FundProduct'],{
        'customerId':pairs(fundtr,[('WKA28','身分證字號候選；current 語意尚未獨立核對')]),
        'amount':pairs(fundtr,[('WKA31','總手續費；metadata 原文含「台？」疑義，幣別未確認')]),
        'incomePeriod':pairs(fundtr,[('WKA02','交易日期；不是快照日')])},'sec_fund_fee',
        'SQL SUM(WKA31)；歷史/current 聚合後 UNION。',fee_date,
        '私銀 securities_fund；僅記錄已提供來源的手收範圍。',
        ['原 current 最大日期子查詢引用 PB_BONDTRADM_SEC，保留為待覆核異常，不自行修正。','WKA31 幣別不明；客戶識別不能直接與 AUM WKB02 相連。'],['meta_sec_fund_fee'])
    stocktr=['DSPBM.PB_STOCKTRADM_PM_SEC_M','DSPBM.PB_STOCKTRADM_AM_SEC_M','DSPBM.PB_STOCKTRADM_PM_SEC']
    concept('securities.foreign_stock_fee_income','證券複委託外國股票淨手收','fee_income','securities_foreign_stock',['StockProduct','OverseasFinancialProduct'],{
        'customerId':pairs(stocktr,[('IDNO','客戶識別候選')]),
        'amount':pairs(stocktr,[('CFEE','金額輸入：客戶手續費'),('ABFEE','扣除輸入：上手手續費'),('FXRATE','金額輸入：匯率')]),
        'incomePeriod':pairs(stocktr,[('CLRDATE','結算日期；不是資料快照日期')])},'sec_stock_fee',
        'SQL SUM((CFEE - ABFEE) * FXRATE)；PM/AM 分支 UNION；不可改成毛手收。',fee_date,
        '私銀 securities_foreign_stock 為複委託外國股票；保留淨手收定義。',
        ['原 current AM 分支 FROM PB_STOCKTRADM_AM_SEC_M，最大日期卻查 PB_STOCKTRADM_AM_SEC；不擅自更換來源或重複計入歷史。','幣別、收入期間、PM/AM 去重及人員歸屬待確認。'],['meta_sec_stock_fee'])
    # Referenced only by a max-date subquery, not as an approved amount source.
    add_source('DSPBM.PB_STOCKTRADM_AM_SEC','sec_stock_fee')
    model['sources'] = sorted(sources.values(),key=lambda s:s['table'])
    prior_evidence = {**prior_aum['evidence'], **prior_fees['evidence']}
    for eid in {'metadata_offshore', *(eid for s in model['sources'] for eid in s['evidence'])}:
        if eid not in evidence: evidence[eid] = copy.deepcopy(prior_evidence[eid])
    return model


if __name__ == '__main__':
    if TARGET.exists(): raise SystemExit('Refusing to overwrite canonical investment-metrics.json')
    TARGET.write_text(json.dumps(make_model(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Seeded candidate metadata; no source SQL executed')
