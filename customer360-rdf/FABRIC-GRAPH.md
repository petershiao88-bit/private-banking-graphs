# 客戶360 RDF＋PG 的 Microsoft Fabric 圖譜

目前為**本機匯入包，尚未部署 Fabric**。原始 RDF v0.16.0、PG、來源 SQL 與欄位映射均未改動。

使用 Fabric 原生 **Graph model**，以 OneLake Delta tables 承接 RDF schema 與 PG metadata，再用 Graph 的互動圖與 GQL 檢視。這是視覺化投影；不執行 OWL 推論、不載入客戶或金額實例，也不執行業務 SQL。SQL 計算與 Tool 綁定繼續由 Tool 負責。

## 匯入包

在專案根目錄執行：

```powershell
.venv/Scripts/python.exe -X utf8 -B tools/export_fabric_graph.py
```

輸出到 `outputs/fabric-v0.16.0/`：

- `Customer360-Fabric-Import.ipynb`：內含目前快照的完整資料與轉換函式，可直接匯入 Fabric，不需要另傳 JSON。
- `fabric-bundle.json`、`nodes.jsonl`、`edges.jsonl`、`rdf_triples.jsonl`：可檢查的資料。
- `graph-model-template/`：Fabric 公開定義格式；Delta 路徑由 Notebook 在指定 Lakehouse 建表後代入，不能直接提交含占位符的範本。
- `queries/`：六種 GQL 檢視，先看私銀與證券，再看總指標分項、來源與 RDF 階層。
- `customer360-ontology.ttl`、`.owl`：原輸出的逐位元組副本。
- `manifest.json`：數量、來源 SHA-256、快照雜湊與本機準備狀態。

## Fabric 操作

1. 在已有合適 capacity、支援 Graph 的區域與建立權限的工作區，新增獨立 Lakehouse，例如 `Customer360Graph`。
2. 匯入 Notebook，將該 Lakehouse 設成預設 Lakehouse；使用 PySpark runtime。
3. 將 Notebook 第一個程式儲存格的 `WORKSPACE_ID`、`LAKEHOUSE_ID` 設成實際 UUID。Notebook 會驗證目前工作區、預設 Lakehouse 及其工作區相符。
4. 執行到建表儲存格。採用版本＋內容雜湊命名的新表，不覆蓋既有資料；相同快照可以接續，既有同名表內容不同則在寫入前停止。
5. 核對目標後將 `CREATE_GRAPH_MODEL = True`，重跑設定儲存格與最後建立儲存格。這個動作只新增具快照名稱的 Graph model，不更新或刪除既有 model。同名 model 已存在則停止，請直接開啟。
6. 等 Graph model 建立及來源同步完成，在 Graph 的 Query 模式執行 `queries/01-private-securities.gql`，結果切換 Diagram。設定顯示名稱欄位為 `display_name`；保存 queryset 作為日後入口。若 POST 回傳 202，只代表受理，仍需回到 Fabric 核對完成狀態。

尚未在真實 Fabric capacity 執行 Spark、Graph REST API 或 GQL；本機驗證不能替代雲端同步與互動檢視驗收。若租戶未開放 Graph 或該區域不支援，需先確認環境，不自行開啟付費容量或建立試用。

## 投影規則

- PG 原有每個 node ID、edge ID、關係型別完整保留。原節點 properties 放在 `properties_json`，其中 null／pending／evidence 也保留。
- `Department`、`Metric` 是展示分類，來自現有部門定義與 `USES_METRIC` 範圍，沒有新增業務認定；原 PG label 另存 `pg_label`。
- RDF 宣告的 Class／ObjectProperty／DataProperty／AnnotationProperty，以原 URI 與 PG 的 ontology reference 合併。
- `RDF_SUBCLASS_OF`、`RDF_DOMAIN`、`RDF_RANGE` 是原始 schema 宣告。`RDF_DECLARED_*` 只是 domain／range 的直接視覺化箭頭，`semantic_status=domain_range_visual_projection`，**不是實例間的屬性事實**。
- 所有 RDF triples 另存 audit 表，包含 literal 的 datatype 與 language。完整原始 TTL／OWL 也保留；Graph 投影本身不宣稱提供完整 OWL 語意。
- 不把 SQL 檔案當可執行查詢、不補實體欄位映射。所有 `observed_in_files`、`database_verified=false`、待確認語意與來源角色保留。
- 指標總額與分項只呈現關係，不執行加總；缺來源的股票設質 LUM、台股手收、集合管理手收不變成有效指標。
- 欄位定義仍完整匯入，預設查詢以部門、證券指標與來源為主，不一次展開 420 個欄位。

實體 Delta 表依節點型別與「關係型別＋起訖型別」分開，以符合 Fabric 公開 JSON Schema，不依賴文件例子中未納入 Schema 的 `filter`。另建三張完整 audit 表，不列為圖譜資料來源。

`dataSources` 1.1.0 採 Lakehouse item reference ＋相對 `Tables/...` 路徑；Notebook 由實際 Delta location 擷取相對路徑。官方說明頁的部分例子仍用絕對路徑，匯入包依目前公布的 Schema 產製。`validation/schema-validation.json` 記錄結構檢查範圍：官方 `graphIndex/common/identifiers/1.0.0/schema.json` 目前回傳 404，因此只有可取得的結構條件通過檢查，名稱約束尚未獲完整官方驗證，須以 Fabric 實際建立結果確認。

## 官方參考

- [Graph 概覽與可用環境](https://learn.microsoft.com/en-us/fabric/graph/overview)
- [建立 Graph model](https://learn.microsoft.com/en-us/fabric/graph/tutorial-create-graph)
- [Graph model 定義格式](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/graph-model-definition)
- [建立 Graph model REST API](https://learn.microsoft.com/en-us/rest/api/fabric/graphmodel/items/create-graph-model)
- [GQL 語言](https://learn.microsoft.com/en-us/fabric/graph/gql-language-guide)
- [Notebook runtime context](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-runtime)
- [Notebook credentials](https://learn.microsoft.com/en-us/fabric/data-engineering/notebookutils/notebookutils-credentials)

獨立的 Fabric Ontology 也能匯入部分 RDF／OWL schema，但此任務採用 Graph model 串接 PG metadata。未把 Graph 當成 OWL reasoner，也沒有額外建立或修改 Fabric Ontology。
