# Ontology Hub 畫面驗收（2026-10-25）

- 實際在 Chrome 重新整理 http://127.0.0.1:8866/?ontologyTab=registry。
- Registry 顯示一筆「客戶360共通語意整合本體」，格式 turtle，43 Classes、33 Props。
- 畫面證據：data/ontology-hub.jpg。
- 8866／8865 的實際服務 API 均確認本體已載入；主畫布分別保持146／246、29／44（節點／關係）。
- 完整本體類別、屬性、定義、繼承及 domain／range 的 API 驗證記錄於 data/verification.json。
- 本次未操作編輯、SHACL、對齊或版本發布。


## Agent 交接驗證（2026-10-26）

- Chrome 實際開啟 http://127.0.0.1:8866/handoff，提交「銀行＋證券：缺少同意」；畫面顯示銀行子公司、個資、證券子公司三項標籤、SHACL 未通過、接收 Agent 沒有收到任何內容。
- 提交「手收移除後重驗」；原始輸出含公開說明與手收1.5%，初次 SHACL 未通過；註冊工具移除整個手收項目後重跑規則與 SHACL，標籤只剩公開資訊，接收端只收到公開說明。
- 由瀏覽器按「執行全部14個情境」，實際服務回傳14／14符合預期，表格分別呈現允許、阻擋、需同意，以及接收端是否收到內容。
- 畫面證據：data/handoff/redacted-delivery.jpg、data/handoff/needs-consent.jpg。完整 CLI 輸入／輸出、SHACL、血緣與決策報告：data/handoff/report.json。
- 新增16個交接測試及原有19個問答／OWL測試，共35個通過。驗證被擋的 payload 不進 inbox、移除手收後不殘留其數值與來源、來源限制聯集、多跳血緣、同意範圍／效期、假標籤、工具輸出竄改、缺少分類、循環來源、推理／SHACL／稽核故障時不傳送。
- 使用原生 MCP run_reasoning handler（Reasoner）、run_shacl_validation（pySHACL 0.40.1）、獨立 ContextGraph、ProvenanceManager，以及原生決策紀錄與追溯。沒有修改 Semantica 安裝檔。
- 兩端 Agent、工具收據、資料與同意服務為模擬；不呼叫 LLM／HermiT／付費 API，不啟動外部 MCP 或真正跨廠商 A2A。政策是示範，未宣稱實際銀行合規驗收。
- 原模型與四個視圖的既有驗證通過：full146／246、business104／146、securities29／44、ontology43／46，原始來源 SHA-256 不變。交接資料只進獨立的記憶體圖。

## 原問答改用 Semantica Reasoner（2026-10-26）

- `/ask` 預設後端改為 `semantica_reasoner.SemanticaReasoner`。本機8866服務已重啟；既有8865此次未運行，日後啟動也使用同一預設後端。
- 真正呼叫 Semantica `Reasoner.infer_with_results`，80 facts＝43類別宣告＋37條原始繼承，2條固定自反／遞移規則，產生50個新facts。輸入／輸出與原生匹配紀錄存於 `data/semantica-reasoning/<cache-key>/report.json`。
- Chrome 實際提交「證券AUM是否屬於金控定義的指標（Metric）？」；OpenRouter LLM 選擇正確的 `check_subclass` 與兩個正式 URI，後端回傳 `engine=Semantica Reasoner`、`verdict=entailed`、`used_hermit=false`。
- 實際工具紀錄含原生遞移規則與兩條匹配前提：SecuritiesAUM→AUM、AUM→Metric；LLM 回答正確引用[R1]。畫面顯示相同本體與規則的快取、推導時間、PG未納入及完整OWL一致性未驗證。
- 畫面：`data/semantica-qa.jpg`；實際瀏覽器工具請求與回傳：`data/semantica-reasoning-browser-example.json`；彙整：`data/semantica-reasoning-verification.json`。
- 38個測試通過：新引擎15、原問答7、交接16。涵蓋全43類別與獨立RDF可達性核對、直接／間接／自反及反向查詢、未知不等於否定、PG不進規則引擎、原畫布不變、來源更動拒絕舊結果，以及不支援的OWL公理不會被靜默忽略。
- `check_consistency` 回傳 `unsupported_consistency`，只呼叫一次LLM做規劃，後端固定文字明確說無法判定完整OWL一致性；不交由LLM改寫成通過。新引擎的實際執行測試禁止 `subprocess.Popen`，確認沒有依賴Java或HermiT。
- 既有四視圖、Hub434 triples／43classes／33properties及原始RDF／PG來源雜湊驗證通過；full畫布保持146／246。
- 舊HermiT程式、runtime、測試與歷史報告已移至 ../archive/cleanup-20261027/semantica-poc/ 留作參考，預設問答不使用，也不在遇到不支援公理時自動回退。

整理前的完整歷史驗收紀錄：../archive/cleanup-20261027/before-edits/semantica-poc/UI-VERIFICATION.md。
