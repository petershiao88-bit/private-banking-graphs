from pathlib import Path
HERE=Path(__file__).resolve().parent
previous=HERE/'README.full_graph_two_jev.archived.md'
if not previous.exists():previous.write_text((HERE/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
readme='''# AUM／Income KB：完整概念圖 → 單輪 Jev → 直接查映射

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

完整純概念圖目前有 27 節點、40 關係、30 條路徑。原生 `typesafe/jev-1.13` 逐候選判斷 included／uncertain／excluded，可多選，僅按 choice=included 納入。原始機率、confidence 原樣保留；沒有數值門檻、top-1、跨候選正規化、機率相乘、IF 或額外 Agent。domains／metricCodes 僅為提示，圖顆粒度留待使用者問題實測。

映射階段沿既有 SharedProduct、實作與 SQL 血緣關係取回所有對應路徑，不做第二輪評選。`mappingPaths` 不包含合成的判斷或機率。共用實作可對應多條概念路徑；保留整個實作的所有必要 UNION／JOIN 依賴，SQL 按 statementKey 共用，避免重複或遺失來源。

主要欄位為 `conceptGraph`、`conceptPathScores`、`selectedConceptPaths`、`mappingPaths`、`sqlEvidence`、`products`、`queryPlan`、`decision.concept`、`mappingResolution`。完整 SQL 位於 `sqlEvidence.statements[].properties.sql`；`products[].mappings[].sqlEvidence` 以 tableKeys、statementKeys、paths 參照共享證據。每個 mapping 的 mappingPathKeys 是圖查詢回傳的路徑。沒有 mappingPathScores、selectedMappingPaths 或 decision.mapping。

SQL Agent 依問題及原始 SQL 判斷日期、範圍、估值、客戶粒度與適用執行階段；歷史初始化與月更新不能直接加總。來源 SQL 僅作證據，不執行。測試主流程僅修改 SQL Reasoning Agent、Normalize SQL Result、保留候選機率三節點；其接線、憑證引用及其他參數核對通過。

原生 Aura＋单輪 Jev 實測：月底證券 AUM，30 條概念候選中納入 4 條，直接取回 17 條映射路徑。原生機率核對通過；僅有一筆 Jev request。五组真實 Aura 資料搭配合成決策另驗證存款 AUM（5 條映射）、存款 Income（7 條）、證券基金（2 條）、全部證券（17 條）、存款 AUM／Income（12 條），並驗證低機率 included、多對多、空選取、SQL 依賴完整、主流程欄位相容性。合成決策不是原生模型實測。

關於 cust_id：此次只做唯讀核對，沒有新增或修改客戶圖模型。既有圖已包含 AUM／Income 的「客戶」BusinessDimension、部分 PhysicalColumn CUST_ID，以及來源 SQL 的客戶鍵映射，例如證券基金 `WKB02 AS cust_id`。目前第一輪僅讀 PBConcept，尚未包含這些客戶維度；下游 SQL 證據保留客戶鍵。尚未建立跨來源客戶身分一致性規則，不能僅因別名相同就認定不同來源識別碼可直接 JOIN。

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
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
handoff=HERE.parents[1]/'docs'/'n8n_AUM_Income_KB_交接_2026-10-08.txt'
text=handoff.read_text(encoding='utf-8')
new='''【2026-10-08 更新：七節點／單輪 Jev；以下九節點及更舊內容均為歷史。】
使用者已批准：完整概念圖 → 原生 Jev 選概念路徑 → 沿既有圖關係查全部映射與 SQL；取消第二輪 Jev。
七節點：KB Input → Aura - Full Concept Graph → Jev - Prepare Concept Paths → Jev - Concept Path Decisions API → Concept Path Result → Aura - Mapping Paths → KB Result。
新合約 pb_kb_full_graph_single_jev_v1：conceptPathScores、selectedConceptPaths、mappingPaths、sqlEvidence、products、queryPlan、decision.concept、mappingResolution；映射沒有第二輪機率。
KB 草稿 tL7HTesvAzqwsqv6 及主流程測試版 nBrzHm3pNsVcOpeu 已保存未發布；主流程仍 32 節點，只改 SQL Reasoning Agent、Normalize SQL Result、保留候選機率。線上匯出參數／憑證引用／接線核對通過，固定測試輸入已清除。
原生單輪實測：月底證券 AUM，30 條概念候選 → 4 條納入 → 17 條映射直接取回。另五組圖查詢資料搭配合成決策驗證多對多、空選取、SQL 必要依賴及原始機率。未執行完整金額查詢或來源 SQL。
cust_id 唯讀核對：此次没有新增或修改圖譜。既有圖已含 AUM／Income 客戶 BusinessDimension、部分 PhysicalColumn CUST_ID，以及來源 SQL 映射（如 WKB02 AS cust_id）；目前 PBConcept 純概念圖未含客戶維度，也未建立跨來源識別碼一致性規則。
最新權威：ontology/n8n_kb/README.md、PB_AUM_Income_KB.single_jev.saved.json、main.single_jev.saved.json、single_jev.deployment.json、single_jev.native_securities_all.json、single_jev.customer_identity_audit.json。
建置 build_single_jev_workflow.py、測試 test_single_jev.cjs、核對 verify_single_jev_saved.py。不要回用舊生成器；不要自行發布。

'''
handoff.write_text(new+text,encoding='utf-8')
