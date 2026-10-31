# 客戶360：共通 RDF／OWL 與部門 Property Graph

## 先看這裡（2026-10-27 整理）

目前有效模型是 **v0.16.0**，模型最後更新為 2026-10-24。只要看私銀指標，先開 [44 項指標與來源表](department-pg/METRIC-TABLE-SOURCES.md)。

| 要找的內容 | 目前位置 |
|---|---|
| 完整 RDF／OWL | [customer360-ontology.ttl](customer360-ontology.ttl)、[customer360-ontology.owl](customer360-ontology.owl)，由來源模組產生 |
| 可編輯的 RDF 來源 | 根目錄五份 TTL：holding-core、bank-deposit、bank-common、bank-investment-products、securities-common |
| 最新 PG | [department-pg/](department-pg/) 內九份業務 JSON；model.json 只含通聯，不代表整份 PG |
| 圖譜、問答、推理與交接展示 | [semantica-poc/README.md](semantica-poc/README.md)；執行該資料夾的 launch.ps1 |
| 回歸測試 | tests/（RDF／Fabric）、tests/pg/（PG）；介面與推理測試留在 semantica-poc/ |
| 最新可選 Fabric 匯出 | outputs/fabric-v0.16.0/ 與同版 ZIP，屬完整技術 metadata 匯出 |
| 歷史版本、草稿與舊實作 | [archive/README.md](archive/README.md)，不是目前建置來源 |

本機圖譜：http://127.0.0.1:8866/；圖譜問答：http://127.0.0.1:8866/ask；交接示範：http://127.0.0.1:8866/handoff。需先啟動服務。
目前問答本體推理使用 **Semantica Reasoner**；舊 HermiT 已歸檔。畫布保持 146 節點／246 關係，只顯示一個 RDF 私銀部門，連到 44 項 PG 指標。以下建模紀錄的 PG metadata 數量與畫布顯示數量不同。

## 本輪：證券總指標涵蓋範圍（securities-summary-20261024）

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

新備份 archive/before-securities-summary-20261024；修訂與來源SHA-256見 archive/department-pg/history/securities-summary-20261024.json。本輪沒有執行來源SQL、資料庫查核、Git提交或Neo4j部署。

目前版本 **v0.16.0，2026-10-24，設計草案**。部門建模與指標名稱沿用v0.16.0；本輪依確認清單完成證券總指標PG涵蓋定義，僅本機建置與驗證，未部署Neo4j。

固定交接入口：[HANDOFF-ZED-RDF-PG-20261022.md](HANDOFF-ZED-RDF-PG-20261022.md)。指標來源：[METRIC-TABLE-SOURCES.md](department-pg/METRIC-TABLE-SOURCES.md)。本輪備份：[archive/before-securities-summary-20261024](archive/before-securities-summary-20261024/)。前輪部門備份：archive/before-department-v0.16.0。

## 既有 v0.16.0 部門與命名

| 層級 | 本輪內容 |
|---|---|
| 金控 RDF | 新增 fh:Department（部門），及 fh:usesMetric（採用指標，Department → Metric） |
| 銀行 RDF | 新增 bank:PrivateBankingDepartment，直接繼承 fh:Department，表達私人銀行部門類型 |
| 私銀 PG | 新增 bank.private_banking（私銀），參照銀行部門類型，採用44項指標（42項原分項／指標加2項證券總指標） |
| PG 指標名稱 | 全部加「私銀－」並保留銀行／證券來源，如「私銀－銀行基金 AUM」「私銀－證券複委託債券 AUM」 |

原42項指標的ID、商品分類、定義、來源、欄位候選、理專關係及計算口徑均保留；本輪原七份JSON逐位元組保持，部門清單只加兩項總指標。商品、人員、通聯概念不加私銀前綴；RDF 銀行 AUM／手收等共通類別名稱不改。

fh:Department 是 Class；既有 fh:department 繼續作治理註記。bank:PrivateBankingDepartment 是部門類型，PG 的 bank.private_banking 是 metadata 概念，沒有建立真實組織實例。先只有私銀一層，不拆一部、二部、分行或團隊。

PG USES_METRIC 是採用範圍連線，由同一模組的關係定義參照 RDF usesMetric；HAS_PARENT_CLASS_REFERENCE 只鏡射已宣告的 RDF 類型父類參照，不做 PG 推論。採用指標不等於承作商品、資料權責、理專收入歸屬、閱覽權限或自動合計。

## 指標、商品與計算邊界

共44項指標：19 AUM（銀行13／證券6）、1銀行 LUM、22手收（銀行17／證券5）、2銀行利收。私銀採用全部44項，包括通用商品手收；後者仍為原 partial_scope，沒有擴大來源或當成完整總手收。

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
| departments.json | 私銀部門與44項採用範圍；department_model.py |
| securities-summary-metrics.json | 證券兩項總指標與分項涵蓋；securities_summary_model.py |

customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生；model.cypher 由九份 active JSON 合併產生，勿手改。archive/department-pg/ 下的 history／drafts 不參與建置。

## 統計與驗證

RDF：43 Class、9 Object Property、19 Data Property、5 Annotation Property、434 triples。PG：52 BusinessConcept、668 metadata節點、1415關係，含420 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、8 MetadataModule、7 MappingSlot。44條 USES_METRIC、9條 HAS_COMPONENT_METRIC；原88金額來源、3估值輔助、2日期查詢連線保持。

RDF19＋PG101＝120項測試通過，無略過。前輪部門新增與42項命名持續受保存性測試約束；本輪驗證RDF與原七份JSON逐位元組未變、兩項總指標／九條涵蓋與44項採用正確、欄位候選／來源／理專關係保留、錯誤範圍與執行規則反例、確定性及產出一致。24份 SQL／Excel SHA-256 未變。

```powershell
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests/pg -v
```

上述為模型建置階段紀錄。後續圖譜、問答、規則推理及示範 SHACL 已於 semantica-poc 實作，詳見其 README；真實資料庫查核、SQL 執行與 Neo4j 部署仍未完成。

## 已確認待辦與來源疑點

- 股票設質 LUM、台股手收缺可確認來源，先不建立；股票設質估值不當 AUM 或 LUM。原台股 AUM 保留。
- 集合管理手收 CASE 的 TA／TB／TD／TE 分支被前方基金條件遮蔽，保持 pending，不改 SQL；原集合 AUM 保留。
- 銀行總AUM／總收入、目標達成率等尚未新增；本輪僅完成兩項證券總指標的涵蓋定義。客戶數／分群、放款額度／人數尚未建模；Organic／Migration／轉介依賴人工來源，未確認完整性。
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

前輪部門修訂紀錄 archive/department-pg/history/department-v0.16.0.json 列出42項名稱前後對照及新增語意；本輪兩項總指標另記於 securities-summary-20261024.json。舊 history 原文保持。MERGE 不刪舊資料；未來部署前須確認目標 namespace，不能假設重跑即完整同步。

保存性測試各有歷史基準，不全域替換 archive 路徑。review_contract_v016.py 只在測試中還原核定名稱或移除本輪新增主詞及版本標頭；來源、欄位、型別、權責與計算規則仍受完整比對。test_departments.py 直接驗證本輪精確新增與命名。

不重跑歷史一次性 seeder 或 archive/cleanup-20261027/tools/legacy-v0.2.0。archive/cleanup-20261027/outputs/department-v0.16.0/apply.py 為本輪已執行的一次性維護紀錄，不是建置入口；before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。歷史圖與舊文件不代表本版。

## 本輪總指標驗證與查閱

test_securities_summary.py 直接驗證兩項／九條精確涵蓋、RDF逐位元組未變、原七份JSON與歷史不變、部門只新增兩個採用ID、既有節點／關係保存、七個空映射、SQL證據／草稿狀態、原來源角色、錯誤範圍／公式反例及產出確定性。底表清單把兩項總指標標成「沿分項追溯」；同一表在不同分項可同時作金額來源及日期查詢，分角色呈現。

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(t:BusinessConcept)
MATCH (t)-[:HAS_COMPONENT_METRIC]->(c:BusinessConcept)
OPTIONAL MATCH (c)-[:HAS_SOURCE_TABLE|USES_VALUATION_SOURCE|USES_DATE_LOOKUP_SOURCE]->(s:SourceTable)
RETURN d, t, c, s;
```

此查詢供未來已載入metadata的Neo4j Browser查閱，本輪未執行。HAS_COMPONENT_METRIC只表涵蓋，不是可執行SUM、正式RDF繼承或資料實例。產生器只MERGE，沒有部署／刪舊資料或自動遷移。銀行總量及目標比較繼續暫緩。

## Fabric 圖譜匯入包（2026-10-24）

已新增獨立的 RDF＋PG 視覺化投影，詳見 [FABRIC-GRAPH.md](FABRIC-GRAPH.md)。`tools/export_fabric_graph.py` 產出自含資料的 Fabric PySpark Notebook、Graph model 定義範本與 GQL 檢視到 `outputs/fabric-v0.16.0/`。原模型及業務 SQL 均未改動；677 個節點、1,498 條關係保留全部 PG metadata，另加明確標示的 RDF schema 宣告，434 個 RDF triples 另存 audit。預設查詢維持私銀與證券優先。**目前僅本機準備，尚未登入目標工作區或完成 Fabric 部署／同步／互動驗收。**
