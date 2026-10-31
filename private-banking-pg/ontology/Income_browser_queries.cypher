// 1. 業務主幹（集合管理帳戶是DECLARED概念）
MATCH p=(root:BusinessMetric {key:'income:metric:income_total_customer_month'})
  -[:HAS_COMPONENT*0..3]->(m:BusinessMetric)
OPTIONAL MATCH q=(m)-[:INCLUDES_PRODUCT|DECLARES_PRODUCT]->(product:ProductCategory)
RETURN p,q;

// 2. 三條保險來源如何接回總收入
MATCH p=(:BusinessMetric {key:'income:metric:income_total_customer_month'})
  -[:HAS_COMPONENT*1..3]->(:BusinessMetric)
  -[:INCLUDES_PRODUCT]->(:ProductCategory {code:'bank_insurance'})
  -[:IMPLEMENTED_BY]->(s:StagingOutput)
RETURN p;

// 3. 保險技術追溯：JSON術語與來源欄位
MATCH p=(:ProductCategory {key:'income:product:bank_insurance'})
  -[:IMPLEMENTED_BY]->(:StagingOutput)
  -[:DESCRIBED_BY]->(:Term)
  -[:USES_SOURCE_COLUMN]->(:PhysicalColumn)
RETURN p;

// 4. 待確認或與metadata有差異的規則
MATCH (r:CalculationRule {ontologyId:'income'})
WHERE r.issue=true
RETURN r.name AS rule,r.description AS explanation,r.status AS status
ORDER BY rule;

// 5. 查看來源SQL
MATCH (s:StagingOutput {key:'income:stage:INCOME_030'})
  -[:SUPPORTED_BY_SQL]->(e:SqlEvidence)
RETURN s.name AS source,e.file AS file,e.lineStart AS line,e.sql AS sql;

// 6. 比較客戶月總收入、組織報表與CNT定義
MATCH (m:BusinessMetric {ontologyId:'income'})
WHERE m.code IN ['income_total_customer_month','report_income_amount','report_row_count']
RETURN m.name AS metric,m.definition AS definition,m.formula AS formula;
