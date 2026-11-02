# 客戶360：共通 RDF／OWL 與部門 Property Graph

目前版本：**v0.5.0，2026-10-22，設計草案**。已加入職員／行員、金控及銀行手收語意、理專 PG，以及兩項有私銀來源證據的商品手收候選。修改前快照為 `archive/before-v0.5.0/`。

## 共通語意與部門分工

金控／子公司 RDF 定義共通概念、關係、屬性與正式繼承；部門 PG 描述業務概念、欄位、語意參照及來源映射。真實資料留在來源系統，PG 只建 metadata。example.org 為示意命名空間。

```text
金控 RDF：職員 ──服務客戶──→ 客戶
           △
銀行 RDF：行員 ──行員編號──→ 字串
           ↑ 參照
部門 PG： 理專

金控 RDF：指標
           └─ 手續費收入指標
                △
銀行 RDF：銀行手續費收入指標
                ↑ 參照
部門 PG：商品手收／各商品手收 ──對應──→ 金融商品概念
           └─ 欄位、來源候選及計算觀察
```

- `bank:BankEmployee` 繼承 `fh:Employee`；`bank:employeeId` 的 domain 為行員、range 為 xsd:string。無底表映射仍可定義共通屬性。
- `bank:BankFeeIncome` 繼承 `fh:FeeIncome`，再繼承 `fh:Metric`。
- `fh:serves` 連職員與客戶；`fh:measuresProduct` 連指標與金融商品。domain/range 不要求所有職員必有客戶或所有指標必有商品，也不授予資料閱覽權。
- 理專是 PG 的部門業務角色；沿用行員編號，未另造理專 ID。理專認定、服務關係適用期間及來源尚待確認。
- 手收與金融商品透過關係連接；各商品手收留在 PG。收入期間與快照日期分開，日／月／年累計口徑尚未核定。
- **權限由使用者暫緩討論**。未新增內外部指標類別、可見角色、揭露標記或授權規則；JSON 的 deferred_by_user 只記錄延期狀態。

## 既有存款邊界保持

銀行四個商品 Class：DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct，仍全部直接繼承 fh:FinancialProduct。沒有「銀行金融商品」中間層。

台幣／外幣／結構型存款與行員存款只在部門 PG，使用一般關係參照共通分類。不得恢復 TWDDepositProduct、ForeignCurrencyDepositProduct、StructuredDepositProduct 等組合 OWL Class。

行員存款指存款人本人是行員。行員 RDF 語意現在已建立，但本人識別、JOIN 與適用期間仍未解決；deposits.json 的 pending reference 已填 bank:BankEmployee，狀態改為 pending_depositor_identity_mapping。仍不得用客戶管理 AO 的 AUM_TMP02.EMP_NO 代替存款人行員識別。

既有存款五張來源、分類與原始欄位證據保留；幣別、日期、跨來源識別、聚合與完整覆蓋仍待確認。分行／數位、帳戶與帳戶識別繼續排除。

## 第一批商品手收

僅選現有 RDF 的「結構型金融商品」可承接、且有私銀 SQL／metadata 證據的兩項；沒有新增其他商品 RDF Class。

| PG 概念 | 原始來源及金額 | 範圍 |
|---|---|---|
| 境內結構型商品手收（SI） | DSDEP.SI_PERFO_RPT、DSDEP.SI_PERFO_RPT_HS；FEE_AMOUNT_TWD | INCOME_039 的 SI 分支；未納入 ELI／FCI，不是完整境內總手收 |
| 境外結構型商品手收 | DSFND.PB_FUND_SPREAD_DAILY；BRHREBATEAMT | INCOME_042：FHID='SN'、BAOPCCCODE LIKE '2E%' 的既有 SQL 範圍 |

兩者均參照 bank:BankFeeIncome，並透過 fh:measuresProduct 的關係定義指向 bank:StructuredFinancialProduct，沒有把它們視為「結構型存款」。原始欄位、SQL 範圍、metadata 列號與限制保存在 `department-pg/product-fees.json`。

- SI 的 TRADE_DATE 是交易日；SN 的 FEEDATE 是手續費發生日。兩者均未被選為 snapshotDate。
- SI current metadata 的 FEE_AMOUNT_TWD 定義為「手續費換算台幣」；HS 語意未獨立確認。SN 的 BRHREBATEAMT 只定義為「分行手續費」，計價幣別未確認。selected currency 均保持 null。
- SI current 的 RM_ID／USER_ID，及 SN 的 BAOEMPID／SAOEMPID，只記錄為不同人員角色的候選；不自動認定理專角色或收入歸屬。
- SN 的 FUNDID 在 metadata 是基金代碼，對 SN 商品識別的適用性待確認；SI 的 DEALNO 是交易單號，不代替商品 ID。
- 舊 SQL 的 SUM、GROUP BY、UNION、日期轉換及篩選只保存為觀察，不變成新版執行規則。舊彙總未保留員編與商品識別，不能直接還原理專／單一商品手收。
- 私銀存款收入目前屬利收，未硬塞進手收。基金、ETF 等僅存在其他 HTML／私銀模型的商品，尚未擴入本 RDF。

## 有效來源與輸出

| 檔案 | 用途 |
|---|---|
| holding-core.ttl | 金控共通語意：既有通聯、客戶、金融商品，以及職員、指標與手收 |
| bank-deposit.ttl | 四個銀行共通商品分類 |
| bank-common.ttl | 行員、行員編號及銀行手收 |
| build-config.json、catalog-v001.xml | 明列三份來源與本機 URI／版本對應 |
| customer360-ontology.ttl、.owl | 自含整合輸出，由 tools/build_ontology.py 產生，勿手改 |
| department-pg/model.json | 通聯 PG |
| department-pg/deposits.json | 存款 PG 與原始來源證據 |
| department-pg/advisory-income.json | 理專、服務客戶關係及通用商品手收欄位架構 |
| department-pg/product-fees.json | 第一批兩項具來源證據的商品手收候選 |
| department-pg/model.cypher | 四個 PG 模組合併產生的 Neo4j 5 metadata 腳本；未部署 |
| HANDOFF-ZED-RDF-PG-20261022.md | 最新交接入口 |

共 **14 Class、4 Object Property、8 Data Property、5 Annotation Property、168 triples**。PG 共 **10 個業務概念、94 metadata 節點、153 關係**。數字僅描述目前版本，不是未來固定基準。各模組的 executable schema 與測試需隨擴充同步更新。

## 建置與驗證

在本目錄執行，沿用本地 .venv／rdflib 7.6.0：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

本輪 RDF 14 項＋PG 37 項通過，無略過，含舊通聯／存款回歸、RDF 參照與繼承、來源檔案證據、日期／角色未定案值與確定性輸出。未執行完整 OWL reasoner、SHACL、GUI、SQL、真實資料或 Neo4j 部署。

不新增未確認的 Hash、有效註記、基數、互斥、等價、sameAs、keys、反向關係、property chain 或格式／必填限制。不要執行 tools/legacy-v0.2.0。tools/seed_product_fees.py 是本批固定內容的一次性初始產生器，會拒絕覆寫 active JSON；後續維護 product-fees.json，不把產生器當成通用 SQL 分析器。

私銀來源 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 均未修改。沒有 Git 提交、外部部署或已確認雲端備份。
