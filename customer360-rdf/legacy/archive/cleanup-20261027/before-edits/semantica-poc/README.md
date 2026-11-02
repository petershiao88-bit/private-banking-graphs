# 客戶360 × Semantica 本機 PoC

用官方 Semantica 0.7.0 的 ContextGraph、Explorer API 與隨套件附帶的瀏覽器介面，查閱現有 v0.16.0 模型。預設合併畫布保留全部43個 RDF 類別，以及103個 PG 業務概念、指標與來源表；property、欄位、參照、對映及模組不作節點。保留54條 PG → 實際 RDF 類別的 REFERS_TO_CLASS 對應線，同一 URI 只保留一個真正 RDF 類別節點，不增加中介參照節點。私銀只顯示 RDF「私人銀行部門」，由它直接連到44項 PG 指標，不再另畫 PG「私銀」。沒有使用 LLM、付費 API、業務 SQL、Neo4j 或 Fabric 雲端服務。

原始 RDF／OWL、九份 active PG JSON 與 model.cypher 均不改動。Explorer 中的操作只影響載入記憶體的快照，沒有寫回原模型的連接。

## 開啟

在此資料夾執行（預設開 RDF＋PG 合併視圖，8866）：

```powershell
.\launch.ps1
```

服務只監聽本機 127.0.0.1。瀏覽器會在服務就緒後開啟。終止前景服務可按 Ctrl+C。

```powershell
# 完整圖；可與證券視圖同時開啟
.\launch.ps1 -View full -Port 8866

# 證券指標與來源表
.\launch.ps1 -View securities -Port 8865

# 業務概念、指標與來源表
.\launch.ps1 -View business -Port 8867

# RDF 類別與屬性宣告
.\launch.ps1 -View ontology -Port 8868
```

| 視圖 | 節點 | 關係 | 用途 |
|---|---:|---:|---|
| securities | 29 | 44 | RDF 私人銀行部門、採用的證券指標、總指標分項及來源表 |
| business | 104 | 146 | RDF 私人銀行部門＋103個 PG 業務概念、指標與來源表 |
| ontology | 43 | 46 | 只畫 RDF 類別；繼承與正式關係宣告作連線，不畫 property 或參照節點 |
| full | 146 | 246 | 43個 RDF 類別＋103個 PG 業務／來源節點；含54條 PG → RDF 類別對應線 |

各視圖均排除 property、欄位、參照、對映及模組節點；full 不再提供原先677節點的技術 metadata 圖。REFERS_TO_CLASS 只表示原模型的類別對應，並非 rdf:type 的實例斷言，例如 PG「私銀－證券總 AUM」對應 RDF「證券 AUM」。

依使用者要求，畫面將 bank.private_banking 收合到 RDF 的 bank:PrivateBankingDepartment，原44條 USES_METRIC 的起點在顯示時改為該 RDF 節點；原重複部門及對應自環不顯示。證券／business 視圖也使用同一個 RDF 私銀節點。這是視覺化端點投影，不新增 RDF 類別層級的採用斷言，也不把 RDF 類別當成已驗證的組織實例。原邊 ID、原始出發點與 metadata 留在邊屬性；metadata.visual_projection 明記收合來源及 visualization_only_not_rdf_instance_assertion，data/manifest.json 記錄收合對照。原始 RDF／PG 檔案保持不變。

## 建議先試

1. 開預設合併視圖，進入 Graph 畫布，可看到 RDF 的客戶、金融商品與各指標類別。
2. 搜尋「證券總 AUM」，選取 PG 指標，查看連線與屬性。
3. 展開／查看五項分項，再沿 HAS_SOURCE_TABLE 看金額來源。
4. 需要簡化時，另開 securities 或 business 視圖。

圖中的英文關係 ID 保持原文。節點 content／name 使用模型中文名稱，表節點使用原表名。原始 PG properties 完整保存在 properties.original_pg_properties；顯示投影資訊保存在 properties.projection；RDF 文字註記在 properties.rdf_annotations。

## Ontology Hub 已載入原始本體

每次啟動由 ontology_hub.py 自動讀取 customer360-ontology.ttl，使用 Semantica 原生 RDF 解析器載入獨立的 Hub session，並註冊「客戶360共通語意整合本體」。本版包含434個 RDF triples、43個 Class、9個 Object Property、19個 Data Property、5個 Annotation Property，合計33個屬性。保留中文定義、37條繼承、domain 與 range；不連網解析 example.org。

在左側 Ontology Hub 的 Registry 開啟該本體即可查閱。本體的屬性定義只載入 Hub，主畫布仍保持146個節點／246條關係，私銀只顯示 RDF 節點並連到44項 PG 指標。Hub 的載入／編輯操作不寫回原始 TTL，也不修改主畫布 session；重新啟動會重新讀取本機來源。

此版本原生 OntologyIngestor 的轉換會略過 annotation properties，因此啟動載入採用套件自己的完整 RDF parser，保留全部33個屬性。這個銜接只在本 PoC 內，不修改套件檔案。Ontology Hub 匯入接受 Turtle、RDF/XML、JSON-LD 等 RDF 格式；一般 PG JSON／CSV 走 Enrich 的圖譜匯入。

## 語意邊界

- 現在展示的是模型與 metadata，沒有真實客戶、交易實例或實際 AUM 金額。
- HAS_COMPONENT_METRIC 只表涵蓋，不代表已核定的 SUM 公式。
- RDF_SUBCLASS_OF 是繼承宣告；RDF_DECLARED_* 是 domain/range 的視覺化投影，不是實例事實。property 不作節點，RDF_DOMAIN／RDF_RANGE 與技術參照邊不顯示。
- 原 pending、execution=null、database_verified=false 等狀態均保留。表出現在來源檔案，不等於查核過真實資料庫。
- 來源關係 HAS_SOURCE_TABLE、USES_VALUATION_SOURCE、USES_DATE_LOOKUP_SOURCE 保持區分。
- Explorer 的通用分析或推論功能不等同本專案業務驗證。載入與 API 驗收記錄在 data/verification.json。新增的交接 PoC 僅驗證獨立示範政策與合成輸出，詳見下方；不是整份原始本體的業務驗證。一般 SPARQL 查詢仍使用主圖投影，並非直接查詢原始434個 triples。

## 安裝與驗證

Semantica 與新增依賴放在此資料夾 .venv，不改原專案 .venv，也不安裝到全域 Python。本次為減少大量科學運算套件的重複下載，.venv 開啟 system-site-packages，唯讀沿用已安裝且符合需求的 numpy／scipy／pandas 等套件；需乾淨隔離環境時，可依下列步驟另建預設 .venv。

```powershell
uv venv --python 3.11 .venv
uv pip install --native-tls --index-url https://pypi.org/simple --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe -X utf8 -B export_graph.py
.venv\Scripts\python.exe -X utf8 -B verify.py
```

data/manifest.json 保存來源 SHA-256、各視圖數量與語意說明；data/rdf-triples-audit.json 保存全部434個 RDF triples。verify.py 驗證實際 ContextGraph 載入／重存、平行邊、原始屬性、中文搜尋、URI 查閱及 Explorer API，報告存於 data/verification.json。

官方文件：

- https://github.com/semantica-agi/semantica/blob/main/docs/reference/explorer.md
- https://github.com/semantica-agi/semantica/blob/main/docs/reference/visualization.md

Semantica 為 MIT 授權；本 PoC 使用原套件，不替換其圖引擎或修改套件原始碼。


## OpenRouter LLM configuration

Local `.env` is ignored by Git; `.env.example` contains no credentials. Fill only
`OPENROUTER_API_KEY` in `.env` to start. The default model is
`openai/gpt-4o-mini`; change `OPENROUTER_MODEL` to another OpenRouter model ID if needed.
`llm_config.py` reads this local file without exporting the key to the process environment.

Run from this directory:

```powershell
# Validate settings locally; no API request.
.venv\Scripts\python.exe -X utf8 -B llm_config.py
# Send a single fixed-text test request (at most 16 output tokens; may incur a small charge).
.venv\Scripts\python.exe -X utf8 -B llm_config.py --test
```

The optional dependency file is `requirements-llm.txt`. The test uses Semantica's
OpenAI-compatible provider with the explicit OpenRouter endpoint. It sends only
`Reply with exactly: OK`, never the ontology or PG snapshot. Errors and model responses
are not printed verbatim. Normal imports and Explorer startup do not call the model.

The local graph Q&A extension is available at `http://127.0.0.1:8866/ask` (full)
and `http://127.0.0.1:8865/ask` (securities). The Explorer home page has a
?????? link. Reasoning Playground keeps its original facts/rules behavior.

`graph_qa.py` retrieves matching nodes from the active in-memory graph and follows
component metrics to source tables. Definitions are enriched from the local TTL.
This is a local lexical/graph retrieval extension using Semantica's LLM adapter,
not the upstream AgentContext GraphRAG UI. Questions and selected graph metadata
are sent to OpenRouter only on explicit submission. No SQL or generated code is
executed; no inferred edges are written. Every question is independent.

Answers include [N] node and [E] edge references, with expandable raw evidence.
Citation IDs are checked for existence, not for semantic entailment; model claims
still need comparison with the evidence. Retrieval is bounded to 64 nodes, 100
edges and 40,000 context characters, and truncation is disclosed in the page.
The original graph and TTL remain unchanged. The local `.env` key is never sent
to the browser or included in the model prompt. Requests have a 30-second model
timeout, no SDK retries, and one active model request per service.

Offline verification:

```powershell
.venv\Scripts\python.exe -X utf8 -B -m unittest test_graph_qa -v
.venv\Scripts\python.exe -X utf8 -B verify.py
```


## 問答已改用 Semantica Reasoner（2026-10-26）

原本 `/ask` 介面保留，預設本體推理後端已從 HermiT 換成 Semantica 0.7.0 的符號規則 `Reasoner`。沒有使用 LLM 型的 `GraphReasoner`，也不自動回退 HermiT。

問答流程：OpenRouter LLM 選擇工具 → `ontology_tools.ToolPlan` 驗證白名單與參數 → `SemanticaReasoner` 執行固定規則 → LLM 依工具結果解釋。指標定義、分項、來源表等 PG 問題仍走原檢索，不進規則引擎。

- `check_subclass(class_uri, parent_uri)`：依已宣告的繼承關係推導，回傳 `entailed` 或 `not_entailed`。後者表示目前規則與宣告無法證明，不能解讀成已證明不是。
- `get_superclasses(class_uri)`：查出所有直接及間接上層類別。
- `check_consistency()`：明確回傳 `status=unsupported`、`verdict=unsupported_consistency`，不宣稱驗證通過，也不讓 LLM 改寫這項限制。
- 類別參數限原43個金控／銀行／證券 class；PG ID、原視覺化投影及任何新增公理均不能由 LLM 傳入。

`semantica_reasoner.py` 讀取原始434 triples 的 TTL，但只將43個 class 宣告與37條 `rdfs:subClassOf` 轉成80個 facts；中文定義等註記只供檢索解釋，不作推理規則。兩條規則分別表達類別對自身的繼承，以及繼承的遞移。原生 `Reasoner.infer_with_results` 真正產生50個新 facts（43個自反＋7個額外繼承結論），保留原生 rule／premises 紀錄。

完整分類輸入、規則、token→URI 對照、derived facts、原生匹配紀錄與來源雜湊放在 `data/semantica-reasoning/<cache-key>/report.json`。快取依原TTL、規則、adapter程式碼與 Semantica 版本區分，來源檔改動後必須重啟，不能靜默沿用舊報告。問答的 `[R1]` 顯示實際引擎、規則、快取與時間、佐證路徑及對應的原生推導紀錄；不會把完整分類報告逐題送給 LLM。

能力邊界：這是 named-class 繼承規則，不是完整 OWL DL 推理。沒有執行一致性、可滿足性、datatype（含 `xsd:date`）或個體推理。日後加入 `equivalentClass`、`disjointWith`、匿名 restriction、functional property 等未支援公理，adapter 會回報 `unsupported_axioms` 並停止類別判定，不會忽略後假稱完整推理。外部 imports 仍需先在本機處理。

```powershell
# 本機規則推導，不呼叫 LLM／Java
.venv\Scripts\python.exe -X utf8 -B semantica_reasoner.py --force
# 目前問答、交接與規則邊界，共38個測試
.venv\Scripts\python.exe -X utf8 -B -m unittest test_semantica_reasoner test_graph_qa test_handoff_demo -v
.venv\Scripts\python.exe -X utf8 -B verify.py
```

目前例題：證券AUM→Metric（經AUM遞移）、銀行AUM→證券AUM（無法證明）、完整OWL一致性（不支援）、證券總AUM來源（原PG路徑）。原畫布146／246與原始RDF／PG均保持不變。

一般提問仍是兩次模型呼叫（工具規劃＋解釋）。不支援、釐清或工具錯誤會在規劃後結束；沒有自動付費重試。未知結論使用後端固定文字，來源表回答保留原完整性檢查；這不是任意 LLM 文字的通用語意驗證器。

舊 HermiT 實作、`requirements-reasoning.txt`、專案 Java runtime 與歷史報告留作參考，預設問答不匯入或呼叫 `owl_reasoner.py`／`reasoner_worker.py`。歷史驗證見 `data/reasoning-verification.json`；目前驗證見 `data/semantica-reasoning-verification.json` 與 `UI-VERIFICATION.md`。

## Agent 交接 PoC（2026-10-26）

開啟 http://127.0.0.1:8866/handoff，或在圖譜首頁點「Agent 交接測試」。
此頁是本專案的自訂整合，重現 `Agent協作與Ontology_v6.pptx` 第1、2頁的交接情境。

實際執行流程：

1. 模擬 Agent A 提交最後工具的結構化 object 與收據 ID。Harness 與伺服器端模擬工具收據核對完整內容與來源，拒絕竄改、未登記詞條及缺少來源。
2. 使用 Semantica MCP 原生 `_tool_run_reasoning` handler（其底層為 `Reasoner`，不是 `DatalogReasoner`）執行固定 IF／THEN 規則。事實來自可信 adapter 的詞條對照、來源登記與既有金控／子公司 class 繼承；Agent 自報標籤及「已取得同意」不作證據。
3. 把推導標籤、內容、來源與已核對的同意狀態建立成 RDF，呼叫 Semantica `run_shacl_validation`，底層為真正的 pySHACL。沒有使用佔位的 `OntologyValidator.validate()`。
4. 通過後才呼叫模擬 Agent B 的 `receive()`。每個案例都顯示它真正收到的 inbox；失敗案例的 inbox 為空。
5. 遮罩只允許註冊的 `remove_bank_performance_v1`：移除整個獨立的手收項目，重新推導、重新 SHACL 驗證，再交接。保留其他項目的限制；沒有通用的自由文字遮罩、匿名化或任意降級。
6. 獨立的 Semantica `ContextGraph` 保存輸出、class、來源與決策；`ProvenanceManager.track_entity/get_lineage` 追溯多來源，`record_decision/trace_decision_chain` 記錄原始拒絕與遮罩後重驗的決策。核准投影的完整原始血緣留在稽核側，不隨 payload 傳給接收者。

政策檔案：`handoff-policy/rules.txt`、`handoff-policy/customer-report.ttl`。標籤、來源及詞條登記在 `handoff_demo.py`，是簡報用的**示範政策**，不是經法遵核准的銀行政策。取最嚴格在此實作為「所有來源限制的聯集，必須同時滿足」，不是 Semantica 自動理解一份內規。規則引擎只執行已寫出的繼承規則，沒有完整 OWL DL 語意。

頁面提供14個固定情境：公開資訊通過、手收未遮罩阻擋、手收移除後通過、銀行＋證券缺少／具備同意、Agent 假稱同意、同意對象不符、同意過期、自稱公開、竄改工具 object、缺少來源、自創 class、未核准降級、遮掉手收仍有個資。可展開真正的 facts／rules／derived_facts、SHACL RDF 與 shapes、血緣、決策、接收端 payload。

```powershell
# 只安裝到此 PoC 的 .venv
uv pip install --native-tls --index-url https://pypi.org/simple --python .venv\Scripts\python.exe -r requirements-handoff.txt
# 執行14個情境，輸出完整合成資料報告
.venv\Scripts\python.exe -X utf8 -B handoff_demo.py --report
# 單一情境的 input／output
.venv\Scripts\python.exe -X utf8 -B handoff_demo.py --case fee_mask
# 規則、SHACL、交接阻擋與原有問答／OWL 回歸檢查
.venv\Scripts\python.exe -X utf8 -B -m unittest test_handoff_demo test_graph_qa test_owl_reasoner -v
```

完整報告：`data/handoff/report.json`。新增16個驗證測試，含原有測試共35個通過；測試驗證接收端 payload、限制繼承、有效同意、失敗時不傳送及原始模型不變。

HTTP：`GET /handoff`、`GET /api/handoff/scenarios`、`POST /api/handoff/run`（`X-Handoff-Demo: 1`，body 僅接受 `case_id`，包括 `all`）。不開放任意 facts、規則、客戶同意或 graph 寫入。每次執行使用獨立記憶體，不寫入原有圖譜；完整報告只由 CLI 的 `--report` 寫入。

限制：兩端 Agent、資料、工具收據與同意服務皆為本機模擬，不呼叫 LLM、HermiT、OpenRouter 或真實 IAM；也未啟動外部 MCP transport 或真正跨廠商 A2A。模擬收據是 server-side fixture，正式版必須換成可信工具 adapter／可驗證收據，同意紀錄需接集團服務，稽核需持久化，傳送需有重試與去重機制。此測試證明設定的政策能控制交接，不證明資料本身是真實或計算正確，也不驗證任意 LLM 自由文字。示範 RecommendationAmount 是記憶體政策的局部擴充，原43類別、434 triples、146／246畫布與 PG 檔案不改動。
