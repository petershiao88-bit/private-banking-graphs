# AUM／Income KB：完整概念圖 → 概念路徑 → 映射路徑

2026-10-08 最新草稿合約為 `pb_kb_full_graph_mapping_paths_v1`。KB 有 9 節點；主流程測試版保留 32 節點，更新 SQL 提示與兩輪路徑結果欄位。兩者已保存，未發布。原始主流程及圖模型未修改。

## 九個節點與輸入輸出

| 節點 | 輸入 | 輸出 |
|---|---|---|
| KB Input | question、domains、metricCodes | 問題與提示；不以 domains／metricCodes 預篩選概念 |
| Aura - Full Concept Graph | 唯讀概念圖查詢 | 所有 PBConcept 節點、内部關係及由底到頂的完整有向業務路徑 |
| Jev - Prepare Concept Paths | 問題＋完整概念圖及路徑 | conceptPathCandidates、第一輪 Decisions 請求；不含 SQL／映射 |
| Jev - Concept Path Decisions API | 第一輪 decisionRequest | 原生 answers、choice、probabilities、confidence、model、usage、id |
| Concept Path Result | 第一輪回答＋候選 | conceptPathScores、selectedConceptPaths、selectedPaths、conceptDecision |
| Aura - Mapping Paths | selectedPaths | 所選概念的實作、staging、底表路徑、原始 SQL 與必要依賴 |
| Jev - Prepare Mapping Paths | 第一輪上下文＋映射查詢結果 | mappingPathCandidates、共享 sqlEvidence、第二輪 decisionRequest |
| Jev - Mapping Path Decisions API | 第二輪 decisionRequest | 原生映射路徑回答、機率、confidence 與請求資訊 |
| KB Result | 第二輪回答＋兩輪上下文 | 兩輪候選分數與所選路徑、products／mappings、共享 SQL 證據、queryPlan、原生 decision |

兩輪皆使用既有 OpenRouter 憑證引用及 `typesafe/jev-1.13` 原生 `/api/alpha/decisions`。每個候選各自判斷 included／uncertain／excluded，可選多條。僅按原生 choice=included 納入；無額外門檻、top-1、跨候選正規化、機率相乘、IF 節點或額外 Agent。

目前完整概念圖有 27 節點、40 關係、30 條完整業務路徑。先完成純業務判斷，再載入映射與 SQL；圖顆粒度留待實測後再決定。

第二輪每條 external_source 到 target 的完整實體路徑皆是候選。共用實作可對應多條概念路徑。原始 SQL 按 statementKey 共用，保留原文。Jev state 使用 T／S／E／M 共用參照表达表、SQL、關係、實作，避免重複的大型資料血緣 hash 與原始 SQL 已呈現的解析表達式。所有候選、依賴關係及原始 SQL 都保留；輸出合約仍使用原始 keys。

選定實作後，KB Result 保留其全部必要 SQL 依賴，避免遺失 UNION／JOIN 的其他來源；這些依賴不會偽裝成 Jev 選取結果。歷史初始化與月更新依原始 SQL 分開理解，不直接加總。

## 回傳與主流程相容性

主要欄位：`conceptGraph`、`conceptPathScores`、`selectedConceptPaths`、`mappingPathScores`、`selectedMappingPaths`、`sqlEvidence`、`products`、`queryPlan`、`decision.concept/mapping`。不沿用舊版 candidateScores／pathScores／selectedConcepts 的不同語意。

原始 SQL 位於頂層 `sqlEvidence.statements[].properties.sql`，带 statementKey、requiredTableKeys。`products[].mappings[].sqlEvidence` 使用 tableKeys／statementKeys／paths 參照共享證據。測試主流程更新三節點：SQL Reasoning Agent、Normalize SQL Result、保留候選機率；接線及其他參數保留。

## 驗證與限制

原生 Aura＋兩輪 Jev 三次成功測試：

| 問題 | 概念候選／選取 | 映射候選／選取 |
|---|---|---|
| 證券基金月底 AUM | 30／1 | 2／2 |
| 全部證券產品月底 AUM | 30／4 | 17／17 |
| 台幣存款月底 AUM 及當月存款收入 | 30／2 | 12／12 |

第三題選到目前圖中的 deposit AUM 與 deposit Income。圖沒有台幣子概念，故本測試證明跨領域流程能完成，不證明台幣口徑已解決或取得真實金額。

整體證券早期第二輪曾 max_tokens_exceeded。改共用參照後保留全部 17 候選及完整原始 SQL，實際第二輪输入為 13,796 tokens；跨領域為 16,734 tokens。圖與 SQL 增長時仍需觀察原生模型容量。

本地五組真實 Aura 查詢資料搭配合成 Jev 回答，另驗證多路徑、多對多、低機率 included 原樣保留、mixed uncertain、空選取、完整 SQL 依賴與主流程欄位相容性。合成回答不是原生 Jev。空候選不造假題目；第二輪原生空問題錯誤保存在 decision.mapping.error。

尚未執行主流程完整金額查詢或來源 SQL；沒有發布。既有來源缺漏及草案定義仍存在，不能宣稱資料完整。固定測試輸入已清除。

## 權威檔案與重建

- `PB_AUM_Income_KB.full_graph.saved.json`、`main.full_graph.saved.json`：本次線上草稿匯出。
- `full_graph.deployment.json`：參數／憑證引用／接線核對與原生 request id。
- `full_graph.native_securities_fund.json`、`full_graph.native_securities_all.json`、`full_graph.native_deposit_both.json`：原生結果。
- `full_graph.contract_validation.json`：本地合約測試，合成決策；`full_graph.query_validation.json`：真實 Aura 唯讀查詢測試。
- `full-graph-kb-draft.png`、`full-graph-main-draft.png`：可檢視草稿。
- `build_full_graph_workflow.py`：本次生成器。先執行 `python build_full_graph_workflow.py`，再用 `node test_full_graph.cjs` 驗證；線上匯出保存後跑 `python verify_full_graph_saved.py`。
- `PB_AUM_Income_KB.full_graph.ready.json`、`main.full_graph.ready.json`：生成草稿；`.full_graph.test.json` 帶固定输入，只供測試。

其他 simplified／lazy／paths／deployed 檔案及舊 build 入口為歷史版本，不代表目前九節點流程。不要用舊交接中「僅討論／先選產品」的方向覆蓋本次使用者已批准的完整概念圖與兩輪路徑評選。
