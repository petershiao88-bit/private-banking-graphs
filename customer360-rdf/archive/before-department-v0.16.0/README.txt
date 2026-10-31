客戶360 RDF／OWL v0.15.0；PG 修訂 pg-income-extension-20261024。
最新說明 README.md；固定交接 HANDOFF-ZED-RDF-PG-20261022.md。
本輪只修改 PG：新增存款利收、債券信託手收、債券自營手收，擴充 DCI 及保險手收。
RDF 五份來源、輸出、版本與 catalog 均逐位元組保持。
DCI 補 DCD／TMU；保險補兩項 PS 月檔，保留客戶貢獻度性質。
依 SQL 作業務字典；圖譜記語意與來源，計算由 Tool 承接，Tool 綁定未實作。
新欄位映射 pending／null、候選空白；既有候選保留，execution 全 null。
42 項指標：18 AUM、1 LUM、21 手收、2 利收；52 張 SourceTable。
PG：49 業務概念、652 metadata 節點、1338 關係、413 DataFieldDefinition。
RDF：41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples。
RDF19＋PG85＝104項測試通過，無略過；24份來源SQL／Excel雜湊未變。
備份 archive/before-pg-income-extension-20261024；修訂紀錄 department-pg/history/pg-income-extension-20261024.json。
股票設質LUM、台股手收缺來源先不放；集合管理手收 CASE 遮蔽維持 pending，原台股與集合AUM保留。
外匯／開狀／黃金只保留手收；放款有LUM與利收，沒有放款AUM。
無Git提交、來源SQL執行或Neo4j部署；權限、帳戶、畫圖與欄位映射繼續暫緩。
