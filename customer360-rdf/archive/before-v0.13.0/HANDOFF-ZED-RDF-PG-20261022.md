# 客戶360 RDF／OWL＋部門 PG：v0.12.0 交接

更新：2026-10-22。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 最新決議與結果：ETF

bank:ETFProduct 依使用者決議直接繼承 fh:FinancialProduct，不繼承 bank:FundProduct；治理歸銀行。PG 的 bank.etf_aum／bank.etf_fee_income 與既有基金指標分列，不自動合計。

| PG 指標 | RDF 指標／商品參照 | 金額來源底表 |
|---|---|---|
| bank.etf_aum，銀行 ETF AUM | bank:BankAUM／bank:ETFProduct | DSFND.PB_FUND_MONTH |
| bank.etf_fee_income，銀行 ETF 手續費收入 | bank:BankFeeIncome／bank:ETFProduct | DSFND.PB_FUND_SPREAD_DAILY |

僅新增表級來源及必要元素，AUM 八欄位、手收十一欄位全部 pending、table／column 全 null、candidates 全空。AUM 用 fh:measuresProduct，手收用 fh:feeIncomeFromProduct；銀行手收沿用 bank:attributedToAdvisor，實際理專歸屬仍待定。來源接在指標上，商品分類沒有底表關係。

手收 SQL 有 ETF 分支；AUM SQL 共用底表並保留 ELSE TRUSTPRD，ETF 實際分類取值仍待確認。兩項來源皆為檔案觀察，database_verified=false；不把全表視為 ETF、不新增分類執行規則。既有基金及其他指標、欄位候選與關係保持。通用手收補充 ETF 涵蓋說明，沿用相同共用底表，仍是 partial_scope。

## 前批保險決議與結果（v0.11.0）

使用者確認：銀行保險共通分類泛指銀行通路提供的保險商品，私銀實際涵蓋哪些保險留在 PG。已新增 bank:InsuranceProduct，直接繼承 fh:FinancialProduct，治理歸銀行；不限定投資型或其他特定保險，不建立保單／契約模型。定義放在既有 bank-investment-products.ttl，模組顯示名稱改為銀行共通商品分類；沿用舊檔名與 URI 不代表所有保險都是投資型。

investment-metrics.json 新增兩項指標：

| PG 指標 | RDF 指標／商品參照 | 金額來源底表 | 來源性質 |
|---|---|---|---|
| bank.insurance_aum，銀行保險 AUM | bank:BankAUM／bank:InsuranceProduct | DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT | 彙總 SQL 註記原始投資金額，不直接視為保單市值或現金價值 |
| bank.insurance_fee_income，銀行保險手續費收入 | bank:BankFeeIncome／bank:InsuranceProduct | DSINS.INSU_RPT_Q01 | 目前僅涵蓋明確標示手收的日報，status=partial_scope |

新 AUM 八個、手收十一個欄位均 pending，table／column 全 null、candidates 全空。AUM 用 fh:measuresProduct，手收用 fh:feeIncomeFromProduct；銀行手收另參照 bank:attributedToAdvisor，實際歸屬未核定。

DSKPI.KPI_DET_IU_002_NEW、DSKPI.KPI_DET_OFI_001 的 PS 在 metadata 定義為客戶貢獻度，不直接併入手續費金額來源。其 SQL 與 metadata 證據保留在 observations／evidence，沒有建立金額來源表關係。日報 current 金額的特定月份限制也保留，未查驗完整時間覆蓋，不視為完整保險收入清冊。

保險 AUM 的 metadata 工作表名稱截短為 DSKPI.AFAUM_AFCUST_MON_ASSET_RE；完整底表名依 SQL 記錄，未宣告資料庫別名。原始投資金額意義可追溯到 2._AUM_SUMY.sql 第 21–39 行。來源只是檔案觀察，database_verified=false。

## 已完成的銀行與證券指標

目前 15 項 AUM、14 項手收都有 table_sources，來源接在指標 BusinessConcept 上，不接商品分類。清單見 department-pg/METRIC-TABLE-SOURCES.md。

- 銀行 AUM：台幣／外幣／結構型存款、海外股票、海外債券（信託／自營）、境外結構型、基金、保險、ETF，共十項。
- 證券 AUM：複委託債券、結構型、基金、外股、台股，共五項。
- 銀行手收：通用手收、SI、SN、基金、海外股票、ELI、FCI、DCI 純手續費、保險日報手收、ETF，共十項。
- 證券手收：複委託債券、結構型、基金、外股，共四項。台股手收仍缺來源定義。

前批新增的海外股票／ELI／FCI／DCI 手收保留。DCI 只涵蓋 INCOME_037 的手續費報表來源，不包含 INCOME_038／DSTAS.FO108_W 的 TMU 損益，不等同結構型存款；ELI／FCI 與 SI 分開，不自動合計，也沒有新增其 AUM。四項手收的 44 個欄位仍全部 pending／null，候選為空。

通用手收已納入盤點過的保險日報底表，本輪另補 ETF 涵蓋說明，仍標 partial_scope，不代表完整銀行總手收來源或直接加總。既有概念、欄位、候選、來源與關係保留；本輪同步 ontology_version 至 0.12.0。

## 最新範圍澄清

金控層級只需 AUM／手收指標與計算必要元素，不要求詳細公式。公式、毛淨額算法、選日與月底跨月規則留在子公司／部門，不是本階段共通建模的確認前提。

欄位映射先不處理。客戶／商品識別、幣別匯率、收入期間與實際理專歸屬繼續待定；權限、帳戶模型、分行／數位及畫圖仍暫緩。未確認範圍不自行擴充，不把來源 SQL 當執行規則。

後續待討論：集合管理、規劃型信託、員工持股與信託保管；海外債券收入中的交易利得與自營收入性質；FX／黃金／DCI 的 TMU 損益；開狀服務；存款／放款利收；保險月檔客戶貢獻度。ETF 商品分類與兩項指標、保險通用商品分類與日報手收已完成，不應再列為整項尚未納入。

## 共通語意與必要元素

金控／子公司 RDF 定義共通概念、屬性、關係與正式繼承；PG 保存部門概念、欄位、商品分類參照與來源觀察，沒有客戶、人員、商品、部位或交易資料實例。example.org 是示意命名空間。

- fh:Metric 的子類為 fh:AUM、fh:FeeIncome；銀行／證券各有對應子類。AUM 用 measuresProduct，手收用 feeIncomeFromProduct，不混用，也沒有手收指向 AUM 的關係。
- bank:BankEmployee 繼承 fh:Employee，bank:FinancialAdvisor 再繼承行員，沿用 bank:employeeId，不另造理專 ID。銀行手收可參照 attributedToAdvisor；證券不套用銀行理專關係。
- fh:serves 連職員與客戶，不表示資料閱覽授權。權限 deferred_by_user 只記錄延期。
- 銀行與證券商品分類治理各屬其子公司，直接繼承 fh:FinancialProduct；證券不繼承銀行商品，不宣告兩者等價。海外不等同外幣；組合商品留 PG。
- 行員存款指存款人本人為行員，不得用管理客戶的 AO 員編代替本人識別。

八個金控 Data Property 繼續沿用：

| 屬性 | Domain | Range |
|---|---|---|
| fh:metricAmount | fh:Metric | xsd:decimal |
| fh:aumAsOfDate | fh:AUM | xsd:date |
| fh:valuationQuantity | fh:AUM | xsd:decimal |
| fh:valuationUnitPrice | fh:AUM | xsd:decimal |
| fh:incomePeriodStart | fh:FeeIncome | xsd:date |
| fh:incomePeriodEnd | fh:FeeIncome | xsd:date |
| fh:feeBaseAmount | fh:FeeIncome | xsd:decimal |
| fh:feeDeductionAmount | fh:FeeIncome | xsd:decimal |

元素按情境適用，不新增必填、固定基數或公式。metricAmount 是結果金額；舊 amount 候選可能包含同一計算的多個輸入，不把輸入各自當成結果。舊 snapshotDate／incomePeriod 保留，不自動轉成新的業務基準日／期間起迄日。數量單位、報價基準與扣減項目的具體意義留 PG。

不新增未確認 Hash、互斥、等價、sameAs、keys、反向關係、property chain、完整推論、SHACL 或額外保單／契約／資產模型。

## 有效來源、輸出與表級對應

RDF 五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。build-config.json 明列來源，catalog-v001.xml 對應本機 URI／v0.12.0。tools/build_ontology.py 產生自含 customer360-ontology.ttl／.owl，勿手改，不連網解析 example.org。

PG 六份 active JSON：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。各有 JSON Schema 或 Python executable schema；build_cypher.py 合併產生 Neo4j 5 metadata 腳本 model.cypher，只依賴標準函式庫，未部署。穩定 ID＋MERGE 支援重複載入，但不刪舊資料，也不提供完整同步遷移。

目前有 58 條 HAS_SOURCE_TABLE、3 條 USES_VALUATION_SOURCE、2 條 USES_DATE_LOOKUP_SOURCE，來源表共 35 個。表級記錄 tables 僅有 table、role、evidence，不新增欄位映射。SourceTable 節點沿用穩定 ID。來源 SQL cp950，JSON／Turtle UTF-8。

證券基金手收的債券表與外股 AM_SEC 只供日期查詢，不是額外金額來源；原始異常保持。四項證券手收引用的 T_LAST_TWO_WORKDAYS 缺 schema／底層定義，只保留為未辨識期間輔助關係。基金 WKB02／WKB24 角色、ETF AUM 分類取值、日期／FX、UNION 去重與股票設質等疑點仍留供後續，不阻塞本階段必要元素建模。

## 建置與驗證

沿用 .venv／rdflib 7.6.0，在工作目錄執行：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B tools\export_metric_tables.py
.venv\Scripts\python.exe -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

目前 RDF：30 Class、6 Object Property、16 Data Property、5 Annotation Property、324 triples。PG：36 概念、462 metadata 節點、972 關係，含 290 DataFieldDefinition、35 SourceTable、40 BusinessRelationDefinition、5 MetadataModule。

RDF 19 項＋PG 64 項通過，無略過。涵蓋保險廣義分類、原始投資金額／手收／客戶貢獻度意義、來源檔案與 metadata 儲存格、ETF 直接繼承金融商品與基金範圍保持、原有 RDF／PG 定義及欄位保留、空欄位候選與來源角色、跨公司參照、pending 安全、確定性與輸出逐位元組比對。未執行完整 OWL reasoner、SHACL、GUI、來源 SQL、真實資料查核或 Neo4j 部署。

維護時同步 JSON、驗證器、測試、RDF 整合輸出及底表對照清單。tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 是舊批次一次性 seeder，不是通用 SQL 分析器；不重跑覆寫 active JSON。不要執行 tools/legacy-v0.2.0。

## 快照與接續

本輪修改前完整來源、工具、文件、測試快照為 archive/before-v0.12.0，不含 venv。前輪保險快照為 before-v0.11.0。前批銀行四手收快照為 before-bank-fee-extension-20261022，初次表級對應為 before-table-sources-20261022，更早版本供回查。before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。

私銀 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 與外部同步專案未修改。沒有 Git 提交、外部部署或已確認雲端備份。outputs/rdf-review-v0.7.0 仍為歷史圖，不代表目前模型。

使用繁體中文，區分共通語意、已實作指標與來源候選。依客戶360/AGENTS.md 已授權本機專案修改、建置與測試，不反覆詢問；外部部署及訊息傳送未授權。

可貼到新 Session：

> 請先讀客戶360/AGENTS.md、customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md 與 README.md，接續 v0.12.0。使用者決議 ETF 直接繼承金控金融商品，已新增 bank:ETFProduct，沒有繼承基金。PG 補 bank.etf_aum／bank.etf_fee_income，來源分別為 DSFND.PB_FUND_MONTH／PB_FUND_SPREAD_DAILY，與基金分列且不自動合計；AUM 的 ETF 分類取值仍待確認。現在 15 項 AUM、14 項手收有表級來源，新增欄位全部 pending／null、候選為空，先不對欄位。保險 AUM 保留原始投資金額意義，日報手收已納入，月檔客戶貢獻度仍待討論。沿用八個金控必要元素，不要求詳細公式；保單／契約、帳戶、權限與畫圖暫緩。信託／保管、開狀、利收及交易損益等留待討論。先摘要，再依我的指示繼續。
