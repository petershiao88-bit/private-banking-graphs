# Semantica 與 GPT-6.1 本體生成比較交接

更新日期：2026-10-26。使用者要求以 metadata＋SQL，透過 Semantica 的 LLM ontology 生成器產出本體，與現有私銀 ontology 比較；之後指定改用 GPT-6.1 再試一次。兩輪實驗與比較均已完成，本次停在交接，沒有待完成的 API 呼叫。

結論：GPT-6.1 Sol 比 GPT-4o-mini 保留更多公式、日期、來源差異與識別限制，適合作為來源及指標本體草稿；產品、指標與來源之間的完整業務關係仍有缺口。尚未替換正式 ontology，也未匯入 Neo4j 或修改 n8n。

## 先讀這些檔案

以下連結相對於本交接檔；工作區根目錄為 `C:\Users\petershiao\Desktop\Ontology`。

| 用途 | 檔案 |
|---|---|
| GPT-6.1 完整比較報告 | [REPORT.md](../../deliverables/semantica_ontology/20261026_gpt61/REPORT.md) |
| GPT-6.1 生成結果 | [JSON](../../deliverables/semantica_ontology/20261026_gpt61/generated_ontology.json)、[Turtle](../../deliverables/semantica_ontology/20261026_gpt61/generated_ontology.ttl) |
| 41 概念、69 關係與 8 題逐項覆核 | [codex_review.json](../../deliverables/semantica_ontology/20261026_gpt61/comparison/codex_review.json) |
| 結構、評估、費用彙整 | [comparison_summary.json](../../deliverables/semantica_ontology/20261026_gpt61/comparison_summary.json) |
| 最終交付檢查 | [delivery_checks.json](../../deliverables/semantica_ontology/20261026_gpt61/delivery_checks.json) |
| 原始檔與擷取內容完整性 | [verification.json](../../deliverables/semantica_ontology/20261026_gpt61/verification.json) |
| 第一輪 GPT-4o-mini 報告 | [基準報告](../../deliverables/semantica_ontology/20261026_v1/REPORT.md) |

## 輸入資料與比較基準

生成輸入共 17 份來源：6 份 Excel、53 張工作表，以及 11 份 SQL。實際選檔、來源編號、SHA-256、工作表與輸入分包請以兩輪目錄中的 `manifest.json` 為準，並非 sources 下每一份備份或衍生 SQL 都已納入。

資料處理分三層，供回溯資訊是否在擷取、模型生成或整合時遺失：

1. `originals/`：保留來源檔原始位元組；原始 Excel、SQL 均未改寫。
2. `evidence/`：Excel 非空儲存格保留座標、值、型別、公式及相關擷取資訊；SQL 嚴格解碼並驗證可還原原始位元組，另產生正規化換行的文字投影。SQL 引用行號與逐字引文依投影判讀。
3. `inputs/`：組成 AUM、Income、LUM、Customer 四包文字。兩輪四包逐位元組相同。圖片保留於原始檔與媒體，未做視覺解讀送入文字模型。

既有 ontology 僅用於生成後比較，未放入生成提示詞：

- `ontology/AUM Ontology.json`：62 個 terms。
- `ontology/Income Ontology.json`：90 個 terms。
- `ontology/independent_concepts/concept_graph.json`：41 個概念、69 條關係、39 條映射路徑；其中 25 個為產品／服務概念。

比較快照位於 `comparison/reference_snapshot.json`；來源雜湊位於 `comparison/reference_manifest.json`。生成類別包含實體表、維度、指標與業務概念，不能將類別總數當成業務概念覆蓋率。

## 實驗設定與結果

使用 Semantica 0.7.0 原生 `LLMOntologyGenerator`，經 OpenRouter 呼叫模型。GPT-6.1 的實際模型 ID 為 `openai/gpt-6.1-sol`，reasoning effort 為 low，依相容性省略 temperature；共用 `.env` 未修改。

四包各自生成後再整合。四包輸出上限皆為 14,000 tokens；GPT-6.1 首次整合在 14,000 截斷，紀錄保留於 `runs/integrated/attempt_14000/`。僅將整合上限提高至 32,000 後成功，來源與整合指示不變。這是單次實驗且有上限差異，不能將全部提升歸因於模型。

| 項目 | GPT-4o-mini | GPT-6.1 Sol |
|---|---:|---:|
| 類別／屬性 | 22／27 | 196／91 |
| 引用未宣告類別 | 10 | 0 |
| 註解含來源編號的項目 | 0 | 125 |
| 41 概念：明確／部分／缺少 | 1／4／36 | 11／30／0 |
| 69 關係：明確／部分／缺少 | 0／4／65 | 6／63／0 |
| 8 題規則問題：充分／部分／不足 | 0／0／8 | 4／4／0 |

概念、關係及八題結果為 Codex 根據生成 schema、comment 與來源證據覆核，尚非業務人員確認。partial 包含只在註解提及、語意角色不同或規則不完整，不等同可直接查詢的圖結構。語意對應可接受等價的兩段關係，但不代表已建立可執行 property chain。

GPT-6.1 原模型評估將 12 條關係列為 matched；覆核將索引 0、1、5、6、9、10 六條組成關係降為 partial，原因為缺少「上層與子指標不能再相加」限制。原判定與調整理由均保留於 `codex_review.json`，未修改生成本體。

另有同模型輔助評估 152 個 terms：AUM 為 matched 42／partial 20；Income 為 matched 27／partial 63。這些不是獨立評審分數，引用存在檢查也不等於語意正確。

GPT-6.1 本輪 10 次 API 請求回報費用約 US$1.9031，含一次截斷及四次評估。五次成功生成約 US$0.8174；兩者統計範圍不同。

## 重要改善與剩餘缺口

生成版保留了證券基金 SQL 的 `WKB28*WKB23*WKB31` 與 metadata 建議版 WKB17 的差異、收入 CASE 分支遮蔽疑點、月底最後兩個工作日認列、跨表日期依賴，以及最終收入彙總沒有 CUST_ID 等資訊。客戶識別碼與 AO 關係也保留了跨來源不等價、月份及非唯一性的限制。

尚未解決的事項：

- 25 個產品／服務多出現在指標或來源表註解，缺少完整「產品 → 指標 → 來源」結構。
- 銀行投資 AUM、證券 AUM、銀行／證券手收及私銀組織仍只有部分對應。
- 公式、粒度、來源依據與規則多放在自然語言 comment，尚無可逐欄驗證的結構化表示。
- Q1 會科與 SQL CASE 對應、Q2 存款細項 UNION、Q4 外幣日期粒度、Q8 跨流程 AO 連結仍只能部分回答。Q3、Q5、Q6、Q7 判定資訊充分，但仍保留各題來源限制。
- 原始資料完整保存，不代表模型輸出完整保留所有資訊；未執行 Oracle 金額查詢或實際問答流程回歸。

## 腳本與接續操作

Python 環境沿用 `客戶360/customer360-rdf-owl/semantica-poc/.venv/Scripts/python.exe`。GPT-6.1 腳本會匯入上一輪 `20261026_v1/run_experiment.py`，再切換工作目錄與 provider；兩個實驗資料夾都需要保留。憑證透過既有 `llm_config.read_settings()` 讀取，交接檔不包含金鑰。

| 腳本 | 用途 |
|---|---|
| `run_gpt61.py` | initialize、generate、compare、verify、show；生成及評估可讀取既有結果快取 |
| `audit_results.py` | 檢查實際輸入、模型參數、生成結構與來源編號，產生 audit_summary.json 與 inspection.txt |
| `review_gpt61.py` | 保存本輪 Codex 覆核與六條調整，檢查引用、題號與投影引文 |
| `build_report.py` | 依結果與覆核產生 REPORT.md、comparison_summary.json |
| `check_delivery.py` | 檢查完整性、模型、回應狀態、成果及金鑰未落入產物 |

下列 PowerShell 指令從工作區根目錄執行，僅重做本地驗證與報告，不呼叫生成 API：

```powershell
$semanticaPython = '.\客戶360\customer360-rdf-owl\semantica-poc\.venv\Scripts\python.exe'
$semanticaRun = '.\私銀智能問答\deliverables\semantica_ontology\20261026_gpt61'
& $semanticaPython "$semanticaRun\run_gpt61.py" verify
& $semanticaPython "$semanticaRun\audit_results.py"
& $semanticaPython "$semanticaRun\review_gpt61.py"
& $semanticaPython "$semanticaRun\build_report.py"
& $semanticaPython "$semanticaRun\check_delivery.py"
```

`review_gpt61.py` 的人工指定調整只適用本次輸出；若重新生成，必須重新閱讀結果覆核，不能直接套用判定。`generate`／`compare` 可能使用快取，因此重新執行命令不代表新一輪模型實驗。新實驗應另建版本目錄，調整輸出位置與對照設定，保留本輪證據。

## 停點與後續建議

本輪交付檢查全部通過：17 份來源及輸入完整、比較基準未變、五份有效生成正常結束、四份模型評估與覆核引用檢查通過、TTL 可解析為 1,396 triples、產物未含 API 金鑰。

下一輪建議先討論是否要改生成提示詞或擴充 schema，重點為明確區分產品、指標、來源表，將公式、粒度、日期、排除條件與加總限制做成結構化欄位。若要測試改善，沿用相同來源與八題，再增加未參與調整的新題，才能觀察泛化效果。這些是待決定的後續方向，尚未實作或開始執行。
