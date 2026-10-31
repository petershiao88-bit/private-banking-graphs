# 私銀部門 PG metadata v0.16.0

本輪完成「部門 → 私銀部門類型 → 私銀採用指標」。共通語意與完整操作見 [專案 README](../README.md)，來源見 [底表清單](METRIC-TABLE-SOURCES.md)。修改前備份 ../archive/before-department-v0.16.0。

## 部門模組

departments.json 是第八份 active JSON，department_model.py 作 executable schema。定義一個 BusinessConcept：bank.private_banking（私銀），參照 bank:PrivateBankingDepartment；後者在 RDF 繼承 fh:Department。fh:department 原治理註記保持。

私銀透過 USES_METRIC 採用42項現有指標，對應 RDF fh:usesMetric（Department → Metric）。同模組用一個 BusinessRelationDefinition 保存共通採用關係；HAS_PARENT_CLASS_REFERENCE 鏡射 RDF 部門父類，HAS_DOMAIN_CLASS／HAS_RANGE_CLASS 保存新關係的共通參照。皆為 metadata，沒有組織／客戶／交易實例或 PG 推論。

所有42項指標顯示名稱加「私銀－」，銀行／證券來源保留，ID與其他內容不變。通用手收也納入，仍維持原 partial_scope；商品、人員、通聯概念不改名。不拆私銀一部／二部或新增目標／彙總指標。

部門的 subsidiary=bank 只描述部門所在子公司；證券來源指標仍 subsidiary=securities。採用不決定資料權責或理專歸屬，department_owner／source_data_owner 待定。指標仍透過原關係接到底表，部門不直接接底表。

## 模組與建置

八份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments。各以 schema／Python 驗證器檢查，再由 build_cypher.py 合併。既有 render_cypher 聯絡資訊 API 保留；build_combined_graph／render_combined_cypher 新增尾端可選 department_model 參數，舊呼叫保持可用。

42項指標：18 AUM、1 LUM、21手收、2利收；50 BusinessConcept、658節點、1388關係。含413 DataFieldDefinition、52 SourceTable、61 BusinessRelationDefinition、7 MetadataModule、7 MappingSlot。42 USES_METRIC；88 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE 保持。

bank-business-metrics 的12項、115個空欄位定義保持；其他舊候選也保持。所有 execution=null；工具負責 SQL 執行與計算，Tool 綁定尚未完成。history／drafts／outputs 不參與建置，不重跑歷史 seeder。

## 測試與待辦

PG92＋RDF19＝111項測試通過，無略過。test_departments.py 檢查精確 RDF 新增、舊 JSON 僅改版本／名稱、全部採用與來源可達、子公司／權責／理專分離、錯誤目標反例、確定性與來源雜湊。舊測試的歷史路徑保持，review_contract_v016.py 僅正規化核定顯示名稱與 RDF 新增主詞；其餘語意不忽略。

三項 pending 保持：股票設質 LUM、台股手收缺來源，集合管理手收 CASE 遮蔽。總 AUM／總收入／目標比較、客戶數／分群、放款額度／人數與 ROA／ROBA 尚未新增。權限、帳戶、分行／數位、畫圖與欄位映射仍暫緩。

部門異動見 history/department-v0.16.0.json；前輪收入擴充與股票設質退場等 history 原文保持。產生的 Cypher 只 MERGE，沒有部署／自動遷移或刪除舊資料。
