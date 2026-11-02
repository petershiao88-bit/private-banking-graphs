# 用我們的本體測 Semantica：推理路徑和來源怎麼來（不接 LLM）

> 2026-11-01。Semantica 0.7.0（PyPI `semantica`，GitHub `semantica-agi/semantica`）。本體 v0.17.0。
> 目的：確認 Semantica 回傳的「推理路徑（reasoning_path）」和「來源（sources）」是什麼，和 PoC 的語意計畫＋關卡差在哪裡。

## 一句話結論

Semantica 的推理路徑是**程式在呼叫 LLM 之前**，從檢索命中的節點出發，在圖上做廣度優先遍歷得到的。它代表「餵給 LLM 什麼」，**不是 LLM 的 CoT**，也不代表 LLM 用了什麼。回傳值只保留第一條路徑。信心值只由檢索分數算出，和答案無關。

PoC 的語意計畫是 **LLM 自己交出的**「用了什麼」，關卡在作答前拿它對照本體和問題文字。兩者的資料長相很像，但寫的人和用途不同。

---

## 一、設定

### 資料：同一份本體轉成 Semantica 的圖

`export_ontology.py` 從 PoC 讀本體，匯出 `c360-ontology.json`。`load_c360.py` 再轉成 Semantica 的圖，共 95 個節點、165 條邊。

| 節點 | 數量 | 內容 |
|---|---|---|
| 類別（Class） | 43 | 標籤、ID、定義 |
| PG 指標（Metric） | 44 | 名稱、ID、定義 |
| 業務詞條（Term） | 8 | 名稱、定義 |

| 邊 | 方向 |
|---|---|
| `subClassOf` | 子類別 → 上層類別 |
| 物件屬性，例如「歸屬理專」「衡量金融商品」 | domain → range |
| `instance_of` | 指標 → 指標類別 |
| `about_product` | 指標 → 商品類別 |
| `has_component` | 總指標 → 分項指標 |
| `maps_to_<role>` | 詞條 → 類別 |

### 三種設定

| 設定 | 圖的格式 | 起點怎麼找 |
|---|---|---|
| A | `ContextGraph` 物件（官方文件主推的寫法） | Semantica 內建的關鍵字比對 |
| B | `{"entities", "relationships"}` 字典 | 同上 |
| C | 字典 | 直接指定正確的起點（假設檢索完全正確） |

### 其他說明

- **沒用向量檢索。** Semantica 預設的向量模型是英文的 `BAAI/bge-small-en-v1.5`，雲端環境下載被擋，所以只用它的圖檢索。拿不到模型時，它內建的退路是用雜湊值算向量（更退一步是隨機向量），測了也沒意義。
- **LLM 換成 `StubLLM`。** 它只記下 Semantica 組好的 prompt，不作答。
- **直接呼叫 `ContextRetriever`。** `AgentContext.query_with_reasoning` 內部就是轉呼叫它；用 `AgentContext` 的話一定要給向量庫。

### 題目

| 題號 | 問題 | 正確指標 | 容易混淆的 |
|---|---|---|---|
| q1 | 這位客戶在銀行的基金手收是多少 | `bank.fund_fee_income` | `securities.fund_fee_income` |
| q2 | 客戶的複委託基金庫存有多少 | `securities.fund_aum` | `bank.fund_aum` |
| q3 | 基金手收是多少 | 有歧義，應該澄清或兩邊都列 | 銀行和證券的兩個基金手收 |
| q4 | 理專的手收怎麼算 | `bank.product_fee_income` | |
| q5 | 銀行 AUM 算不算指標 | `bank:BankAUM` ⊑ `fh:Metric` | |

每題跑兩次：中文原句，以及用空格斷好詞的版本。原因是 Semantica 的關鍵字比對是用空格切詞。

---

## 二、原始碼裡的實作

位置在 `semantica/context/context_retriever.py`。`query_with_reasoning` 依序做這些事：

1. `retrieve()` 找出起點節點：向量（本測試沒有）加上圖的關鍵字比對。
2. 收集每個起點 2 跳內的鄰居。
3. `_build_reasoning_path()` 從這些鄰居做廣度優先遍歷，列出所有長度不超過 2 跳的路徑。
4. 把前 5 筆來源和**前 3 條路徑**組成 prompt，呼叫 LLM。
5. 回傳的 `reasoning_path` **只保留第一條路徑**的文字。
6. `confidence` = 檢索分數平均 × 0.8，只要有路徑就再加 0.2。

所以路徑是在第 3 步、呼叫 LLM 之前就決定的。LLM 回答什麼都不會改變它。

---

## 三、逐題結果

「來源」只列前 5 名，「@N」表示排第幾。

### q1 這位客戶在銀行的基金手收是多少

| 設定 | 查詢 | 來源數 | 路徑數 | 信心值 | 正確指標 | 回傳的 reasoning_path |
|---|---|---|---|---|---|---|
| A | 原句 | 0 | 0 | 0.00 | — | （空） |
| B | 原句 | 0 | 0 | 0.00 | — | （空） |
| A | 銀行 基金 手收 | 10 | **0** | 0.26 | @1 | （空） |
| B | 銀行 基金 手收 | 10 | 101 | 0.43 | 不在前 5 | `AUM --[subClassOf]--> 指標` |

B 實際交給 LLM 的 3 條路徑，全都和基金手收無關：

```
Path 1: AUM --[subClassOf]--> 指標
Path 2: AUM --[衡量金融商品]--> 金融商品
Path 3: 私銀－銀行規劃型信託 AUM --[instance_of]--> 銀行 AUM
```

C（起點指定為 `bank.fund_fee_income`）的 5 條路徑都和題目相關：

```
私銀－銀行基金手收 --[instance_of]--> 銀行手收指標
私銀－銀行基金手收 --[about_product]--> 基金商品
私銀－銀行基金手收 --[instance_of]--> 銀行手收指標 --[subClassOf]--> 手收指標
私銀－銀行基金手收 --[instance_of]--> 銀行手收指標 --[歸屬理專]--> 理專
私銀－銀行基金手收 --[about_product]--> 基金商品 --[subClassOf]--> 金融商品
```

### q2 客戶的複委託基金庫存有多少

| 設定 | 查詢 | 來源數 | 路徑數 | 信心值 | 正確指標 | 混淆指標 | reasoning_path |
|---|---|---|---|---|---|---|---|
| A／B | 原句 | 0 | 0 | 0.00 | — | — | （空） |
| A | 複委託 基金 AUM | 10 | 0 | 0.18 | @1 | `bank.fund_aum` @4 | （空） |
| B | 複委託 基金 AUM | 10 | 58 | 0.54 | 不在前 5 | — | `AUM --[subClassOf]--> 指標` |

- 「庫存」沒有被當成 AUM，因為它沒有同義詞表。
- A 把銀行的基金 AUM 也一起列進來源，沒有任何標示。
- B 交給 LLM 的路徑和 q1 一字不差。

### q3 基金手收是多少（有歧義）

| 設定 | 查詢 | 來源數 | 路徑數 | 信心值 | 來源裡的雙胞胎 | reasoning_path |
|---|---|---|---|---|---|---|
| A／B | 原句 | 0 | 0 | 0.00 | — | （空） |
| A | 基金 手收 | 10 | 0 | 0.12 | 銀行 @1、證券 @2 | （空） |
| B | 基金 手收 | 10 | 78 | 0.31 | 都不在前 5 | `銀行手收指標 --[subClassOf]--> 手收指標` |

- 兩個基金手收都被找回來了，但沒有任何「這題有歧義」的訊號，信心值也沒有降低。
- 要不要問使用者，完全交給 LLM 自己判斷。

### q4 理專的手收怎麼算

| 設定 | 查詢 | 來源數 | 路徑數 | 信心值 | 正確指標 | reasoning_path |
|---|---|---|---|---|---|---|
| A／B | 原句 | 0 | 0 | 0.00 | — | （空） |
| A | 理專 手收 | 10 | 0 | 0.24 | 不在前 5 | （空） |
| B | 理專 手收 | 10 | 57 | 0.38 | 不在前 5 | `行員 --[subClassOf]--> 職員` |

C 的路徑有找到「手收歸屬理專」這條關係：

```
私銀－銀行商品手收 --[instance_of]--> 銀行手收指標 --[歸屬理專]--> 理專
```

### q5 銀行 AUM 算不算指標

| 設定 | 查詢 | 來源數 | 路徑數 | 信心值 | 正確類別 | reasoning_path |
|---|---|---|---|---|---|---|
| A | 原句（本身含空格，所以有命中） | 10 | 0 | 0.44 | 不在前 5 | （空） |
| B | 原句 | 10 | 62 | 0.31 | `bank:BankAUM` @1 | `AUM --[subClassOf]--> 指標` |
| B | 銀行 AUM 指標 | 10 | 69 | 0.31 | @1、`fh:Metric` @3 | `AUM --[subClassOf]--> 指標` |

C 只走 2 跳，所以看得到「銀行 AUM → AUM → 指標」，這題剛好夠。更深的上層鏈就要把跳數調大，它不像 OWL 推理會事先把上層關係全部算好。

---

## 四、它的另一種推理路徑：規則引擎的證明

`probe_rules.py` 把上層關係和指標歸類寫成事實，再用兩條規則推導，完全不需要 LLM：

```
IF subClassOf(?x, ?y) AND subClassOf(?y, ?z) THEN subClassOf(?x, ?z)
IF instance_of(?m, ?c) AND subClassOf(?c, ?d) THEN instance_of(?m, ?d)
```

| 問題 | 結果 | ExplanationGenerator 回傳的推理路徑 |
|---|---|---|
| 銀行基金手收是一種指標嗎？ | 成立 | 前提：`instance_of(bank.fund_fee_income, bank:BankFeeIncome)`、`subClassOf(bank:BankFeeIncome, fh:Metric)`；套用 Rule 2 |
| 證券複委託基金手收是銀行手收嗎？ | 不成立（正確） | — |
| 理專是一種職員嗎？ | 成立 | 前提：理專 ⊑ 行員、行員 ⊑ 職員；套用 Rule 1 |

- 這是真正的推導證明，和 PoC 用的 OWL 推理鏈（`銀行 AUM ⊑ AUM ⊑ 指標`）是同一類東西。
- 解釋只列一層。「銀行手收指標 ⊑ 指標」本身也是推導出來的，要再展開一層才看得到完整證明樹（見 `results/probe_rules.json` 的 `full_proof_tree`）。
- 這個引擎要由開發者或 agent 指定「要證明什麼」才會跑，和 `query_with_reasoning` 沒有接在一起。

---

## 五、對照：PoC 怎麼處理同樣的問題

PoC 的路徑是反過來的：LLM 先交出語意計畫，關卡拿它比對本體和問題文字（`results/poc_gate_samples.txt`）。

| 情境 | 角色 | 計畫 | 關卡結果 |
|---|---|---|---|
| q1 正確計畫 | 理專 | 基金手收 → `bank:BankFeeIncome`，指標 `bank.fund_fee_income` | 通過 |
| q1 選錯雙胞胎 | 理專 | 指標 `securities.fund_fee_income` | 質疑 `cue_conflict`：問題只提到銀行，但這個指標屬於證券 |
| q3 歧義題只選一邊 | 理專 | 指標 `bank.fund_fee_income` | 質疑 `ambiguous_subsidiary`：另一邊還有證券的基金手收，請澄清或兩邊都列 |
| q1 越權 | 客戶 | 指標 `bank.fund_fee_income` | 硬擋 `not_permitted` |
| q5 編造上層關係 | 理專 | 宣稱銀行 AUM ⊑ 手收指標 | 硬擋 `false_is_a`，並附上正確的上層鏈：銀行 AUM ⊑ AUM ⊑ 指標 |
| q5 正確上層關係 | 理專 | 銀行 AUM ⊑ 指標 | 通過 |

PoC 用 workflow 模式回答 q3 時，回傳的紀錄包含：範本呼叫（`metric_lookup`，kind=fee，products=[基金]）→ 本體查詢結果（兩個基金手收）→ 語意計畫 → 逐項的關卡結果 → 答案（兩邊都列出 ID）。這和 Semantica 的「來源＋路徑」是同一類可以追查的紀錄，差別在 PoC 多了「LLM 宣稱用了什麼」和「作答前擋不擋」。

---

## 六、結論

| 面向 | Semantica 的 `query_with_reasoning` | PoC 的語意計畫＋關卡 |
|---|---|---|
| 路徑誰產生 | 程式在呼叫 LLM 前遍歷圖 | LLM 交出計畫或範本呼叫；本體負責執行和檢查 |
| 代表什麼 | 給了 LLM 什麼 | LLM 說它用了什麼 |
| 回傳多少 | 只回傳第一條（prompt 裡給 3 條） | 完整的計畫、範本呼叫紀錄、每一項檢查結果 |
| 和題目相不相關 | 取決於檢索；測試中常和題目無關 | 由 LLM 宣告，關卡對照問題文字 |
| 中文 | 原句 10 次查詢有 8 次 0 命中；只有本身帶空格的 q5 原句有命中 | 有同義詞表和中文 n-gram 檢索 |
| 雙胞胎和歧義 | 一起列進來源，沒有訊號 | 質疑，退回模型或問使用者 |
| 權限 | 檢索不分角色 | 角色範圍外的指標直接硬擋 |
| 上層關係推理 | 檢索路徑只走 2 跳；規則引擎可以證明，但要另外呼叫 | OWL 推理閉包，計畫裡錯誤的上層關係會被硬擋 |
| 信心值 | 檢索分數平均 × 0.8，有路徑再加 0.2 | 不給信心值；給的是通過或不通過，以及原因 |

**可以借用的部分：**
- 規則引擎附證明的推導，以及決策紀錄和來源追溯，可以補 PoC 的稽核面。
- 設定 C 證明：只要起點選對，它在圖上走出來的路徑是清楚、可讀的。

**不能直接替代的部分：** 它不會在作答前判斷 LLM 是否選對、是否越權。這正是 PoC 關卡在做的事。

**注意：**
- 沒用向量檢索，A／B 的命中率不代表接上中文向量模型後的表現。
- 但「路徑在呼叫 LLM 前產生」「只回傳一條」「信心值和答案無關」「`ContextGraph` 格式不產生路徑」這幾點是程式本身的行為，換檢索方式也一樣。

---

## 重跑

**最簡單的方式：** 在 Mac 上雙擊 `experiments/semantica/run-semantica.command`。第一次會建立 `customer360-agent/.venv-semantica-darwin` 並下載 Semantica，之後直接重用；結果寫到 `results/`。

`.wheels/linux-aarch64-cp310/` 存了 Linux（aarch64、Python 3.10）專用的 47 個套件（141 MB），在這類環境可以離線安裝，約 10 秒；Mac 用不到這些檔案。這個資料夾已加進 `.gitignore`，不需要時可以直接刪掉。

已重跑兩次，`results/probe_paths.json` 和 `results/probe_rules.json` 的內容逐字相同：
- 雲端：Python 3.13，x86_64。
- 使用者機器上的 Linux 環境：Python 3.10，aarch64。

網路慢時，pip 可能卡在單一個大檔案（`pyarrow` 約 47 MB）。這時可以先用 `pip install --dry-run --report` 解析出完整的套件清單，用 `curl -C -` 續傳下載，再用 `pip install --no-index --find-links <資料夾>` 離線安裝。

```bash
# 1. 匯出本體（PoC 環境，在 customer360-agent 目錄）
PYTHONPATH=src:../customer360-rdf/src python experiments/semantica/export_ontology.py

# 2. 另開一個 venv 裝 Semantica（約 500 MB），在這個資料夾執行
python3 -m venv .venv-semantica && .venv-semantica/bin/pip install semantica==0.7.0
cd experiments/semantica
../../.venv-semantica/bin/python probe_paths.py   # → results/probe_paths.json
../../.venv-semantica/bin/python probe_rules.py   # → results/probe_rules.json
```
