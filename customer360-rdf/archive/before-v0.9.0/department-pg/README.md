# 部門 PG metadata 模型 v0.8.0

RDF／OWL 定義共通語意；PG 定義部門概念、欄位、關係與來源映射。這裡只有 metadata，不含客戶、人員或交易資料實例。模型參照完整概念 URI，不執行 OWL 推論或資料同步。

本輪新增 AUM 與銀行 AUM 共通語意及七項商品 AUM 候選。fh:measuresProduct 專屬 AUM；手收 PG 改用獨立 fh:feeIncomeFromProduct。理專與歸屬語意沿用前版。依使用者指示不更新圖片。

## Active 模組

| 來源 | 內容 | 契約／驗證器 |
|---|---|---|
| model.json | 貸款照會手機、客戶訪問地址 | model.schema.json ＋ build_cypher.py |
| deposits.json | 台幣、外幣、結構型及行員存款 | deposit_model.py |
| advisory-income.json | 理專、服務關係、通用商品手收架構 | advisory_income_model.py |
| product-fees.json | 境內 SI、境外 SN 商品手收及來源候選 | product_fees_model.py |
| product-aum.json | 七項商品 AUM、估值與來源候選 | product_aum_model.py |

build_cypher.py 合併五個 active 模組產生 model.cypher；不連線部署。drafts/employee-deposit.json 是已取代草稿，不參與建置。

## 理專與商品手收

理專參照 bank:FinancialAdvisor（繼承 bank:BankEmployee），行員編號欄位仍參照 bank:employeeId。另以 BusinessRelationDefinition 描述「理專服務客戶」，參照 fh:serves，保存行員／客戶識別欄位的 pending 映射。理專 OWL Class 已在銀行共通層建立；PG 保留來源映射，沒有新增理專 ID、角色自動認定或客戶實例。

通用商品手收參照 bank:BankFeeIncome；另以關係定義參照 fh:feeIncomeFromProduct（domain 為 FeeIncome），對應收入來源金融商品；不再使用 AUM 專屬的 fh:measuresProduct。收入期間與快照日期各自建欄位；金額、幣別、行員、客戶、商品識別均是 metadata 欄位定義。另以 bank:attributedToAdvisor 指向 bank:FinancialAdvisor，通用商品手收與 SI／SN 各有一個 pending 歸屬關係定義，沿用概念上現有 employeeId 欄位，不重複建員編欄位。未選定資料列粒度、日／月／年累計、收入認列及人員歸屬。

權限由使用者暫緩，access_policy_status 只記錄 deferred_by_user，不包含可見角色、內外部揭露或授權規則。

## 有來源的第一批手收

| 概念 | RDF 指標／商品參照 | 來源候選 |
|---|---|---|
| 境內結構型商品手收（SI） | bank:BankFeeIncome；商品關係指向 bank:StructuredFinancialProduct | DSDEP.SI_PERFO_RPT／_HS 的 CUSTOMER_ID、FEE_AMOUNT_TWD |
| 境外結構型商品手收 | 同上 | DSFND.PB_FUND_SPREAD_DAILY 的 IDNO、BRHREBATEAMT |

這兩項只對應既有「結構型金融商品」，不假定是結構型存款、DCI 或互斥商品分類。不新增境內／境外商品 OWL Class。每項保留七個欄位定義：employeeId、customerId、productId、amount、currency、incomePeriod、snapshotDate。

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

`department-pg/product-aum.json` 保留五個欄位定義：customerId、productId、amount、currency、snapshotDate。amount 狀態為 pending_aum_recognition，selected table／column 均 null；不把存款原始餘額直接認定為核定 AUM，也不將欄位名稱中的 TWD 直接轉成幣別常數。

既有 PB_FUND_MONTH SQL 將「其他-國外有價證券」等分類歸為海外股票，需覆核分類範圍；TRUSTPRD 是類型，不代替單一商品識別。自營債券的三個欄位是同一估值公式的輸入，不是任選金額。其舊 SQL 取全體每月最大日期，不是各客戶最後交易日，也不自動成為新版預設選日規則。

商品分類與來源可能重疊；七項不是完整銀行 AUM 清冊，不自動相加成銀行 AUM。認列、幣別、快照日、跨來源識別、去重及聚合仍待確認；execution 全部 null。來源 SQL 只作唯讀文字證據。

商品分類參照保存在 product_class_uris；BusinessRelationDefinition 的 HAS_TARGET_CLASS 包含共通 FinancialProduct 與較具體的商品分類，僅作語意限定 metadata，沒有 OWL 交集或自動分類。存款 AUM 的 basis_concept 指向既有存款概念；來源與證據沿用，原始餘額仍不是已核定 AUM。底表節點使用相同穩定 ID 合併，既有來源 metadata 保持一致。

## 既有通聯與存款

通聯保留七個金控 Data Property 參照及七個 pending MappingSlot。存款保留四個 PG 業務概念與 17 個欄位定義；多個 class_uris 是一般 REFERS_TO_CLASS，不產生 OWL 繼承、交集、等價或自動分類。

行員存款指存款人本人是行員。行員 Class 已確認，因此 pending reference 的 class_uri 改為 bank:BankEmployee；來源本人識別、關係 URI、JOIN、適用期間仍待確認，狀態為 pending_depositor_identity_mapping。不能把服務客戶的 AO 編號拿來當存款人本人員編。

存款五張來源為 DEP_NT_ACCT／_HS、DEP_FN_ACCT／_HS、EMP_DEP_NT_ACCT_HS，原始客戶／金額候選沿用既有證據。幣別、快照日、跨來源識別、聚合、去重、時間窗與完整覆蓋均未核定；分類碼 2545、普通分類碼與歷史門檻只作來源觀察。分行／數位及帳戶模型仍排除。

## 圖譜與產生器

目前合計 **156 metadata 節點、299 關係、17 個業務概念**：含 76 DataFieldDefinition、7 MappingSlot、10 SourceTable、14 BusinessRelationDefinition、4 MetadataModule。Object Property 與 Data Property 的 RDF 參照分開標記，避免把服務關係當欄位屬性。

所有節點有 MetadataNode 與 scope: metadata_only。穩定 ID＋MERGE 可重複載入，但不刪舊資料、不提供完整同步／遷移。未知值及巢狀 metadata 以 JSON 字串保留 null。來源表 database_verified 固定 false，表示本地檔案觀察，不是連線驗證。

新增語意／來源時同步更新 JSON、所屬模組驗證器與測試；不要只修改產生後的 model.cypher。project_graph 是通過模組驗證後共用的投影函式，實際建置入口仍驗證各模組。

在上層 customer360-rdf-owl 執行：

```powershell
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

本輪 43 項 PG 測試通過，無略過，涵蓋檔案來源、欄位語意、RDF 交叉參照、pending 狀態、端點、escaping、確定性及輸出逐位元組比對。RDF／來源交叉檢查使用已安裝的本地 rdflib；投影與 Cypher 建置仍只依賴標準函式庫。未執行 SQL、資料庫查核、Neo4j 部署或完整 OWL 推論。
