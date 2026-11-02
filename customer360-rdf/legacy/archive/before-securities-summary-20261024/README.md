# 客戶360：共通 RDF／OWL 與部門 Property Graph

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
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s department-pg -v
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
