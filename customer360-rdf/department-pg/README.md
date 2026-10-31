# 最新 PG 檔案入口

先看 [44 項指標與來源表](METRIC-TABLE-SOURCES.md)，再依名稱開啟對應的九份業務 JSON。model.json 僅含通聯；model.cypher 是九份 JSON 的合併輸出。
測試與比對輔助程式已移至 ../tests/pg/；舊修訂紀錄與未採用草稿移至 ../archive/department-pg/。本資料夾保留有效模型、schema 與建置／驗證程式。

從專案根目錄執行測試：`.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests/pg -v`。

# 私銀部門 PG metadata v0.16.0

## 本輪：證券總指標涵蓋範圍（securities-summary-20261024）

使用者確認後完成本機 PG 實作。RDF 與 ontology_version 保持 v0.16.0，五份 RDF、Turtle／OWL、build-config、catalog 均逐位元組未變。原七份指標／通聯 JSON 逐位元組保持；departments.json 僅在原42項採用清單加入下列兩項。

| PG ID／名稱 | 沿用類別 | 涵蓋分項 |
|---|---|---|
| securities.total_aum／私銀－證券總 AUM | SecuritiesAUM | 複委託債券、結構型、基金、外國股票、台股5項 AUM |
| securities.total_fee_income／私銀－證券總手收 | SecuritiesFeeIncome | 複委託債券、結構型、基金、外國股票4項手收 |

新增 securities-summary-metrics.json 及 securities_summary_model.py（第九份 active JSON）。9條 HAS_COMPONENT_METRIC 是 PG 分項涵蓋 metadata，不新增 RDF Property，也不代表可直接 SUM。總指標的 lineage_mode=via_component_metrics、coverage_status=included_products_only、calculation_status=pending_tool_definition。

總指標經分項追溯既有金額／估值／日期來源；沒有另造 SourceTable 或新增總指標到底表的直接連線。原分項仍各自保留，總指標與其分項不得再次一起加總。「總」僅代表目前納入私銀模型的證券商品範圍，不宣稱證券公司全部業務。

兩項總指標只有7個結果元素：AUM為amount／currency／aumAsOfDate，手收為amount／currency／incomePeriodStart／End。均pending、table／column=null、candidates=[]，不帶入分項估值數量／單價、單一客戶或商品識別；execution全null，沒有新增Tool綁定、理專關係或可執行計算。

總 AUM 排除股票設質。舊SQL把AUM_027與AUM_028同標證券／台股，不能只篩COMP／PROD取本輪總額，須保留來源分支血緣。AUM_TMP02／AUM_REPORT完整產製邏輯未提供，字典「各分類月內最新日期」仍屬draft_metric_query，不當正式月底或同日口徑。

總手收先不含缺來源的台股手收；外國股票保留淨手收、月底最後兩工作天移至次月及UNION投影去重觀察。來源日曆、基金current取債券日期、外股current AM仍讀AM_SEC_M、私銀客戶歸屬連接等疑點不改寫。

新備份 archive/before-securities-summary-20261024；修訂與來源SHA-256見 ../archive/department-pg/history/securities-summary-20261024.json。本輪沒有執行來源SQL、資料庫查核、Git提交或Neo4j部署。

本輪完成「部門 → 私銀部門類型 → 私銀採用指標」。共通語意與完整操作見 [專案 README](../README.md)，來源見 [底表清單](METRIC-TABLE-SOURCES.md)。修改前備份 ../archive/before-department-v0.16.0。

## 部門模組

departments.json 是第八份 active JSON，department_model.py 作 executable schema。定義一個 BusinessConcept：bank.private_banking（私銀），參照 bank:PrivateBankingDepartment；後者在 RDF 繼承 fh:Department。fh:department 原治理註記保持。

私銀透過 USES_METRIC 採用44項指標，對應 RDF fh:usesMetric（Department → Metric）。同模組用一個 BusinessRelationDefinition 保存共通採用關係；HAS_PARENT_CLASS_REFERENCE 鏡射 RDF 部門父類，HAS_DOMAIN_CLASS／HAS_RANGE_CLASS 保存新關係的共通參照。皆為 metadata，沒有組織／客戶／交易實例或 PG 推論。

原42項指標顯示名稱的「私銀－」前綴及銀行／證券來源保留，ID與其他內容不變；兩項新總指標採同樣命名。通用手收也納入，仍維持原 partial_scope；商品、人員、通聯概念不改名。不拆私銀一部／二部，不新增目標比較；證券兩項總指標只增加涵蓋定義。

部門的 subsidiary=bank 只描述部門所在子公司；證券來源指標仍 subsidiary=securities。採用不決定資料權責或理專歸屬，department_owner／source_data_owner 待定。指標仍透過原關係接到底表，部門不直接接底表。

## 模組與建置

九份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments、securities-summary-metrics。各以 schema／Python 驗證器檢查，再由 build_cypher.py 合併。既有 render_cypher 聯絡資訊 API 保留；build_combined_graph／render_combined_cypher 提供尾端可選 department_model、summary_model 參數，舊呼叫保持可用。

44項指標：19 AUM、1 LUM、22手收、2利收；52 BusinessConcept、668節點、1415關係。含420 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、8 MetadataModule、7 MappingSlot。44 USES_METRIC；88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE 保持。

bank-business-metrics 的12項、115個空欄位定義保持；其他舊候選也保持。所有 execution=null；工具負責 SQL 執行與計算，Tool 綁定尚未完成。history／drafts／outputs 不參與建置，不重跑歷史 seeder。

## 測試與待辦

PG101＋RDF19＝120項測試通過，無略過。test_departments.py 檢查精確 RDF 新增、舊 JSON 僅改版本／名稱、全部採用與來源可達、子公司／權責／理專分離、錯誤目標反例、確定性與來源雜湊。舊測試的歷史路徑保持，review_contract_v016.py 僅正規化核定顯示名稱與 RDF 新增主詞；其餘語意不忽略。

三項 pending 保持：股票設質 LUM、台股手收缺來源，集合管理手收 CASE 遮蔽。銀行總 AUM／總收入／目標比較、客戶數／分群、放款額度／人數與 ROA／ROBA 尚未新增。權限、帳戶、分行／數位、畫圖與欄位映射仍暫緩。

部門異動見 ../archive/department-pg/history/department-v0.16.0.json；前輪收入擴充與股票設質退場等 history 原文保持。產生的 Cypher 只 MERGE，沒有部署／自動遷移或刪除舊資料。

## 本輪總指標驗證與查閱

test_securities_summary.py 直接驗證兩項／九條精確涵蓋、RDF逐位元組未變、原七份JSON與歷史不變、部門只新增兩個採用ID、既有節點／關係保存、七個空映射、SQL證據／草稿狀態、原來源角色、錯誤範圍／公式反例及產出確定性。底表清單把兩項總指標標成「沿分項追溯」；同一表在不同分項可同時作金額來源及日期查詢，分角色呈現。

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(t:BusinessConcept)
MATCH (t)-[:HAS_COMPONENT_METRIC]->(c:BusinessConcept)
OPTIONAL MATCH (c)-[:HAS_SOURCE_TABLE|USES_VALUATION_SOURCE|USES_DATE_LOOKUP_SOURCE]->(s:SourceTable)
RETURN d, t, c, s;
```

此查詢供未來已載入metadata的Neo4j Browser查閱，本輪未執行。HAS_COMPONENT_METRIC只表涵蓋，不是可執行SUM、正式RDF繼承或資料實例。產生器只MERGE，沒有部署／刪舊資料或自動遷移。銀行總量及目標比較繼續暫緩。
