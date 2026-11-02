"""Update only current documents; historical copies are retained in the snapshot."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
intro='''## 本輪：證券總指標涵蓋範圍（securities-summary-20261024）

使用者確認後完成本機 PG 實作。RDF 與 ontology_version 保持 v0.16.0，五份 RDF、Turtle／OWL、build-config、catalog 均逐位元組未變。原七份指標／通聯 JSON 逐位元組保持；departments.json 僅在原42項採用清單加入下列兩項。

| PG ID／名稱 | 沿用類別 | 涵蓋分項 |
|---|---|---|
| securities.total_aum／私銀－證券總 AUM | SecuritiesAUM | 複委託債券、結構型、基金、外國股票、台股5項 AUM |
| securities.total_fee_income／私銀－證券總手收 | SecuritiesFeeIncome | 複委託債券、結構型、基金、外國股票4項手收 |

新增 securities-summary-metrics.json 及 securities_summary_model.py（第九份 active JSON）。9條 HAS_COMPONENT_METRIC 是 PG 分項涵蓋 metadata，不新增 RDF Property，也不代表可直接 SUM。總指標的 lineage_mode=via_component_metrics、coverage_status=included_products_only、calculation_status=pending_tool_definition。

總指標經分項追溯既有金額／估值／日期來源；沒有另造 SourceTable 或新增總指標到底表的直接連線。原分項仍各自保留，總指標與其分項不得再次一起加總。「總」僅代表目前納入私銀模型的證券商品範圍，不宣稱證券公司全部業務。

兩項總指標只有7個結果元素：AUM為amount／currency／aumAsOfDate，手收為amount／currency／incomePeriodStart／End。均pending、table／column=null、candidates=[]，不帶入分項估值數量／單價、單一客戶或商品識別；execution全null，沒有新增Tool綁定、理專關係或可執行計算。

總 AUM 排除股票設質。舊SQL把AUM_027與AUM_028同標證券／台股，不能只篩COMP／PROD取本輪總額，須保留來源分支血緣。AUM_TMP02／AUM_REPORT完整產製邏輯未提供，字典「各分類月內最新日期」仍屬draft_metric_query，不當正式月底或同日口徑。

總手收先不含缺來源的台股手收；外國股票保留淨手收、月底最後兩工作天移至次月及UNION投影去重觀察。來源日曆、基金current取債券日期、外股current AM仍讀AM_SEC_M、私銀客戶歸屬連接等疑點不改寫。

新備份 archive/before-securities-summary-20261024；修訂與來源SHA-256見 department-pg/history/securities-summary-20261024.json。本輪沒有執行來源SQL、資料庫查核、Git提交或Neo4j部署。

'''

replacements={
 '私銀用42條 USES_METRIC':'私銀用44條 USES_METRIC',
 '採用現有42項指標':'採用44項指標（42項原分項／指標加2項證券總指標）',
 '私銀透過 USES_METRIC 採用42項現有指標':'私銀透過 USES_METRIC 採用44項指標',
 '私銀部門與42項採用範圍':'私銀部門與44項採用範圍',
 '共42項指標：18 AUM（銀行13／證券5）、1銀行 LUM、21手收（銀行17／證券4）、2銀行利收。私銀採用全部42項':'共44項指標：19 AUM（銀行13／證券6）、1銀行 LUM、22手收（銀行17／證券5）、2銀行利收。私銀採用全部44項',
 '42項指標：18 AUM、1 LUM、21手收、2利收；50 BusinessConcept、658節點、1388關係。含413 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、7 MetadataModule、7 MappingSlot。42 USES_METRIC':'44項指標：19 AUM、1 LUM、22手收、2利收；52 BusinessConcept、668節點、1415關係。含420 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、8 MetadataModule、7 MappingSlot。44 USES_METRIC',
 '42項指標：18AUM（銀行13／證券5）、1銀行LUM、21手收（銀行17／證券4）、2銀行利收；新增部門不增加指標數。':'44項指標：19AUM（銀行13／證券6）、1銀行LUM、22手收（銀行17／證券5）、2銀行利收；本輪新增兩項總指標涵蓋定義，原42項保持。',
 'PG：50 BusinessConcept、658 metadata節點、1388關係，含413 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、7 MetadataModule':'PG：52 BusinessConcept、668 metadata節點、1415關係，含420 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、8 MetadataModule',
 'PG：50BusinessConcept、658節點、1388關係，含413DataFieldDefinition、52SourceTable、61BusinessRelationDefinition、7MetadataModule':'PG：52BusinessConcept、668節點、1415關係，含420DataFieldDefinition、52SourceTable、61BusinessRelationDefinition、8MetadataModule',
 '新增42條 USES_METRIC；原88':'44條 USES_METRIC、9條 HAS_COMPONENT_METRIC；原88',
 '42USES_METRIC；88':'44USES_METRIC、9HAS_COMPONENT_METRIC；88',
 'RDF19＋PG92＝111項測試通過':'RDF19＋PG101＝120項測試通過',
 'PG92＋RDF19＝111項測試通過':'PG101＋RDF19＝120項測試通過',
 '總 AUM／總收入、目標達成率等彙總指標未新增。':'銀行總AUM／總收入、目標達成率等尚未新增；本輪僅完成兩項證券總指標的涵蓋定義。',
 '總 AUM／總收入／目標比較、客戶數／分群':'銀行總 AUM／總收入／目標比較、客戶數／分群',
 '總AUM／總收入、目標達成率等彙總指標留下一輪確認。':'銀行總AUM／總收入、目標達成率等留下一輪確認；本輪證券總指標僅定涵蓋，不核定計算。',
 '不拆私銀一部／二部或新增目標／彙總指標。':'不拆私銀一部／二部，不新增目標比較；證券兩項總指標只增加涵蓋定義。',
 'PG8份：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments':'PG9份：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments、securities-summary-metrics',
 '八份 active JSON 合併產生':'九份 active JSON 合併產生',
 '八份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments':'九份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments、securities-summary-metrics',
 'build_combined_graph／render_combined_cypher 新增尾端可選 department_model 參數':'build_combined_graph／render_combined_cypher 提供尾端可選 department_model、summary_model 參數',
}

for rel in ('README.md','department-pg/README.md','HANDOFF-ZED-RDF-PG-20261022.md'):
    p=ROOT/rel;text=p.read_text(encoding='utf-8')
    first,rest=text.split('\n',1)
    text=first+'\n\n'+intro+rest.lstrip('\n')
    for old,new in replacements.items():text=text.replace(old,new)
    if rel=='README.md':
        text=text.replace('本輪依使用者逐項確認及「可以，啟動」完成部門建模與指標名稱調整，僅本機建置與驗證，未部署 Neo4j。',
            '部門建模與指標名稱沿用v0.16.0；本輪依確認清單完成證券總指標PG涵蓋定義，僅本機建置與驗證，未部署Neo4j。')
        text=text.replace('修改前完整備份：[archive/before-department-v0.16.0](archive/before-department-v0.16.0/)。',
            '本輪備份：[archive/before-securities-summary-20261024](archive/before-securities-summary-20261024/)。前輪部門備份：archive/before-department-v0.16.0。')
        text=text.replace('## 本輪新增與命名','## 既有 v0.16.0 部門與命名')
        text=text.replace('42項既有指標 ID、商品分類、定義、來源、欄位候選、理專關係及計算口徑均保留；既有七份 JSON 僅改版本與指標顯示名稱。',
            '原42項指標的ID、商品分類、定義、來源、欄位候選、理專關係及計算口徑均保留；本輪原七份JSON逐位元組保持，部門清單只加兩項總指標。')
        text=text.replace('| departments.json | 私銀部門與44項採用範圍；department_model.py |',
            '| departments.json | 私銀部門與44項採用範圍；department_model.py |\n| securities-summary-metrics.json | 證券兩項總指標與分項涵蓋；securities_summary_model.py |')
    elif rel=='HANDOFF-ZED-RDF-PG-20261022.md':
        text=text.replace('## 本輪完成的範圍','## 前輪 v0.16.0 部門基礎（本輪證券總指標見上列）')
        text=text.replace('3. 私銀用44條 USES_METRIC 連到全部既有指標',
            '3. 私銀原有42條採用連線保持，本輪增為44條 USES_METRIC，連到原指標及兩項證券總指標')
        text=text.replace('本輪備份 archive/before-department-v0.16.0；名稱前後對照與新增 URI 見',
            '前輪備份 archive/before-department-v0.16.0；名稱前後對照與新增 URI 見')
    text+='''
## 本輪總指標驗證與查閱

test_securities_summary.py 直接驗證兩項／九條精確涵蓋、RDF逐位元組未變、原七份JSON與歷史不變、部門只新增兩個採用ID、既有節點／關係保存、七個空映射、SQL證據／草稿狀態、原來源角色、錯誤範圍／公式反例及產出確定性。底表清單把兩項總指標標成「沿分項追溯」；同一表在不同分項可同時作金額來源及日期查詢，分角色呈現。

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(t:BusinessConcept)
MATCH (t)-[:HAS_COMPONENT_METRIC]->(c:BusinessConcept)
OPTIONAL MATCH (c)-[:HAS_SOURCE_TABLE|USES_VALUATION_SOURCE|USES_DATE_LOOKUP_SOURCE]->(s:SourceTable)
RETURN d, t, c, s;
```

此查詢供未來已載入metadata的Neo4j Browser查閱，本輪未執行。HAS_COMPONENT_METRIC只表涵蓋，不是可執行SUM、正式RDF繼承或資料實例。產生器只MERGE，沒有部署／刪舊資料或自動遷移。銀行總量及目標比較繼續暫緩。
'''
    p.write_text(text,encoding='utf-8')

(ROOT/'README.txt').write_text('''客戶360 RDF／OWL v0.16.0；PG修訂securities-summary-20261024，2026-10-24。
PG新增私銀－證券總AUM、總手收，涵蓋5項AUM／4項手收，排除股票設質估值與缺來源台股手收。
「總」只代表目前已納入私銀的證券商品範圍，不宣稱全部業務。
新增9條HAS_COMPONENT_METRIC，來源沿分項追溯；不另造底表、不新增總指標直接到底表連線。
私銀採用44項指標：19AUM、1LUM、22手收、2利收；原42項及欄位候選完整保持。
RDF逐位元組未變：43Class、9Object Property、19Data Property、5Annotation Property、434triples。
PG：52概念、668節點、1415關係、420DataFieldDefinition、52SourceTable、44USES_METRIC。
兩項總指標calculation_status=pending_tool_definition，7個結果欄位為空映射、execution全null。
AUM月底口徑、股票設質分支混標、手收跨次月及UNION去重等疑點保留，計算由Tool承接。
RDF19＋PG101＝120項測試通過，無略過；24份來源SQL／Excel雜湊未變。
備份archive/before-securities-summary-20261024；修訂紀錄department-pg/history/securities-summary-20261024.json。
完整說明README.md；固定交接HANDOFF-ZED-RDF-PG-20261022.md；底表清單department-pg/METRIC-TABLE-SOURCES.md。
未執行來源SQL、資料庫查核、Neo4j部署或Git提交；三項pending及其他暫緩範圍保持。
''',encoding='utf-8')
print('Updated four current documents; pre-change versions retained in snapshot')
