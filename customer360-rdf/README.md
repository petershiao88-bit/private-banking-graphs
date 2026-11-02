# 客戶360 本體（customer360-rdf）

> 第一次接手？先看 **[HANDOFF.md](HANDOFF.md)**：白話說明這個專案在做什麼、怎麼用 Semantic Studio、怎麼維護與升版。

金控三層架構的語意本體：金控與子公司兩層用 RDF／OWL，部門層用屬性圖（PG）。本體定位是**多 agent 協作的共通語意基礎**；PoC 階段先發佈成單一 agent 可直接放進 prompt 的 CoT context。

目前版本 **v0.17.0**（2026-10-31，design draft）。這一版把 RDF 依 FIBO 的「領域／模組」方式重新拆檔，類別與屬性的定義完全沒變（見 `release/0.17.0/CHANGELOG.md`）。

## 專案結構

```text
customer360-rdf/
├── config.yaml              唯一設定：路徑、版本、模組、發佈規則、前端設定
├── pyproject.toml           套件定義（src 結構）
├── requirements.txt
├── ontology/                RDF 來源（只改這裡）
│   ├── catalog-v001.xml     IRI → 檔案對照
│   ├── holding/             金控層 fh:   annotations／parties／products／metrics／organization
│   ├── bank/                銀行層 bank: parties／products／metrics／organization
│   └── securities/          證券層 securities: products／metrics
├── shapes/                  SHACL：ontology.ttl（類別組成元件）、dictionary.ttl（字典對應）
├── dictionary/terms.yaml    新業務字典詞條與類別對應（Semantic Studio 維護）
├── policy/access-policy.yaml  角色 × 類別權限規則（Semantic Studio 維護）
├── pg/                      部門層 PG：9 份模型 JSON、驗證器、model.cypher、指標來源表
├── build/                   產物：合併後的 customer360-ontology.ttl／.owl（勿手改）
├── release/                 發佈版本：0.16.0、0.17.0、LATEST
├── src/
│   ├── ontology_kit/        建置、組成元件、版本控制、OWL 推理、agent context
│   └── semantic_studio/     語意前端：server.py、core/（後端）、web/（前端 ES modules）
├── scripts/                 start-studio.command（macOS）、start-studio.cmd（Windows）
├── tests/                   ontology／kit／studio／pg 四組，共 152 項
└── legacy/                  不再維護的舊檔案與歷史快照（見 legacy/README.md）
```

## 快速開始

```bash
cd customer360-rdf
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export PYTHONPATH=$PWD/src            # 或 pip install -e .（之後可用 c360、c360-studio 指令）

python -m ontology_kit check          # 版號與成熟度一致性＋類別組成元件
python -m ontology_kit build          # 合併模組到 build/（--check 只驗證）
python -m ontology_kit diff           # 與前一版比對
python -m ontology_kit release        # 產出 release/<版號>/
python -m semantic_studio --open      # 語意前端 http://127.0.0.1:8870/
python -m unittest discover -s tests  # 152 項測試
```

macOS 也可以直接雙擊 `scripts/start-studio.command`：第一次會自動建立 `.venv` 並安裝套件。Windows 用 `scripts/start-studio.cmd`。

---

## 1. RDF 模組（參考 FIBO）

一個檔案就是一個 `owl:Ontology` 模組，依「層／主題」放在 `ontology/<層>/<主題>.ttl`：

| 層 | 模組 | 內容 |
|---|---|---|
| 金控 | `holding/annotations` | 名稱、定義、治理層級、子公司等註記屬性 |
| | `holding/parties` | 客戶、職員、通聯資訊；職員服務客戶、客戶具有通聯資訊 |
| | `holding/products` | 金融商品；**客戶持有金融商品（`fh:holds`）** |
| | `holding/metrics` | 指標、AUM、LUM、手收、利收；衡量商品的關係與結果欄位 |
| | `holding/organization` | 部門；部門採用指標 |
| 銀行 | `bank/parties` | 行員、理專 |
| | `bank/products` | 存款與投資類 17 種商品 |
| | `bank/metrics` | 銀行 AUM／LUM／手收／利收；手收歸屬理專 |
| | `bank/organization` | 私人銀行部門 |
| 證券 | `securities/products` | 債券、基金、海外、股票、結構型商品 |
| | `securities/metrics` | 證券 AUM、手收 |

每個模組的標頭都有：
- `owl:versionIRI`；
- `owl:versionInfo`；
- FIBO 的成熟度 `fibo-fnd-utl-av:hasMaturityLevel`；
- `owl:imports`：只匯入「實際用到其中詞彙」的模組，由測試檢查。

建置與發佈時，模組會合併成一個本體。

## 2. 類別組成元件

一個類別必須具備的元件（`config.yaml` 的 `components`），`check`、`release` 與 SHACL 都會檢查：

| 元件 | RDF | 要求 |
|---|---|---|
| URI | 命名空間決定所屬層 | 必要 |
| 名稱 | `rdfs:label`（zh-TW） | 必要 |
| 定義 | `skos:definition` | 必要 |
| 治理層級 | `fh:governanceLevel`＝該層設定 | 必要 |
| 所屬子公司 | `fh:subsidiary`：子公司層必填，金控層不得有 | 依層 |
| 上層 | 具名 `rdfs:subClassOf`；子公司類別必須接到金控類別 | 子公司層必要 |
| 屬性 | 以本類別為 domain 的屬性 | 選用 |
| 模組／成熟度 | 宣告所在模組與其成熟度 | 由 config 與 TTL 決定 |
| 下架 | `owl:deprecated true`＋`dcterms:isReplacedBy` | 下架時必要 |

## 3. 版本控制

- **版號唯一來源**是 `config.yaml` 的 `project.version`。
- `bump X.Y.Z --apply` 會一次改好以下位置，並保留原檔的換行格式：
  - 模組 TTL；
  - catalog；
  - PG JSON 與 PG 驗證器裡的版號；
  - config（版號、日期，以及把 `previous_release` 指到上一版）。
- **FIBO 規則**：
  - 成熟度標在模組上；
  - `release.include_maturity` 決定哪些模組進 release；
  - 類別要先標 `owl:deprecated`，下一版才能移除。
- **升版等級**：
  - patch：改名稱或定義；
  - minor：新增類別或屬性、標下架、換模組；
  - major：改上層、層級、domain／range，或移除（0.x 期間升 minor 即可）。
  - 本體有變更沒升版、或升版等級不夠，都會擋下發佈。
- **發佈不可覆寫**：重跑時內容相同回報 `unchanged`，內容不同就要求先升版。

升版流程：

```bash
python -m ontology_kit bump 0.18.0 --apply
python -m ontology_kit build
python pg/build_cypher.py
python pg/export_metric_tables.py
python -m ontology_kit release
```

## 4. OWL 推理 → agent context

`release` 依序做這些事：
1. 對 release 包做 owlrl（OWL 2 RL）閉包；
2. 用獨立的 `subClassOf` 走訪交叉驗證推理結果；
3. 檢查循環繼承與不可滿足類別；
4. 輸出 `agent-context.md` 與 `agent-context.json`。

**白名單**：只接受 `config.reasoner` 列出的公理。出現其他公理時拒絕發佈，避免 context 漏講會影響推論的內容。

目前推理新增 7 組關係：銀行與證券的各類指標 → 指標、理專 → 職員。

`agent-context.md` 可以直接放進 system prompt，內容包括：
- 版本與雜湊，回答可以追溯到用的是哪一版本體；
- 使用規則與推理步驟（文字在 `config.context`）；
- 每個類別的定義、上層鏈和可用屬性。

## 5. Semantic Studio

`python -m semantic_studio --open`（只監聽 127.0.0.1）：

| 分頁 | 內容 |
|---|---|
| RDF 圖譜 | 類別依層著色，畫出宣告的 subClassOf、OWL 推理的上層、關係屬性（例如客戶 → 持有 → 金融商品）、業務字典詞條、SHACL 違規。選角色後依權限著色；點節點看 OWL 定義、上層鏈、權限理由、SHACL 結果與 Turtle |
| 業務字典對應 | 新增或匯入（CSV／JSON）詞條，對應到類別組合（主類別／商品／業務範圍／其他）；即時預覽繼承的權限與 SHACL 結果 |
| 權限 | 角色與規則編輯、類別 × 角色矩陣 |
| OWL 推理 | 統計、推理新增的關係、類別階層樹 |
| SHACL | 驗證結果與 shapes |
| Turtle | 本體、字典對應、shapes 原文 |

**權限規則**
- 一個類別的規則：套用到該類別與所有子類別。
- 多個類別的規則是**組合規則**：只套用到同時涵蓋這些類別的詞條。例如「手收 × 基金」只擋基金手收。
- 同一角色只要命中任何一條拒絕就不可看（取最嚴格）。

**SHACL**：在「本體＋OWL 推理閉包＋所有詞條」上驗證。要加規則，就在 `shapes/` 新增 `.ttl`。

**寫入範圍**：Studio 只寫 `dictionary/terms.yaml` 與 `policy/access-policy.yaml`。

**程式結構**
- 後端 `core/`：`ontology`（載入與推理）、`dictionary`、`permissions`、`validation`（SHACL）、`views`，由 `studio.py` 統一對外。
- 前端 `web/js/`：`graph`、`detail`、`dictionary`、`policy`、`owl`、`shacl`、`turtle`，以 `store` 共享狀態，`main` 是進入點。不需建置工具。

## 6. config.yaml

| 區段 | 內容 |
|---|---|
| `project` | 本體名稱、URI、版號、日期、狀態 |
| `paths` | 所有路徑（相對於 config；可用 `C360_PATH_<KEY>` 覆寫） |
| `evidence` | PG 證據檔原工作區資料夾名稱，經 `paths.evidence_root` 對應到 `../private-banking-pg` |
| `layers`／`modules` | 各層命名空間與模組清單（含成熟度） |
| `components`／`versioning`／`release`／`reasoner`／`context` | 組成元件、升版、發佈、推理白名單、agent 規則 |
| `studio` | 前端位址、對應角色、同義詞 |

## 7. 測試

`python -m unittest discover -s tests`，共 152 項：

| 測試組 | 內容 |
|---|---|
| `tests/ontology/` | 模組結構、拆檔前後每筆 triple 與 v0.16.0 相同、imports 正確，以及沿用自 v0.16 的建模規則 |
| `tests/kit/` | 組成元件、版本控制（含升版端對端）、建置、推理、context、發佈 |
| `tests/studio/` | 權限繼承、詞條組合、SHACL、存檔、HTTP API |
| `tests/pg/` | PG 101 項保存性測試，路徑一律由 config 推導 |

PG 證據檔的路徑經 `config.yaml` 對應到同儲存庫的 `private-banking-pg/`，不再需要額外建立 `私銀智能問答` 連結。

舊檔案與歷史快照在 `legacy/`，說明見 [legacy/README.md](legacy/README.md)。
