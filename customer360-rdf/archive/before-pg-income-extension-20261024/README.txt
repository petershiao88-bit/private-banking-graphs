客戶360 RDF／OWL 與部門 PG v0.15.0，2026-10-24，設計草案。
最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
六類先統一金融商品，FinancialService 與服務專屬關係已移除。
金控共通指標為 AUM、LUM、手收、利收，均繼承 Metric。
規劃型信託／保管各有 AUM、手收；外匯／開狀／黃金只保留手收；放款有 LUM、利收。
手收／利收採來源 SQL 的業務分類；PG 保留兌換／TMU／黃金損益與放款毛利來源性質。
本批九項指標共85個必要元素，全部pending／null、候選為空，只有指標到底表。
私銀為使用／定義部門，資料權責部門待定；五項手收歸理專，實際員編映射待定。
股票設質AUM已退出active，估值證據另存history，不轉作LUM；原台股庫存AUM保持。
股票設質LUM、台股手收缺來源先不放；集合管理手收仍待業務定義。
目前18項AUM、1項LUM、19項手收、1項利收，共39項指標、49個SourceTable。
RDF：41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples。
PG：46概念、611 metadata節點、1245關係。RDF19＋PG78＝97項測試通過，無略過。
修改前快照：archive/before-v0.15.0/。24份來源SQL／Excel雜湊未變。
無Git提交、來源SQL執行或Neo4j部署；欄位映射、公式、權限、帳戶、畫圖維持暫緩。
