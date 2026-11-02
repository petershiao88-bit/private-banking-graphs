# legacy：不再維護的舊檔案

這裡的東西**不參與**目前的建置、測試與發佈，只留作歷史查閱。程式可能引用舊路徑，不能直接執行。

| 位置 | 內容 |
|---|---|
| `archive/` | v0.3.0～v0.16.0 各輪模型快照與 PG 修訂紀錄（`department-pg/history/`）。`tests/pg` 的保存性測試仍以這裡的快照作比對基準，**不可修改** |
| `ontology-v0.16/` | v0.16.0 拆模組前的 5 份 TTL、`build-config.json`、`catalog-v001.xml` 原檔 |
| `tools/` | 舊的建置與審閱工具（`build_ontology.py` 已由 `python -m ontology_kit build` 取代） |
| `tests/test_ontology_v016.py` | v0.16.0 結構的本體測試；新版是 `tests/ontology/test_modules.py` |
| `semantica-poc/` | 舊的 Semantica 圖譜瀏覽與 Agent 交接（SHACL）示範。OpenRouter 的 LLM 問答已移除，其餘無法單獨執行 |
| `docs/` | v0.16.0 的專案 README 與交接文件 |
| `MIGRATION-20261031.log` | 2026-10-31 結構重整的逐項紀錄（搬移、刪除、修補） |

2026-10-31 結構重整時刪除、未保留的東西：Microsoft Fabric 匯出（`outputs/`、`FABRIC-GRAPH.md` 與對應工具和測試）、semantica-poc 的 OpenRouter LLM 問答。
