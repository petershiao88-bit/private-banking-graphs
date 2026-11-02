"""One-shot local PG maintenance; backup must exist. Never executes source SQL."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PG = ROOT / 'department-pg'
BACKUP = ROOT / 'archive/before-pg-income-extension-20261024/department-pg'
assert BACKUP.is_dir()

def read(name):
    return json.loads((PG / name).read_text(encoding='utf-8'))

def write(name, value):
    (PG / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sql(file, start, end):
    return {'file': 'Ontology/私銀智能問答/sources/sql/' + file,
            'lines': [start, end], 'encoding': 'cp950'}

business, fees, inv = map(read, ['bank-business-metrics.json', 'product-fees.json', 'investment-metrics.json'])
assert len(business['concepts']) == 9, 'Already applied or unexpected baseline'
bank = 'https://example.org/ontology/bank#'
fh = 'https://example.org/ontology/holding#'
business['evidence'].update({
    'deposit_income_history': sql('8.INCOME_DETAIL.sql', 546, 581),
    'deposit_income_current': sql('8.INCOME_DETAIL.sql', 583, 600),
    'deposit_income_monthly': sql('8.INCOME_DETAIL.sql', 602, 644),
    'deposit_income_monthly_job': sql('X-INCOME_MOTHLY.sql', 7, 49),
    'deposit_income_summary': sql('9.INCOME_SMY.sql', 231, 240),
    'bond_trust_income': sql('8.INCOME_DETAIL.sql', 39, 51),
    'bond_proprietary_income': sql('8.INCOME_DETAIL.sql', 54, 61),
    'bond_income_summary': sql('9.INCOME_SMY.sql', 40, 59),
})
deposit_tables = ['DSDEP.DEP_NT_ACCT_HS', 'DSDEP.DEP_FN_ACCT_HS',
                  'DSDEP.EMP_DEP_NT_ACCT_HS', 'DSDEP.DEP_FN_ACCT']
# Reuse the identical shared table catalog records. Metric-specific evidence is
# on each table_sources edge context, not a change to other metrics' scope.
for model, tables in [(read('deposits.json'), deposit_tables),
                      (fees, ['DSFND.PB_FUND_SPREAD_DAILY'])]:
    for s in model['sources']:
        if s['table'] in tables:
            business['sources'].append(copy.deepcopy(s))
            for eid in s['evidence']:
                business['evidence'][eid] = copy.deepcopy(model['evidence'][eid])
business['sources'].append({'table': 'DSWTR.BOND_TXN', 'status': 'observed_in_files',
                           'database_verified': False, 'evidence': ['bond_proprietary_income']})

loan = next(c for c in business['concepts'] if c['id'] == 'bank.loan_income')
fee_template = next(c for c in business['concepts'] if c['id'] == 'bank.gold_fee_income')

def add(cid, name, code, scope, kind, table_evidence, observations):
    observations['evidence'].append('private_products')
    c = copy.deepcopy(loan if kind == 'interest_income' else fee_template)
    c.update(id=cid, name=name, definition=name + '；依私銀 SQL 業務字典記錄來源範圍，計算由 Tool 承接。',
             product_code=code, business_scope_class_uri=bank + scope,
             class_uri=bank + ('BankInterestIncome' if kind == 'interest_income' else 'BankFeeIncome'),
             metric_kind=kind, observations=observations)
    c['table_sources'] = {'status': 'observed_in_files', 'coverage': observations['coverage'],
        'tables': [{'table': t, 'role': 'primary', 'evidence': e} for t, e in table_evidence],
        'unresolved_supporting_relations': []}
    if scope == 'BondProduct':
        c['product_class_uris'] = [bank + 'BondProduct', bank + 'OverseasFinancialProduct']
    business['concepts'].append(c)
    business['relation_definitions'].append({'id': cid + '.scope', 'name': name + '來源商品',
        'source_concept': cid, 'property_uri': fh + ('interestIncomeFromProduct' if kind == 'interest_income' else 'feeIncomeFromProduct'),
        'domain_uri': fh + ('InterestIncome' if kind == 'interest_income' else 'FeeIncome'),
        'target_class_uri': fh + 'FinancialProduct', 'fields': []})
    if kind == 'fee_income':
        business['relation_definitions'].append({'id': cid + '.advisor', 'name': name + '歸屬理專',
            'source_concept': cid, 'property_uri': bank + 'attributedToAdvisor',
            'domain_uri': bank + 'BankFeeIncome', 'target_class_uri': bank + 'FinancialAdvisor', 'fields': []})

common_gaps = ['只對應指標到底表；客戶、商品識別、幣別、收入期間及欄位映射維持待定。',
               'SQL 計算由 Tool 承接；來源觀察不是可執行規則，未查驗資料庫。']
add('bank.deposit_interest_income', '銀行存款利收', 'deposit', 'DepositProduct', 'interest_income',
    [(t, ['deposit_income_current'] if t == 'DSDEP.DEP_FN_ACCT' else
      ['deposit_income_history', 'deposit_income_monthly', 'deposit_income_monthly_job']) for t in deposit_tables], {
    'coverage': 'INCOME_066 存款利收：台幣／外幣／行員存款歷史月檔及外幣 current；依 SQL 整體存款範圍記錄，不拆成三種存款利收。',
    'classification_observation': '9.INCOME_SMY.sql 歸類為利收／銀行／存款；沿用 BankInterestIncome 與 DepositProduct。',
    'amount_observation': 'SQL 加總 GROSS_INCM；這是銀行業務利收，不宣稱等於客戶收到的存款利息。',
    'date_observation': '歷史 YYYYMM||01 為月份標記，current 取 DATA_DT；月更新以 SYSDATE 上月替換，未核定期間起迄。',
    'gaps': common_gaps + ['歷史初建有私銀分行及 YYYYMM>202505 條件；上月替換分支未加同樣分行條件，保留範圍差異。',
       '初建歷史合併用 UNION ALL，上月替換用 UNION；不能直接相加所有分支。',
       'INCOME_066 引用 TMP01，但該檔前段定義位於註解；current 台幣表無 GROSS_INCM 的註記保留，不補作金額來源。',
       '存款利收先不新增理專歸屬；行員存款底表的存在不代表已完成存款人身分映射。'],
    'evidence': ['deposit_income_history','deposit_income_current','deposit_income_monthly',
                 'deposit_income_monthly_job','deposit_income_summary']})
add('bank.overseas_bond_trust_fee_income', '銀行海外債券（信託）手收', 'bank_bond_trust', 'BondProduct', 'fee_income',
    [('DSFND.PB_FUND_SPREAD_DAILY', ['bond_trust_income'])], {
    'coverage': 'INCOME_031 海外債券信託收入，取 PB_FUND_SPREAD_DAILY 的 CB 及私銀分支；不是整張共用底表。',
    'classification_observation': '9.INCOME_SMY.sql 歸類為手收／銀行／海外債券_信託；信託承作方式留在 PG，沿用債券及海外商品分類。',
    'amount_observation': 'SQL SUM(BRHREBATEAMT + WKR028/100)；保留費用與交易利得來源組成，不改成純手續費，也不自行對空值補零。',
    'date_observation': 'FEEDATE 加 19110000 後轉換日期；客戶、PCCODE 與日期為來源分組觀察，不核定收入期間。',
    'gaps': common_gaps + ["FHID='CB'、BAOPCCCODE LIKE '%2E%' 只保留為來源範圍觀察，不擴大既有基金或通用商品手收。",
                          '歸屬理專沿用銀行手收關係；實際員編未映射。'],
    'evidence': ['bond_trust_income','bond_income_summary']})
add('bank.overseas_bond_proprietary_fee_income', '銀行外國債券（自營）手收', 'bank_bond_proprietary', 'BondProduct', 'fee_income',
    [('DSWTR.BOND_TXN', ['bond_proprietary_income'])], {
    'coverage': 'INCOME_032 自營平台外國債券手收；來源 BOND_TXN 的私銀 PCC_CODE 分支。',
    'classification_observation': '9.INCOME_SMY.sql 歸類為手收／銀行／外國債券_自營；自營方式留在 PG，沿用債券及海外商品分類。',
    'amount_observation': 'SQL SUM(ABS(INC_AMT_NT))，逐筆取絕對值再加總；不可改為 ABS(SUM(...)) 或自行恢復正負號。',
    'date_observation': '來源 TXN_DT；按客戶、日期及 PCC_CODE 分組，未核定收入期間與快照日。',
    'gaps': common_gaps + ["PCC_CODE LIKE '2E%' 為來源觀察；交易收益性質仍保留，不將此底表作 AUM 或 LUM 金額來源。",
                          '歸屬理專沿用銀行手收關係；實際員編未映射。'],
    'evidence': ['bond_proprietary_income','bond_income_summary']})

fees['evidence'].update({'sql_dci_tmu': sql('8.INCOME_DETAIL.sql',116,128),
                         'sql_dci_summary': sql('9.INCOME_SMY.sql',71,90),
                         'fx_pnl': copy.deepcopy(business['evidence']['fx_pnl'])})
fees['sources'].append(copy.deepcopy(next(s for s in business['sources'] if s['table']=='DSTAS.FO108_W')))
dci = next(c for c in fees['concepts'] if c['id']=='bank.dci_fee_income')
dci['name'] = '銀行 DCI 手收'
dci['definition'] = '依私銀 SQL 手收分類，涵蓋 DCI 手續費報表及 DCD 的 TMU 損益；沿用結構型金融商品分類，不認定為結構型存款。'
dci['observations'] = {
    'coverage': 'INCOME_037 純手續費與 INCOME_038 的 DCD／TMU 收入，兩者在 SQL 均歸手收／銀行／DCI。',
    'classification_observation': "INCOME_037 取 FEE_AMOUNT_TWD，INCOME_038 取 SUM(TMUPROFIT) 且 TRIM(Product)='DCD'；保留不同金額性質。私銀為使用／定義部門，來源權責仍待定。",
    'excluded_scope': ['FO108_W 的非 DCD 分支不屬於本指標；既有 FX 指標排除 DCD／Cash Bond，不因共表而混用。'],
    'gaps': common_gaps + ['INCOME_SMY 使用 UNION 匯集，不宣稱可直接加總底表或按交易去重。',
        'current／歷史選日、POSTDATE 與收入期間仍待定；本輪理專員編映射不變。'],
    'evidence': list(dict.fromkeys(dci['observations']['evidence'] + ['sql_dci_tmu','sql_dci_summary']))}
dci['table_sources']['status'] = 'observed_in_files'
dci['table_sources']['coverage'] = dci['observations']['coverage']
dci['table_sources']['tables'].append({'table':'DSTAS.FO108_W','role':'primary','evidence':['sql_dci_tmu']})
for r in fees['relation_definitions']:
    if r['source_concept']==dci['id']:r['name']=r['name'].replace('銀行 DCI 手續費收入','銀行 DCI 手收')

inv['evidence']['insurance_income_summary'] = sql('9.INCOME_SMY.sql',11,39)
insurance = next(c for c in inv['concepts'] if c['id']=='bank.insurance_fee_income')
insurance['name'] = '銀行保險手收'
insurance['definition'] = '依私銀 SQL 手收分類，涵蓋保險日報 COMM_AMT 與兩項月檔 PS；PS 的客戶貢獻度性質另行保留，不宣稱均為純手續費。'
insurance['observations'].update({
    'coverage': 'SQL INCOME_028 日報及 INCOME_029／030 月檔均歸手收／銀行／保險；來源涵蓋不代表已查驗完整生產時間範圍。',
    'classification_observation': '沿用銀行通路 InsuranceProduct；SQL 將日報與月檔歸同一保險手收指標。私銀為使用／定義部門，來源權責仍待定。',
    'valuation_observation': '日報加總 COMM_AMT；月檔加總 PS，metadata 定義為客戶貢獻度。SQL 分類為手收，不抹除來源性質差異。',
    'date_observation': '日報用 APPLY_DT；兩項月檔將 LST_MTN_DT 以 ADD_MONTHS(...,1) 移至次月，保留為來源觀察，不直接當收入期間起迄。',
    'gaps': common_gaps + ["IU 月檔篩選 PS IS NOT NULL；OFI 月檔篩選 OPEN_ACCOUNT='Y'，不互相套用條件。",
        '日報註記僅有特定月份 current；日報與月檔是否重疊未查驗。SQL UNION 只對投影整列去重，不等同保單或交易去重。',
        '日報與月檔沿用同一指標 ID；不建立三個可直接相加的收入指標。'],
    'evidence': insurance['observations']['evidence'] + ['insurance_income_summary']})
insurance['table_sources']['status']='observed_in_files'
insurance['table_sources']['coverage']=insurance['observations']['coverage']
for table, meta in [('DSKPI.KPI_DET_IU_002_NEW','insurance_contribution_iu_metadata'),
                    ('DSKPI.KPI_DET_OFI_001','insurance_contribution_ofi_metadata')]:
    e=['insurance_contribution_sql',meta]
    insurance['table_sources']['tables'].append({'table':table,'role':'primary','evidence':e})
    inv['sources'].append({'table':table,'status':'observed_in_files','database_verified':False,'evidence':e})
for r in inv['relation_definitions']:
    if r['source_concept']==insurance['id']:r['name']=r['name'].replace('銀行保險手續費收入','銀行保險手收')

for name,model in [('bank-business-metrics.json',business),('product-fees.json',fees),('investment-metrics.json',inv)]:
    write(name, model)

review = {'revision':'pg-income-extension-20261024','ontology_version':'0.15.0',
    'status':'implemented_locally_not_deployed','rdf_changed':False,
    'new_concepts':[c['id'] for c in business['concepts'][-3:]],
    'expanded_concepts':[dci['id'],insurance['id']],
    'tool_execution':'deferred; no SQL execution or indicator-to-Tool binding added',
    'backup':'archive/before-pg-income-extension-20261024',
    'source_evidence':{}}
for model in (business,fees,inv):
    for eid,record in model['evidence'].items():
        if eid in {'deposit_income_history','deposit_income_current','deposit_income_monthly','deposit_income_monthly_job',
                    'deposit_income_summary','bond_trust_income','bond_proprietary_income','bond_income_summary',
                    'sql_dci_tmu','sql_dci_summary','insurance_contribution_sql','insurance_income_summary'}:
            path=ROOT.parents[1].joinpath(*Path(record['file']).parts[1:])
            review['source_evidence'][eid]={**record,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
write('history/pg-income-extension-20261024.json',review)
print('Updated three PG modules; RDF and source files untouched')
