# 部門 PG metadata 模型 v0.15.0

本輪依使用者確認：六類統一金融商品、採 SQL 的手收／利收分類、新增銀行 LUM、股票設質退出 AUM。完整共通語意與操作見 [專案 README](../README.md)；逐項底表見 [METRIC-TABLE-SOURCES.md](METRIC-TABLE-SOURCES.md)。

## Active 模組

| JSON | 執行驗證器 | 範圍 |
|---|---|---|
| model.json | model.schema.json、build_cypher.py | 貸款照會手機、客戶訪問地址 |
| deposits.json | deposit_model.py | 台幣、外幣、結構型與行員存款 |
| advisory-income.json | advisory_income_model.py | 理專、服務客戶、通用商品手收 |
| product-fees.json | product_fees_model.py | SI／SN、海外股票、ELI／FCI、DCI 純手續費 |
| product-aum.json | product_aum_model.py | 七項商品 AUM |
| investment-metrics.json | investment_metrics_model.py | 銀行基金／保險／ETF／集合管理與證券十六項指標 |
| bank-business-metrics.json | bank_business_model.py | 規劃型信託／保管／外匯／開狀／黃金／放款九項指標 |

build_cypher.py 僅載入上述七份 active JSON，產生 Neo4j 5 model.cypher，不部署或執行來源 SQL。history/ 與 drafts/ 不參與建置。drafts/employee-deposit.json 是已取代草稿。

## 本輪九項指標

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

六個商品 Class 均直接繼承 fh:FinancialProduct。FinancialService、四個 *Service Class、measuresService／feeIncomeFromService 已退出有效 RDF 與 PG 參照。

AUM 參照 measuresProduct；LUM 參照 lumMeasuresProduct；手收參照 feeIncomeFromProduct；利收參照 interestIncomeFromProduct。各關係的 domain 分別為 AUM／LUM／FeeIncome／InterestIncome，range 為 FinancialProduct，不新增指標或商品的 OWL 實例。

HAS_BUSINESS_SCOPE 是 PG metadata 商品範圍參照，HAS_TARGET_CLASS 保存關係的具體商品 Class 參照，非 RDF 實例斷言、正式繼承或會計推論。

## 必要元素與部門

本模組兩項 AUM 各八個、五項手收各十一個、LUM 六個、利收八個，共 85 個 DataFieldDefinition，全部 pending、table／column=null、candidates=[]。沒有 serviceId，統一用 productId。

LUM 使用 metricAmount／lumAsOfDate；利收使用 metricAmount／interestPeriodStart／End，不套用 AUM 或手收專屬日期／計算元素。snapshotDate／incomePeriod 保留為 PG 元素，不自動指定日期或期間。

department_context 記錄 using_department／definition_department 為私人銀行，source_data_owner=null；每項 department_owner=null、subsidiary=bank。使用部門不等於來源資料權責部門。本輪五項手收都參照 bank:attributedToAdvisor，實際員編與認列未定；放款利收不新增理專關係。

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

39 項指標：18 AUM、1 LUM、19 手收、1 利收。46 BusinessConcept、611 metadata 節點、1245 關係，含 383 DataFieldDefinition、49 SourceTable、55 BusinessRelationDefinition、6 MetadataModule、7 MappingSlot。通聯沒有獨立 MetadataModule。

79 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。證券 T_LAST_TWO_WORKDAYS 因缺 schema／定義仍保留 unresolved_supporting_relations，未列成底表。

本輪 PG 78 項測試通過，無略過；RDF 另 19 項，共 97 項。來源 24 份 SQL／Excel SHA-256 未變；含原證據儲存格與 SQL 交叉查核、分類 domain、空映射、退場保存、反例拒絕、確定性與逐位元組輸出比對。建置命令見上層 README。

不執行來源 SQL、資料庫部署、完整 OWL 推論或權限設計；不產生客戶／交易資料。不重跑歷史一次性 seeder，保存性測試的各自歷史路徑保持。修改前快照為 ../archive/before-v0.15.0/。
