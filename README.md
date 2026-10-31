# 私銀 PG 與客戶360 RDF 圖譜

整理日期：2026-10-31。本儲存庫彙整兩個獨立專案的圖譜檔案，保留來源目錄結構，未將兩套模型合併或改寫。原工作區檔案保留。

| 資料夾 | 內容與入口 |
|---|---|
| [private-banking-pg/](private-banking-pg/) | 私銀 AUM／Income 概念、映射與 SQL 血緣 PG；[模型說明](private-banking-pg/ontology/NEO4J_README.md)、[獨立概念圖](private-banking-pg/ontology/independent_concepts/README.md) |
| [customer360-rdf/](customer360-rdf/README.md) | 客戶360 RDF／OWL v0.16.0，含來源 TTL、合併本體、工具、測試、展示與歷史版本 |
| [customer360-rdf/department-pg/](customer360-rdf/department-pg/README.md) | 客戶360 對應的私銀部門 PG；[44 項指標與來源表](customer360-rdf/department-pg/METRIC-TABLE-SOURCES.md) |
| [reference/](reference/) | 金控自然人客戶360需求／欄位盤點 Excel |
| [FILE_MANIFEST.json](FILE_MANIFEST.json) | 每個來源檔的相對位置、大小與 SHA-256 |

## 使用順序

1. 私銀 PG：先閱讀 `private-banking-pg/ontology/` 的模型說明。`ontology/aura_migration/` 保留舊版移轉快照；最新本機重建使用 `local_graph/import_snapshot.py` 指定的兩個來源快照，請勿將兩者版本混用。
2. 客戶360 RDF：先閱讀 `customer360-rdf/README.md`；完整本體為 `customer360-ontology.ttl` 與 `.owl`，來源由 `build-config.json` 管理。
3. 私銀指標：閱讀 `customer360-rdf/department-pg/METRIC-TABLE-SOURCES.md`。兩套 PG 目前獨立，不代表已完成跨模型整合。

## 收錄範圍

私銀專案收錄 `ontology/`、`sources/`、`local_graph/`、`docs/`，以及 `deliverables/graph_exports/`、`deliverables/concept_update/`、`deliverables/local_graph/`。原專案 README 與交接文件保留原文，其中部分問答流程、實驗或其他交付檔的連結不在此次圖譜整理範圍。

客戶360 收錄 RDF 專案、部門 PG、測試、工具、展示及 archive。排除虛擬環境、下載的 vendor 套件、執行期設定、日誌、快取與 ZIP 重複封裝；依原專案文件安裝依賴。Semantica 的 vendor 套件未隨附。

本次整理不連線修改 Neo4j，也未執行匯入。模型包含業務定義與技術血緣；各檔所標示的草稿、待核定、尚未驗證與版本狀態仍然有效。
