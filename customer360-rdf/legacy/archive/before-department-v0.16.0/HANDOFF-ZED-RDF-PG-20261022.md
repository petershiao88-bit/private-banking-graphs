# 客戶360 RDF／OWL v0.15.0＋PG 收入擴充交接

更新：2026-10-24。PG 修訂識別 `pg-income-extension-20261024`。固定沿用本檔名作正式入口。

## 新 Session 先讀

先讀 ../AGENTS.md、本檔、README.md；逐項底表見 department-pg/METRIC-TABLE-SOURCES.md。工作目錄 C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

使用者要求實質模型變更先說明清單、確認後執行。本輪已確認「PG 新增三項、擴充兩項，RDF 沿用」，並指示「好的啟動」，已完成本機建置／驗證，未部署資料庫。方向維持證券優先；現有可確認來源的證券商品指標已納入，本輪補銀行 SQL 已定義的收入缺口。

本輪修改前完整本機備份 archive/before-pg-income-extension-20261024（不含 .venv、archive、outputs）；修訂紀錄 department-pg/history/pg-income-extension-20261024.json。前輪完整 v0.15.0 交接保存在上述備份；更早 v0.14.0／v0.15.0 快照繼續保留。

## 本輪完成：只改 PG，RDF 未變

RDF 五份來源、customer360-ontology.ttl／.owl、build-config.json、catalog-v001.xml 均逐位元組保持；ontology_version 仍為 0.15.0，不新增 Class、Property、正式繼承或資料實例。

| 動作／PG ID | 指標類型／商品參照 | 金額來源 |
|---|---|---|
| 新增 bank.deposit_interest_income | BankInterestIncome／DepositProduct | INCOME_066：DSDEP.DEP_NT_ACCT_HS、DEP_FN_ACCT_HS、EMP_DEP_NT_ACCT_HS、DEP_FN_ACCT |
| 新增 bank.overseas_bond_trust_fee_income | BankFeeIncome／BondProduct＋OverseasFinancialProduct | INCOME_031：DSFND.PB_FUND_SPREAD_DAILY |
| 新增 bank.overseas_bond_proprietary_fee_income | BankFeeIncome／BondProduct＋OverseasFinancialProduct | INCOME_032：DSWTR.BOND_TXN |
| 擴充 bank.dci_fee_income，名稱銀行 DCI 手收 | BankFeeIncome／StructuredFinancialProduct | 保留 INCOME_037 純手續費，補 INCOME_038 的 DSTAS.FO108_W／DCD |
| 擴充 bank.insurance_fee_income，名稱銀行保險手收 | BankFeeIncome／InsuranceProduct | 保留 INCOME_028 日報，補 INCOME_029／030 的 DSKPI.KPI_DET_IU_002_NEW、KPI_DET_OFI_001 |

前三項新增在 bank-business-metrics.json；DCI 在 product-fees.json；保險在 investment-metrics.json。原指標 ID、欄位與候選完整保留；DCI／保險各維持一項，不因中繼表拆新商品／新指標。

bank-business-metrics 共十二項指標、115 個必要元素：兩項 AUM 各八、七項手收各十一、一項 LUM 六、兩項利收各八；新增三項共三十個空映射。全部 pending、table／column=null、candidates=[]；其他舊模組既有候選不刪除。

兩項債券手收新增商品範圍與理專關係；存款利收比照放款利收，不加理專歸屬。該模組 department_context 的使用／定義部門為私人銀行，source_data_owner=null，概念 department_owner=null、subsidiary=bank。DCI／保險使用／定義脈絡記在來源觀察；不宣稱來源資料權責歸私銀，實際員編仍待定。

通用 bank.product_fee_income 的 partial_scope 與來源完全維持，不因新增商品手收而視為完整總手收或自動合計。

## SQL 是業務字典，執行仍在 Tool

SQL 分類為主：手收不限定純手續費，利收不限定純客戶利息。圖譜保存語意、來源表與來源觀察，不加入可執行 SQL、JOIN、篩選、加總、去重、換匯或認列規則。所有 execution 欄位為 null。指標到 Tool 的綁定與 Tool 實作尚未完成，不宣稱已可查詢生產數字。

- 存款利收 INCOME_066 取 GROSS_INCM，保留業務收益口徑，不宣稱為客戶收到的存款利息。三項歷史與外幣 current 有明確來源；台幣 current 註記無 GROSS_INCM，不補成來源。
- 初建歷史有私銀分行及 YYYYMM>202505 條件；上月替換沒有同樣分行條件，初建用 UNION ALL、上月替換用 UNION；日期標記與 DATA_DT 不視為同義。原 INCOME_066 引用 TMP01，但其前段定義位於註解，保留異常。上月替換另見 X-INCOME_MOTHLY.sql 第 7–49 行。沒有執行或修正 SQL。
- 債券信託 INCOME_031 取 SUM(BRHREBATEAMT + WKR028/100)，保留費用與交易利得組成，不自行補零；條件 FHID='CB'、BAOPCCCODE LIKE '%2E%'。自營 INCOME_032 取 SUM(ABS(INC_AMT_NT))，逐筆取絕對值，不改成 ABS(SUM(...))，不擅自恢復正負號。
- DCI INCOME_038 僅取 TRIM(Product)='DCD' 的 SUM(TMUPROFIT)，和 INCOME_037 同歸 DCI 手收；既有 FX TMU 排除 DCD／Cash Bond。共表不代表收入範圍相同，FO108_W catalog 共用，但每個指標保留自己的 SQL 證據。
- 保險月檔取 PS，metadata 為客戶貢獻度；仍依 SQL 歸保險手收。月檔 LST_MTN_DT 移至次月；IU 篩選 PS IS NOT NULL、OFI 篩選 OPEN_ACCOUNT='Y'。日報特定月份限制、日月重疊與 UNION 投影整列去重保留，不認定可直接相加或按保單／交易去重。

來源 SQL 為 cp950，JSON／Turtle 為 UTF-8。SourceTable 均 observed_in_files、database_verified=false。table_sources 僅 table／role／evidence，底表接在指標，不接商品 Class。來源欄位名稱只能作觀察，實體映射仍未核定。

## 原有模型決議保持

- 金控 AUM、LUM、FeeIncome（手收）、InterestIncome（利收）直接繼承 Metric。銀行各有對應 Class；證券／人壽未新增 LUM 分項。
- 規劃型信託、信託保管、外匯、開狀、黃金、放款均先納銀行金融商品，直接繼承 FinancialProduct；FinancialService 及兩個服務專屬關係已退出。未來資訊足夠才討論拆分。
- AUM 使用 measuresProduct；LUM 使用 lumMeasuresProduct；手收使用 feeIncomeFromProduct；利收使用 interestIncomeFromProduct。domain 分別 AUM／LUM／FeeIncome／InterestIncome、range=FinancialProduct。金額共用 metricAmount；各自日期／期間元素沿用。沒有必填、基數、同義、等價或自動合計。
- 外匯、黃金依 SQL 歸手收，保留兌換／TMU／黃金損益；開狀維持手收。使用者已決定三者先不建 AUM，不以舊需求恢復。
- 放款有 LUM、利收，沒有 AUM。LUM 四表為 DSLON.LN_NT_ACCT／LN_FN_ACCT 及各自 _HS；會科 1886 應付保證等範圍疑點保留。放款利收台幣歷史取毛利 GROSS_INCM；外幣歷史／current 取 INT_INCM-CB_INT_AMT，不與 LUM 金額混用。
- 規劃型信託、保管分列；員工持股費用累計註記、保管在來源收入彙總併規劃型信託等觀察保持，不擅自差分或合計。
- ETF、基金、集合管理分列；ETF／集合管理直接繼承金融商品，ETF AUM 實際分類取值待定。保險 AUM 保留原始投資金額，不等同保單市值或現金價值。SI／ELI／FCI 分列。
- 證券五項 AUM：複委託債券、結構型、基金、外股、台股庫存；四項手收為前四類，外股保留淨手收。證券不繼承銀行商品或套用銀行理專關係，銀行與證券不自動加總。
- 證券基金 BONDTRADM_SEC、外股 AM_SEC 僅供日期查詢；T_LAST_TWO_WORKDAYS 缺 schema／底層定義，留 unresolved_supporting_relations。WKB02／WKB24 識別角色、日期、FX 與 UNION 疑點保持。
- 行員存款須識別存款人本人為行員，不借用管理客戶的 AO 員編。職員 serves 客戶不等於閱覽權限。

## 三項 pending 與退場紀錄

SQL 查核決議見 department-pg/history/sql-scope-review-20261024.json，維持三項 pending，均不是 active 指標：

1. securities.stock_pledge_lum：pending_source_definition。股票設質 SQL 僅有 Qty×Product_Price 估值，缺實際借款／融通餘額，不建立 AUM 或 LUM。
2. securities.taiwan_stock_fee_income：pending_source_definition。未找到可辨識手收分支，先不建立；原台股 AUM 保留。
3. bank.collective_account_fee_income：pending_business_semantics。TA／TB／TD／TE 分支先被前方基金 CASE 條件攔截，先不另建手收，不改 SQL；原集合 AUM 保留。

股票設質 AUM 完整退場紀錄在 history/stock-pledge-aum-retired-v0.15.0.json；v0.15 Class／ID 對照在 history/changes-v0.15.0.json。history 不參與建置。MERGE 不會刪除舊關係；未來若更新既有資料庫，須先查清實際 namespace 與舊版範圍，不能視重跑為完整同步。本輪沒有資料庫連線或部署。

尚未建模：總收入彙總、放款額度／人數與 ROA／ROBA。10._INCOME_ROA.sql 的比率只寫在註解，實際 SQL 只彙整收入、AUM、ln_amt，不能聲稱已實作除法。權限、帳戶、分行／數位、畫圖與實體欄位映射繼續暫緩。

## 有效來源、輸出與驗證

RDF 五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。PG 七份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics。各有 schema／Python 驗證器；合併產生 Neo4j 5 metadata model.cypher，只依賴標準函式庫。example.org 為示意命名空間，不連網解析。

42 項指標：18 AUM（銀行13／證券5）、1 銀行 LUM、21 手收（銀行17／證券4）、2 銀行利收。52 SourceTable；88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。

RDF：41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples。PG：49 BusinessConcept、652 metadata 節點、1338 關係，含413 DataFieldDefinition、60 BusinessRelationDefinition、6 MetadataModule、7 MappingSlot。通聯沒有獨立 MetadataModule。

RDF19＋PG85＝104項測試通過，無略過。RDF／config／catalog 逐位元組不變、三項新增與兩項擴充、原候選與未涉範圍保存、SQL 原文／metadata 儲存格、四種指標 domain、空映射、錯誤來源／型別／執行規則反例及確定性皆驗證。24份原 SQL／Excel SHA-256 未變。Cypher 與底表清單須與模型逐位元組一致。

```powershell
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s department-pg -v
```

不重建或改寫 RDF 以求版本一致，本輪只做 --check。未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI 或部署，沒有資料實例、Git 提交或已確認雲端備份。

## 保存性測試與維護

各歷史測試的 before-v0.13.0／before-v0.12.0／before-v0.10.0 等路徑保持，不能全域換成最新快照。review_contract_v015.py 只正規化既核定文字，不忽略型別或 domain／range；review_contract_pg_income.py 只供歷史測試還原兩項核定擴充的名稱、定義、來源觀察、表級涵蓋與關係名稱，不忽略 Class、欄位候選、關係語意。test_pg_income.py 直接驗證本輪變更及 RDF／來源未改。

歷史一次性 tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 不可重跑覆寫 active JSON；tools/legacy-v0.2.0 不可執行。outputs/pg-income-extension-20261024/apply.py 是本輪已執行的一次性維護紀錄，有基準保護，不是建置入口。before-deposit-pg-correction 為錯誤組合 OWL 實作，不可恢復；outputs/rdf-review-v0.7.0 為歷史圖。
