# 私銀智能問答／Ontology 專案

這份 README 是專案入口。根目錄只保留導覽文件、正式資料夾與 Supabase migration，歷史版本及工具暫存已分開收納。

## 目前優先使用

| 用途 | 目前檔案 |
|---|---|
| 單輪 RAG hybrid v5（10/28）：移除操作／停止分流、恢復關鍵字命中保留；本機實作與 10 項契約檢查完成，地端 20 題結構整合完成（合成排序，非模型驗收）。Docker／Neo4j 已啟動；公開通道待明確授權，雲端已還原原單題，尚未部署新版 | [最新單輪交接](docs/handoffs/20261028_單輪RAG關鍵字保留與地端接線待部署交接.txt)、[實作與停點](deliverables/single_turn_qa/rag_v1/hybrid_v5_20261028/README.txt)、[地端整合紀錄](deliverables/single_turn_qa/rag_v1/hybrid_v5_20261028/local-integration.json) |
| GraphRAG 續作交接（10/27）：確認前四入口、每組必留、硬補節點及複數商品路徑覆蓋問題；完成門檻離線試算。下一步討論原句＋切詞／重疊片語檢索，尚未實作或重新部署 | [最新交接](docs/handoffs/20261027_GraphRAG入口選擇與詞組檢索方案交接.txt)、[入口門檻報告](deliverables/single_turn_qa/rag_v1/graph_retrieval_v8/threshold_analysis/入口門檻評估.html)、[續作分流入口](docs/handoffs/RESUME.txt) |
| Semantica 本體生成比較：GPT-4o-mini 與 GPT-6.1 已完成；GPT-6.1 同 8 題有 4 題資訊充分，產品與指標關係仍不完整，尚未替換正式 ontology | [實驗交接](docs/handoffs/20261026_Semantica與GPT61本體生成比較交接.md)、[比較報告](deliverables/semantica_ontology/20261026_gpt61/REPORT.md)、[生成本體](deliverables/semantica_ontology/20261026_gpt61/generated_ontology.json) |
| GraphRAG v8 純語意入口＋本機圖譜：移除直接命中；雲端 n8n 經授權通道查本機 Neo4j，1,618 節點／4,649 關係。38 題同標準由 v7 32/38 降至 5/38；前 4 入口造成範圍過大，仍待調整。線上單題已保存未發布 | [本輪交接](docs/handoffs/20261020_GraphRAG純語意入口與本機圖譜v8交接.txt)、[38 題實測圖](deliverables/single_turn_qa/rag_v1/graph_retrieval_v8/純語意入口與本機圖譜重測.html)、[測試與限制](deliverables/single_turn_qa/rag_v1/graph_retrieval_v8/README.txt)、[本機圖譜與啟動](deliverables/local_graph/20261020/README.txt)、[保存核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v8/saved-verification.json) |
| GraphRAG v7 使用者批註核對：第 8 題原問法與評分基準不一致，撤回確定多取判定。修正問法 3 題實測 1/3 符合：黃金可辨識、列出包含商品的所有 AUM 仍漏上層、否定條件仍選錯；第 16 題正確 Rerank 第一名被程式忽略，第 21 題缺少小範圍候選。原 v7 邏輯未改 | [修正問法三題圖](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/rephrase_20261020/修正問法重測.html)、[原因與更正](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/rephrase_20261020/README.txt)、[原報告與批註更正](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/新題24題子圖測試.html) |
| GraphRAG v7 最新新題驗證（10/20）：凍結原邏輯測全新 24 題，19 題符合；5 題多取，其中 1 題也漏取。已定位排除條件、property 範圍繞過、母入口保留、停點與角色鄰居過大等問題，尚未修正；線上已恢復原單題入口 | [新題交接](docs/handoffs/20261020_GraphRAG全新24題測試交接.txt)、[24 題圖與差異](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/新題24題子圖測試.html)、[逐題範圍核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/evaluations.json)、[原因與評估邊界](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/README.txt)、[還原核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/holdout_20261020/saved-verification.json) |
| 最新 GraphRAG 子圖檢索 v7：不預設補客戶／理專，不強制走到頂層；保留中間指標、商品本身及完整組成候選。同 12 題無多取／漏取概念節點或關係，映射角色／商品／連通性檢查通過；14 節點，單題入口，保存未發布 | [本輪交接](docs/handoffs/20261019_GraphRAG子圖範圍收斂v7交接.txt)、[子圖檢索流程](https://chiang4901.app.n8n.cloud/workflow/ntHWYmjJ7Q2HVLeT)、[12 題前後比較](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/子圖範圍調整前後比較.html)、[範圍核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/evaluations.json)、[保存核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/saved-verification.json)、[說明與評估邊界](deliverables/single_turn_qa/rag_v1/graph_retrieval_v7/README.txt) |
| 歷史 GraphRAG 子圖檢索 v6：14 節點；移除五種操作分類與澄清分流，入口／路徑分別 Rerank。原 12 題核對商品範圍、方向與分支集合；角色與多餘上層路徑的更嚴格檢查及修正見 v7，原線上副本已更新 v7 | [歷史交接](docs/handoffs/20261019_GraphRAG子圖檢索v6交接.txt)、[12 題歷史子圖](deliverables/single_turn_qa/rag_v1/graph_retrieval_v6/子圖檢索檢查.html)、[歷史範圍核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v6/evaluations.json)、[歷史保存核對](deliverables/single_turn_qa/rag_v1/graph_retrieval_v6/saved-verification.json) |
| 最新單輪 RAG 實驗版 selection_v4：操作／參數分開檢索，16 節點，保存未發布；同 20 題正確選路 3 → 5，原正確 3 題保留，仍有比例方向與漏客戶條件等問題。下個 session 先討論改善與缺口 | [最新單輪交接](docs/handoffs/20261019_單輪RAG操作選擇改善與20題重測交接.txt)、[RAG 實驗流程](https://chiang4901.app.n8n.cloud/workflow/H2Jr1mJHmdpaOWrY)、[20 題前後比較](deliverables/single_turn_qa/rag_v1/selection_v4/20題改善前後比較.html)、[已保存匯出](deliverables/single_turn_qa/rag_v1/selection_v4/workflow.saved.live.json)、[保存核對](deliverables/single_turn_qa/rag_v1/selection_v4/saved-verification.json) |
| 原單輪獨立版 v3 第一輪（Jev 基準，本次未改動）：13 節點，保存未發布；10/16 十二題曾有漏選及一次超限，與目前 RAG 版分開保留 | [原版歷史交接](docs/handoffs/20261016_單輪獨立流程v3交接.txt)、[原單輪流程](https://chiang4901.app.n8n.cloud/workflow/Td4cymdWpu8sYNkv)、[原版保存基準](deliverables/single_turn_qa/v3/workflow.frozen.json)、[十二題選路紀錄](deliverables/single_turn_qa/v3/route_assessment.json)、[歷史 v2 報告](deliverables/single_turn_qa/testing_20261016/測試結果與待修問題.html) |
| 最新 Resume／前置 LLM 多輪整合 v12：已加入逐組產品／指標配對、Jev 只查明確納入；10 輪原生診斷的檢索範圍符合預期，澄清與回答品質仍未全過。21 節點，保存未發布 | [最新 Resume](docs/handoffs/RESUME.txt)、[本輪交接](docs/handoffs/20261016_前置LLM多輪整合與配對測試_v12.txt)、[逐題測試報告](deliverables/graph_qa/v12_rewrite_pairs_20261016/多輪問題整合與指定配對測試結果.html)、[最新完整保存](deliverables/graph_qa/v12_rewrite_pairs_20261016/workflow.after.json) |
| 歷史通用回答 v11 r2：完成兩版共四輪 C1→C2 診斷，第二版比較承接改善、檢索仍有額外候選；18 節點，保存未發布，未完成穩定性及完整回歸 | [最新 Resume](docs/handoffs/RESUME.txt)、[本輪交接](docs/handoffs/20261016_通用回答最小對照結果_v11.txt)、[最小對照報告](deliverables/graph_qa/v11_direct_answer_20261016/通用回答最小對照結果.html)、[最新完整保存](deliverables/graph_qa/v11_direct_answer_20261016/workflow.after.json) |
| 歷史 v9 原生序列：18 題逐題判定 6 通過／12 未通過，非獨立案例準確率；後續乾淨 C1/C2 與新方案見最新交接 | [v9 交接](docs/handoffs/20261016_原生對話測試結果與待修問題_v9.txt)、[v9 報告](deliverables/graph_qa/v9/continuation_20261016/測試結果與待修問題.html) |
| v8 SQL 分流、日期血緣與來源範圍控制的完整已保存基準 | [v8 交接](docs/handoffs/20261015_SQL分流修正與重測交接_v8.txt)、[v8 更新紀錄](deliverables/graph_qa/v8/更新紀錄.txt)、[v8 流程匯出](deliverables/graph_qa/v8/workflow.saved.json) |
| SQL 三題重測與額外通用性測試：含實際業務／資料路徑、SQL 與獨立參考對照；未執行 Oracle | [SQL 重測與路徑報告](deliverables/graph_qa/v8/SQL重測與路徑報告.html)、[來源核對](deliverables/graph_qa/v8/sql_review.json)、[原始六題報告](deliverables/graph_qa/testing_20261015/測試結果與SQL對照.html) |
| n8n 問答流程重整原始交接（v4 已部分保存，最新狀態見下一列） | [2026-10-14 流程重整交接](docs/handoffs/20261014_n8n私銀問答流程重整交接.md) |
| 獨立圖譜問答 v4 歷史停止點；其未上線提案不可直接覆蓋最新 v5 | [歷史停止點與待辦](deliverables/graph_qa/v4/更新紀錄.txt)、[線上測試流程](https://chiang4901.app.n8n.cloud/workflow/pqvhkncZ9bFlfe4B) |
| 映射圖業務字典 v1.0（單一工作表；含 SQL 業務邏輯與原始程式碼） | [Excel 業務字典](deliverables/business_dictionary/v1.0/私銀業務字典.xlsx)、[完整包](deliverables/business_dictionary/私銀業務字典_單一工作表.zip)、[閱讀版](deliverables/business_dictionary/v1.0/私銀業務字典.md)、[系統用 JSON](deliverables/business_dictionary/v1.0/私銀業務字典.json)、[核對紀錄](deliverables/business_dictionary/v1.0/核對紀錄.json) |
| 最新 Aura 概念圖＋映射圖 JSON 與完整離線備份（2026-10-14） | [ZIP 完整包](deliverables/graph_exports/Neo4j_概念與映射圖_20261014.zip)、[使用說明與替代查詢方案](deliverables/graph_exports/20261014/使用說明.txt)、[匯出核對](deliverables/graph_exports/20261014/匯出核對.json) |
| 獨立圖譜問答 v3：Jev 選路後只保留選中路徑及必要上下文（已保存／實測 #2561 成功；未發布） | [線上測試版](https://chiang4901.app.n8n.cloud/workflow/pqvhkncZ9bFlfe4B)、[本次更新](deliverables/graph_qa/v3/更新紀錄.txt)、[原 v2 對話與證據整理說明](deliverables/graph_qa/v2/使用說明.txt) |
| 最新概念圖 Aura 更新與驗證（41／69） | [更新紀錄](deliverables/concept_update/20261013/更新紀錄.md) |
| 映射圖更新與概念图接續歷史（2026-10-13） | [映射圖進度與概念圖接續](docs/handoffs/20261013_映射圖進度與概念圖接續.md) |
| 正式概念圖業務定義（第二版，已部署 Aura） | [業務定義更新草稿](deliverables/concept_review/20261013/business_v2/私銀概念圖業務定義更新草稿.md)、[新增候選業務核對](deliverables/concept_review/20261013/business_v2/新增候選業務核對.md) |
| 概念圖本機建立與查詢已支援第二版 | [本機更新與核對](deliverables/concept_build/20261013/更新紀錄.md) |
| 最新底表映射 JSON（含 AO；104 節點／218 關係） | [底表映射圖匯出](deliverables/graph_exports/20261014/底表映射圖_20261014.json) |
| 映射圖規則修正與 AO 納入紀錄 | [概念規則與 AO 更新](deliverables/concept_ao_update/20261013/更新紀錄.md) |
| n8n AUM／Income KB：新版概念＋最新映射規則（2026-10-14 已發布） | [更新紀錄](deliverables/n8n_kb_update/20261014/更新紀錄.md)、`ontology\n8n_kb\PB_AUM_Income_KB.single_jev.saved.json` |
| 獨立共用概念圖／n8n 兩段固定查詢（已部署 Aura） | `ontology\independent_concepts\README.md` |
| 原型系統交接（2026-10-01；本輪未重新核對其流程狀態） | `docs\handoffs\智能查詢系統_專案交接說明_v5.md` |
| n8n Metadata KB（全 AUM） | `deliverables\metadata\v0.4\AUM_Metadata_KB_v0.4.csv` |
| Metadata Master（全 AUM） | `deliverables\metadata\v0.4\AUM_Metadata_Master_v0.4.xlsx` |
| 存款五表 Metadata 基準版 | `deliverables\metadata\v0.3\AUM_Deposit_Metadata_KB_v0.3.csv` |
| Staging SQL KB | `deliverables\staging\v0.2\AUM_Staging_SQL_KB_v0.2.csv` |
| Metric Router Registry | `deliverables\metrics\router_postgresql_v0.4\AUM_Metric_Router_Registry_PostgreSQL_v0.4.csv` |
| Metric Execution Registry | `deliverables\metrics\execution_postgresql_v0.3\AUM_Metric_Execution_Registry_PostgreSQL_v0.3.csv` |
| AUM Ontology | `ontology\AUM Ontology.json` |
| Income Ontology | `ontology\Income Ontology.json` |
| Supabase schema / mock data | `supabase\migrations\` |

## 資料夾用途

映射圖的概念檢視已更新為 41 節點／67 關係；獨立 PBConcept 概念圖已同步本機與 Aura，為 41 節點／69 關係／39 條衡量路徑。兩者屬於不同圖，不要混用狀態。

```text
私銀智能問答/
├─ README.md                 # 專案入口與目前版本索引
├─ docs/
│  └─ handoffs/             # 最新交接文件；舊版放在 archive/
├─ ontology/                # Ontology JSON
├─ sources/
│  ├─ metadata/             # 原始／參考 metadata Excel
│  └─ sql/                  # 原始 Oracle SQL（內容維持原樣）
├─ deliverables/
│  ├─ metadata/             # 可供 KB / n8n 使用的 metadata 成品
│  ├─ metrics/              # 指標 registry、router、execution registry
│  └─ staging/              # Staging SQL KB
├─ supabase/
│  └─ migrations/           # 依時間排序執行的 migration
└─ archive/
   └─ tooling/              # 舊的檢查腳本、render 與工具暫存
```

## 版本與維護原則

- 新成品請放在 `deliverables\<類型>\vX.Y\`，不要再直接放根目錄。
- 最新交接文件固定放在 `docs\handoffs\`；被取代的版本移至 `docs\handoffs\archive\`。
- 原始輸入放 `sources\`，正式 ontology 放 `ontology\`，避免和匯出成品混在一起。
- `archive\tooling\` 是歷史工具資料，部分腳本保留搬移前的路徑，只供追溯，不視為目前執行入口。
- `supabase\` 保留在根目錄，讓 Supabase CLI / migration 慣例維持不變。
