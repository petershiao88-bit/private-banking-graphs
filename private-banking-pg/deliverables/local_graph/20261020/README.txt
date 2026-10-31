本機圖譜與雲端 n8n 橋接（2026-10-20）

圖譜已還原到獨立容器 pb-graphrag-neo4j：1,618 節點、4,649 關係。
概念層採 2026-10-18 最新快照（41 節點、69 關係）；映射與 SQL 定義採 2026-10-14 完整備份。
標籤、屬性、關係類型及端點內容指紋完全符合來源；Neo4j 內部 elementId 重新產生。
原有 neo4j-community 容器及原資料卷未改動。這些資料是定義與 SQL 血緣，不是客戶交易或餘額資料。

查詢架構：
使用者 → 雲端 n8n → Embedding／入口 Rerank → 本機候選路徑查詢 → 雲端路徑 Rerank → 本機映射查詢 → 子圖。
OpenRouter 金鑰留在雲端 n8n。雲端持有專用橋接權杖，不持有本機資料庫管理密碼。
本機只接受 full_concept_graph、candidate_paths、mapping_paths 三種固定查詢與對應參數；拒絕任意 Cypher。
使用者已明確授權啟用 Cloudflare 暫時通道及設定 n8n 權杖。

本機位址：
Neo4j Browser：http://127.0.0.1:17474/browser/
Bolt：127.0.0.1:17687
查詢橋接：127.0.0.1:18780
資料卷：pb_graphrag_data
私密設定：.local_runtime/graph/connection.json、bridge-token.txt（不隨公開交付檔分享）。

執行與重啟：
先開啟 Docker Desktop，在專案目錄執行 powershell -File local_graph/start.ps1。
腳本會啟動本專案容器與隱藏背景橋接程序，並沿用仍有效的暫時通道。
若通道失效，腳本會建立新通道，產生 .local_runtime/graph/workflow.bridge-single.json。
通道網址改變後，需將新檔匯入現有 n8n 流程再儲存；雲端無法自行發現新網址。
電腦、Docker、橋接及通道都必須持續運作。未設定開機排程。暫時通道適合測試，尚非固定服務網址。

驗證：
import-verification.json：完整還原及來源指紋。
query-verification.json：概念、候選路徑、映射及原 12 題映射查詢核對。
bridge-verification.json：權杖驗證、固定操作、拒絕任意查詢。
初輪 38 題並發曾在映射階段發生連線拒絕；橋接改用 128 個等待連線、最多 4 個同時資料庫查詢，38 個並發通道請求均回傳 200。
完整語意檢索結果另見 graph_retrieval_v8/evaluations.json；查詢連通成功不代表選圖全部正確。
