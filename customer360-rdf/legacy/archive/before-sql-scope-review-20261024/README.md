# 客戶360：共通 RDF／OWL 與部門 Property Graph

目前版本：**v0.15.0，2026-10-24，設計草案**。本輪依使用者確認的七項變更清單執行；本機來源與輸出已更新，未部署 Neo4j。

本輪修改前快照：[archive/before-v0.15.0](archive/before-v0.15.0/)。最新交接入口沿用 [HANDOFF-ZED-RDF-PG-20261022.md](HANDOFF-ZED-RDF-PG-20261022.md)。完整指標與來源見 [底表清單](department-pg/METRIC-TABLE-SOURCES.md)。

## 本輪已確認的分類

規劃型信託、信託保管、外匯、開狀、黃金、放款，均先納為銀行金融商品，直接繼承 fh:FinancialProduct。移除 v0.14.0 的 FinancialService 與兩個服務專屬關係；本輪不展開帳戶、契約或組織 Class。

| 銀行商品 Class | 私銀 PG 規模指標 | 私銀 PG 收入指標 |
|---|---|---|
| PlannedTrustProduct／規劃型信託 | AUM | 手收 |
| TrustCustodyProduct／信託保管 | AUM | 手收 |
| ForeignExchangeProduct／外匯 | 本輪不新增 | 手收 |
| LetterOfCreditProduct／開狀 | 本輪不新增 | 手收 |
| GoldProduct／黃金 | 本輪不新增 | 手收 |
| LoanProduct／放款 | LUM | 利收 |

bank-business-metrics.json 共九項指標、85 個必要元素。既有金額、期間與識別觀察保留，但本批所有實體欄位映射仍為 pending、table／column=null、candidates=[]，execution 全 null。來源只是 observed_in_files／database_verified=false。

外匯、黃金按照 SQL 的 TYP 歸手收，PG 保留兌換損益、TMU／黃金交易損益的來源性質；放款按照 SQL 歸利收，保留台幣 GROSS_INCM 為毛利、外幣 INT_INCM 減 CB_INT_AMT 的意義。手收不限定為純手續費，利收不限定為純客戶利息。FeeIncome 等既有 URI 沿用，中文名稱與定義同步採業務分類。

## 金控共通指標與必要元素

AUM、LUM、FeeIncome（手收）、InterestIncome（利收）均直接繼承 fh:Metric。銀行各有對應 Class；證券既有 AUM／手收保持，尚未建立證券／人壽 LUM 分項。

| 指標 | 商品關係（Domain → Range） | 按情境適用的共通元素 |
|---|---|---|
| AUM | measuresProduct：AUM → FinancialProduct | metricAmount、aumAsOfDate、valuationQuantity、valuationUnitPrice |
| LUM | lumMeasuresProduct：LUM → FinancialProduct | metricAmount、lumAsOfDate |
| 手收 | feeIncomeFromProduct：FeeIncome → FinancialProduct | metricAmount、incomePeriodStart／End、feeBaseAmount／DeductionAmount |
| 利收 | interestIncomeFromProduct：InterestIncome → FinancialProduct | metricAmount、interestPeriodStart／End |

metricAmount 的 domain 為 Metric、range 為 decimal；日期為 date，估值數量／單價與手收組成為 decimal。沒有必填、固定基數、單位、公式或自動合計。既有 AUM／手收關係與屬性的 domain／range 保持，未把它們擴大到所有 Metric。

LUM 依業務認列口徑衡量放款或融通餘額，不以擔保品估值、收入或未動用額度代替。3.LUM_by_day.sql／4.LUM_BY_HS.sql 提供台外幣 current／歷史四表；5.LUM_MERGE.sql 彙總放款餘額。原彙總含「1886／應付保證」會科標示，實際納入範圍保留待核對，不把整段 SQL 核定成純借款本金公式。放款利收另補外幣 current 收入分支。

## 指標、部門與來源

金控／子公司 RDF 定義共通概念與正式繼承，PG 記錄部門具體指標、必要元素、商品分類參照與來源觀察。底表接在指標 BusinessConcept，不接商品 Class。沒有客戶、人員、商品、部位或交易資料實例。

本輪九項商品指標的 department_context 記錄使用／定義部門為私人銀行；承作子公司仍為 bank，department_owner 與 source_data_owner 均待定。沒有因私銀使用資料就宣告資料權責歸私銀。

本輪五項手收（規劃型信託、保管、外匯、開狀、黃金）均參照 bank:attributedToAdvisor；實際理專／員編映射未定。放款利收未新增理專歸屬關係。HAS_BUSINESS_SCOPE 是 PG metadata 範圍參照，不是 RDF Object Property 或實例推論。

bank:FinancialAdvisor 繼承 BankEmployee，沿用 employeeId。fh:serves 表示職員服務客戶，不是閱覽授權。行員存款指存款人本人為行員，不得以管理客戶的 AO 員編代替。權限仍 deferred_by_user。

## 股票設質修正與待辦

依使用者明確決議，securities.stock_pledge_aum 已退出 active AUM 清單，其關係與 DSCSD.PBCMS_REPORTA03 的 active 金額來源關係一起移除。原需求表與 SQL 雖列 AUM，金額證據是設質股票估值，不直接改名為 LUM。

完整舊指標、來源與證據保存在 [退場紀錄](department-pg/history/stock-pledge-aum-retired-v0.15.0.json)，原台股庫存 AUM 保持。來源證據仍留在 investment-metrics.json 的 evidence 供 pending 回查，退場 JSON 不參與建置。

pending_scope 三項：

- securities.stock_pledge_lum：pending_source_definition，待實際借款／融通餘額底表。
- securities.taiwan_stock_fee_income：pending_source_definition，待台股手收底表與範圍。
- bank.collective_account_fee_income：pending_business_semantics，收入定義空白且原 CASE 順序有疑點。

未順帶新增：存款利收、海外債券收入、DCI TMU、保險月檔客戶貢獻度、證券／人壽 LUM。黃金、外匯、開狀不建立 AUM。開狀原始需求曾列 AUM，但使用者本輪決定先維持手收。

## 其他既有決議保持

- ETF、基金、集合管理各自分列；ETF、集合管理均直接繼承金融商品。ETF AUM 分類取值待確認，不把共用表全部視為單一商品。
- 保險泛指銀行通路商品；AUM 保留原始投資金額意義，日報手收 partial_scope，月檔客戶貢獻度未併入。
- SI、ELI、FCI 分列；DCI 只有純手續費報表，不含 TMU。一般銀行通用手收仍 partial_scope，本輪五項商品手收分列，未擴大通用來源。
- 證券五項 AUM：複委託債券、結構型、基金、外股、台股庫存；四項手收為前四類，外股保留淨手收觀察。證券不套用銀行理專關係，不繼承銀行商品分類。
- 證券基金手收的 BONDTRADM_SEC、外股手收的 AM_SEC 僅供日期查詢；T_LAST_TWO_WORKDAYS 缺 schema，仍是未辨識期間輔助關係。WKB02／WKB24 識別角色、日期、FX、UNION 去重等疑點保持。

## 有效模組與輸出

RDF 五份來源，由 build-config.json 明列：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。catalog-v001.xml 對應本機 URI／v0.15.0。example.org 是示意命名空間，不連網解析。

| PG 來源 | 用途 | 驗證器 |
|---|---|---|
| model.json | 通聯概念 | model.schema.json、build_cypher.py |
| deposits.json | 存款概念與證據 | deposit_model.py |
| advisory-income.json | 理專、服務客戶與通用手收 | advisory_income_model.py |
| product-fees.json | SI／SN、海外股票、ELI／FCI、DCI 六項手收 | product_fees_model.py |
| product-aum.json | 七項銀行商品 AUM | product_aum_model.py |
| investment-metrics.json | 基金／保險／ETF／集合管理與證券十六項指標 | investment_metrics_model.py |
| bank-business-metrics.json | 本輪六類商品、九項 AUM／LUM／手收／利收 | bank_business_model.py |

customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生，勿手改。department-pg/model.cypher 由七份 active JSON 合併產生，只依賴標準函式庫，不連線資料庫。

目前 39 項指標：**18 AUM、1 LUM、19 手收、1 利收**。49 SourceTable；79 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。RDF 為 **41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples**；PG 為 **46 業務概念、611 metadata 節點、1245 關係**，含 383 DataFieldDefinition、55 BusinessRelationDefinition、6 MetadataModule。

## 建置與驗證

```powershell
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s department-pg -v
```

本輪 **RDF 19＋PG 78＝97 項測試通過，無略過**。驗證來源 SQL 與 metadata 儲存格、LUM／利收／手收 domain 分離、商品統一分類、部門使用與資料權責區分、股票設質退場與歷史完整保留、既有候選保留、新映射空白、反例拒絕與確定性／輸出逐位元組比對。修改前對 24 份來源 SQL／Excel 保存 SHA-256，測試確認來源未改動。

未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI 或 Neo4j 部署。權限、帳戶、分行／數位、欄位映射與畫圖繼續暫緩。不新增 Hash、sameAs、等價、互斥、keys、反向關係、property chain、必填／基數或執行公式。

## 歷史與維護注意

[變更對照](department-pg/history/changes-v0.15.0.json) 記錄四個商品 Class 的 URI 替換、外匯／黃金兩個指標 ID 替換、放款利收 Class 變更與股票設質退場。它是離線紀錄，不是部署或自動遷移腳本。產生器只有 MERGE、不刪舊資料；若未來曾載入舊版資料庫，不能把重跑 MERGE 視為完整同步。

保存性測試各有歷史基準，不全域替換 before-v0.13.0、before-v0.12.0、before-v0.10.0 等路徑。review_contract_v015.py 僅列明本輪核定的名稱／定義文字差異；型別、繼承與 domain／range 的舊語意仍受保留測試約束。完整前版文件在 before-v0.15.0 快照。

歷史一次性 seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 不可重跑覆寫 active JSON；tools/legacy-v0.2.0 不可執行。before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。outputs/rdf-review-v0.7.0 僅供歷史對照。未做 Git 提交、外部部署或已確認雲端備份。
