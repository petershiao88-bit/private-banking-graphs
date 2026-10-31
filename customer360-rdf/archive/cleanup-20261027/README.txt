客戶360 RDF／OWL v0.16.0；PG修訂securities-summary-20261024，2026-10-24。
PG新增私銀－證券總AUM、總手收，涵蓋5項AUM／4項手收，排除股票設質估值與缺來源台股手收。
「總」只代表目前已納入私銀的證券商品範圍，不宣稱全部業務。
新增9條HAS_COMPONENT_METRIC，來源沿分項追溯；不另造底表、不新增總指標直接到底表連線。
私銀採用44項指標：19AUM、1LUM、22手收、2利收；原42項及欄位候選完整保持。
RDF逐位元組未變：43Class、9Object Property、19Data Property、5Annotation Property、434triples。
PG：52概念、668節點、1415關係、420DataFieldDefinition、52SourceTable、44USES_METRIC。
兩項總指標calculation_status=pending_tool_definition，7個結果欄位為空映射、execution全null。
AUM月底口徑、股票設質分支混標、手收跨次月及UNION去重等疑點保留，計算由Tool承接。
RDF19＋PG101＝120項測試通過，無略過；24份來源SQL／Excel雜湊未變。
備份archive/before-securities-summary-20261024；修訂紀錄department-pg/history/securities-summary-20261024.json。
完整說明README.md；固定交接HANDOFF-ZED-RDF-PG-20261022.md；底表清單department-pg/METRIC-TABLE-SOURCES.md。
未執行來源SQL、資料庫查核、Neo4j部署或Git提交；三項pending及其他暫緩範圍保持。
