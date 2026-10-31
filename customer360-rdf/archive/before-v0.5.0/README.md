# 客戶 360：共通 RDF／OWL 與部門 Property Graph

目前版本：**v0.4.0，2026-10-22，設計草案**。工作目錄：`Ontology/客戶360/customer360-rdf-owl/`。本輪新增銀行存款語意與部門 PG 存款映射模型，未連線部署；修改前快照保存在 `archive/before-v0.4.0/`。

## 分工

- 金控／子公司 RDF：共通概念、關係、屬性及正式繼承，不依底表現況決定概念分類。
- 部門 PG：業務概念、資料欄位定義、RDF 參照及底表映射候選，不執行 OWL 推論。
- 真實資料留在來源系統；golden record、有效性、去重及衝突取捨由來源權責系統處理。

## RDF 模型

金控核心保留：客戶、金融商品、通聯資訊、手機通聯資訊、地址通聯資訊。手機與地址繼承通聯；客戶透過 `fh:hasContactPoint` 連到通聯、透過 `fh:holds` 連到金融商品。

銀行存款模組：

| Class | 父類別 |
|---|---|
| `bank:DepositProduct` 存款商品 | `fh:FinancialProduct` |
| `bank:TWDFinancialProduct` 台幣金融商品 | `fh:FinancialProduct` |
| `bank:ForeignCurrencyFinancialProduct` 外幣金融商品 | `fh:FinancialProduct` |
| `bank:StructuredFinancialProduct` 結構型金融商品 | `fh:FinancialProduct` |


不建立「銀行金融商品」中間層；公司治理歸屬透過 Annotation 表達。**台幣存款、外幣存款、結構型存款只建立在部門 PG，不建立對應 OWL Class 或多重繼承組合。** PG 用一般關係分別參照存款商品與台幣／外幣／結構型金融商品；不宣告交集等價、反向分類或互斥。商品幣別與餘額的計價幣別是不同層次，來源仍須確認。

目前整合模型共 **9 Class、2 Object Property、7 Data Property、5 Annotation Property、124 triples**。七個 Data Property 仍僅為金控通聯欄位：手機號碼、國家／地區代碼、縣市、鄉鎮市區、街道門牌、郵遞區號、完整地址。沒有把客戶餘額、員編、快照日期放到商品類別上。

## 部門 PG

來源檔分開維護，產生同一份 `model.cypher`：

| 業務概念 | 資料欄位／RDF 屬性參照 |
|---|---|
| 貸款照會手機 | 既有金控手機號碼屬性 |
| 客戶訪問地址 | 既有金控六個地址屬性 |
| 台幣存款 | 客戶識別、幣別、餘額、快照日期 |
| 外幣存款 | 同上四項 |
| 結構型存款 | 同上四項 |
| 行員存款 | 同上四項＋行員識別 |

行員存款指「存款人本人為銀行行員的存款」，不是 AO 管理的客戶存款，也不限於優惠方案。行員 RDF 類別及本人身分對照仍待確認，不以 `AUM_TMP02.EMP_NO` 代替，也不捏造行員類別 URI。行員存款在 PG 關聯存款商品，並保留待確認的人員語意參照，沒有行員存款 OWL 子類別。

此版 PG 共 **50 metadata 節點、82 關係**，包括既有通聯、四個存款概念、17 個存款欄位定義、五張有本地證據的來源表參照。這些不是客戶資料實例。`REFERS_TO_CLASS` 等關係不會產生 RDF 公理或自動跨系統同步。

來源範圍與缺口：

- 台幣一般分支：`DSDEP.DEP_NT_ACCT`、`DSDEP.DEP_NT_ACCT_HS`，原始客戶／金額欄位為 `CUST_ID`／`BAL_AMT`。
- 外幣一般分支：`DSDEP.DEP_FN_ACCT`、`DSDEP.DEP_FN_ACCT_HS`，原始客戶／金額欄位為 `CUST_ID`／`AVAIL_BAL`。
- 行員分支僅觀察到 `DSDEP.EMP_DEP_NT_ACCT_HS` 的 `CUST_ID`／`BAL_AMT`；是否完整涵蓋行員本人所有存款待確認。
- 結構型分類碼 2545 在 NT、FN、employee 分支均有證據；不假定它們互斥或可以直接 UNION。
- 來源幣別與餘額計價幣別、統一快照日期、行員識別、客戶跨來源對照、粒度、聚合、JOIN 及時間窗未核定。候選寫在 JSON，selected mapping 保持 null。
- SQL 普通台幣分類碼不含 2545，不代表 RDF 台幣與結構型概念互斥；現有來源候選不是完整業務覆蓋的承諾。
- 分類碼、歷史門檻及 SQL 日期僅是檔案證據，不自動轉為新版執行規則。`execution` 保持 null。

**分行／數位分類、帳戶模型與帳戶識別仍排除在本輪之外。** 詳見 `department-pg/README.md`。

## 編輯來源及產生檔

| 檔案 | 用途 |
|---|---|
| `holding-core.ttl` | 金控核心模型來源；本輪僅更新版本資訊 |
| `bank-deposit.ttl` | 新增銀行存款分類來源，匯入金控核心 |
| `build-config.json` | 明確列出兩份來源、版本、日期與輸出 |
| `customer360-ontology.ttl`、`.owl` | 自含整合 Turtle／RDF/XML，建置產生，勿手改 |
| `catalog-v001.xml` | 有效本體及 v0.4.0 URI 到本機檔案的對應 |
| `department-pg/model.json` | 保留的通聯 PG 編輯來源 |
| `department-pg/deposits.json` | 存款 PG 欄位、來源候選及證據的有效編輯來源 |
| `department-pg/model.cypher` | 兩個 PG 模組合併產生的 Neo4j 5 腳本，未部署 |
| `department-pg/drafts/` | 已取代的討論草稿，不參與建置 |
| `HANDOFF-ZED-RDF-PG-20261022.md` | 最新完整交接，含新 Session 可貼指令與最後層級更正 |
| `HANDOFF-ZED-RDF-20261021.md` | 舊檔名相容入口，指向最新交接 |
| `archive/` | 先前版本快照，不參與建置 |
| `tools/legacy-v0.2.0/` | 舊工具與舊基準，只供追溯，勿執行 |

RDF 建置合併明確列出的來源模型，以整合本體資訊取代模組標頭；`owl:imports` 必須在來源清單與 catalog 本機可解析，不連網抓取示意 URI。PG 的通聯 JSON Schema 與存款 Python 契約驗證器分開，不把未定案映射當作可執行取數服務。

## 建置與驗證

依賴限定本專案 `.venv`，不修改系統 Python。首次設定：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

在本目錄執行：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

`--check` 只讀不寫。以 RDF 圖同構比對，不固定三元組數量或文字排列。使用 rdflib 7.6.0 通用解析器；另測試共通分類繼承、組合類別不在 RDF／只以 PG 關聯表達、通聯模型語意未變、治理與 catalog、來源驅動建置、PG RDF 參照、來源證據及確定性輸出。本輪 RDF 13 項、PG 29 項測試全數通過，無略過；另有 6 份有效 Python 與 5 份 JSON 語法檢查通過。完整 OWL reasoner、SHACL、GUI、SQL、真實資料與 Neo4j 部署未執行。

`pyrightconfig.json` 指定本專案 `.venv`；若從整個 Ontology 工作區開啟仍顯示 rdflib 找不到，語言伺服器需選擇此子專案 `.venv/Scripts/python.exe`。命令列均使用該環境。

## 其他未定案邊界

不新增 Hash、有效註記、基數、互斥、等價、sameAs、反向關係、keys、property chain、SHACL 或格式／必填限制。自然人情境不等同 Customer 已形式化為 NaturalPerson。`holds` 的持有認定及時間範圍仍待確認。

其他金融商品、帳戶／契約／保單／持有部位、集團職員及行員完整模型均未加入；結構型存款不直接等同 DCI，亦未宣告保本條件。國家碼標準、地址行政層級與組合規則未核定。`example.org` 仍為示意命名空間。外部 ChatGPT 同步專案、私銀 SQL／metadata／圖譜、需求 Excel 及其他 PoC 都未修改。
