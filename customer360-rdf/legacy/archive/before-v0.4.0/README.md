# 客戶 360：共通 RDF／OWL 與部門 Property Graph

目前版本：**v0.3.0，2026-10-21，設計草案**。工作目錄為 `Ontology/客戶360/customer360-rdf-owl/`。本次共識取代 v0.2.0 的公司別通聯分類及部門 OWL 延伸；原檔已封存在 `archive/before-v0.3.0/`，外部 ChatGPT 同步專案未修改。

## 分工與目前模型

- 金控／子公司：RDF／OWL 定義共通概念、關係與屬性；不依底表現況拆分類別。
- 部門：PG 描述業務用途與底表／欄位／JOIN／篩選／SQL 的映射，不建立客戶資料實例，不執行 OWL 推論。
- 真實資料：仍留在來源系統。golden record、有效性、去重與衝突取捨由來源權責系統處理。

```text
客戶 ──具有通聯資訊──→ 通聯資訊
                         ├─ 手機通聯資訊
                         └─ 地址通聯資訊

客戶 ──持有──→ 金融商品
```

客戶到通聯／商品是 Object Property；手機、地址到通聯是 `rdfs:subClassOf`，不是整條鏈都用繼承。

| 宣告 | 目前內容 |
|---|---|
| 5 個 Class | `fh:Customer`、`fh:FinancialProduct`、`fh:ContactInformation`、`fh:MobileContactInformation`、`fh:AddressContactInformation` |
| 2 個 Object Property | `fh:hasContactPoint`、`fh:holds` |
| 7 個 Data Property | `fh:mobileNumber`、`fh:countryCode`、`fh:city`、`fh:district`、`fh:addressLine`、`fh:postalCode`、`fh:fullAddress` |
| 5 個 Annotation Property | `rdfs:label`、`skos:definition`、`fh:governanceLevel`、`fh:subsidiary`、`fh:department` |

手機號碼的 domain 是手機通聯；其餘六欄的 domain 是地址通聯；range 均為 `xsd:string`。目前全部模型定義由金控治理；子公司仍可定義經確認的公司共通延伸，但本次沒有新增子公司專屬類別。`fh:department` 保留宣告供相容與治理詞彙參考，未用來建立部門 OWL 類別。

## 編輯來源及輸出

| 檔案 | 用途 |
|---|---|
| `holding-core.ttl` | 目前唯一模型編輯來源 |
| `build-config.json` | 列出來源模組、版本與整合輸出；新增正式子公司模組時更新 |
| `customer360-ontology.ttl` | 自含整合 Turtle，建置產生，勿手改 |
| `customer360-ontology.owl` | 與整合 TTL 同圖的 RDF/XML，建置產生，勿手改 |
| `catalog-v001.xml` | 目前有效的本體 URI／版本至本機檔案對應 |
| `department-pg/model.json` | 部門業務概念與待確認來源映射的編輯來源 |
| `department-pg/model.cypher` | 離線產生的 Neo4j 5 metadata 圖腳本，未部署 |
| `HANDOFF-ZED-RDF-20261021.md` | 最新接續交接 |
| `archive/before-v0.3.0/` | 修改前完整模型與文件快照，不參與建置 |
| `tools/legacy-v0.2.0/` | 舊工具與舊基準，只供追溯，勿執行 |

整合輸出合併來源的模型三元組，以整合本體資訊取代各模組本體標頭；不是單純拼接文字。若來源有 `owl:imports`，被匯入本體必須列入來源清單並具本機 catalog 對應，建置器不連網解析示意 URI。

## 部門 PG

目前有「貸款照會手機」與「客戶訪問地址」兩個業務概念，分別參照 `fh:MobileContactInformation`、`fh:AddressContactInformation` 及對應欄位。這些參照是 PG metadata，不是 `owl:sameAs`、等價、subclass 或資料列型別宣告。

實際部門名稱、底表、欄位、SQL、JOIN 與篩選條件均未確認，以 `null`／`pending` 保留；未知不表示不需要 JOIN 或篩選。此版共 18 個 metadata 節點、23 條關係，沒有假來源表或客戶實例。後續確認來源後需同步擴充 PG 契約與測試，才可寫入實際映射。詳見 `department-pg/README.md`。

## 建置與測試

依賴限定在本專案 `.venv`，不修改系統 Python。首次設定：

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

`--check` 只讀不寫。測試以 RDF 圖同構比較，不以文字順序或舊版 232 三元組為目標。請勿執行 `tools/legacy-v0.2.0/build_ontology.py`。

## 已確認邊界與待辦

- 業務定義保持精簡；建模限制與未定案內容寫在文件，不堆入 `skos:definition`。
- 不新增 Hash、有效註記、基數、互斥、等價、sameAs、反向關係、keys、property chain 或 SHACL。
- 子公司既有通聯類別與屬性 URI 已退役；對照見 `MIGRATION-v0.3.0.md`，不宣告自動等價。真實映射尚未接入。
- 國家碼標準、國際地址行政層級、格式、必填、唯一性及完整地址組合函數尚未核定。
- `Customer` 情境聚焦自然人，但未形式化等同自然人。`holds` 的持有認定與時間範圍仍待確認。
- 金融商品分類、帳戶、持有部位、集團職員／行員仍在討論，未加入模型。
- `example.org` 是示意命名空間，尚未核定正式 URI。

## 驗證範圍

使用 rdflib 7.6.0 通用解析器，檢查來源 TTL、整合 TTL 與 RDF/XML；整合兩格式和來源模型圖一致，目前整合圖 100 個三元組。另檢查類別／屬性、domain／range、治理、catalog、新舊模組隔離、來源驅動建置及 PG 參照契約。RDF 9 項、PG 13 項測試全部通過（無略過）。

`pyrightconfig.json` 指定本專案 `.venv`；若從整個 Ontology 工作區開啟時語言伺服器仍使用其他 Python，請選擇此子專案 `.venv/Scripts/python.exe`。命令列驗證均使用該環境。

未執行專用 OWL reasoner、一致性／可滿足性檢查、SHACL、GUI、真實資料查詢、SQL 或 Neo4j 部署。成功解析及結構測試不等於完整 OWL 或業務正確性驗證。
