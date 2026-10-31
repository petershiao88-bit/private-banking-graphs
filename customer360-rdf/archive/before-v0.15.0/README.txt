客戶360 RDF／OWL 與部門 PG v0.14.0，2026-10-24，設計草案。
最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
本批補齊私銀六類：規劃型信託、信託保管、外匯、開狀、黃金、放款，共八項指標。
規劃型信託與保管各有 AUM／手收，開狀為手收，外匯／黃金為交易損益，放款為來源業務收益口徑的利收。
金融服務獨立於金融商品；損益與放款利收參照一般 Metric，避免推成手續費或 AUM。
新67個欄位全pending／null、候選為空，只有指標到底表，未加入執行公式。
證券原六項AUM與四項手收保持；台股手收缺底表，暫不建立active指標。
股票設質AUM已完成，不是借款／可融資額，與庫存的重疊仍待定。
集合管理手收、海外債券收入、存款利收、DCI TMU與保險月檔貢獻度等仍未擴充。
目前19項AUM、17項手收、3項其他收益／損益；來源清單見department-pg/METRIC-TABLE-SOURCES.md。
RDF五份來源：38 Class、8 Object Property、16 Data Property、5 Annotation Property、382 triples。
PG七份active JSON：46概念、589 metadata節點、1197關係、48個來源表。
RDF19＋PG75＝94項測試通過，無略過。修改前快照：archive/before-v0.14.0/。
未執行來源SQL、完整OWL推論或Neo4j部署；權限、帳戶、欄位映射與畫圖暫緩。
