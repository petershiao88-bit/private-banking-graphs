# 客戶 360 工作區

本目錄集中客戶 360 的需求來源、RDF／OWL 模型與既有展示工具。各子專案目前彼此獨立，不應假設已完成整合。

## 目錄

| 位置 | 用途 | 狀態 |
|---|---|---|
| `金控自然人客戶360.xlsx` | 186 個需求／欄位盤點項目的參考清單 | 唯讀參考；不是客戶實例資料 |
| `customer360-rdf-owl/` | 客戶 360 RDF／OWL v0.4.0 與部門 PG 通聯／存款映射模型 | 目前主要工作入口 |
| `asset-financial-ontology/` | 既有資產財力本體視覺化與文件 | 獨立 PoC，尚未與目前 RDF／OWL 整合 |
| `AGENTS.md` | 本目錄及子目錄的工作規則 | 修改前必讀 |

## RDF／OWL 接續入口

依序閱讀：

1. `AGENTS.md`
2. `customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md`
3. `customer360-rdf-owl/README.md`
4. `customer360-rdf-owl/holding-core.ttl`、`bank-deposit.ttl` 與 `department-pg/README.md`

不要因檔名或主題相近，直接把 `asset-financial-ontology/` 的概念併入 RDF／OWL；整合前需逐項確認業務定義與治理層級。
