# AUM 業務圖譜（Neo4j）

本機 Neo4j `neo4j` 資料庫已匯入 `AUM Ontology.json` 的技術證據層，
並以 `AUM_business_dictionary.json` 建立業務概念層。開啟
<http://127.0.0.1:7474/browser/>，以 `neo4j` 登入。

業務字典是根據現有 staging SQL、月底總額查詢草稿與 JSON 推論的討論稿。
它描述**現行計算邏輯**，不是已核定的業務制度。

## 圖譜結構

- `(:BusinessMetric)-[:HAS_COMPONENT]->(:BusinessMetric)`：總 AUM → 存款／投資 → 銀行／證券。
- `(:BusinessMetric)-[:INCLUDES_PRODUCT]->(:ProductCategory)`：13 個產品分類。
- `(:ProductCategory)-[:IMPLEMENTED_BY]->(:StagingOutput)`：產品對應的 staging 輸出。
- `(:StagingOutput)-[:DEPENDS_ON]->(:StagingOutput)`：31 個 staging 輸出的依賴。
- `(:StagingOutput)-[:DESCRIBED_BY]->(:Term)`：連回 JSON 的 62 個術語。
- `(:StagingOutput)-[:READS_FROM]->(:PhysicalTable)`：SQL 的來源資料表。
- `(:Term)-[:HAS_SOURCE_PROPERTY]->(:SourceProperty)-[:REFERS_TO_COLUMN]->(:PhysicalColumn)`：欄位血緣。
- `(:BusinessMetric)-[:USES_CALCULATION_RULE]->(:CalculationRule)`：月底最新日期與加總規則。

`AUM_028` 是「股票設質申請估值」staging 輸出，依現有 SQL 與 `AUM_027`
一起歸入「投資／證券／台股」，沒有負數處理。其 `overlapRisk=true` 表示
與一般台股可能重複，尚未經實際資料核對。`AUM_012` 的計價基礎為
`AMT_INVEST`（原始投資金額）。

原 JSON 的 `aliases` 保留在 `Term` 屬性及 `sourceJson`，但不再轉成
`HAS_ALIAS` 業務同義詞關係，因為其中混有面額、匯率等計價因子。
圖譜只含定義和血緣，沒有實際客戶 AUM 紀錄。

## 可直接貼入 Neo4j Browser 的查詢

**1. 查看整張業務主幹：**

```cypher
MATCH p=(root:BusinessMetric {key: 'aum:metric:aum_total_month_end'})
  -[:HAS_COMPONENT*0..3]->(m:BusinessMetric)
OPTIONAL MATCH q=(m)-[:INCLUDES_PRODUCT]->(product:ProductCategory)
RETURN p, q;
```

**2. 查看保險與兩條台股來源如何接回總 AUM：**

```cypher
MATCH p=(root:BusinessMetric {key: 'aum:metric:aum_total_month_end'})
  -[:HAS_COMPONENT*1..3]->(:BusinessMetric)
  -[:INCLUDES_PRODUCT]->(:ProductCategory)
  -[:IMPLEMENTED_BY]->(s:StagingOutput)
WHERE s.outputObject IN ['AUM_012', 'AUM_027', 'AUM_028']
RETURN p;
```

**3. 追溯台股來源到 JSON 術語與資料表：**

```cypher
MATCH p=(product:ProductCategory {code: 'securities_taiwan_stock'})
  -[:IMPLEMENTED_BY]->(s:StagingOutput)
  -[:DESCRIBED_BY]->(t:Term)
  -[:HAS_SOURCE_PROPERTY]->(sp:SourceProperty)
  -[:REFERS_TO_COLUMN]->(col:PhysicalColumn)
RETURN p LIMIT 30;
```

**4. 查看目前的月底取日與加總規則：**

```cypher
MATCH (m:BusinessMetric {code: 'aum_total_month_end'})
  -[:USES_CALCULATION_RULE]->(r:CalculationRule)
RETURN r.name AS rule, r.description AS explanation, r.status AS status;
```

## 更新資料後重新匯入

使用 Python 3 與既有 Neo4j 即可；匯入程式只用標準函式庫與 Neo4j Query API。
從工作區根目錄執行：

```powershell
$env:NEO4J_PASSWORD = '<your Neo4j password>'
python 'ontology\import_ontology_neo4j.py' 'ontology\AUM Ontology.json'
python 'ontology\import_aum_business_graph.py'
Remove-Item Env:\NEO4J_PASSWORD
```

兩個匯入程式都以穩定鍵合併；同樣的輸入重跑不會新增重複節點。
若日後從字典刪除產品或規則，舊節點不會自動刪除，需另行核對後清理。
