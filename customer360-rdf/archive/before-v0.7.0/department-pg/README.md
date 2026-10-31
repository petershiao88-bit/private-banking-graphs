# 部門 PG metadata 模型 v0.6.0

RDF／OWL 定義共通語意；PG 定義部門概念、欄位、關係與來源映射。這裡只有 metadata，不含客戶、人員或交易資料實例。模型參照完整概念 URI，不執行 OWL 推論或資料同步。

本輪只新增銀行 RDF 的股票、債券、海外金融商品共通分類。PG 內容沿用前版並同步 ontology_version；海外股票／海外債券組合尚未建入 PG。

## Active 模組

| 來源 | 內容 | 契約／驗證器 |
|---|---|---|
| model.json | 貸款照會手機、客戶訪問地址 | model.schema.json ＋ build_cypher.py |
| deposits.json | 台幣、外幣、結構型及行員存款 | deposit_model.py |
| advisory-income.json | 理專、服務關係、通用商品手收架構 | advisory_income_model.py |
| product-fees.json | 境內 SI、境外 SN 商品手收及來源候選 | product_fees_model.py |

build_cypher.py 合併四個 active 模組產生 model.cypher；不連線部署。drafts/employee-deposit.json 是已取代草稿，不參與建置。

## 理專與商品手收

理專參照 bank:BankEmployee，行員編號欄位參照 bank:employeeId。另以 BusinessRelationDefinition 描述「理專服務客戶」，參照 fh:serves，保存行員／客戶識別欄位的 pending 映射。沒有新增理專 ID、理專 OWL Class、角色自動認定或客戶實例。

通用商品手收參照 bank:BankFeeIncome；另以關係定義參照 fh:measuresProduct，對應金融商品概念。收入期間與快照日期各自建欄位；金額、幣別、行員、客戶、商品識別均是 metadata 欄位定義。未選定資料列粒度、日／月／年累計、收入認列及人員歸屬。

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

## 既有通聯與存款

通聯保留七個金控 Data Property 參照及七個 pending MappingSlot。存款保留四個 PG 業務概念與 17 個欄位定義；多個 class_uris 是一般 REFERS_TO_CLASS，不產生 OWL 繼承、交集、等價或自動分類。

行員存款指存款人本人是行員。行員 Class 已確認，因此 pending reference 的 class_uri 改為 bank:BankEmployee；來源本人識別、關係 URI、JOIN、適用期間仍待確認，狀態為 pending_depositor_identity_mapping。不能把服務客戶的 AO 編號拿來當存款人本人員編。

存款五張來源為 DEP_NT_ACCT／_HS、DEP_FN_ACCT／_HS、EMP_DEP_NT_ACCT_HS，原始客戶／金額候選沿用既有證據。幣別、快照日、跨來源識別、聚合、去重、時間窗與完整覆蓋均未核定；分類碼 2545、普通分類碼與歷史門檻只作來源觀察。分行／數位及帳戶模型仍排除。

## 圖譜與產生器

目前合計 **94 metadata 節點、153 關係、10 個業務概念**：含 41 DataFieldDefinition、7 MappingSlot、8 SourceTable、4 BusinessRelationDefinition、3 MetadataModule。Object Property 與 Data Property 的 RDF 參照分開標記，避免把服務關係當欄位屬性。

所有節點有 MetadataNode 與 scope: metadata_only。穩定 ID＋MERGE 可重複載入，但不刪舊資料、不提供完整同步／遷移。未知值及巢狀 metadata 以 JSON 字串保留 null。來源表 database_verified 固定 false，表示本地檔案觀察，不是連線驗證。

新增語意／來源時同步更新 JSON、所屬模組驗證器與測試；不要只修改產生後的 model.cypher。project_graph 是通過模組驗證後共用的投影函式，實際建置入口仍驗證各模組。

在上層 customer360-rdf-owl 執行：

```powershell
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

本輪 37 項 PG 測試通過，無略過，涵蓋檔案來源、欄位語意、RDF 交叉參照、pending 狀態、端點、escaping、確定性及輸出逐位元組比對。RDF／來源交叉檢查使用已安裝的本地 rdflib；投影與 Cypher 建置仍只依賴標準函式庫。未執行 SQL、資料庫查核、Neo4j 部署或完整 OWL 推論。
