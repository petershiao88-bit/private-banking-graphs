# 部門 PG metadata 模型 v0.15.0

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

沿用既有決議：六類統一金融商品、採 SQL 的手收／利收分類、銀行 LUM、股票設質退出 AUM；本輪再補三項收入及兩項既有手收來源。完整共通語意與操作見 [專案 README](../README.md)；逐項底表見 [METRIC-TABLE-SOURCES.md](METRIC-TABLE-SOURCES.md)。

## Active 模組

| JSON | 執行驗證器 | 範圍 |
|---|---|---|
| model.json | model.schema.json、build_cypher.py | 貸款照會手機、客戶訪問地址 |
| deposits.json | deposit_model.py | 台幣、外幣、結構型與行員存款 |
| advisory-income.json | advisory_income_model.py | 理專、服務客戶、通用商品手收 |
| product-fees.json | product_fees_model.py | SI／SN、海外股票、ELI／FCI、DCI 手收（含 DCD／TMU） |
| product-aum.json | product_aum_model.py | 七項商品 AUM |
| investment-metrics.json | investment_metrics_model.py | 銀行基金／保險／ETF／集合管理與證券十六項指標 |
| bank-business-metrics.json | bank_business_model.py | 規劃型信託／保管／外匯／開狀／黃金／放款／存款／債券十二項指標 |

build_cypher.py 僅載入上述七份 active JSON，產生 Neo4j 5 model.cypher，不部署或執行來源 SQL。history/ 與 drafts/ 不參與建置。drafts/employee-deposit.json 是已取代草稿。

## bank-business-metrics 十二項指標

| ID | 種類 | 商品參照 |
|---|---|---|
| bank.planned_trust_aum | 銀行 AUM | PlannedTrustProduct |
| bank.planned_trust_fee_income | 銀行手收 | PlannedTrustProduct |
| bank.trust_custody_aum | 銀行 AUM | TrustCustodyProduct |
| bank.trust_custody_fee_income | 銀行手收 | TrustCustodyProduct |
| bank.fx_fee_income | 銀行手收 | ForeignExchangeProduct |
| bank.lc_fee_income | 銀行手收 | LetterOfCreditProduct |
| bank.gold_fee_income | 銀行手收 | GoldProduct |
| bank.loan_lum | 銀行 LUM | LoanProduct |
| bank.loan_income | 銀行利收 | LoanProduct |
| bank.deposit_interest_income | 銀行利收 | DepositProduct |
| bank.overseas_bond_trust_fee_income | 銀行手收 | BondProduct＋OverseasFinancialProduct |
| bank.overseas_bond_proprietary_fee_income | 銀行手收 | BondProduct＋OverseasFinancialProduct |

六個商品 Class 均直接繼承 fh:FinancialProduct。FinancialService、四個 *Service Class、measuresService／feeIncomeFromService 已退出有效 RDF 與 PG 參照。

AUM 參照 measuresProduct；LUM 參照 lumMeasuresProduct；手收參照 feeIncomeFromProduct；利收參照 interestIncomeFromProduct。各關係的 domain 分別為 AUM／LUM／FeeIncome／InterestIncome，range 為 FinancialProduct，不新增指標或商品的 OWL 實例。

HAS_BUSINESS_SCOPE 是 PG metadata 商品範圍參照，HAS_TARGET_CLASS 保存關係的具體商品 Class 參照，非 RDF 實例斷言、正式繼承或會計推論。

## 必要元素與部門

本模組兩項 AUM 各八個、七項手收各十一個、LUM 六個、兩項利收各八個，共 115 個 DataFieldDefinition，全部 pending、table／column=null、candidates=[]。沒有 serviceId，統一用 productId。

LUM 使用 metricAmount／lumAsOfDate；利收使用 metricAmount／interestPeriodStart／End，不套用 AUM 或手收專屬日期／計算元素。snapshotDate／incomePeriod 保留為 PG 元素，不自動指定日期或期間。

department_context 記錄 using_department／definition_department 為私人銀行，source_data_owner=null；每項 department_owner=null、subsidiary=bank。使用部門不等於來源資料權責部門。本模組七項手收都參照 bank:attributedToAdvisor，實際員編與認列未定；存款與放款利收不新增理專關係。

所有 execution 欄位為 null，包括 SQL、JOIN、篩選、粒度、估值、換匯、認列、期間、加總、去重與歸屬。SQL／metadata 只作來源證據。

## 來源與分類

LUM 金額來源為 DSLON.LN_NT_ACCT／LN_FN_ACCT 及各自 _HS。觀察到 LN_BAL／BAL_AMT、分行條件、月份／昨日日期與會科 1886 應付保證標示，涵蓋與日期／換匯未核定。利收來源為台外幣歷史月更新與外幣 current；金額分別為來源毛利及利息收入減聯行息收入。

外匯／黃金沿 SQL 歸手收，保留兌換／TMU／交易損益 metadata 意義；FX TMU 分支排除 DCD／Cash Bond，未將全表或 DCI TMU 納入。開狀手收原攤提／換算疑點保持，沒有新增外匯、開狀或黃金 AUM。

規劃型信託的員工持股手收有累計註記，不核定差分或與其他信託／保管自動加總。保險／ETF／集合管理／基金及證券的既有來源疑點保持，通用手收仍 partial_scope，本輪未擴大通用來源。

所有 SourceTable 為 observed_in_files、database_verified=false。table_sources.tables 僅 table／role／evidence；primary、valuation_support、date_lookup_only 各投影為 HAS_SOURCE_TABLE、USES_VALUATION_SOURCE、USES_DATE_LOOKUP_SOURCE。底表關係由指標出發，不由商品 Class 出發。

## 股票設質退場與 pending

securities.stock_pledge_aum 已移出 active 模型，原指標／關係／底表與證據完整另存 history/stock-pledge-aum-retired-v0.15.0.json。DSCSD.PBCMS_REPORTA03 不在有效來源 catalog，也沒有借款或 LUM 金額關係；原 evidence 留供查核。

pending_scope：securities.stock_pledge_lum、securities.taiwan_stock_fee_income 均待來源定義；bank.collective_account_fee_income 待業務語意。原台股庫存 AUM 與其他證券指標保持。

history/changes-v0.15.0.json 記錄新舊 Class／指標 ID 對照。沒有實際資料庫遷移；MERGE 不會移除舊節點／關係，未來若更新既有部署需另做限定範圍遷移。

## 統計與驗證

42 項指標：18 AUM、1 LUM、21 手收、2 利收。49 BusinessConcept、652 metadata 節點、1338 關係，含 413 DataFieldDefinition、52 SourceTable、60 BusinessRelationDefinition、6 MetadataModule、7 MappingSlot。通聯沒有獨立 MetadataModule。

88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。證券 T_LAST_TWO_WORKDAYS 因缺 schema／定義仍保留 unresolved_supporting_relations，未列成底表。

本輪 PG 85 項測試通過，無略過；RDF 另 19 項，共 104 項。來源 24 份 SQL／Excel SHA-256 未變；含原證據儲存格與 SQL 交叉查核、分類 domain、空映射、退場保存、反例拒絕、確定性與逐位元組輸出比對。建置命令見上層 README。

不執行來源 SQL、資料庫部署、完整 OWL 推論或權限設計；不產生客戶／交易資料。不重跑歷史一次性 seeder，保存性測試的各自歷史路徑保持。修改前快照為 ../archive/before-v0.15.0/。

## PG 收入擴充的來源差異與保存驗證

存款 INCOME_066 有三項歷史表與外幣 current 表；不補台幣 current 利收來源。初建與上月替換的私銀條件、UNION ALL／UNION、日期涵蓋不同；原 TMP01 定義註解疑點保留。債券信託 INCOME_031 取 BRHREBATEAMT + WKR028/100；自營 INCOME_032 逐筆 ABS 後加總，不改寫正負號或空值規則。

DCI INCOME_038 僅取 FO108_W 的 DCD，既有 FX 排除 DCD／Cash Bond。保險 INCOME_029／030 取 PS，保留客戶貢獻度意義；次月歸屬、IU／OFI 條件差異、日月重疊與 UNION 整列去重只作觀察。所有 execution 仍為 null，Tool 綁定未完成。

review_contract_pg_income.py 只供歷史測試正規化兩項核定擴充的名稱、定義、來源觀察、底表涵蓋及關係名稱，不忽略 Class、欄位候選或關係語意。test_pg_income.py 另直接檢查本輪來源規則、三項新指標、兩項擴充、RDF 逐位元組未變及來源雜湊。
