// 2026-10-06：真正獨立儲存的共用概念圖，已部署於 Aura 4bb479b2 / neo4j。
// 2026-10-09：28 個概念節點、51 條內部關係；12 個指標以同一 Customer 為衡量對象。
// 客戶關係為 PB_HAS_MEASUREMENT_SUBJECT；全部關係附有業務 definition。
// Customer 基本資訊為 property 定義，不建立屬性節點或實際客戶資料。
// 不引用既有 SharedProduct 或 BusinessMetric。
// 集合管理帳戶 Income 定義留白，未建立收入衡量關係，原收入指標仍保留。
// n8n 請使用 independent_concepts/01_list_concepts.cypher 的固定欄位投影。
MATCH p=(a:PBConcept)-[r]->(b:PBConcept)
RETURN p;
