# 獨立共用概念圖與 n8n 固定查詢

2026-10-06 已實際建立於 **Aura `4bb479b2.databases.neo4j.io`／`neo4j`**。
本目錄是新的概念圖；上層既有 AUM／Income／SharedProduct／SQL 圖直接作為映射圖保留，沒有重建或複製。

2026-10-09 後續更新：使用者另要求映射圖顯示客戶，已在映射層新增獨立 `MappingCustomer` 及十四條關係，詳見 [../mapping_customer/README.md](../mapping_customer/README.md)。本目錄概念圖仍為 28／52，沒有新增跨圖關係。下列映射圖 1,166／3,650 與舊摘要是本次概念圖匯入驗證當時的歷史數字；映射客戶更新後為 1,167／3,664，新增前既有內容完整性已另行驗證。

## 2026-10-09 客戶概念更新

依使用者確認的「產品 → 衡量指標 → Customer」設計，新增一個 `PBConcept:PBConceptCustomer` 節點，代碼為 `conceptCode=customer`。六個 AUM 與六個 Income 指標各自透過 `PB_MEASURES_CUSTOMER` 直接連到它；沒有產品直接連客戶、沒有客戶屬性節點，也不採用上層指標的維度繼承。概念圖共 **28 節點、52 關係**。

Customer 的 `customerId`、`customerName`、`customerNumber` 是基本屬性的**業務定義文字**，並非實際客戶資料。名稱來源可缺值，客戶編號為選用；`status=model_confirmed` 表示概念結構已由使用者確認，不代表跨來源客戶身分對照已確認。產品、指標定義及既有歸屬保持原狀，原映射圖與跨圖隔離邊界保持原狀。

- [view_customer_graph.cypher](view_customer_graph.cypher)：直接展示產品、衡量指標與 Customer。
- [lookup_customer_dimension.cypher](lookup_customer_dimension.cypher)：以 `$metricCode` 直接取客戶維度，不經過總 AUM 或總收入。
- [full_concept_graph_with_customer.cypher](full_concept_graph_with_customer.cypher)：含 Customer 代碼、屬性及關係的完整唯讀投影；原本 30 條產品到總指標的衡量路徑仍保留，Customer 不成為計算路徑終點。

本次沒有修改或發布 n8n 工作流。`ontology/n8n_kb` 的 2026-10-08 single_jev saved 草稿目前固定投影只有產品／指標代碼，對新增 Customer 會得到空 key，且不提供三個基本屬性。這是既有草稿待接線的相容性缺口，不能宣稱 Jev 已能完整使用客戶概念。上列新版查詢已直接在 Aura 驗證，可供後續經授權更新固定投影；不得將 Customer 邊加入衡量／彙總路徑的類型集合，避免客戶成為計算根節點。單輪 Jev 與映射流程的設計保持不變。

來源欄位仍由原 metadata 與映射圖描述：`DSPMS.PB_PMS_AUM` 的客戶 ID／名稱、存款的 `CUST_NO` 等是本次基本屬性依據。證券基金 AUM 的投資人帳號與 Income 的身分證字號不能僅憑相同別名直接串接；本次沒有新增身分合併或來源 JOIN 規則，也沒有執行金額查詢。屬性採純業務文字，不把實體欄位與來源表寫進 PBConcept。

匯入前備份：[concept_graph.before_customer.json](concept_graph.before_customer.json)、[validation.before_customer.json](validation.before_customer.json)；線上概念備份：[customer_update.before.json](customer_update.before.json)。最新實測：[validation.json](validation.json)、[customer_graph.output.json](customer_graph.output.json)。

## 部署確認與隔離邊界

| 環境 | 實際檢查 | 分庫能力 | 本次操作 |
|---|---|---|---|
| 本機 `127.0.0.1:7474` | Discovery API：Neo4j 2026.09.0 Community；查詢 API 要求登入 | Community 僅一個標準資料庫 | 唯讀確認版本，沒有修改資料 |
| Aura `4bb479b2` | Console：My instance／AuraDB Professional／2 GB／試用剩餘 14 天；線上版本 5.27-aura；`SHOW DATABASES` 為 neo4j、system | 此 Professional 執行個體不支援多個業務資料庫 | 在既有 neo4j 新增獨立概念節點及內部關係 |

以本專案的 `aura_migration/import_validation.json`、對應下載憑證、線上既有圖譜與目前 Aura Console 的執行個體相互核對，確認 Aura 是本次沿用的部署目標。本機仍運作，不代表本次應寫入本機。

[Neo4j 官方分庫說明](https://neo4j.com/docs/aura/managing-instances/multiple-databases/)列出的 Aura 多資料庫方案為 Business Critical 與 Virtual Dedicated Cloud，且須在建立執行個體時啟用，不能事後切換。底層回報 enterprise 不表示 Professional 方案可新增資料庫。[Community 版限制](https://neo4j.com/docs/operations-manual/current/database-administration/)為一個標準資料庫。

本次沒有建立執行個體、升級方案、購買付費資源或變更既有使用者權限。採用使用者允許的「同一資料庫、節點完全獨立」方案。

**這不是資料庫權限隔離：持有任意 Cypher 權限的 AI 仍可直接查詢現有映射圖。** `PBConcept` 標籤、無跨圖關係及固定投影不會撤銷該權限。n8n 必須把連線憑證與查詢文字保留在受控節點，只開放以下固定功能；不得把通用 Neo4j、HTTP Request、Cypher 執行器或工作流編輯權交給 Agent。若未來分庫，仍需搭配分庫授權，不能讓概念查詢憑證同時讀取映射庫。

## 新圖內容

- 15 個 `PBConcept:PBConceptProduct`；只存 `productCode`、`name`、`definition`、`status`、`aumStatus`、`incomeStatus`。
- 12 個 `PBConcept:PBConceptMetric`；其中 6 個另有 `PBConceptAUM`、6 個另有 `PBConceptIncome` 標籤；只存 `metricCode`、`name`、`definition`、`status`。
- 1 個 `PBConcept:PBConceptCustomer`；只存 `conceptCode`、`name`、`definition`、`status`、`customerId`、`customerName`、`customerNumber`。
- 52 條內部關係：15 條 AUM 衡量、14 條 Income 衡量、1 條 Income 待確認、10 條指標向上歸屬、12 條指標直接衡量客戶。關係不含技術屬性。
- 不共用既有指標或產品節點；没有連至 `SharedProduct`、`BusinessMetric`、`StagingOutput`、`SqlTable` 等原圖節點的關係。
- 概念屬性與文字不含 Stage、底表、SQL 或篩選條件。全部定義為業務文字；原圖仍保有完整技術證據。
- `bank_collective_account` 的 `incomeStatus=pending_confirmation`，並以 `PB_INCOME_PENDING` 連往自己的 Income 指標。這不代表獨立收入已確認計入。
- 保留銀行保險收入重複計入未解的狀態，月底總 AUM 維持草案；未將推論提升為正式確認。

範圍沿用 15 個共用產品。放款等單側產品仍留在原映射圖；新圖的利息收入定義仍包含存款與放款，但共用產品圖不新增放款產品。分類指標是業務歸屬，不表示可將同一分類金額分配給每個產品後再加總。

Neo4j Query／Browser 可執行 [view_concept_graph.cypher](view_concept_graph.cypher) 檢視新圖。上層 `AUM_Income_concept_only.cypher` 也已改為只查新圖。其他舊圖查詢保留。

## 重跑

在專案根目錄執行；Python 3 標準函式庫即可，不安裝套件、不建立資料庫：

```powershell
python -X utf8 ontology\independent_concepts\build_concepts.py
python -X utf8 ontology\independent_concepts\import_concepts.py --credentials "$env:USERPROFILE\Downloads\Neo4j-4bb479b2-Created-2026-10-06.txt" --check-only
python -X utf8 ontology\independent_concepts\import_concepts.py --credentials "$env:USERPROFILE\Downloads\Neo4j-4bb479b2-Created-2026-10-06.txt"
python -X utf8 ontology\independent_concepts\build_n8n_assets.py
node ontology\independent_concepts\test_n8n_guards.cjs
```

也可不帶 `--credentials`，改由環境變數 `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD` 提供連線。憑證不會寫入輸出或驗證報告。

匯入前檢查舊圖 15 個代碼存在且唯一；遇到新概念標籤、代碼、屬性或關係衝突即停止，不覆蓋陌生內容。三個唯一約束只套用於概念產品、指標及客戶代碼；資料寫入為單一交易。沒有刪除操作，不清空舊圖。重跑保留新節點 ID、數量與內容。

未來若已有可用的獨立概念資料庫，可指定 `--database pbconcepts --mapping-database neo4j`。腳本不會建立資料庫或複製映射圖；這不是本次已部署的配置。

## n8n 接線

本次交付固定查詢、Code 節點內容、HTTP 請求範本及輸出範例；**尚未匯入或修改線上的 n8n 工作流**。查詢已直接在實際 Aura 執行，Code 節點邏輯已在本機以實際結果測試。

固定流程：

`01 Prepare → HTTP Concepts → ConceptCatalog → 選定 productCode 與 domain → 02 Prepare → HTTP Mapping → MappingResult`

所有 Code 節點使用 **Run Once for All Items**。兩個 HTTP 節點都設為一般工作流節點，不能直接掛為可自由設定的 Agent 工具。

| 設定 | 固定值 |
|---|---|
| Method | POST |
| URL | `https://4bb479b2.databases.neo4j.io/db/neo4j/query/v2` |
| Authentication | Generic Credential Type／Basic Auth；由管理者在 n8n Credential 配置 |
| Headers | `Content-Type: application/json`、`Accept: application/json` |
| Body | JSON，使用 `{{ $json }}`；輸入必須直接來自對應 Prepare Code 節點 |
| Response | JSON、僅 body；不要啟用 Never Error |

第一段使用 [n8n_01_prepare.js](n8n_01_prepare.js) 與 [n8n_01_project_output.js](n8n_01_project_output.js)。將投影節點命名為 **ConceptCatalog**。Agent 只接收其 `{products:[...]}`，不接收請求內容、Neo4j 原始回應、錯誤內容或連線資料。Prepare 完全不讀取 Agent 提供的查詢內容。

選定產品及指標後，第二段的輸入只能是：

```json
{"productCode":"bank_insurance","domain":"income"}
```

第二段使用 [n8n_02_prepare.js](n8n_02_prepare.js) 與 [n8n_02_project_output.js](n8n_02_project_output.js)。Guard 從本次執行的可信 `ConceptCatalog` 驗證代碼，僅接受 `aum`／`income`，拒絕額外欄位及任意查詢文字；先前未執行概念查詢則停止。若跨工作流或跨回合，須由伺服器保存及驗證該次 catalog／選擇狀態，不能接受 Agent 自行提交的 catalog 替代。

第二段用 `$productCode` 比對**既有** `SharedProduct.code`；新圖的 `productCode` 和舊圖的 `code` 字串一致。這是應用層代碼對照，不新增映射節點、舊圖屬性或 Neo4j 跨圖關係。查询文字固定在工作流，參數不拼接入 Cypher。

Neo4j Query API 可能以 HTTP 200 回傳 `errors`；兩個投影節點都檢查此欄位並停止，對 Agent 只顯示通用錯誤。HTTP 層失敗也應由工作流錯誤分支轉為通用訊息，不直接轉發技術內容。

## 兩段固定查詢與輸出契約

### 第一段：概念探索

[01_list_concepts.cypher](01_list_concepts.cypher)／[01_request.json](01_request.json)。無參數，15 筆結果，僅列出以下 8 個欄位：

| 欄位 | 型態與意義 |
|---|---|
| productCode、productName、definition、status | 字串：產品業務代碼、名稱、定義、狀態 |
| aumStatus、incomeStatus | 字串：兩側業務定義狀態 |
| aumMetrics、incomeMetrics | 指標陣列，由直接歸屬分類一路到總指標；每筆僅 `metricCode`、`name`、`definition`、`status` 四個字串 |

投影後輸出為 `{"products":[產品物件]}`。完整的實際 15 產品輸出存於 [01_output.json](01_output.json)。不使用 `RETURN p`、`properties(p)`、`p{.*}`，也不回傳原圖欄位。

### 第二段：選定產品後追查原映射圖

[02_lookup_mapping.cypher](02_lookup_mapping.cypher)／[02_request.example.json](02_request.example.json)。僅兩個參數：`productCode`、`domain`。

| 輸出欄位 | 型態與意義 |
|---|---|
| productCode、productName、domain、status | 字串；domain 為 aum／income |
| mappingActive | 布林；集合管理帳戶 Income 為 false |
| calculationAuthorized | 固定 false；查到血緣不構成業務計算核准 |
| mappings | 陣列，包含既有映射與其底表路徑 |

每個 `mappings` 物件明確包含 `mappingType`、`mappingStatus`、`productScope`、`outputTable`、`sqlTable`、`lineageStatus`、`lineage`。`lineage` 每筆為 `baseTable`、`tablePath`、`rules`。

`rules` 只投影：`operation`、`operationTypes`、`whereConditions`、`joinConditions`、`groupExpressions`、`aggregateExpressions`、`selectExpressions`、`caseExpressions`、`unionBranchOrders`、`unionDeduplication`、`file`、`lineStart`、`lineEnd`、`status`、`sql`。缺少的舊圖屬性可為 null。這些技術資訊只在第二段提供。

完整實測 JSON 見 [02_output_examples.json](02_output_examples.json)，涵蓋保險及集合管理帳戶的 AUM、Income。集合管理帳戶 Income 回傳 `status=pending_confirmation`、`mappingActive=false`、`calculationAuthorized=false`，映射類型仍為 `INCOME_DECLARED_BY`。

查詢沿現有 active_sql／primary_reference 的資料流追查最多 8 層，保留所有已匹配來源而不以 LIMIT 截斷；無法追到來源時回傳 `missing_evidence`，不靜默丟掉映射。底表一詞在此指原圖標示的 `external_source`，可能包括匯率／工作日等參照物件，不代表已連上來源資料庫驗證其實體存在。沒有執行底表 SQL 或查詢客戶金額。

## 已完成的實際驗證

| 檢查 | 結果 |
|---|---|
| 原映射圖節點／關係 | 修改前後皆 1,166／3,650 |
| 原圖 ID、標籤、全部屬性、關係方向及屬性摘要 | 修改前後 SHA-256 一致 |
| 新圖節點／關係 | 28／52（客戶更新前 27／40） |
| 新圖與舊圖共用節點 | 0 |
| 新圖與舊圖跨圖關係 | 0 |
| 新圖重跑 | 節點 ID、數量、內容與關係不變 |
| 第一段白名單／技術文字檢查 | 15 筆產品，通過，技術洩漏 0 |
| 第二段所有產品與兩側指標 | 30／30 組均追到既有來源，未遺漏所選產品的映射 Stage |
| 第二段無效／注入參數 | 3 組均無結果，未被當作查詢執行 |
| n8n Guard | 30 組有效選擇通過；5 組非法輸入被拒；缺少第一段結果被拒；額外技術欄位／技術文字被拒 |

例如銀行保險 AUM 追到 `DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT`；Income 保留 3 條既有映射，分別追到 `DSKPI.KPI_DET_OFI_001`、`DSKPI.KPI_DET_IU_002_NEW`、`DSINS.INSU_RPT_Q01`。集合管理帳戶 Income 可追到 `DSFND.PB_FUND_SPREAD_DAILY`，但仍是定義待確認的證據。

原圖前後摘要：`9aa66443e902ad9a547a28353a0ede517ddee7377d5fb364591b698e4d2ddd1a`。
機器可讀證據：[validation.json](validation.json)、[n8n_guard_validation.json](n8n_guard_validation.json)。

相關官方介面文件：[Neo4j Query API](https://neo4j.com/docs/query-api/current/query/)、[n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)。
