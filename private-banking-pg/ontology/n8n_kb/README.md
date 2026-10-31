# AUM／Income KB：完整概念圖 → 單輪 Jev → 直接查映射

**2026-10-14 最新狀態：已更新並發布。** 完整概念圖為 41 節點／69 關係／39 條衡量路徑。KB 同時回傳選取產品的現行 MappingDraft 規則與既有 SharedProduct SQL 血緣，加入 ruleEvidence、dimensionEvidence、evidenceGuidance，並保留父子重疊、月份、身分對照與待確認限制。全部 39 組產品／領域、95 條規則來源及必要依賴已用實際 Aura 查詢核對；原生 Jev 與完整七節點 KB 的放款利收測試通過。修改四節點，憑證、接線、其餘參數及單輪 Jev 保留；發布後無固定測試資料。未修改主流程、圖譜或執行金額 SQL。權威線上匯出為 `PB_AUM_Income_KB.single_jev.saved.json`；詳細核對、備份與使用邊界見[本次更新紀錄](../../deliverables/n8n_kb_update/20261014/更新紀錄.md)。下列未發布及 28／51／29 等內容均為歷史。

**2026-10-09 後續關係更新：** Aura 概念圖現為 28 節點／51 關係／29 條衡量路徑。已移除集合管理帳戶的 PB_INCOME_PENDING，12 條客戶關係改為 PB_HAS_MEASUREMENT_SUBJECT，全部 51 條關係補上 definition。已保存的 n8n Query 會動態讀取關係類型與 properties(r)，直接對 Aura 核對通過，候選準備程式本地核對得到 29 條候選。此次未修改或發布 n8n，也未在 n8n 執行流程或呼叫 Jev；詳見 [關係更新紀錄](../../deliverables/concept_relations/20261009/更新紀錄.md)。下段 28／52／30 是關係更新前的 n8n 實測歷史。

**2026-10-09 概念查詢更新：** 已在 n8n「私銀 AUM Income KB」保存新版概念 Query，重新載入並匯出核對通過。本次更新 Aura - Full Concept Graph、Jev - Prepare Concept Paths、KB Result 三個節點；七節點接線、憑證引用、映射 Query 與其餘參數保持原狀，未發布。概念查詢在 n8n 實測回傳 28 節點／52 關係／30 條衡量路徑，全部 key 有值；產品提供 aumDefinition／incomeDefinition，Customer 提供 conceptCode 與三個基本屬性。Customer 只作維度上下文，沒有加入計算路徑。KB Result 依領域取對應定義並移除舊 definitionStatus；30 組產品／領域的本地輸出驗證通過。新版完整 query 見 lookup_full_concept_graph.cypher；本次驗證與匯出見 [n8n 更新紀錄](../../deliverables/n8n_concept_query/20261009/更新紀錄.md)。下方原生 Jev 實測與 single_jev.deployment.json 是 2026-10-08 的歷史結果；本次只實際執行概念 Query 與候選準備，沒有重新呼叫 Jev、執行主流程金額查詢或 SQL。

2026-10-08 最新草稿合約為 `pb_kb_full_graph_single_jev_v1`。使用者批准七節點 KB：Jev 選概念路徑後，沿既有映射查回所有實作與 SQL，取消第二輪 Jev。KB 與 32 節點測試主流程已保存，未發布。此次沒有修改 Aura 圖譜或原始主流程。

| 節點 | 輸入 | 輸出 |
|---|---|---|
| KB Input | question、domains、metricCodes | 問題與提示；不預篩概念 |
| Aura - Full Concept Graph | 唯讀查詢 | 全部 PBConcept、内部關係及由底到頂的完整有向路徑 |
| Jev - Prepare Concept Paths | 問題＋完整概念圖及路徑 | 所有候選與原生 Decisions 請求；不含映射／SQL |
| Jev - Concept Path Decisions API | decisionRequest | 原生 answers、choice、probabilities、confidence、usage、request id |
| Concept Path Result | 原生回答＋候選 | conceptPathScores、selectedConceptPaths、selectedPaths、conceptDecision |
| Aura - Mapping Paths | selectedPaths | 全部對應實作、staging、底表、原始 SQL 與必要依賴 |
| KB Result | 映射結果＋概念決策 | products／mappings、mappingPaths、共享 sqlEvidence、queryPlan、decision.concept |

完整純概念圖目前有 28 節點、51 關係、29 條衡量路徑。原生 `typesafe/jev-1.13` 逐候選判斷 included／uncertain／excluded，可多選，僅按 choice=included 納入。原始機率、confidence 原樣保留；沒有數值門檻、top-1、跨候選正規化、機率相乘、IF 或額外 Agent。domains／metricCodes 僅為提示，圖顆粒度留待使用者問題實測。

映射階段沿既有 SharedProduct、實作與 SQL 血緣關係取回所有對應路徑，不做第二輪評選。`mappingPaths` 不包含合成的判斷或機率。共用實作可對應多條概念路徑；保留整個實作的所有必要 UNION／JOIN 依賴，SQL 按 statementKey 共用，避免重複或遺失來源。

主要欄位為 `conceptGraph`、`conceptPathScores`、`selectedConceptPaths`、`mappingPaths`、`sqlEvidence`、`products`、`queryPlan`、`decision.concept`、`mappingResolution`。完整 SQL 位於 `sqlEvidence.statements[].properties.sql`；`products[].mappings[].sqlEvidence` 以 tableKeys、statementKeys、paths 參照共享證據。每個 mapping 的 mappingPathKeys 是圖查詢回傳的路徑。沒有 mappingPathScores、selectedMappingPaths 或 decision.mapping。

SQL Agent 依問題及原始 SQL 判斷日期、範圍、估值、客戶粒度與適用執行階段；歷史初始化與月更新不能直接加總。來源 SQL 僅作證據，不執行。測試主流程僅修改 SQL Reasoning Agent、Normalize SQL Result、保留候選機率三節點；其接線、憑證引用及其他參數核對通過。

原生 Aura＋单輪 Jev 實測：月底證券 AUM，30 條概念候選中納入 4 條，直接取回 17 條映射路徑。原生機率核對通過；僅有一筆 Jev request。五组真實 Aura 資料搭配合成決策另驗證存款 AUM（5 條映射）、存款 Income（7 條）、證券基金（2 條）、全部證券（17 條）、存款 AUM／Income（12 條），並驗證低機率 included、多對多、空選取、SQL 依賴完整、主流程欄位相容性。合成決策不是原生模型實測。

關於 cust_id：此次只做唯讀核對，沒有新增或修改客戶圖模型。既有圖已包含 AUM／Income 的「客戶」BusinessDimension、部分 PhysicalColumn CUST_ID，以及來源 SQL 的客戶鍵映射，例如證券基金 `WKB02 AS cust_id`。第一輪讀 PBConcept，已含獨立 Customer 概念；映射層來源與實體客戶鍵仍由下游 SQL 證據提供。尚未建立跨來源客戶身分一致性規則，不能僅因別名相同就認定不同來源識別碼可直接 JOIN。

尚未執行主流程完整金額查詢或來源 SQL。定義草案與來源缺漏仍存在，不能宣稱可用資料已完整。固定測試輸入已清除，未發布。

權威檔案：

- `PB_AUM_Income_KB.single_jev.saved.json`、`main.single_jev.saved.json`：線上草稿匯出。
- `single_jev.deployment.json`：節點／參數／憑證引用／接線及原生 request 核對。
- `single_jev.native_securities_all.json`：本次原生結果。
- `single_jev.contract_validation.json`、`single_jev.result_examples.json`：本地合約驗證與範例。
- `single_jev.customer_identity_audit.json`：圖譜客戶鍵的唯讀核對。
- `single-jev-kb-draft.png`、`single-jev-main-draft.png`：未發布草稿畫面。
- `build_single_jev_workflow.py`：建置；`node test_single_jev.cjs`：合約測試；`python verify_single_jev_saved.py`：線上匯出核對。
- `PB_AUM_Income_KB.before_single_jev.saved.json`、`main.before_single_jev.saved.json`：修改前備份。

full_graph／simplified／lazy／paths／deployed 檔案以及 `README.full_graph_two_jev.archived.md` 均為歷史。不要用舊生成器覆蓋目前七節點／單輪 Jev 版本。
