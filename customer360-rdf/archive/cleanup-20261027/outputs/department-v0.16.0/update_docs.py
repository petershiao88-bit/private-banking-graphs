"""Write current documentation; full previous documents remain in the snapshot."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

readme='''# 客戶360：共通 RDF／OWL 與部門 Property Graph

目前版本 **v0.16.0，2026-10-24，設計草案**。本輪依使用者逐項確認及「可以，啟動」完成部門建模與指標名稱調整，僅本機建置與驗證，未部署 Neo4j。

固定交接入口：[HANDOFF-ZED-RDF-PG-20261022.md](HANDOFF-ZED-RDF-PG-20261022.md)。指標來源：[METRIC-TABLE-SOURCES.md](department-pg/METRIC-TABLE-SOURCES.md)。修改前完整備份：[archive/before-department-v0.16.0](archive/before-department-v0.16.0/)。

## 本輪新增與命名

| 層級 | 本輪內容 |
|---|---|
| 金控 RDF | 新增 fh:Department（部門），及 fh:usesMetric（採用指標，Department → Metric） |
| 銀行 RDF | 新增 bank:PrivateBankingDepartment，直接繼承 fh:Department，表達私人銀行部門類型 |
| 私銀 PG | 新增 bank.private_banking（私銀），參照銀行部門類型，採用現有42項指標 |
| PG 指標名稱 | 全部加「私銀－」並保留銀行／證券來源，如「私銀－銀行基金 AUM」「私銀－證券複委託債券 AUM」 |

42項既有指標 ID、商品分類、定義、來源、欄位候選、理專關係及計算口徑均保留；既有七份 JSON 僅改版本與指標顯示名稱。商品、人員、通聯概念不加私銀前綴；RDF 銀行 AUM／手收等共通類別名稱不改。

fh:Department 是 Class；既有 fh:department 繼續作治理註記。bank:PrivateBankingDepartment 是部門類型，PG 的 bank.private_banking 是 metadata 概念，沒有建立真實組織實例。先只有私銀一層，不拆一部、二部、分行或團隊。

PG USES_METRIC 是採用範圍連線，由同一模組的關係定義參照 RDF usesMetric；HAS_PARENT_CLASS_REFERENCE 只鏡射已宣告的 RDF 類型父類參照，不做 PG 推論。採用指標不等於承作商品、資料權責、理專收入歸屬、閱覽權限或自動合計。

## 指標、商品與計算邊界

共42項指標：18 AUM（銀行13／證券5）、1銀行 LUM、21手收（銀行17／證券4）、2銀行利收。私銀採用全部42項，包括通用商品手收；後者仍為原 partial_scope，沒有擴大來源或當成完整總手收。

金控 AUM、LUM、FeeIncome（手收）、InterestIncome（利收）均繼承 Metric。商品關係分別 measuresProduct、lumMeasuresProduct、feeIncomeFromProduct、interestIncomeFromProduct，各自 domain 不混用，range 為 FinancialProduct。金額與基準日／期間元素沿用；沒有新增公式、必填、基數、等價、互斥或實例斷言。

規劃型信託、保管均有 AUM／手收；外匯、開狀、黃金僅保留手收；放款有 LUM／利收，沒有放款 AUM。六類均先納為金融商品。ETF、基金、集合管理分列；SI／ELI／FCI 分列。證券不繼承銀行商品或套用銀行理專關係。

前輪已新增存款利收、債券信託手收、自營債券手收，並擴充 DCI 的 DCD／TMU、保險兩項 PS 月檔；原指標 ID、來源性質及日月重疊疑點保留。收入依 SQL 分類，手收不限定純手續費、利收不限定純客戶利息。

SQL 作業務字典；圖譜保存語意與來源 metadata，計算與 SQL 執行由 Tool 承接。Tool 綁定與實作尚未完成。所有 execution 欄位仍 null；欄位映射待定，舊候選保留，新欄位候選空白。SourceTable 為 observed_in_files、database_verified=false。

底表關係只由指標出發：HAS_SOURCE_TABLE 為金額來源、USES_VALUATION_SOURCE 為估值輔助、USES_DATE_LOOKUP_SOURCE 為日期查詢。私銀部門不直接接底表；承作子公司、資料權責與理專關係分開保留。

## 有效來源與輸出

RDF五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。build-config.json／catalog-v001.xml 與 active JSON 同步 v0.16.0。example.org 是示意命名空間，不連網解析。

| PG JSON | 用途／驗證器 |
|---|---|
| model.json | 通聯；model.schema.json／build_cypher.py |
| deposits.json | 存款概念；deposit_model.py |
| advisory-income.json | 理專、服務客戶、通用手收；advisory_income_model.py |
| product-fees.json | 六項銀行手收；product_fees_model.py |
| product-aum.json | 七項銀行商品 AUM；product_aum_model.py |
| investment-metrics.json | 基金／保險／ETF／集合管理與證券16項指標；investment_metrics_model.py |
| bank-business-metrics.json | 12項銀行指標；bank_business_model.py |
| departments.json | 私銀部門與42項採用範圍；department_model.py |

customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生；model.cypher 由八份 active JSON 合併產生，勿手改。history／drafts 不參與建置。

## 統計與驗證

RDF：43 Class、9 Object Property、19 Data Property、5 Annotation Property、434 triples。PG：50 BusinessConcept、658 metadata節點、1388關係，含413 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、7 MetadataModule、7 MappingSlot。新增42條 USES_METRIC；原88金額來源、3估值輔助、2日期查詢連線保持。

RDF19＋PG92＝111項測試通過，無略過。驗證本輪僅新增兩個 RDF Class／一個 Property、舊 RDF 定義保存、七份舊 JSON 僅改名稱與版本、42項採用範圍與子公司保留、欄位候選／來源／理專關係不變、錯誤目標與所有權反例、確定性及輸出逐位元組一致。24份 SQL／Excel SHA-256 未變。

```powershell
.venv\\Scripts\\python.exe -X utf8 -B tools\\build_ontology.py
.venv\\Scripts\\python.exe -X utf8 -B tools\\build_ontology.py --check
.venv\\Scripts\\python.exe -X utf8 -B department-pg\\build_cypher.py
.venv\\Scripts\\python.exe -X utf8 -B tools\\export_metric_tables.py
.venv\\Scripts\\python.exe -X utf8 -B tools\\export_metric_tables.py --check
.venv\\Scripts\\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\\Scripts\\python.exe -X utf8 -B -m unittest discover -s department-pg -v
```

未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI、Neo4j部署或Git提交。權限、帳戶、分行／數位、實體欄位映射與畫圖仍暫緩。

## 已確認待辦與來源疑點

- 股票設質 LUM、台股手收缺可確認來源，先不建立；股票設質估值不當 AUM 或 LUM。原台股 AUM 保留。
- 集合管理手收 CASE 的 TA／TB／TD／TE 分支被前方基金條件遮蔽，保持 pending，不改 SQL；原集合 AUM 保留。
- 總 AUM／總收入、目標達成率等彙總指標未新增。客戶數／分群、放款額度／人數尚未建模；Organic／Migration／轉介依賴人工來源，未確認完整性。
- ROA／ROBA 僅在原 SQL 註解有比率定義，程式實際彙整分子與分母，不宣稱已計算比率。
- ETF AUM 分類、保險原始投資金額、信託累計費用、存款歷史與月替換篩選差異、債券逐筆 ABS、DCI 與 FX 的 DCD 範圍、保險日月重疊、LUM 1886會科與日期／換匯等疑點保留，詳見 JSON 來源觀察與底表清單。
- 證券基金 BONDTRADM_SEC、外股 AM_SEC 僅日期查詢；T_LAST_TWO_WORKDAYS 缺 schema／底層定義，維持未辨識期間輔助關係。

## 查閱與保存

以下查詢供未來已載入本版 metadata 的 Neo4j Browser 使用；本輪沒有執行資料庫查詢。

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(m:BusinessConcept)
RETURN d, m;
```

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(m:BusinessConcept)
MATCH (m)-[:HAS_SOURCE_TABLE|USES_VALUATION_SOURCE|USES_DATE_LOOKUP_SOURCE]->(s:SourceTable)
RETURN d, m, s;
```

本輪修訂紀錄 department-pg/history/department-v0.16.0.json 列出42項名稱前後對照及新增語意。舊 history 原文保持。MERGE 不刪舊資料；未來部署前須確認目標 namespace，不能假設重跑即完整同步。

保存性測試各有歷史基準，不全域替換 archive 路徑。review_contract_v016.py 只在測試中還原核定名稱或移除本輪新增主詞及版本標頭；來源、欄位、型別、權責與計算規則仍受完整比對。test_departments.py 直接驗證本輪精確新增與命名。

不重跑歷史一次性 seeder 或 tools/legacy-v0.2.0。outputs/department-v0.16.0/apply.py 為本輪已執行的一次性維護紀錄，不是建置入口；before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。歷史圖與舊文件不代表本版。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')

pg='''# 私銀部門 PG metadata v0.16.0

本輪完成「部門 → 私銀部門類型 → 私銀採用指標」。共通語意與完整操作見 [專案 README](../README.md)，來源見 [底表清單](METRIC-TABLE-SOURCES.md)。修改前備份 ../archive/before-department-v0.16.0。

## 部門模組

departments.json 是第八份 active JSON，department_model.py 作 executable schema。定義一個 BusinessConcept：bank.private_banking（私銀），參照 bank:PrivateBankingDepartment；後者在 RDF 繼承 fh:Department。fh:department 原治理註記保持。

私銀透過 USES_METRIC 採用42項現有指標，對應 RDF fh:usesMetric（Department → Metric）。同模組用一個 BusinessRelationDefinition 保存共通採用關係；HAS_PARENT_CLASS_REFERENCE 鏡射 RDF 部門父類，HAS_DOMAIN_CLASS／HAS_RANGE_CLASS 保存新關係的共通參照。皆為 metadata，沒有組織／客戶／交易實例或 PG 推論。

所有42項指標顯示名稱加「私銀－」，銀行／證券來源保留，ID與其他內容不變。通用手收也納入，仍維持原 partial_scope；商品、人員、通聯概念不改名。不拆私銀一部／二部或新增目標／彙總指標。

部門的 subsidiary=bank 只描述部門所在子公司；證券來源指標仍 subsidiary=securities。採用不決定資料權責或理專歸屬，department_owner／source_data_owner 待定。指標仍透過原關係接到底表，部門不直接接底表。

## 模組與建置

八份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments。各以 schema／Python 驗證器檢查，再由 build_cypher.py 合併。既有 render_cypher 聯絡資訊 API 保留；build_combined_graph／render_combined_cypher 新增尾端可選 department_model 參數，舊呼叫保持可用。

42項指標：18 AUM、1 LUM、21手收、2利收；50 BusinessConcept、658節點、1388關係。含413 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、7 MetadataModule、7 MappingSlot。42 USES_METRIC；88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE 保持。

bank-business-metrics 的12項、115個空欄位定義保持；其他舊候選也保持。所有 execution=null；工具負責 SQL 執行與計算，Tool 綁定尚未完成。history／drafts／outputs 不參與建置，不重跑歷史 seeder。

## 測試與待辦

PG92＋RDF19＝111項測試通過，無略過。test_departments.py 檢查精確 RDF 新增、舊 JSON 僅改版本／名稱、全部採用與來源可達、子公司／權責／理專分離、錯誤目標反例、確定性與來源雜湊。舊測試的歷史路徑保持，review_contract_v016.py 僅正規化核定顯示名稱與 RDF 新增主詞；其餘語意不忽略。

三項 pending 保持：股票設質 LUM、台股手收缺來源，集合管理手收 CASE 遮蔽。總 AUM／總收入／目標比較、客戶數／分群、放款額度／人數與 ROA／ROBA 尚未新增。權限、帳戶、分行／數位、畫圖與欄位映射仍暫緩。

部門異動見 history/department-v0.16.0.json；前輪收入擴充與股票設質退場等 history 原文保持。產生的 Cypher 只 MERGE，沒有部署／自動遷移或刪除舊資料。
'''
(ROOT/'department-pg/README.md').write_text(pg,encoding='utf-8')

handoff='''# 客戶360 RDF／OWL＋私銀部門 PG：v0.16.0 交接

更新2026-10-24。固定沿用本檔名作正式入口；先讀 ../AGENTS.md、本檔、README.md，再讀 department-pg/METRIC-TABLE-SOURCES.md。

工作目錄 C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。使用者要求先討論實質變更清單、確認再執行；本輪已逐項確認，最後指示「可以，啟動」，已完成本機建置／驗證，沒有部署。方向保持證券優先；可確認來源的證券商品指標已納入。

## 本輪完成的範圍

1. 金控新增 fh:Department、fh:usesMetric（Department → Metric）；銀行新增 bank:PrivateBankingDepartment，直接繼承 Department。原 fh:department 仍為治理註記。五份來源／整合輸出／catalog／active JSON 同步0.16.0。
2. 新增 PG departments.json 及 department_model.py，只有 bank.private_banking（私銀）一層。它是 metadata 概念並參照部門類型，不建立真實組織實例，不拆一部／二部、分行或團隊。
3. 私銀用42條 USES_METRIC 連到全部既有指標，含AUM／手收／LUM／利收及通用部分範圍手收。關係定義參照 RDF usesMetric；PG 保存父類／domain／range參照但不推論。
4. 42項指標顯示名稱加私銀並保留銀行／證券來源；ID、定義、欄位候選、底表、理專關係與計算口徑保持。七份舊 active JSON 除 ontology_version 與指標 name 外完全相同。
5. 採用不等於承作子公司、來源權責、理專歸屬、閱覽權限或自動加總。私銀部門屬銀行；證券指標仍屬證券。原 department_owner=null 等內容不因新增部門而改寫。

本輪備份 archive/before-department-v0.16.0；名稱前後對照與新增 URI 見 department-pg/history/department-v0.16.0.json。前一輪詳細交接完整保存在本輪備份；更早 archive/before-pg-income-extension-20261024、before-v0.15.0 等保持。history 不參與建置，原記錄逐位元組保持。

## 架構與原有決議保持

RDF 定義共通／子公司類別和正式繼承；PG 描述部門、具體指標、商品範圍與來源 metadata。圖譜保存定義，SQL 執行與計算交給 Tool。Tool 綁定及實作尚未完成；所有 execution=null，實體欄位映射待定，舊候選保留，新增候選空白。SourceTable observed_in_files、database_verified=false；原SQL cp950，JSON／Turtle UTF-8。

AUM、LUM、FeeIncome（手收）、InterestIncome（利收）直接繼承Metric；商品關係分別measuresProduct、lumMeasuresProduct、feeIncomeFromProduct、interestIncomeFromProduct，domain分離、range=FinancialProduct。RDF銀行／證券指標Class不加私銀前綴。指標的底表關係保持，不從部門或商品Class直接接底表。

規劃型信託、保管、外匯、開狀、黃金、放款先統一金融商品；規劃型信託／保管有AUM及手收，外匯／開狀／黃金只有手收，放款有LUM與利收，沒有放款AUM。FinancialService及服務專屬關係已退出。ETF、基金、集合管理分列，SI／ELI／FCI分列。證券不繼承銀行商品分類，也不套用銀行理專關係。

前輪已補存款利收、債券信託／自營手收；DCI擴充DCD／TMU、保險擴充兩項PS月檔，ID保留。收入按SQL業務分類，手收不限定純手續費，利收不限定純客戶利息。通用商品手收維持原partial_scope，不是完整總手收或可直接相加清單。

bank-business-metrics共12項、115欄位定義，全部pending／null、candidates=[]。使用／定義部門原為私人銀行，來源權責待定；七項手收沿用理專關係，存款／放款利收未加理專歸屬。行員存款須識別存款人本人為行員，不以AO員編代替；serves不代表閱覽授權。

來源疑點保持：存款GROSS_INCM、初建私銀條件與月替換差異、TMP01註解問題；債券信託BRHREBATEAMT+WKR028/100、自營SUM(ABS(INC_AMT_NT))；DCI只取FO108_W的DCD，FX排除DCD／Cash Bond；保險PS為客戶貢獻度、跨次月、日月重疊與UNION投影去重；保險AUM原始投資金額；ETF AUM分類取值；信託累計費用；LUM會科1886／應付保證及日期／匯率；證券WKB02／WKB24識別、日期、FX與UNION等。均為檔案觀察，不擅改原SQL。

證券基金BONDTRADM_SEC、外股AM_SEC僅日期查詢；T_LAST_TWO_WORKDAYS缺schema／底層定義，維持unresolved_supporting_relations，不補造來源表。

## 三項pending及後續範圍

pending_scope精確保持三筆，均不是active指標：

- securities.stock_pledge_lum：pending_source_definition，股票設質只有Qty×Product_Price估值，缺實際借款／融通餘額，不建AUM或LUM。
- securities.taiwan_stock_fee_income：pending_source_definition，未找到可辨識收入分支，先不建；原台股AUM保留。
- bank.collective_account_fee_income：pending_business_semantics，TA／TB／TD／TE先被前方基金CASE遮蔽，先不另建，不改SQL；原集合AUM保留。

總AUM／總收入、目標達成率等彙總指標留下一輪確認。客戶母體、客戶數／分群、放款額度／人數尚未建模；Organic／Migration／轉介依賴人工來源未確認完整。11.TARGET.sql確實計算達成率；10._INCOME_ROA.sql僅註解寫ROA／ROBA比率，程式只彙整分子／分母，未實作除法。

股票設質退場及舊ID對照保存在history/stock-pledge-aum-retired-v0.15.0.json、changes-v0.15.0.json；SQL範圍查核見sql-scope-review-20261024.json。權限、帳戶、分行／數位、畫圖與實體欄位映射繼續暫緩。

## Active來源與統計

RDF5份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。PG8份：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments，各有schema／Python驗證器。RDF輸出由tools/build_ontology.py產生，PG由department-pg/build_cypher.py合併，只依賴標準函式庫，不手改產生檔、不連網解析example.org。

42項指標：18AUM（銀行13／證券5）、1銀行LUM、21手收（銀行17／證券4）、2銀行利收；新增部門不增加指標數。

RDF：43Class、9Object Property、19Data Property、5Annotation Property、434triples。PG：50BusinessConcept、658節點、1388關係，含413DataFieldDefinition、52SourceTable、61BusinessRelationDefinition、7MetadataModule、7MappingSlot。42USES_METRIC；88HAS_SOURCE_TABLE、3USES_VALUATION_SOURCE、2USES_DATE_LOOKUP_SOURCE。

RDF19＋PG92＝111項測試通過，無略過。精確新增兩Class／一Property、舊語意／JSON保存、42項命名與採用、跨子公司及所有權分離、來源可達、錯誤目標／權限／執行規則反例、確定性與逐位元組產出一致均驗證。24份來源SQL／Excel SHA-256未變。

建置／測試命令見README。未執行來源SQL、真實資料庫查核、完整OWL reasoner、SHACL、GUI、Neo4j部署或Git提交，也沒有已確認雲端備份。

## 維護注意

保存性測試各有歷史基準，不能全域換archive路徑。review_contract_v015.py與review_contract_pg_income.py保留前輪核定差異；review_contract_v016.py僅供測試還原核定顯示名稱、移除三個新增RDF主詞與版本標頭，來源、欄位、型別、權責及規則不忽略。test_departments.py直接驗證本輪精確異動。

歷史一次性seeder與tools/legacy-v0.2.0不可重跑。outputs/department-v0.16.0/apply.py為本輪已執行的維護紀錄，不是建置入口。before-deposit-pg-correction為錯誤組合OWL實作，不可恢復。舊圖與舊文件不代表本版。

Cypher只有MERGE，沒有刪舊資料或自動遷移。未來部署須先確認目標namespace與舊版範圍，不能假設重跑即完整同步。本輪未部署。
'''
(ROOT/'HANDOFF-ZED-RDF-PG-20261022.md').write_text(handoff,encoding='utf-8')
(ROOT/'README.txt').write_text('''客戶360 RDF／OWL＋私銀部門PG v0.16.0，2026-10-24。
金控新增Department、usesMetric；銀行新增PrivateBankingDepartment類型。
PG新增私銀bank.private_banking，採用42項既有指標；顯示名稱加私銀並保留銀行／證券來源，ID不變。
採用不決定承作子公司、資料權責、理專歸屬、權限或自動加總。
42項指標：18AUM、1LUM、21手收、2利收；來源、候選與計算口徑保持。
RDF：43Class、9Object Property、19Data Property、5Annotation Property、434triples。
PG：50概念、658節點、1388關係、413DataFieldDefinition、52SourceTable、42USES_METRIC。
RDF19＋PG92＝111項測試通過，無略過；24份來源SQL／Excel雜湊未變。
修改前備份archive/before-department-v0.16.0；修訂紀錄department-pg/history/department-v0.16.0.json。
README.md為完整說明，固定交接HANDOFF-ZED-RDF-PG-20261022.md，底表清單department-pg/METRIC-TABLE-SOURCES.md。
總量／目標比較留待下一輪；三項pending與原有暫緩範圍保持。
Tool負責SQL與計算，綁定尚未完成；未執行來源SQL、部署Neo4j或Git提交。
''',encoding='utf-8')
print('Updated four current documents; prior complete versions remain archived')
