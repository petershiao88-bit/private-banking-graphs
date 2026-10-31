"""One-shot reviewed PG scope addition, without RDF/source SQL changes."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PG=ROOT/'department-pg'
assert (ROOT/'archive/before-securities-summary-20261024').is_dir()
assert not (PG/'securities-summary-metrics.json').exists(),'Already applied'

def read(name):return json.loads((PG/name).read_text(encoding='utf-8'))
def write(name,value):(PG/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sql(file,start,end):return {'file':'Ontology/私銀智能問答/sources/sql/'+file,'lines':[start,end],'encoding':'cp950'}
old=read('investment-metrics.json')
fields={k:copy.deepcopy(old['field_definitions'][k]) for k in ['amount','currency','aumAsOfDate','incomePeriodStart','incomePeriodEnd']}
fields['amount']['definition']='目前已納入範圍的證券彙總結果金額；計算與實體映射尚待 Tool 定義。'
fields['currency']['definition']='彙總結果的計價幣別；沿分項來源保留幣別／換匯疑點，不指定折台規則。'
evidence={
    'aum_summary_included':sql('2._AUM_SUMY.sql',90,129),
    'aum_summary_pledge_mixed_as_taiwan':sql('2._AUM_SUMY.sql',121,139),
    'aum_detail_components':sql('1.AUM_DETAIL.sql',316,438),
    'income_summary_components':sql('9.INCOME_SMY.sql',201,230),
    'income_detail_components':sql('8.INCOME_DETAIL.sql',329,496),
    'income_customer_scope':sql('9.INCOME_SMY.sql',254,304),
    'aum_report_copy_only':sql('12.GRANT.sql',12,15),
    'aum_monthly_query_draft':{'file':'Ontology/私銀智能問答/ontology/AUM_business_dictionary.json',
        'encoding':'utf-8','selector':'metrics.code=aum_total_month_end; rules.code=category_latest_date',
        'status':'draft_metric_query'},
}
aum_components=['securities.bond_aum','securities.structured_aum','securities.fund_aum',
                'securities.foreign_stock_aum','securities.taiwan_stock_aum']
fee_components=['securities.bond_fee_income','securities.structured_fee_income',
                'securities.fund_fee_income','securities.foreign_stock_fee_income']
common_gaps=['涵蓋分項是 PG metadata，不表示已核定 SUM、去重或跨分項合計公式；計算由 Tool 承接。',
             '本指標只代表目前已納入的私銀證券商品範圍，不宣稱證券公司全部業務。',
             '不新增底表、欄位映射、理專關係或資料權責；沿分項保留金額來源／估值輔助／日期查詢角色。',
             '總指標與其分項不得再一起加總；兩項總指標不新增可執行 SQL 或 Tool 綁定。']

def concept(cid,name,kind,cls,components,names,excluded,obs):
    return {'id':cid,'name':name,
        'definition':name+'；僅涵蓋目前已納入私銀模型的證券商品分項，金額與期間口徑待 Tool 定義。',
        'subsidiary':'securities','department_owner':None,'class_uri':'https://example.org/ontology/securities#'+cls,
        'specific_product_class_uri':None,'metric_kind':kind,'coverage_status':'included_products_only',
        'lineage_mode':'via_component_metrics','calculation_status':'pending_tool_definition',
        'component_metric_ids':components,'excluded_metric_ids':excluded,
        'fields':[{'field':n,'status':'pending','table':None,'column':None,'candidates':[]} for n in names],
        'observations':obs}

aum=concept('securities.total_aum','私銀－證券總 AUM','aum','SecuritiesAUM',aum_components,
    ['amount','currency','aumAsOfDate'],['securities.stock_pledge_aum'],{
    'coverage':'已納入的複委託債券、結構型、基金、外國股票與台股五項 AUM；股票設質估值排除。',
    'sql_behavior_observation':'原 AUM 彙整以 UNION 匯集，AUM_027 台股庫存與 AUM_028 股票設質均標證券／台股；不能只以 COMP=證券 或 PROD=台股篩選舊成品總額。',
    'amount_observation':'沿五項分項保留估值與匯率觀察；本輪不選擇現成 AUM_REPORT 或 AUM_TMP02 作新底表，也不把股票估值接成 LUM。',
    'date_observation':'AUM 是基準日規模；各分項歷史／current 日期與匯率日期仍待定。字典的各分類月內最新日期為 draft_metric_query，不當正式月底或同日口徑。',
    'gaps':common_gaps+['已提供檔案缺 AUM_TMP02／AUM_REPORT 完整產製邏輯；12.GRANT.sql 只有遠端複製，不能視為已確認計算。',
                       '排除 AUM_028 須保留來源分支血緣，不能在混合台股標籤後假設可辨別或直接扣除。',
                       '基金 WKB02／WKB24 身分角色、current／歷史 UNION 及部位／匯率日期疑點繼承，未用總指標自動解決。'],
    'evidence':['aum_summary_included','aum_summary_pledge_mixed_as_taiwan','aum_detail_components',
                'aum_report_copy_only','aum_monthly_query_draft']})
fee=concept('securities.total_fee_income','私銀－證券總手收','fee_income','SecuritiesFeeIncome',fee_components,
    ['amount','currency','incomePeriodStart','incomePeriodEnd'],['securities.taiwan_stock_fee_income'],{
    'coverage':'已納入的複委託債券、結構型、基金與外國股票四項手收；台股手收缺來源先不納入。',
    'sql_behavior_observation':'INCOME_051_054、052、053 以 UNION 投影到手收／證券；債券與結構型依 FLG 分列。UNION 為投影整列去重，不是交易層去重或四個金額的直接相加。',
    'amount_observation':'外國股票保留 SUM((CFEE-ABFEE)*FXRATE) 的淨手收，不改成毛手收；基金幣別與各分項金額組成仍待定。',
    'date_observation':'原 SQL 用 T_LAST_TWO_WORKDAYS 將月底最後兩個工作天移至次月，YYYYMM||01 為收入歸屬月份標記；總手收按收入期間衡量，期間與工作日曆待 Tool 定義。',
    'gaps':common_gaps+['INCOME_REPORT 篩除 PRFT_CNTR_CD 為空，且按客戶／月份連 PB_CUST_005；歸屬連接與倍增／遺漏未查驗，不套用銀行理專關係。',
                       '基金 current 最大日期查債券交易表；外股 current AM 金額仍取 AM_SEC_M，最大日期卻查 AM_SEC；保留原異常，不修正或擴大來源。',
                       'T_LAST_TWO_WORKDAYS 缺 schema／底層定義，仍由原分項 unresolved_supporting_relations 承接，不另建來源表。'],
    'evidence':['income_summary_components','income_detail_components','income_customer_scope']})
execution={k:None for k in ['sql','join_rules','filter_rules','aggregation_rules','row_grain',
    'snapshot_selection','currency_conversion','deduplication_rules','recognition_rules','period_basis']}
m={'schema_version':'1.0.0','ontology_version':'0.16.0','status':'active','scope':'metadata_only',
   'inference':False,'instance_mapping':False,'access_policy_status':'deferred_by_user',
   'field_definitions':fields,'execution':execution,'evidence':evidence,'concepts':[aum,fee],'relation_definitions':[]}
write('securities-summary-metrics.json',m)
dept=read('departments.json')
assert len(dept['metric_ids'])==42
dept['metric_ids']=sorted(dept['metric_ids']+['securities.total_aum','securities.total_fee_income'])
write('departments.json',dept)
record={'revision':'securities-summary-20261024','ontology_version':'0.16.0',
    'status':'implemented_locally_not_deployed','backup':'archive/before-securities-summary-20261024',
    'rdf_changed':False,'new_concepts':['securities.total_aum','securities.total_fee_income'],
    'component_memberships':{c['id']:sorted(c['component_metric_ids']) for c in m['concepts']},
    'excluded_metric_ids':{c['id']:c['excluded_metric_ids'] for c in m['concepts']},
    'lineage_mode':'via_component_metrics','calculation_status':'pending_tool_definition',
    'new_source_tables':[],'existing_component_models_changed':False,'source_evidence':{}}
for eid,e in evidence.items():
    p=ROOT.parents[1].joinpath(*Path(e['file']).parts[1:])
    record['source_evidence'][eid]={**e,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
write('history/securities-summary-20261024.json',record)
print('Created 2 summary scopes, 9 memberships; department adopts 44; no RDF/source changes')
