# 客戶360 RDF／OWL＋部門 PG：v0.5.0 交接

更新：2026-10-22。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 最新決議與停留點

使用者已接受「金控指標 → 金控手收 → 銀行手收 → PG 各商品手收」架構，並要求參照私銀既有手收及目前產品先建一點。職員／行員與理專部分一併落地。**權限由使用者明確暫緩討論，不自行補內外部指標分類、揭露標記或角色可見規則。**

已實作：金控 Employee、Metric、FeeIncome；銀行 BankEmployee、BankFeeIncome、employeeId；PG 理專、服務客戶關係、通用商品手收，以及境內 SI／境外 SN 兩項有來源證據的手收候選。來源未知值保持 pending/null，沒有部署或執行來源 SQL。

## 共通語意

- bank:BankEmployee 繼承 fh:Employee。職員是任職於金控或旗下子公司的人員；行員是任職於銀行的職員。
- bank:employeeId 是行員 Data Property，domain bank:BankEmployee、range xsd:string。共通屬性不需先有底表映射；未承諾跨銀行唯一或與金控共用員編等同。
- fh:serves 是職員服務客戶的 Object Property；不要求每位職員必有客戶，也不代表取得資料閱覽權。
- fh:FeeIncome 繼承 fh:Metric；bank:BankFeeIncome 繼承 fh:FeeIncome。銀行手收描述銀行認列範圍與口徑，金控手收供其他子公司沿用。
- fh:measuresProduct：Metric → FinancialProduct。手收與商品以關係連接；手收不是商品子類別。
- 理專是部門 PG 角色，不建立理專 OWL Class／新理專 ID；員編、客戶對應、理專角色認定與適用期間的來源仍待確認。
- 金額、計價幣別、收入期間、快照日、員編、客戶／商品識別目前是 PG 欄位定義；除 employeeId 外，沒有替它們捏造共通 RDF 屬性 URI。

## 第一批商品手收範圍

| PG 概念 | 可對應的現有 RDF 商品 | 來源證據 |
|---|---|---|
| 境內結構型商品手收（SI） | bank:StructuredFinancialProduct | 8.INCOME_DETAIL.sql 131–148：DSDEP.SI_PERFO_RPT／_HS，CUSTOMER_ID、FEE_AMOUNT_TWD，聚合後 UNION |
| 境外結構型商品手收 | 同上 | 同檔 191–202：DSFND.PB_FUND_SPREAD_DAILY，IDNO、BRHREBATEAMT，FHID='SN' 與 BAOPCCCODE LIKE '2E%' |

兩者參照 bank:BankFeeIncome，並以關係定義參照 fh:measuresProduct 連到 StructuredFinancialProduct。只細化 PG 業務範圍，未新增境內／境外商品 RDF，也未把它們對成結構型存款。私銀產品對照 product_code 為 bank_structured_domestic／bank_structured_offshore。

- **境內只有 SI，不是完整境內總手收。** ELI／FCI 尚未納入。
- current SI metadata 的 FEE_AMOUNT_TWD 為手續費換算台幣；歷史表語意未獨立核對。SN 的 BRHREBATEAMT 為分行手續費，幣別未定。selected currency 均 null。
- TRADE_DATE 是交易日，FEEDATE 是手續費發生日；不直接選成 snapshotDate。incomePeriod 亦未決定為當日、當月或年度累計，不自行補日期／月份。
- 員編候選：SI current 的 RM_ID／USER_ID；SN 的 BAOEMPID／SAOEMPID。分別保留角色意義，不自動選定收入歸屬，也不從有服務客戶推斷理專資格。
- S_PCC_CODE 在 SI SQL 有用，但提供的 current metadata 未列。PCC 不是員編。
- FUNDID 是基金代碼，對 SN 的適用性待確認；DEALNO 是交易單號，不拿來當商品 ID。
- 舊 SUM、GROUP BY、UNION、日期轉換及篩選只作 observations；所有 execution 值仍 null。舊彙總未保留員編／商品識別，不能直接還原理專／單一商品手收。
- 私銀存款收入屬利收，未加入手收；基金、ETF 等尚未加入本 RDF 的產品本輪未擴充。HTML 是獨立模型，不可把其中商品誤稱為目前 RDF 已實作。

完整 SQL 範圍、metadata 工作表與列號、原始欄位及限制存於 department-pg/product-fees.json；新手收沒有可執行取數 SQL。私銀來源檔全部唯讀。

## 既有模型必須保留的邊界

- 金控五個既有 Class、兩個 Object Property 與七個通聯 Data Property 保持原語意，手機／地址仍在金控。
- 銀行 DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct 仍直接繼承 fh:FinancialProduct；無銀行金融商品中間層。
- 台幣／外幣／結構型存款及行員存款只在 PG；不得恢復三個組合 OWL Class、多重繼承或交集公理。
- 行員存款定義是存款人本人為行員，不是行員管理客戶存款或限定優惠方案。已補 BankEmployee 語意，但存款人的來源／本人對照仍 pending；不能用 AUM_TMP02.EMP_NO 代替。
- deposits.json 的 pending_semantic_reference.class_uri 現為 bank:BankEmployee，status 為 pending_depositor_identity_mapping；relation_uri／source_table／source_column／join_rules 仍 null。
- 五張存款來源與原有證據保留，含唯一已觀察員工來源 DSDEP.EMP_DEP_NT_ACCT_HS。metadata 的 EMP_NT_ACCT_HS 名稱差異仍不當成別名。
- 存款幣別／快照日期／聚合／跨來源識別未核定；2545 等分類碼、歷史門檻不是新執行規則。
- 分行／數位、帳戶、帳戶識別、契約、保單與持有部位繼續延後。不加未確認的 Hash、基數、互斥、等價、sameAs、keys、反向、property chain、SHACL 或格式／必填限制。

## Active 檔案與建置

RDF 來源由 build-config.json 明列：holding-core.ttl、bank-deposit.ttl、bank-common.ttl。catalog 對應有效 URI 與 v0.5.0。整合 customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生，勿手改；不連網解析 example.org。

PG active 來源：model.json、deposits.json、advisory-income.json、product-fees.json。前三個來源含保留通聯、存款與新角色／通用手收，第四個含有證據的兩項商品手收。各有 JSON Schema／Python executable schema；擴充需同步驗證器與測試。build_cypher.py 合併產生 model.cypher，未部署。drafts 是歷史草稿，不替代 active 來源。

tools/seed_product_fees.py 是本批固定內容的一次性初始產生器，拒絕覆寫已存在 active JSON；後續修改 product-fees.json。它不是通用 SQL 分析器。不要執行 tools/legacy-v0.2.0。

在工作目錄執行：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

目前：**14 Class、4 Object Property、8 Data Property、5 Annotation Property、168 triples**；PG **10 概念、94 metadata 節點、153 關係**。RDF 14 項＋PG 37 項通過，無略過；TTL／RDF/XML 與來源圖同構，PG 輸出確定且逐位元組一致。來源證據測試包含 cp950 SQL、metadata 原始儲存格與私銀產品語意。

未執行完整 OWL reasoner／SHACL／GUI／SQL／真實資料或 Neo4j 部署，不把結構測試說成完整業務驗證。只沿用專案 .venv／rdflib 7.6.0。

## 快照與未修改範圍

archive/before-v0.5.0 為本輪變更前完整專案來源／工具／測試快照，不含 venv。舊 before-deposit-pg-correction 仍是錯誤組合 OWL 實作，不能恢復。before-v0.3.0、before-v0.4.0 只供回查。

私銀 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC、外部 ChatGPT 同步專案均未修改；沒有 Git 提交、部署或可確認雲端備份。

## 接續方式

使用繁體中文，先白話與小圖再看 JSON；明確區分確認、提議、已實作。來源未知保持 pending，不自行挑員編／日期／幣別／認列口徑。可接著逐項確認本批 SI／SN 的細節，或依使用者指示擴其他產品；不要自動擴完整產品清單或權限。

本專案相關檔案／程式／建置／測試已授權直接執行，遵守上層 AGENTS.md，不反覆詢問；未授權外部部署或訊息傳送。

可貼到新 Session：

> 請先讀客戶360/AGENTS.md、customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md 與 README.md，接續 v0.5.0。職員→行員、理專 PG、金控指標→手收→銀行手收，以及 PG 商品手收已建立。第一批只有境內 SI 與境外 SN，保留 SQL／metadata 候選與未定案值；權限由我暫緩，帳戶與分行／數位仍排除。先摘要狀態，再依我的指示逐項繼續。
