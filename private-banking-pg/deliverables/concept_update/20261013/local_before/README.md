# 獨立概念圖

2026-10-13 後續：本機建立器、欄位驗證與查詢已支援第二版業務草稿，包括單側產品／服務、AO、私銀與個別關係限制。正式字典與 concept_graph.json 仍為 28／51；草稿另建立 41／69 與 39 條衡量路徑。新版查詢及雙映射入口範本與核對結果見[本機更新紀錄](../../deliverables/concept_build/20261013/更新紀錄.md)。未同步資料庫或線上 n8n；新規則證據與既有工作流 SQL 血緣格式的接線整合留待後續。

2026-10-13 接續狀態：本目錄仍為下述 2026-10-09 的 28 節點／51 關係版本。本輪更新的是 MappingDraft 映射圖，已新增理專（AO）並修正計算與概念關聯，尚未同步到本獨立概念圖。下一步整理 AO、私銀、放款／放款利收及產品分類與業務關係定義差異；詳見[最新進度與接續清單](../../docs/handoffs/20261013_映射圖進度與概念圖接續.md)。本輪沒有重新查驗此正式圖的線上版本。

2026-10-09 已依使用者確認稿更新於 **Aura `4bb479b2.databases.neo4j.io`／`neo4j`**，並完成後續關係更新。概念圖為 28 個節點、51 條關係；映射圖為 1,167 個節點、3,664 條關係。沒有共用節點或跨圖關係，產品透過程式以 productCode 對 SharedProduct.code。

## 目前欄位

| 節點 | 數量 | 欄位 |
|---|---:|---|
| PBConceptProduct | 15 | productCode、name、aumDefinition、incomeDefinition |
| PBConceptMetric／PBConceptAUM | 6 | metricCode、name、definition |
| PBConceptMetric／PBConceptIncome | 6 | metricCode、name、definition |
| PBConceptCustomer | 1 | conceptCode、name、definition、customerId、customerName、customerNumber |

全部概念 status 及產品的 aumStatus、incomeStatus 已移除。產品原 definition 拆成兩側定義，不適用或未確認可用空字串表示。集合管理帳戶收入定義留白，PB_INCOME_PENDING 關係已移除，也沒有新增正式收入衡量關係；原收入指標仍保留。

指標維持單一 definition。AUM 描述衡量時點的資產，收入描述衡量期間的收入；月底、月份及最新可用日期規則由 SQL／映射層負責。六個 AUM 代碼移除 _month_end，income_total_customer_month 改 income_total，其餘收入代碼保留。「利息收入」改名「利收」。

客戶定義為「與機構建立往來關係，使用其產品或服務的個人或組織。」三個客戶屬性仍為說明文字，沒有實際客戶資料，也沒有建立跨來源身分對照。證券基金的投資人帳號與身分證字號不可僅憑來源別名直接串接。

完整定義來源：[business_dictionary.json](business_dictionary.json)；[更新前確認稿](../../deliverables/concept_review/20261009/概念圖更動確認稿.md)。保險來源重複、自營債券兩側範圍對應等不確定性仍保留在定義中。

## 關係與查詢

51 條關係包含 15 條 AUM 衡量、14 條收入衡量、10 條指標彙總、12 條指標以客戶為衡量對象的關係。Customer 提供維度語意，不成為計算路徑終點；移除集合管理帳戶收入待確認路徑後，產品到總指標有 29 條路徑。

保留 PB_AUM_MEASURED_BY、PB_INCOME_MEASURED_BY、PB_AUM_ROLLS_UP_TO、PB_INCOME_ROLLS_UP_TO。PB_MEASURES_CUSTOMER 改為 PB_HAS_MEASUREMENT_SUBJECT，方向仍為指標 → 客戶。所有關係加入業務 definition，來源為 [relationship_dictionary.json](relationship_dictionary.json)；彙總關係表示指標歸屬，具體計算口徑仍由映射與計算規則決定。

- [view_concept_graph.cypher](view_concept_graph.cypher)：Neo4j Browser 展示完整概念圖。
- [view_customer_graph.cypher](view_customer_graph.cypher)：產品、指標與客戶。
- [01_list_concepts.cypher](01_list_concepts.cypher)：15 筆產品，輸出 productCode、productName、aumDefinition、incomeDefinition、aumMetrics、incomeMetrics。指標僅 metricCode、name、definition。
- [lookup_customer_dimension.cypher](lookup_customer_dimension.cypher)：以新版 metricCode 直接查客戶概念。
- [full_concept_graph_with_customer.cypher](full_concept_graph_with_customer.cypher)：完整投影與 29 條衡量路徑，包含關係 definition。
- [02_lookup_mapping.cypher](02_lookup_mapping.cypher)：以 productCode、domain 查原映射圖，投影維持原樣。

映射圖、SQL status、日期選取、收入符號與來源規則保持原狀。本次移除狀態欄位僅限 PBConcept 節點。

## 本次執行與證據

migrate_relations_20261009.py 先核對前一版 28／52 圖譜，再於單一交易更新關係。28 個節點的 ID／標籤／屬性全部保留，39 條原有關係保留 ID 並加入 definition。Neo4j 關係類型不能原地改名，因此 12 條客戶關係以新類型重建、保留端點與方向；另移除 1 條 pending。映射圖完整摘要更新前後一致，跨圖關係為 0。概念查詢、客戶查詢及已保存 n8n Query 的 Aura 唯讀驗證通過。

- [關係更新紀錄](../../deliverables/concept_relations/20261009/更新紀錄.md)
- [關係更新驗證](../../deliverables/concept_relations/20261009/validation.applied.json)
- [n8n Query 相容性](../../deliverables/concept_relations/20261009/query_validation.json)
- [關係更新前備份](../../deliverables/concept_relations/20261009/live_before.json)
- [關係更新後快照](../../deliverables/concept_relations/20261009/live_after.json)

下列為稍早節點定義更新的歷史紀錄：migrate_definitions_20261009.py 當時於單一交易更新既有 28 個節點，保留當時全部 52 條關係。此歷史遷移不適用於目前關係版本。

- [更新紀錄](../../deliverables/concept_update/20261009/更新紀錄.md)
- [本次驗證](../../deliverables/concept_update/20261009/validation.json)
- [線上更新前備份](../../deliverables/concept_update/20261009/live_before.json)
- [線上更新後快照](../../deliverables/concept_update/20261009/live_after.json)
- [產品查詢實測輸出](01_output.json)
- [完整概念實測輸出](customer_graph.output.json)

本地來源更新前備份位於 deliverables/concept_update/20261009/local_before。本目錄原 validation.json、validation.before_customer.json 與 concept_graph.before_customer.json 是早期匯入／客戶新增的歷史證據；新版請讀本次更新目錄的驗證報告。

## 建立與一般匯入

business_dictionary.json 保存節點定義，relationship_dictionary.json 保存關係定義，build_concepts.py 依此建立 concept_graph.json。import_concepts.py 採用新版欄位、51 條關係及 definition，允許兩側定義留白；一般匯入只接受既有圖與計畫相符的狀態。未來變更已有節點的代碼／定義或關係類型時需明確遷移，避免直接 MERGE 造成重複。

```powershell
python -X utf8 ontology\independent_concepts\build_concepts.py
python -X utf8 ontology\independent_concepts\import_concepts.py --credentials "$env:USERPROFILE\Downloads\Neo4j-4bb479b2-Created-2026-10-06.txt" --check-only
```

憑證只於執行時讀取，不寫入輸出。沒有建立資料庫或執行個體，沒有刪除節點，也沒有修改映射圖。

## n8n 現況

本地 01_request.json、n8n_01_prepare.js、n8n_01_project_output.js 採用新版概念欄位，第二段映射範本保留原樣。test_n8n_guards.cjs 使用實際 Aura 輸出驗證欄位、30 組產品／側別及非法輸入。這些是本地範本；概念圖更新時沒有修改 n8n。使用者後續已授權更新 n8n 的概念查詢，紀錄如下。

2026-10-09 後續已在 n8n 保存新版概念 Query、候選說明與依側別輸出定義，含 Customer key／基本屬性，未發布。Query 與候選準備已實際測試；詳見 [n8n 更新紀錄](../../deliverables/n8n_concept_query/20261009/更新紀錄.md)。映射層指標代碼維持原值；目前仍由 productCode 跨層對照，映射 query 沒有更動。

再後續的關係更新不需修改 n8n 工作流程：已保存 Query 以 properties(r) 讀取全部概念關係，直接對 Aura 核對得到 28 節點／51 關係／29 路徑與全部關係 definition；已保存候選準備程式的本地相容性驗證通過。此次未在 n8n 執行流程、呼叫 Jev 或發布。

標籤與固定投影不構成資料庫權限隔離；原有受控查詢、參數流程、使用者權限及 n8n 接線設計維持原狀。
