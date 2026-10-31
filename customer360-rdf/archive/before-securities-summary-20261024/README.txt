客戶360 RDF／OWL＋私銀部門PG v0.16.0，2026-10-24。
金控新增Department、usesMetric；銀行新增PrivateBankingDepartment類型。
PG新增私銀bank.private_banking，採用42項既有指標；顯示名稱加私銀並保留銀行／證券來源，ID不變。
採用不決定承作子公司、資料權責、理專歸屬、權限或自動加總。
42項指標：18AUM、1LUM、21手收、2利收；來源、候選與計算口徑保持。
RDF：43Class、9Object Property、19Data Property、5Annotation Property、434triples。
PG：50概念、658節點、1388關係、413DataFieldDefinition、52SourceTable、42USES_METRIC。
RDF19＋PG92＝111項測試通過，無略過；24份來源SQL／Excel雜湊未變。
修改前備份archive/before-department-v0.16.0；修訂紀錄department-pg/history/department-v0.16.0.json。
README.md為完整說明，固定交接HANDOFF-ZED-RDF-PG-20261022.md，底表清單department-pg/METRIC-TABLE-SOURCES.md。
總量／目標比較留待下一輪；三項pending與原有暫緩範圍保持。
Tool負責SQL與計算，綁定尚未完成；未執行來源SQL、部署Neo4j或Git提交。
