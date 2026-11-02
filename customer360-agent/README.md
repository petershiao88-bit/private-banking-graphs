# customer360-agent：本體進入單 agent CoT 的實驗台

把 `customer360-rdf` 的本體（RDF＋OWL 推理＋PG 指標＋業務字典＋權限）放進**單一 LLM（地端 Qwen）**的思考流程，並用同一份題庫比較五種放法，看本體到底幫了什麼。

> **架構結論與實驗證據**：見 [docs/ontology-adoption-findings.md](docs/ontology-adoption-findings.md)。一句話總結：本體定義範本與詞彙 → LLM 讀題並填範本 → 本體執行 → SHACL／程式檢查（硬擋＋質疑）→ 再作答。

本體專案是唯讀的。這裡不複製任何本體資料：改了 `customer360-rdf`，重新執行就生效。每份結果都會標上本體版號和知識指紋。

---

## 1. 五種模式：本體怎麼進入 CoT

| 模式 | 本體進入方式 | LLM 呼叫 | 本體檢查 |
|---|---|---|---|
| **baseline** | 44 項指標平鋪成資料字典，模擬寬表 agent。沒有類別階層、權限、待定範圍與規則 | 1 次 | 只記錄 |
| **context** | 依角色過濾後的 context 包整包放進 system prompt | 1 次 | 只記錄 |
| **plan** | 同一份 context 包，分三步：<br>① 先交「語意計畫」JSON；<br>② 本體檢查，不過就帶錯誤訊息重試；<br>③ 通過後只帶已驗證的指標卡片作答 | 2 次以上 | **強制** |
| **tools** | 只給類別骨架和規則，指標細節用 6 個本體工具查；最後的結果一樣要通過本體檢查 | 多輪 | **強制** |
| **workflow**（建議） | 只給類別骨架和 3 個本體型別化範本。LLM 只選範本、填欄位、必要時拆題；由本體執行，結果經檢查。有質疑時把執行結果退回一次 | 2～4 次 | **強制** |

「只記錄」的意思是照樣算出檢查結果並寫進報告，但不擋回答。這樣可以看出「如果有檢查，會擋下什麼」。

```
customer360-rdf（唯讀）─→ 知識層 knowledge.py ──┬─→ 角色 context 包 packs.py ──→ system prompt
  本體 TTL＋OWL 推理                              ├─→ 本體工具 tools.py（＋MCP 伺服器）
  pg/*.json 44 項指標＋底表                        └─→ 本體檢查 plan.py（Gate）
  dictionary／policy                                         ↑
                                     地端 Qwen ←→ agent.py（四種模式）──→ evaluate.py ──→ report.md／report.html
```

### 1.1 角色 context 包（`packs/<版號>/`）

每個角色一份 Markdown，同內容另有一份 JSON。

| 檔案 | 指標數 | 估計 token |
|---|---|---|
| `rm.compact.md`（理專） | 44 | 約 4,500 |
| `rm.full.md`（含定義、輔助表） | 44 | 約 6,800 |
| `customer.compact.md`（客戶） | 9 | 約 2,700 |
| `baseline.md`（對照組） | 44 | 約 2,700 |
| tools 模式的骨架 | 0 | 約 1,600 |

內容依序是：
1. 版本列：本體 IRI、是否與已發佈 release 一致、知識指紋。
2. 使用規則：本體專案的 6 條，加上 agent 規則 5 條（同名商品要澄清、總指標不可加總、待定範圍不可代替、否定依階層判斷）。
3. 推理步驟。
4. 類別階層樹，同名商品會標出子公司，例如「債券商品（銀行）」。
5. 關係屬性。
6. 依角色過濾的指標清單：類別、商品、底表；總指標標 Σ 並列出分項。
7. 待定範圍：台股手收、集合管理手收、股票設質 LUM。
8. 其他業務詞條。

**權限在建包時就套用。** 角色看不到的指標整條不出現，而不是寫「不可看」請模型自己遵守。寫在 prompt 裡的禁令擋不住提示詞注入，真正的防線仍然在取數工具和資料層。

### 1.2 語意計畫與本體檢查（Gate）

模型要先交出這樣的 JSON：

```json
{"decision": "answer | clarify | out_of_scope",
 "terms": [{"text": "基金手收", "classes": ["bank:BankFeeIncome"], "metrics": ["bank.fund_fee_income"]}],
 "metrics": ["bank.fund_fee_income"], "classes": ["bank:BankFeeIncome"],
 "is_a": [["bank:BankFeeIncome", "fh:FeeIncome"]],
 "clarification": "", "reason": "", "ontology_version": "0.17.0"}
```

檢查分兩級（見結論 C2）：
- **硬擋**：本體能確定推出的錯誤。帶錯誤訊息重試，仍不過就由系統拒答。
- **質疑**：對照問題文字的判斷，可能誤判。退回給模型確認一次，修改後再檢查；仍有疑問就轉成向使用者澄清（`agent.challenge_policy: escalate`，結論 C11）。

| 代碼 | 等級 | 檢查 | 依據 |
|---|---|---|---|
| `unknown_class`／`unknown_metric`／`schema` | 硬擋 | ID 是否存在、格式 | 本體＋PG |
| `not_permitted` | 硬擋 | 角色權限，總指標繼承分項的拒絕 | access-policy |
| `false_is_a`／`gap_metric`／`deprecated_class` | 硬擋 | OWL 閉包、待定範圍、下架 | 本體 |
| `term_metric_mismatch`／`exclusion_violated` | 硬擋 | 用語宣告的類別要被指標涵蓋；排除條件 | 計畫內部一致性 |
| `ambiguous_subsidiary`／`cue_conflict`／`missing_subsidiary` | 質疑 | 銀行／證券歧義與子公司線索 | 本體標籤＋問題文字 |
| `anchor_missing`／`anchor_conflict` | 質疑 | 問題提到的商品、指標種類、縮寫要被指標涵蓋 | 本體標籤當錨點 |

提醒類（不擋）：`summary_with_components`（總指標與分項同時出現，不可加總）、`version`（計畫標的版號與目前不同）。

在 plan、tools、workflow 模式下，硬擋會把錯誤訊息回給模型重試（次數看 `agent.plan_retries`）。重試後還是沒通過，就由系統回覆「無法在本體上驗證」，不讓未驗證的答案出去。

### 1.3 本體工具（tools 模式、MCP）

| 工具 | 用途 |
|---|---|
| `search_terms(query)` | 業務用語 → 候選指標／詞條／類別／屬性（含同義詞） |
| `get_class(class_id)` | 定義、上層鏈（標出哪些是推理出來的）、子類別、可用屬性 |
| `is_a(class_id, ancestor_id)` | 依 OWL 閉包判斷是否為子類別，並回傳推理路徑 |
| `list_metrics(kind, subsidiary, product, metric_class)` | 依條件列指標；`product` 會包含其子類別 |
| `get_metric(metric_id)` | 底表與角色、欄位候選、口徑疑點；總指標會列出分項 |
| `list_gaps()` | 待定範圍 |

角色看不到的指標和不存在的指標，回覆同一句話，不透露是否存在。

`python -m c360_agent.mcp_server --role rm` 會把以上 6 個工具開成 MCP 伺服器（stdio），之後的 harness 或其他 agent 可以直接接。另外還有：
- `check_plan`：替外部 agent 的計畫做本體檢查；
- `handoff_plan`：多 agent 交接時，用接收方角色重檢並去敏；
- context 包 resource。

---

## 2. 快速開始（Mac）

需要 Python 3.10 以上，並能連到地端 Qwen。

1. 打開 `config.yaml`，把 `llm.base_url` 改成 Qwen 的位址：

   | 伺服器 | 預設位址 |
   |---|---|
   | vLLM | `http://主機:8000/v1` |
   | Ollama | `http://主機:11434/v1` |
   | LM Studio | `http://主機:1234/v1` |

   `llm.model` 留 `auto` 會用伺服器回報的第一個模型。
2. 雙擊 **`scripts/setup.command`**。它會建立 `.venv`、安裝套件、檢查題庫、產出 context 包，最後跑 `ping` 測連線。
3. 問一題，看完整過程：

   ```bash
   cd customer360-agent
   scripts/c360a ask "基金手收怎麼算？" --mode workflow        # 也可以 --mode plan／context／tools／baseline
   scripts/c360a ask "我的銀行 AUM 有哪些？" --role customer --mode tools --thinking
   scripts/c360a chat --mode plan                               # 連續問
   ```

4. 跑完整評測：雙擊 **`scripts/eval.command`**，或在終端機執行：

   ```bash
   scripts/c360a eval                                # 33 題 × 5 模式（完成後自動產生 backlog.md）
   scripts/c360a eval --modes context,plan --ids a01,a02,p03
   scripts/c360a eval --thinking off                 # 關掉 Qwen3 思考再跑一次，比較差異
   scripts/c360a eval --repeat 3                     # 每題跑 3 次，看穩定度
   scripts/c360a eval --resume runs/20261101-0930   # 中斷後接續
   ```

   完成後打開 `runs/<時間>/report.html`（可篩選），或閱讀 `report.md`。`backlog.md` 把本體檢查的質疑分成「誤質疑」（可能要補本體）、「促成修正」、「答案仍錯」三類，是本體維護的待辦清單。

Windows 用 `scripts\setup.cmd`、`scripts\eval.cmd`、`scripts\c360a.cmd`。

還沒接上 Qwen，想先確認流程？可以用不經語言模型的關鍵字檢索當替身：`scripts/c360a --backend heuristic eval`。報告會標明這是流程檢查，結果不代表任何模型的能力。

---

## 3. 接地端 Qwen 的注意事項

先跑 `scripts/c360a ping`，它會逐項檢查：
- 模型清單；
- 思考內容的格式；
- 原生工具呼叫是否可用；
- `/tokenize`；
- context 有沒有被截斷：送出整份理專 context 包，比對伺服器實際收到的 token 數。

| 狀況 | 處理 |
|---|---|
| **Ollama context 被截斷**（ping 顯示 ✗） | Ollama 的 OpenAI 相容端點用預設 context 長度，會悄悄截掉 context 包。啟動前設定 `OLLAMA_CONTEXT_LENGTH=16384`，或在 Modelfile 加 `PARAMETER num_ctx 16384` |
| vLLM 不接受 tools 參數 | 啟動加 `--enable-auto-tool-choice --tool-call-parser hermes`。不加也可以：`tool_calling: auto` 會自動改用 Qwen 原生的 `<tool_call>` 文字格式 |
| Qwen3 思考太久、超時或被截斷 | `llm.thinking: off`（送出 `enable_thinking=false` 並加上 `/no_think`），或提高 `max_tokens`／`timeout` |
| 思考內容混進答案 | 不會。`<think>…</think>`、只有 `</think>`、`reasoning_content` 欄位都會拆出來另存在紀錄裡 |
| 走公司 proxy 連不到地端 | 預設 `use_env_proxy: false` 不走 proxy；需要走時改成 true |
| 有 API 金鑰 | 設環境變數 `QWEN_API_KEY`（或 `api_key_env` 指定的名稱） |

環境變數可以臨時覆寫設定，不必改檔案：`C360A_BASE_URL`、`C360A_MODEL`、`C360A_TOOL_CALLING`、`C360A_THINKING`。

---

## 4. 評測

### 4.1 題庫 `eval/questions.yaml`（33 題）

| 題型 | 題數 | 測什麼 |
|---|---|---|
| 直接對應 | 8 | 業務用語對到唯一指標（含同義詞：放款餘額→LUM、保單→保險） |
| 子公司歧義 | 5 | 銀行／證券同名商品：基金、海外股票、結構型、海外債券 |
| 階層與否定 | 6 | 「不屬於證券的海外商品」、理專是不是職員、ETF 算不算基金（本體無法證明） |
| 總指標 | 3 | 證券總 AUM 的分項、不可與分項加總、證券總手收不含台股 |
| 待定或不存在 | 5 | 台股手收、外匯 AUM、集合管理手收、股票設質 LUM、黃金 AUM |
| 權限 | 5 | 客戶問銀行 AUM、基金手收（組合規則）、證券總手收（繼承分項拒絕） |
| 數值請求 | 1 | 要求算金額時，只能指出指標與來源 |

新增題目時，照檔案開頭的欄位說明寫，再跑 `scripts/c360a check`。期望的指標 ID 若不存在，或期望答案跟權限矛盾，這一步會擋下來。

### 4.2 評分

| 結果 | 定義 |
|---|---|
| **正確** | 決策可接受，指標、類別、必要說明都對，沒有越權，也沒有自編 ID |
| **保守未答** | 沒答對，但選了澄清、不在範圍，或被系統擋下；不會誤導使用者 |
| **默默答錯** | 給了回答，但內容錯：指標不對、越權、自編 ID、該澄清卻直接答。這是最需要壓低的數字 |
| 格式錯誤 | 沒有可解析的結果，或呼叫失敗 |

報告另外列出：越權次數、自編 ID 次數、本體檢查第一次就通過的比例、被擋下的次數、baseline／context「若有檢查會擋下」的次數，以及平均 token、秒數、呼叫次數。

`mention_any` 只是粗略的文字比對，用來檢查「不可加總」「待定」這類說明有沒有講到。有爭議的題目請看逐題紀錄判斷。

### 4.3 報告怎麼讀

`report.md` 依序是：
1. 實驗設定：模型、端點、本體版本、四種模式的做法、context 包大小；
2. 結果總表與依題型分數；
3. 逐題紀錄：期望 → 每個模式的決策、本體檢查每一次的結果、工具呼叫、回答。

`report.html` 內容相同，可以依模式、結果、題型篩選。每筆都能展開原始呼叫紀錄，包含 Qwen 的思考內容。

`results.jsonl` 是每題每模式一行的完整紀錄。`prompts/` 存實際送出的 system prompt，方便重現。

### 4.4 想看出什麼

- **context 比 baseline 好多少**：本體結構（階層、權限、待定範圍、規則）本身的價值。
- **plan／tools 比 context 好多少**：「可驗證的推理」的價值，重點看「默默答錯」有沒有轉成「正確」或「保守未答」。
- **若有檢查會擋**：baseline／context 的錯誤中，有多少是本體可以自動攔下的。這是「為什麼需要本體」最直接的證據。
- **tools 的 token 與呼叫次數**：本體變大以後，「整包塞入」和「先查再推」的成本差異。

---

## 5. 實驗（架構結論的證據）

不需要模型就能重跑，結果在 `experiments/results/`，結論整理在 `docs/ontology-adoption-findings.md`。

| 腳本 | 問題 |
|---|---|
| `experiments/exp1_fault_injection.py [題庫]` | 注入 17 種 LLM 典型錯誤，各層本體檢查攔下多少？看計畫和只看輸出差多少？正確答案被誤擋多少？ |
| `experiments/exp2_shacl_vs_code.py` | SHACL（`experiments/plan-shapes.ttl`）能不能取代程式版當檢查器？500 份計畫的一致率與速度 |
| `experiments/exp3_workflow_vs_plan.py` | 預先定義 workflow 範本能答對多少？表達上限？剩下的需要什麼？ |
| `experiments/exp4_grounding_budget.py` | 整包塞入還是先檢索？召回率與 context 預算 |
| `experiments/exp5_challenge_protocol.py` | 質疑出現後怎麼處理？模型被質疑會不會把對的改錯？ |
| `experiments/exp6_handoff.py` | 多 agent 交接時，用接收方角色重新檢查並去敏，能攔下多少越權？ |
| `experiments/exp7_cost.py` | 各模式每題的 token 成本（容量規劃） |
| `experiments/run_all.py [--quick]` | 本體改版前的回歸關卡：跑完 1～4，檢查門檻，不過就失敗 |

題庫有三份：
- `eval/questions.yaml`：調參集，33 題；
- `eval/holdout.yaml`：留出集 1，24 題；
- `eval/holdout2.yaml`：留出集 2，16 題，規則凍結後才寫，用來量測首次接觸的誤擋；
- `eval/holdout3.yaml`：留出集 3，16 題，全部調整完成後才寫，最終的首次接觸驗證。

## 6. 與本體專案的關係

- 只讀取 `../customer360-rdf/config.yaml` 指到的檔案：本體 TTL、`pg/*.json`、`dictionary/terms.yaml`、`policy/access-policy.yaml`、`release/<版號>/manifest.json`。
- 版本標記：
  - context 包與報告都會標本體版號；
  - 比對 release manifest 的模組雜湊，標出「與已發佈 release 一致」或「工作版本」；
  - 另有一個知識指紋，涵蓋本體、PG、字典與權限。
- **這次發現的權限漏洞**：Studio 的權限規則對「證券總手收」判定客戶可看，但它涵蓋了客戶不可看的「證券複委託基金手收」，等於透過總數繞過組合規則。這裡用 `agent.aggregate_inherits_component_deny: true` 讓總指標繼承分項的拒絕。建議之後把同樣的規則放進本體專案的權限計算。

---

## 7. 檔案結構

```
customer360-agent/
├── config.yaml              設定：本體專案位置、Qwen 端點、角色、同義詞、評測模式
├── eval/questions.yaml      評測題庫（33 題）
├── packs/<版號>/             角色 context 包（自動產生；可直接貼進其他系統的 prompt）
├── runs/<時間>/              評測結果：report.md、report.html、results.jsonl、summary.json、prompts/
├── scripts/                 setup／eval（雙擊）、c360a（終端機捷徑）
├── src/c360_agent/
│   ├── knowledge.py         知識層：本體＋OWL 閉包、44 項指標、字典、權限（含總指標繼承）、檢索
│   ├── packs.py             角色 context 包與 baseline 資料字典
│   ├── tools.py             6 個本體工具（綁定角色）
│   ├── plan.py              語意計畫格式、JSON 解析、本體檢查（Gate）
│   ├── llm.py               OpenAI 相容用戶端：Qwen 思考拆分、原生／文字工具呼叫、重試
│   ├── agent.py             四種模式
│   ├── evaluate.py          題庫驗證、評分、執行與續跑
│   ├── report.py            報告（Markdown＋HTML）
│   ├── offline.py           離線流程檢查用的關鍵字檢索後端
│   ├── workflows.py         本體型別化的 workflow 範本（metric_lookup、concept_is_a、concept_relation）
│   ├── backlog.py           質疑紀錄 → 本體維護待辦
│   ├── mcp_server.py        MCP 伺服器（stdio）
│   └── __main__.py          命令列
├── experiments/             四個架構實驗與結果（不需要模型）
├── docs/                    架構結論、本體修改提案、離線範例報告
└── tests/                   64 項測試（含仿 vLLM／Qwen 行為的 HTTP 假伺服器、SHACL 與程式版等價測試）
```

測試：`PYTHONPATH=src python -m unittest discover -s tests -t .`

---

## 8. 下一步

- 用地端 Qwen 跑完五種模式，先看「默默答錯」和「若有檢查會擋」兩欄，再看 `backlog.md` 的誤質疑。
- 接上取數工具：計畫通過後，把 `get_metric` 的底表和欄位候選交給 SQL 生成，或交給既有的寬表答題 agent。
- 走向多 agent：語意計畫 JSON 本身就是 agent 之間交接的格式。
  - 一個 agent 交出計畫，另一個 agent（或 harness）用 `check_plan` 驗證後再接手。
  - 權限決定 agent 能取什麼資料，本體檢查決定它的輸出能不能交給下一個 agent。
