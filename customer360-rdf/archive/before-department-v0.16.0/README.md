# 客戶360：共通 RDF／OWL 與部門 Property Graph

## 本輪 PG 收入擴充（2026-10-24，已依確認清單完成）

修訂識別：`pg-income-extension-20261024`。RDF 及 ontology_version 維持 v0.15.0；五份 RDF 來源、Turtle／OWL 輸出、build-config 與 catalog 均逐位元組未變。

- 新增銀行存款利收 `bank.deposit_interest_income`、海外債券信託手收 `bank.overseas_bond_trust_fee_income`、外國債券自營手收 `bank.overseas_bond_proprietary_fee_income`，放在 bank-business-metrics.json。
- 沿用 `bank.dci_fee_income`、`bank.insurance_fee_income` 的原 ID，分別擴充 DCD／TMU 及兩項保險月檔來源，名稱改為銀行 DCI 手收、銀行保險手收。
- SQL 作業務字典；圖譜保存分類與來源 metadata，計算仍由 Tool 承接。沒有新增 Tool 綁定、欄位映射或可執行公式。
- 新增兩項債券手收沿用理專關係；存款利收不新增理專歸屬。通用商品手收仍維持原 partial_scope，沒有跟著擴大來源。

新備份：archive/before-pg-income-extension-20261024。修訂證據與來源雜湊：department-pg/history/pg-income-extension-20261024.json。僅本機建置／驗證，沒有資料庫部署。

## SQL 查核後的範圍決議（2026-10-24）

使用者確認依原始 SQL 查核結論處理：股票設質只有股票估值 SQL，尚缺可確認的借款／融通餘額來源，不建立 AUM 或 LUM；證券台股保留既有 AUM，手收未找到可辨識分支先不建立；集合管理保留既有 AUM，手收雖有 CASE 分支與底表，但 TA／TB／TD／TE 代碼會先符合前方基金條件，後方集合管理分類被遮蔽，因此先不另建手收，也不自行修改原 SQL 或重複計入。

三筆 pending_scope 只是待辦註記，不是 active 指標。該次範圍查核未新增指標；本輪另外完成上列五項收入範圍調整，RDF 版本維持 v0.15.0。詳見 department-pg/history/sql-scope-review-20261024.json 的來源檔案、行號與 SHA-256。

SQL 執行與計算應由 Tool 承接，圖譜只保留語意與來源 metadata；指標到 Tool 的對應與 Tool 實作尚未完成，不因本次查核而視為已完成。本次未修改來源 SQL、執行 SQL 或部署資料庫。

目前版本：**v0.15.0，2026-10-24，設計草案**。RDF 語意沿用既有確認版；本輪僅擴充 PG 收入範圍，本機輸出已更新，未部署 Neo4j。

前輪 v0.15.0 分類修正快照：[archive/before-v0.15.0](archive/before-v0.15.0/)。本輪備份為 archive/before-pg-income-extension-20261024。最新交接入口沿用 [HANDOFF-ZED-RDF-PG-20261022.md](HANDOFF-ZED-RDF-PG-20261022.md)。完整指標與來源見 [底表清單](department-pg/METRIC-TABLE-SOURCES.md)。

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

bank-business-metrics.json 現共十二項指標、115 個必要元素。既有金額、期間與識別觀察保留，但本批所有實體欄位映射仍為 pending、table／column=null、candidates=[]，execution 全 null。來源只是 observed_in_files／database_verified=false。

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

本模組十二項商品指標的 department_context 記錄使用／定義部門為私人銀行；承作子公司仍為 bank，department_owner 與 source_data_owner 均待定。沒有因私銀使用資料就宣告資料權責歸私銀。

本模組七項手收（規劃型信託、保管、外匯、開狀、黃金、債券信託、債券自營）均參照 bank:attributedToAdvisor；實際理專／員編映射未定。存款與放款利收未新增理專歸屬關係。HAS_BUSINESS_SCOPE 是 PG metadata 範圍參照，不是 RDF Object Property 或實例推論。

bank:FinancialAdvisor 繼承 BankEmployee，沿用 employeeId。fh:serves 表示職員服務客戶，不是閱覽授權。行員存款指存款人本人為行員，不得以管理客戶的 AO 員編代替。權限仍 deferred_by_user。

## 股票設質修正與待辦

依使用者明確決議，securities.stock_pledge_aum 已退出 active AUM 清單，其關係與 DSCSD.PBCMS_REPORTA03 的 active 金額來源關係一起移除。原需求表與 SQL 雖列 AUM，金額證據是設質股票估值，不直接改名為 LUM。

完整舊指標、來源與證據保存在 [退場紀錄](department-pg/history/stock-pledge-aum-retired-v0.15.0.json)，原台股庫存 AUM 保持。來源證據仍留在 investment-metrics.json 的 evidence 供 pending 回查，退場 JSON 不參與建置。

pending_scope 三項：

- securities.stock_pledge_lum：pending_source_definition，待實際借款／融通餘額底表。
- securities.taiwan_stock_fee_income：pending_source_definition，待台股手收底表與範圍。
- bank.collective_account_fee_income：pending_business_semantics，收入定義空白且原 CASE 順序有疑點。

尚未新增：證券／人壽 LUM、總收入彙總、額度／人數及 ROA／ROBA 指標。黃金、外匯、開狀不建立 AUM。開狀原始需求曾列 AUM，但使用者本輪決定先維持手收。

## 其他既有決議保持

- ETF、基金、集合管理各自分列；ETF、集合管理均直接繼承金融商品。ETF AUM 分類取值待確認，不把共用表全部視為單一商品。
- 保險泛指銀行通路商品；AUM 保留原始投資金額意義，手收已包含日報及兩項月檔，PS 保留客戶貢獻度意義，不認定可直接加總。
- SI、ELI、FCI 分列；DCI 手收已含純手續費及 DCD／TMU 分支。一般銀行通用手收仍 partial_scope，本模組七項商品手收分列，未擴大通用來源。
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
| bank-business-metrics.json | 十二項 AUM／LUM／手收／利收，含存款與兩項債券收入 | bank_business_model.py |

customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生，勿手改。department-pg/model.cypher 由七份 active JSON 合併產生，只依賴標準函式庫，不連線資料庫。

目前 42 項指標：**18 AUM、1 LUM、21 手收、2 利收**。52 SourceTable；88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。RDF 為 **41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples**；PG 為 **49 業務概念、652 metadata 節點、1338 關係**，含 413 DataFieldDefinition、60 BusinessRelationDefinition、6 MetadataModule。

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

本輪 **RDF 19＋PG 85＝104 項測試通過，無略過**。驗證來源 SQL 與 metadata 儲存格、LUM／利收／手收 domain 分離、商品統一分類、部門使用與資料權責區分、股票設質退場與歷史完整保留、既有候選保留、新映射空白、反例拒絕與確定性／輸出逐位元組比對。修改前對 24 份來源 SQL／Excel 保存 SHA-256，測試確認來源未改動。

未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI 或 Neo4j 部署。權限、帳戶、分行／數位、欄位映射與畫圖繼續暫緩。不新增 Hash、sameAs、等價、互斥、keys、反向關係、property chain、必填／基數或執行公式。

## 歷史與維護注意

[變更對照](department-pg/history/changes-v0.15.0.json) 記錄四個商品 Class 的 URI 替換、外匯／黃金兩個指標 ID 替換、放款利收 Class 變更與股票設質退場。它是離線紀錄，不是部署或自動遷移腳本。產生器只有 MERGE、不刪舊資料；若未來曾載入舊版資料庫，不能把重跑 MERGE 視為完整同步。

保存性測試各有歷史基準，不全域替換 before-v0.13.0、before-v0.12.0、before-v0.10.0 等路徑。review_contract_v015.py 僅列明本輪核定的名稱／定義文字差異；型別、繼承與 domain／range 的舊語意仍受保留測試約束。完整前版文件在 before-v0.15.0 快照。

歷史一次性 seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 不可重跑覆寫 active JSON；tools/legacy-v0.2.0 不可執行。before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。outputs/rdf-review-v0.7.0 僅供歷史對照。未做 Git 提交、外部部署或已確認雲端備份。

## PG 收入擴充的來源差異與保存驗證

存款 INCOME_066 有三項歷史表與外幣 current 表；不補台幣 current 利收來源。初建與上月替換的私銀條件、UNION ALL／UNION、日期涵蓋不同；原 TMP01 定義註解疑點保留。債券信託 INCOME_031 取 BRHREBATEAMT + WKR028/100；自營 INCOME_032 逐筆 ABS 後加總，不改寫正負號或空值規則。

DCI INCOME_038 僅取 FO108_W 的 DCD，既有 FX 排除 DCD／Cash Bond。保險 INCOME_029／030 取 PS，保留客戶貢獻度意義；次月歸屬、IU／OFI 條件差異、日月重疊與 UNION 整列去重只作觀察。所有 execution 仍為 null，Tool 綁定未完成。

review_contract_pg_income.py 只供歷史測試正規化兩項核定擴充的名稱、定義、來源觀察、底表涵蓋及關係名稱，不忽略 Class、欄位候選或關係語意。test_pg_income.py 另直接檢查本輪來源規則、三項新指標、兩項擴充、RDF 逐位元組未變及來源雜湊。
