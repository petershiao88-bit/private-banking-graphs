# 客戶360 RDF／OWL＋部門 PG：新 Session 交接

更新：2026-10-22。目前版本：**v0.4.0，設計草案，已完成存款層級更正**。
工作目錄：`C:\Users\petershiao\Desktop\Ontology\客戶360\customer360-rdf-owl`。

## 1. 最重要：不要再把部門組合放回 RDF

最後使用者明確更正：**台幣存款、外幣存款、結構型存款是部門 PG 的業務概念，不是 RDF／OWL 類別。** 這項決議取代本輪較早的多重繼承討論及誤實作。

銀行 RDF 只保留四個共通 Class，全部直接 `rdfs:subClassOf fh:FinancialProduct`：

- `bank:DepositProduct`：存款商品。
- `bank:TWDFinancialProduct`：台幣金融商品。
- `bank:ForeignCurrencyFinancialProduct`：外幣金融商品。
- `bank:StructuredFinancialProduct`：結構型金融商品。

**不得新增或恢復** `bank:TWDDepositProduct`、`bank:ForeignCurrencyDepositProduct`、`bank:StructuredDepositProduct`。它們已從來源與整合輸出移除，測試會檢查不存在。

PG 組合是一般關聯，不是 OWL 繼承、交集、等價或自動推論：

| PG 業務概念 | `class_uris` 參照的 RDF 概念 |
|---|---|
| 台幣存款 | 存款商品＋台幣金融商品 |
| 外幣存款 | 存款商品＋外幣金融商品 |
| 結構型存款 | 存款商品＋結構型金融商品 |
| 行員存款 | 存款商品；行員人員概念尚待確認 |

也不建立「銀行金融商品」中間層，治理歸屬用 Annotation 表達。

## 2. 任務背景、分工與使用者偏好

- 以 `Ontology/客戶360/金控自然人客戶360.xlsx` 的186項需求盤點，漸進收斂客戶360語意。Excel不是客戶實例資料，七大項不自動各成一個OWL類別。
- 金控／子公司使用 RDF／OWL 定義共通語意；底表現況不應決定概念分類。
- 部門使用 Property Graph 描述業務概念、資料欄位、共通語意參照及底表／欄位／JOIN／篩選映射。PG是metadata圖，不是把每位客戶、每筆存款或每支電話建成資料實例。
- 真實資料留在來源系統；不要求本輪為每筆資料制定共用RDF實例URI。PG以完整RDF**概念URI**對齊語意，再透過映射指向底表。
- 金控不直接映射底表；子公司可映射共用客戶資料，部門映射業務資料。不要恢復早期「只有部門才能映射」限制。
- 業務定義要精簡、只寫「是什麼」；限制與尚未核定內容另寫說明／observations，不在definition反覆加「不代表什麼」。
- 繁體中文、逐項確認、先講白話與小圖再看JSON。明確區分已確認、提議、已實作。
- 使用者已要求：**本專案內相關程式、建置與測試直接執行，不再逐項詢問。** 遵守上層 `客戶360/AGENTS.md`，不繞過平台核准、不擅自外部部署。
- Zed維護本體與PG；ChatGPT Desktop另做簡報。本輪不製作簡報。

## 3. 目前已實作 RDF

`holding-core.ttl` 有5個金控Class：Customer、FinancialProduct、ContactInformation、MobileContactInformation、AddressContactInformation。

```text
客戶 ──具有通聯資訊──→ 通聯資訊
                         ├─ 手機通聯資訊
                         └─ 地址通聯資訊
客戶 ──持有──→ 金融商品
```

客戶到通聯／商品是Object Property；手機／地址到通聯才是subclass。

- 手機、地址及其七個Data Property統一放金控，沒有銀行／證券／人壽重複的通聯類別或重複欄位。
- `fh:mobileNumber` domain為手機通聯；countryCode、city、district、addressLine、postalCode、fullAddress的domain為地址通聯；range全部xsd:string。
- 2個Object Property：`fh:hasContactPoint`、`fh:holds`。
- 5個Annotation Property：rdfs:label、skos:definition、fh:governanceLevel、fh:subsidiary、fh:department。保留department詞彙不代表建立部門OWL類別。
- `bank-deposit.ttl` 有第1節的4個銀行共通Class。核心通聯語意未變。
- 整合模型目前：**9 Class、2 Object Property、7 Data Property、5 Annotation Property、124 triples**。數量只記錄當前版本，不是未來固定目標。
- 客戶餘額、快照日期、行員編號不放到商品Class上；它們在PG是資料欄位定義。

## 4. 目前已實作 PG

有效來源：`department-pg/model.json`（通聯）、`department-pg/deposits.json`（存款）。

| 業務概念 | 欄位 |
|---|---|
| 貸款照會手機 | 參照fh:mobileNumber，來源待確認 |
| 客戶訪問地址 | 參照金控六個地址欄位，來源待確認 |
| 台幣／外幣／結構型存款 | customerId、currency、balance、snapshotDate，各4項 |
| 行員存款 | 上述4項＋employeeId，共5項 |

- 存款JSON的`field_definitions`是共用欄位定義；各concept的`fields`存來源候選與狀態，不是真實客戶資料值。
- 每個存款concept的`class_uris`是共通RDF類別URI陣列，產生多條`REFERS_TO_CLASS`一般關係；不宣告組合OWL類別或自動推論。
- `deposit_model.py`是存款格式的受限Python驗證器；通聯使用`model.schema.json`與原驗證契約。模型擴充需同步更新驗證器與測試，不只修改JSON。
- `build_cypher.py`離線合併兩模組產生Neo4j 5 `model.cypher`；**未部署**。
- 合計 **50 metadata節點、82關係、6個業務概念**，含17個存款欄位定義、5張來源表參照。
- `department_owner`未知；沒有真實資料實例、可執行來源SQL或自動資料同步。
- `drafts/employee-deposit.json`已標記superseded，不是建置輸入；不要拿舊草稿取代active來源。

## 5. 私銀來源證據與尚未解決的缺口

來源檔案只能證明SQL文字／metadata的內容，不代表已連線驗證資料庫或執行成功。

| 底表 | 客戶欄位 | 原始金額欄位 | SQL使用日期 |
|---|---|---|---|
| DSDEP.DEP_NT_ACCT | CUST_ID | BAL_AMT | DATA_DT |
| DSDEP.DEP_NT_ACCT_HS | CUST_ID | BAL_AMT | LST_MTN_DT |
| DSDEP.DEP_FN_ACCT | CUST_ID | AVAIL_BAL | LST_MTN_DT |
| DSDEP.DEP_FN_ACCT_HS | CUST_ID | AVAIL_BAL | LST_MTN_DT |
| DSDEP.EMP_DEP_NT_ACCT_HS | CUST_ID | BAL_AMT | LST_MTN_DT |

證據入口：

- `Ontology/私銀智能問答/sources/sql/1.AUM_DETAIL.sql`：59–89現況、91–123歷史、125–136員工、140–182合併。
- `Ontology/私銀智能問答/sources/metadata/收入_metadata.xlsx`：DEP_NT_ACCT_HS與EMP_DEP_NT_ACCT_HS工作表；DATA_DT為資料日期，YYYYMM為Snapshot年月，LST_MTN_DT沒有業務定義。
- `AUM_metadata.xlsx`的員工工作表叫`DSDEP.EMP_NT_ACCT_HS`，與SQL名稱不同；不當作第二張已確認底表或自動別名。
- 更完整證據路徑／列號已保存在`deposits.json.evidence`。

**行員存款定義已確認：存款人本人是行員，不是行員管理客戶的存款，亦不限定員工優惠方案。**

不得拿`AUM_TMP02.EMP_NO`補employeeId：它經PB_CUST_005及客戶AO關係取得，是管理客戶的AO員編。證據在`2._AUM_SUMY.~sql` 198–217及`0_PB_CUST_DEATAIL.sql` 102–110。`2._AUM_SUMY.~sql`是檔案證據，不能宣稱為目前部署版本。

最後AUM／CUST_TRANSACTION_SUMMARY沒有員工來源標記；AUM_REPORT進一步彙總後不保留客戶與員工明細。因此不能從最後大表直接還原「行員本人存款」。

未解決：

1. 幣別欄位／餘額計價幣別未確認。FN分支TYP_DTL寫台幣，employee分支寫外幣卻含台幣分類；即使台幣概念也不把來源currency硬填TWD。
2. snapshotDate未選定DATA_DT、LST_MTN_DT或YYYYMM；年月不自行補月初／月底。
3. employeeId本人識別、人事來源、JOIN及身分適用期間未確認；人員RDF語意保持PendingSemanticReference，URI為null。
4. 員工底表是否涵蓋所有行員本人存款未知。一般台幣／外幣來源候選也不是完整業務覆蓋承諾。
5. 原始餘額映射不等於舊SQL的SUM；粒度、跨來源識別、聚合、去重與時間窗未核定。
6. 結構型2545在NT、FN、employee均有分類證據；不假定互斥、可以直接UNION或套用舊門檻。普通存款分類碼不含2545，不代表共通概念互斥。

`execution`及selected table／column仍為null；分類碼、歷史門檻只保留觀察證據，不變成新版操作規則。

## 6. 嚴格範圍與下一步

**分行／數位分類、帳戶模型與帳戶識別本輪明確排除，使用者要先縮小範圍，不要自動補回。**

目前停留點：存款語意與PG欄位模型已落地，最後三個組合類別的RDF／PG邊界已修正並通過測試。下一輪先簡短回報狀態，依使用者指示逐項確認存款映射缺口，或接著收斂其他金融商品，不自行定案未知欄位。

其他金融商品尚未寫入：先前已盤私銀25個產品與服務，來源`Ontology/私銀智能問答/ontology/independent_concepts/concept_graph.json`。該清單同時含存款、基金、ETF、股票、債券、結構型、DCI、保險、黃金、放款、信託安排及外匯／開狀／保管服務，不能全部不加區分地變成FinancialProduct子類別。360另有信用卡、貸款細分類、人壽保險等需求，也未實作。

集團職員／銀行行員曾討論，尚未正式建模。帳戶、契約、保單、持有部位延後；不強制所有商品經帳戶持有。結構型存款不等同DCI，沒有保本或互斥公理。

不自行新增Hash、有效註記、基數、互斥、等價、sameAs、反向、keys、property chain、SHACL、格式、必填、唯一性或碼表。Customer僅情境聚焦自然人，未形式化等同NaturalPerson；holds持有認定與時間範圍仍待確認。

## 7. 檔案、建置與驗證

建議閱讀順序：上層`AGENTS.md` → 本交接 → `README.md` → `holding-core.ttl`、`bank-deposit.ttl` → `department-pg/README.md`與active JSON。

- RDF來源只讀`build-config.json`明列的兩份TTL；整合`customer360-ontology.ttl`與`.owl`由`tools/build_ontology.py`產生，勿分別手改。
- catalog只對應有效URI／v0.4.0。全部example.org仍是示意命名空間。
- `.venv`已安裝rdflib 7.6.0，requirements.txt釘版，不修改系統Python。
- 勿執行`tools/legacy-v0.2.0/`舊建置器／驗證器，模型寫死且舊232 triples基準已不適用。

在工作目錄執行：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

最後實際驗證：**RDF 13項＋PG 29項全部通過，無略過**；6份有效Python及5份JSON語法檢查通過；TTL／RDF/XML與來源模型圖同構一致。測試包括三個組合類別不在RDF、PG多概念參照、來源證據、未定案值、確定性輸出及通聯回歸。

未執行完整OWL reasoner、一致性／可滿足性、SHACL、GUI、SQL、真實資料或Neo4j部署。不得把語法／結構測試說成完整OWL或業務驗證。編輯器曾顯示rdflib找不到，是語言伺服器未選本地.venv，不是命令列解析失敗；pyrightconfig已提供。

## 8. 快照與其他專案

- `archive/before-v0.3.0/`：舊公司別通聯與部門OWL設計，已被取代。
- `archive/before-v0.4.0/`：新增存款前的工作副本。
- **`archive/before-deposit-pg-correction/`：誤加三個組合OWL類別的錯誤實作快照，只供回查，不是核定版本，不可恢復。**
- 私銀SQL／metadata／圖譜、需求Excel、外部ChatGPT同步專案及sources、enterprise_kb_poc與asset-financial-ontology都未修改。沒有提交Git、部署或可確認的雲端備份。

## 9. 可直接貼到新 Session

> 請先閱讀 Ontology/客戶360/AGENTS.md 及 Ontology/客戶360/customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md，再接續客戶360 RDF＋部門PG v0.4.0。RDF銀行層僅有存款商品、台幣／外幣／結構型金融商品；台幣存款、外幣存款、結構型存款及行員存款只在PG，一般關係參照共通概念，不建立組合OWL類別或多重繼承。分行／數位、帳戶先排除。來源未知保持待確認；專案內相關程式與測試直接執行，不逐項問我。先摘要目前狀態，再依我的下一項指示繼續。
