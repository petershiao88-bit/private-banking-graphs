# 部門 PG metadata 模型 v0.11.0

## 最新更新：銀行保險

investment-metrics.json 新增 bank.insurance_aum、bank.insurance_fee_income，分別參照 bank:BankAUM／BankFeeIncome，兩者皆參照銀行共通 bank:InsuranceProduct。分類泛指銀行通路保險；實際私銀範圍由 PG 描述，不限定投資型保險，也不建立保單／契約。

AUM 底表為 DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT，來源意義保留為原始投資金額，不當成保單市值或現金價值。手收底表為 DSINS.INSU_RPT_Q01，僅涵蓋明確標示手收的日報，標 partial_scope；DSKPI.KPI_DET_IU_002_NEW／KPI_DET_OFI_001 的月檔是客戶貢獻度，保留證據但未加入金額來源。原始日報的 current 月份限制也保留，沒有宣告完整時間覆蓋。

新 AUM 八欄位、手收十一欄位均 pending、table／column 全 null、candidates 全空；理專歸屬只參照既有關係，未核定實際人員。通用手收同步加入日報底表，仍是部分覆蓋。既有指標、欄位、來源與關係保留，只同步 ontology_version。修改前快照為 archive/before-v0.11.0/。

## 四項銀行手收

product-fees.json 新增 bank.overseas_stock_fee_income、bank.domestic_structured_eli_fee_income、bank.domestic_structured_fci_fee_income、bank.dci_fee_income。四者沿用 bank:BankFeeIncome、fh:feeIncomeFromProduct 與銀行理專歸屬關係。海外股票以 product_class_uris 參照股票＋海外金融商品；其餘三項參照結構型金融商品，不新增組合 RDF Class。

新增底表分別是 PB_FUND_SPREAD_DAILY，以及 ELI／FCI／DCI_PERFO_RPT 各 current／_HS。DCI 只涵蓋 INCOME_037 的手續費報表，不含 INCOME_038／DSTAS.FO108_W 的 TMU 損益；ELI／FCI 與 SI 分開。新指標各有十一個 pending 欄位，table／column 全 null、candidates 全空。原有欄位與候選保留，未建立公式或選日規則。

目前共 14 項 AUM、13 項手收。各 concept 的 table_sources 只記底表、角色與證據，不指定欄位。role=primary 投影為 HAS_SOURCE_TABLE，valuation_support 為 USES_VALUATION_SOURCE，date_lookup_only 為 USES_DATE_LOOKUP_SOURCE；目前共 56／3／2 條，SourceTable 共 35 個，端點為指標而非商品分類。表級摘要保存在 table_sources_json。

通用手收擴充至已盤點 SI／SN／銀行基金／海外股票／ELI／FCI／DCI 純手續費與保險日報來源，仍標 partial_scope，不代表完整來源或直接加總。證券的未辨識期間輔助關係與原始日期查詢異常維持。

[AUM／手收底表對照](METRIC-TABLE-SOURCES.md) 由 tools/export_metric_tables.py 產生，可用 --check 比對；維護 active JSON，不直接改產出。前批四項手收快照：archive/before-bank-fee-extension-20261022/。通聯、存款商品與既有 AUM／證券項目保持。

RDF／OWL 定義共通語意；PG 定義部門概念、欄位、關係與來源映射。這裡只有 metadata，不含客戶、人員或交易資料實例。模型參照完整概念 URI，不執行 OWL 推論或資料同步。

金控既有八個共通 Data Property 繼續沿用。amount 參照 fh:metricAmount；AUM 有基準日、估值數量／單價，手收有收入期間起迄日、計算基礎／扣減金額。前次共通屬性新增 71 個 pending 欄位，本次四項手收另增 44 個 pending 欄位。欄位定義不構成資料必填要求，各元素按情境適用。

共通屬性的數值 range 為 xsd:decimal，日期 range 為 xsd:date。投影的屬性參照使用各自正確的 range 與 domain；金額欄位不作客戶／商品識別，不會用 FIELD_IDENTIFIES_CLASS 指向 Metric。舊 snapshotDate 與 incomePeriod 及其原始來源證據保持，不自動轉成 AUM 基準日或期間起迄日。既有 amount 的多個來源候選仍是計算輸入證據，未被核定為各自獨立的結果金額。

金控只定義計算必要元素；詳細公式與日期規則留在子公司／部門，非本階段建模前提。客戶與商品識別、幣別匯率及商品範圍先不討論，維持原候選與 null。銀行基金及證券的既有十一項候選沿用；fh:measuresProduct 專屬 AUM，手收沿用 fh:feeIncomeFromProduct。依使用者指示不更新圖片。

## Active 模組

| 來源 | 內容 | 契約／驗證器 |
|---|---|---|
| model.json | 貸款照會手機、客戶訪問地址 | model.schema.json ＋ build_cypher.py |
| deposits.json | 台幣、外幣、結構型及行員存款 | deposit_model.py |
| advisory-income.json | 理專、服務關係、通用商品手收架構 | advisory_income_model.py |
| product-fees.json | SI／SN、海外股票、ELI／FCI、DCI 純手續費六項銀行手收 | product_fees_model.py |
| product-aum.json | 七項商品 AUM、估值與來源候選 | product_aum_model.py |
| investment-metrics.json | 銀行基金／保險 AUM 與手收、五項證券 AUM／四項證券手收 | investment_metrics_model.py |

build_cypher.py 合併六個 active 模組產生 model.cypher；不連線部署。drafts/employee-deposit.json 是已取代草稿，不參與建置。

## 銀行基金與證券

investment-metrics.json 參照本輪新增的 bank:FundProduct，以及 securities-common.ttl 的證券 AUM、證券手收與五個商品分類。各商品指標仍留在 PG；證券概念 subsidiary 為 securities，銀行基金為 bank，共用投影保留原治理歸屬。AUM 的商品關係只參照 fh:measuresProduct，手收只參照 fh:feeIncomeFromProduct。

- 銀行基金：AUM 候選來自 DSFND.PB_FUND_MONTH 的 CurrentTWDValue；TRUSTPRD 完整基金取值未核定，不把全表當基金。手收來自 PB_FUND_SPREAD_DAILY 的 BRHREBATEAMT，FUNDID、BAOEMPID／SAOEMPID 為來源候選，理專歸屬待確認。原分類 CASE 順序可能使後方集合管理條件被先行一般基金條件攔截，保留待覆核。基金與 ETF 在私銀分列，本輪 ETF 未新增。
- 證券 AUM 五項：複委託債券、複委託結構型、複委託基金、複委託外國股票、台股。商品分類以 product_class_uris 參照證券 RDF；估值各組成輸入不是替代金額。
- 證券手收四項：上述前四類；外國股票保留 (CFEE − ABFEE) × FXRATE 淨手收。台股手收來源未見定義，未建立手收概念。股票設質業務意義未定，只列 pending_scope，不建立 AUM。
- 證券基金 WKB02 是 current metadata 的投資人帳號，WKB24 是身分證字號；兩個角色不視為同一客戶 ID。歷史表定義未獨立確認。基金手收 WKA31 的 metadata 原文有「台？」疑義，計價幣別不定案。
- 證券手收月底最後兩個工作天移至次月，YYYYMM＋01 是歸屬月份標記，不是 snapshotDate。基金 current 最大日期子查詢引用 BONDTRADM；外股 current AM FROM AM_SEC_M 卻查 AM_SEC 的最大日期，均記錄為來源異常，不自行修正。歷史 AUM 使用月末 FX 日期，亦不直接視為部位快照日。

SQL 行號、metadata 儲存格、來源角色及疑義均保存在 evidence／observations。所有 selected table／column 與 execution 保持 null；快照、幣別、收入期間、認列、估值、去重與歸屬待確認，不自動加總銀行／證券 AUM。來源表節點沿用穩定 ID；既有兩張 DSFND 來源 metadata 原樣合併，其證據仍可追溯。

tools/seed_investment_metrics.py 僅為一次性初始產生器，拒絕覆寫 active JSON；維護 JSON 與 investment_metrics_model.py 的輸入角色契約及測試。沒有新增資產部位、交易實例或手收指向 AUM 的關係。

## 理專與商品手收

理專參照 bank:FinancialAdvisor（繼承 bank:BankEmployee），行員編號欄位仍參照 bank:employeeId。另以 BusinessRelationDefinition 描述「理專服務客戶」，參照 fh:serves，保存行員／客戶識別欄位的 pending 映射。理專 OWL Class 已在銀行共通層建立；PG 保留來源映射，沒有新增理專 ID、角色自動認定或客戶實例。

通用商品手收參照 bank:BankFeeIncome；另以關係定義參照 fh:feeIncomeFromProduct（domain 為 FeeIncome），對應收入來源金融商品；不再使用 AUM 專屬的 fh:measuresProduct。收入期間與快照日期各自建欄位；金額、幣別、行員、客戶、商品識別均是 metadata 欄位定義。另以 bank:attributedToAdvisor 指向 bank:FinancialAdvisor，通用商品手收與 SI／SN 各有一個 pending 歸屬關係定義，沿用概念上現有 employeeId 欄位，不重複建員編欄位。未選定資料列粒度、日／月／年累計、收入認列及人員歸屬。

權限由使用者暫緩，access_policy_status 只記錄 deferred_by_user，不包含可見角色、內外部揭露或授權規則。

## 有來源的第一批手收

| 概念 | RDF 指標／商品參照 | 來源候選 |
|---|---|---|
| 境內結構型商品手收（SI） | bank:BankFeeIncome；商品關係指向 bank:StructuredFinancialProduct | DSDEP.SI_PERFO_RPT／_HS 的 CUSTOMER_ID、FEE_AMOUNT_TWD |
| 境外結構型商品手收 | 同上 | DSFND.PB_FUND_SPREAD_DAILY 的 IDNO、BRHREBATEAMT |

這兩項只對應既有「結構型金融商品」，不假定是結構型存款、DCI 或互斥商品分類。不新增境內／境外商品 OWL Class。每項保留七個既有欄位定義：employeeId、customerId、productId、amount、currency、incomePeriod、snapshotDate，另增四個手收元素，合計十一欄位。

所有 selected table／column 仍為 null。觀察到的客戶／金額欄位標為 observed_raw_candidate；員編候選標為 pending_attribution；SN 商品代碼候選為 pending_product_identity。來源日期只記於 observations.event_date，不填快照日。

| 證據 | 位置 |
|---|---|
| SI 原始欄位、SUM／UNION、分組 | 私銀 sources/sql/8.INCOME_DETAIL.sql，131–148 行，cp950 |
| SN 原始欄位、SUM、SN／私銀 PCC 篩選 | 同檔 191–202 行 |
| 下游境內／境外分類 | 私銀 sources/sql/9.INCOME_SMY.sql，92–100／122–130 行 |
| SI current 欄位定義 | 收入_metadata.xlsx，DSDEP.SI_PERFO_RPT，列 2、3、8、13、21、23、29 |
| SN 欄位定義 | 同檔 DSFND.PB_FUND_SPREAD_DAILY，列 7、8、9、13、14、18、20、31、32 |
| 私銀產品語意 | ontology/independent_concepts/concept_graph.json，bank_structured_domestic／bank_structured_offshore |

重要未定案事項：

- 境內目前只有 SI，未納 ELI／FCI，因此不是完整境內總手收。
- SI current 的 FEE_AMOUNT_TWD 已有「手續費換算台幣」定義；HS 語意尚未獨立核對。SN 的分行手續費未標幣別。currency 均未選定。
- TRADE_DATE 是交易日；FEEDATE 是手續費發生日，不能直接當 snapshotDate。收入期間及累計口徑亦未核定。
- SI metadata 未列 SQL 所用的 S_PCC_CODE；不可拿 PCC 當員編。RM_ID／USER_ID 的角色與理專資格未定。
- SN 的 BAOEMPID／SAOEMPID 分別是所屬／服務專員編號，歸屬規則未定。FUNDID 是基金代碼，對 SN 商品的適用性待確認。
- SI 的 DEALNO 是交易單號，不當作商品 ID。舊 SQL 聚合後已移除員編與商品識別，無法直接回推細分收入。
- 舊 SQL 的聚合、UNION、條件與日期轉換是來源觀察；execution 所有項目仍為 null，未產生可執行取數 SQL。

## AUM 與各商品 AUM

- 金控 `fh:AUM` 繼承 `fh:Metric`；銀行 `bank:BankAUM` 繼承 `fh:AUM`。
- `fh:measuresProduct` 的 domain 改為 `fh:AUM`，range 仍為 `fh:FinancialProduct`。Metric 不再直接定義對金融商品的關係。
- 手收改用獨立的 `fh:feeIncomeFromProduct`（手收來源商品），domain 為 `fh:FeeIncome`。通用手收及 SI／SN 的 PG 參照已同步切換，避免手收因沿用 AUM 關係而被推成 AUM。
- 各商品 AUM 留在部門 PG，參照 `bank:BankAUM`，以 AUM 衡量關係及商品分類參照描述對應商品；不新增各商品 AUM 的組合 OWL Class。

第一批共七項，金額均是待核定認列的候選：

| PG AUM | 商品分類參照 | 原始來源與估值觀察 |
|---|---|---|
| 台幣存款 AUM | 存款＋台幣金融商品 | 沿用已盤 NT current／HS；BAL_AMT |
| 外幣存款 AUM | 存款＋外幣金融商品 | 沿用已盤 FN current／HS；AVAIL_BAL |
| 結構型存款 AUM | 存款＋結構型金融商品 | 沿用既有五張存款來源的 2545 分類證據 |
| 海外股票 AUM | 股票＋海外金融商品 | DSFND.PB_FUND_MONTH；CurrentTWDValue，依既有 TRUSTPRD 分類 |
| 海外債券（信託）AUM | 債券＋海外金融商品 | 同上，TRUSTPRD='海外債券' |
| 海外債券（自營）AUM | 債券＋海外金融商品 | DSWTR.BOND_POS_DAY；STO_AMT × MKT_PRI ÷ 100 × EXC_RATE |
| 境外結構型商品 AUM | 結構型＋海外金融商品 | DSFND.PB_FUND_MONTH；CurrentTWDValue，TRUSTPRD='結構型商品' |

`department-pg/product-aum.json` 保留五個既有欄位定義：customerId、productId、amount、currency、snapshotDate，另增三個 AUM 元素，合計八欄位。amount 狀態為 pending_aum_recognition，selected table／column 均 null；不把存款原始餘額直接認定為核定 AUM，也不將欄位名稱中的 TWD 直接轉成幣別常數。

既有 PB_FUND_MONTH SQL 將「其他-國外有價證券」等分類歸為海外股票，需覆核分類範圍；TRUSTPRD 是類型，不代替單一商品識別。自營債券的三個欄位是同一估值公式的輸入，不是任選金額。其舊 SQL 取全體每月最大日期，不是各客戶最後交易日，也不自動成為新版預設選日規則。

商品分類與來源可能重疊；七項不是完整銀行 AUM 清冊，不自動相加成銀行 AUM。認列、幣別、快照日、跨來源識別、去重及聚合仍待確認；execution 全部 null。來源 SQL 只作唯讀文字證據。

商品分類參照保存在 product_class_uris；BusinessRelationDefinition 的 HAS_TARGET_CLASS 包含共通 FinancialProduct 與較具體的商品分類，僅作語意限定 metadata，沒有 OWL 交集或自動分類。存款 AUM 的 basis_concept 指向既有存款概念；來源與證據沿用，原始餘額仍不是已核定 AUM。底表節點使用相同穩定 ID 合併，既有來源 metadata 保持一致。

## 既有通聯與存款

通聯保留七個金控 Data Property 參照及七個 pending MappingSlot。存款保留四個 PG 業務概念與 17 個欄位定義；多個 class_uris 是一般 REFERS_TO_CLASS，不產生 OWL 繼承、交集、等價或自動分類。

行員存款指存款人本人是行員。行員 Class 已確認，因此 pending reference 的 class_uri 改為 bank:BankEmployee；來源本人識別、關係 URI、JOIN、適用期間仍待確認，狀態為 pending_depositor_identity_mapping。不能把服務客戶的 AO 編號拿來當存款人本人員編。

存款五張來源為 DEP_NT_ACCT／_HS、DEP_FN_ACCT／_HS、EMP_DEP_NT_ACCT_HS，原始客戶／金額候選沿用既有證據。幣別、快照日、跨來源識別、聚合、去重、時間窗與完整覆蓋均未核定；分類碼 2545、普通分類碼與歷史門檻只作來源觀察。分行／數位及帳戶模型仍排除。

## 圖譜與產生器

目前合計 **437 metadata 節點、921 關係、34 個業務概念**：含 271 DataFieldDefinition、7 MappingSlot、35 SourceTable、37 BusinessRelationDefinition、5 MetadataModule。通聯模組沿用原有投影，沒有獨立 MetadataModule 節點。Object Property 與 Data Property 的 RDF 參照分開標記，避免把服務關係當欄位屬性。

所有節點有 MetadataNode 與 scope: metadata_only。穩定 ID＋MERGE 可重複載入，但不刪舊資料、不提供完整同步／遷移。未知值及巢狀 metadata 以 JSON 字串保留 null。來源表 database_verified 固定 false，表示本地檔案觀察，不是連線驗證。

新增語意／來源時同步更新 JSON、所屬模組驗證器與測試；不要只修改產生後的 model.cypher。project_graph 是通過模組驗證後共用的投影函式，實際建置入口仍驗證各模組。

在上層 customer360-rdf-owl 執行：

```powershell
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

本輪 62 項 PG 測試通過，無略過，涵蓋保險原始投資金額／手收／客戶貢獻度的來源意義、27 項指標表級來源、既有欄位保持、新指標空候選與 DCI 損益排除、日期／數值型別、跨指標適用範圍、RDF 交叉參照、既有定義保留、跨公司治理歸屬、pending 狀態、端點、escaping、確定性及輸出逐位元組比對。RDF／來源交叉檢查使用本地 rdflib；投影與 Cypher 建置仍只依賴標準函式庫。未執行 SQL、資料庫查核、Neo4j 部署或完整 OWL 推論。
