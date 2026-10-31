# 映射圖客戶概念

2026-10-09 已寫入既有 Aura `4bb479b2.databases.neo4j.io`／`neo4j`。使用者要求映射圖也能顯示客戶，沿用「產品 → 衡量指標 → 客戶」與基本資訊為 properties 的設計。

## 新增範圍

- 一個 `BusinessDimension:MappingCustomer` 節點，穩定鍵為 `pb_shared:customer:customer`；獨立於概念圖 `PBConceptCustomer`，兩圖無共用節點與跨圖關係。
- `customerId`、`customerName`、`customerNumber` 都是基本屬性定義；沒有建立屬性節點或實際客戶資料。編號為選用、名稱可缺值。
- 目前 15 個共用產品衡量路徑中的 12 個 `BusinessMetric` 各自新增一條 `MEASURES_CUSTOMER`，包含六個 AUM 與六個 Income 指標；取得客戶維度不需經過總 AUM。產品仍連衡量指標。
- 新客戶節點以兩條 `HAS_DOMAIN_DIMENSION` 參照原有 `aum:dimension:customer` 與 `income:dimension:customer`。原維度、`HAS_DIMENSION`、來源欄位與 SQL 血緣保持原狀；這兩條是維度說明參照，並非實際身分合併。
- 本次只擴充共用產品路徑的客戶表示；放款利收及組織報表等未包含在十二指標中的項目不新增客戶邊。

`status=model_confirmed` 代表結構已由使用者確認；`identityMappingStatus=pending_confirmation` 代表跨來源識別尚待確認。既有產品與指標的草案、待確認及重複計入狀態均保留。

## 基本資訊的來源參考

`build_customer_mapping.py` 唯讀擷取兩份原始 metadata：`sources/metadata/AUM_metadata.xlsx` 與 `sources/metadata/收入_metadata.xlsx`。基本資訊共 43 筆欄位參考，詳細檔案、工作表、列號、資料型態與原始定義存於 [business_dictionary.json](business_dictionary.json)。Customer 的 `customerIdSources`、`customerNameSources`、`customerNumberSources` 保存這些參考；它們不是可執行 JOIN 規則。

例如證券基金 `WKB02` 在 metadata 為投資人帳號，`WKA28` 為身分證字號，保留各自識別種類，沒有將兩者視為同一種 ID。metadata 工作表名稱不一定等於完整實體表名；例如保險工作表名稱被截短，來源參考維持其實際工作表名稱。`sourceAvailability` 註明名稱／編號不一定保留在現有彙整輸出，不能宣稱客戶基本資料已可查得。

## 查圖

- [view_mapping_customer.cypher](view_mapping_customer.cypher)：直接展示共用產品、指標與映射 Customer。
- [view_mapping_with_customer.cypher](view_mapping_with_customer.cypher)：使用者原本的完整產品／指標／Stage／SQL 表血緣查詢，另補 Customer 路徑。
- `../Shared_AUM_Income_SQL_queries.cypher` 第一段與 `../Shared_product_browser_queries.cypher` 第一段也已同步加入客戶。

舊聊天訊息中的查詢文字不會自動更新。若仍執行只回傳 AUM／Income／mapping／lineage 的舊查詢，畫面不會顯示客戶；必須改用本次的查詢。

### 原查詢範圍與列數保留

使用者要求嚴格保留原來四段路徑，只補 cust。原始查詢已保存為 [view_mapping_baseline.cypher](view_mapping_baseline.cypher)。先前直接 OPTIONAL MATCH 每個客戶路徑會把 84 列擴成 498 列，可能受圖形工具的結果列數上限影響顯示。新版以每列的相關子查詢 `collect(DISTINCT customerPath)` 附帶 `customerPaths`，保留 84 列，不重新展開任何 Stage、底表或 ontology。

[view_validation.json](view_validation.json) 直接在 Aura 逐筆比對了完整回傳值與重複列數：原來四欄完全一致，SQL 血緣路徑完全一致，原查詢子圖為 137 節點／194 關係；新版為 138／206，只增加一個 MappingCustomer 及十二條 MEASURES_CUSTOMER。沒有新增 Ontology、Term、SourceProperty 或 PBConcept 節點到這個查詢結果。這些是查詢子圖數量，不是全庫總數。修正只修改查詢檔案，沒有再修改圖譜資料。

`verify_mapping_view.py --credentials <既有憑證檔>` 可唯讀重跑這項精確比對；匯入器也已加入相同檢查，不能只驗證有無客戶就宣稱完整映射查詢相容。初次匯入 `validation.json` 中的 498 是舊查詢回傳列數，最新查詢驗證以 `view_validation.json` 為準。

```cypher
MATCH path=(metric:BusinessMetric)-[:MEASURES_CUSTOMER]->(customer:MappingCustomer {key:'pb_shared:customer:customer'})
RETURN path;
```

## 匯入與驗證

`graph_plan.json` 使用 `pb_shared` 命名空間及外部端點參照；原有共用產品匯入器仍維持原範圍，本擴充由專用匯入器管理，避免將客戶當作產品重建。

先使用 bundled Python 執行 `build_customer_mapping.py` 產生字典／計畫，再執行 `import_customer_mapping.py --credentials <既有憑證檔> --check-only` 核對，最後移除 `--check-only` 匯入。只允許既有 Aura；憑證不寫入輸出。資料新增採單一交易、Customer 穩定鍵有唯一約束；重跑拒絕陌生內容，不覆寫既有外部節點、不刪除資料。

[validation.json](validation.json) 已證明新增一節點、十四關係，原有 **1,194 節點／3,702 關係**的 ID、標籤、全部屬性與關係摘要保持一致；該數字是新增前的全庫受保護資料，包含 28／52 的獨立概念圖，不是映射查詢子圖數量。新增後映射圖為 1,167 節點／3,664 關係，獨立概念圖仍為 28／52，兩圖跨邊為零。已直接執行兩個新版可視查詢，驗證證券基金可直接沿證券 AUM 到客戶，並驗證重跑不增加資料。

本次沒有修改 n8n 流程或發布草稿，沒有執行來源 SQL 或客戶金額查詢。
