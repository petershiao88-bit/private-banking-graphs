// 1. 新版共用圖：共用產品 → AUM／Income 各層指標，並展開 SQL 表血緣。
// 若只看保險，在第一個 MATCH 後加 WHERE p.code='bank_insurance'。
MATCH a=(p:SharedProduct {ontologyId:'pb_shared'})
  -[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key:'aum:metric:aum_total_month_end'})
MATCH i=(p)
  -[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key:'income:metric:income_total_customer_month'})
OPTIONAL MATCH mapping=(p)
  -[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->
  (stage:StagingOutput)-[:REPRESENTS_SQL_TABLE]->(target:SqlTable)
OPTIONAL MATCH lineage=(source:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->(target)
WHERE source.tableKind='external_source'
  AND all(r IN relationships(lineage)
    WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
RETURN a,i,mapping,lineage;

// 2. AI 工具：列出可查詢的共用產品與定義狀態。
MATCH (p:SharedProduct {ontologyId:'pb_shared'})
RETURN p.code AS productCode,p.name AS product,p.definition AS definition,
  p.status AS status,p.incomeMappingActive AS incomeMappingActive
ORDER BY p.displayOrder;

// 3. AI 工具：產品向上查 AUM／向下查 Income 的業務歸屬。
// API parameters: {"productCode":"bank_insurance","domain":"income"}
MATCH path=(p:SharedProduct {ontologyId:'pb_shared',code:$productCode})
  -[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->
  (root:BusinessMetric)
WHERE ($domain='aum' AND root.key='aum:metric:aum_total_month_end')
   OR ($domain='income' AND root.key='income:metric:income_total_customer_month')
RETURN p.name AS product,p.status AS definitionStatus,
  [n IN nodes(path) | n.name] AS metricPath,
  [r IN relationships(path) | {type:type(r),status:r.status,note:r.note}] AS mappings;

// 4. AI 工具：沿來源表連線讀取計算規則，回傳 JSON 可讀的路徑與證據。
// API parameters: {"productCode":"bank_insurance","domain":"income"}
MATCH (p:SharedProduct {ontologyId:'pb_shared',code:$productCode})
  -[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->
  (stage:StagingOutput)-[:REPRESENTS_SQL_TABLE]->(target:SqlTable)
WHERE stage.ontologyId=$domain
MATCH path=(source:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->(target)
WHERE source.tableKind='external_source'
  AND all(r IN relationships(path)
    WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
RETURN p.name AS product,p.status AS definitionStatus,
  type(mapping) AS mappingType,mapping.scope AS productScope,
  stage.outputObject AS outputTable,
  [n IN nodes(path) | n.name] AS tablePath,
  [r IN relationships(path) | {
    operation:type(r),operationTypes:r.operationTypes,
    whereConditions:r.whereConditions,joinConditions:r.joinConditions,
    groupExpressions:r.groupExpressions,aggregateExpressions:r.aggregateExpressions,
    selectExpressions:r.selectExpressions,caseExpressions:r.caseExpressions,
    unionBranchOrders:r.unionBranchOrders,unionDeduplication:r.unionDeduplication,
    file:r.file,lineStart:r.lineStart,lineEnd:r.lineEnd,status:r.status,sql:r.sql
  }] AS rules
LIMIT 50;

// 5. AI 工具：查單張 SQL 表的直接上游；可逐步呼叫直到抵達底表。
// API parameters: {"tableName":"INCOME_TMP01"}
MATCH (source:SqlTable)
  -[r:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM]->
  (target:SqlTable {name:$tableName})
WHERE r.status='active_sql' AND r.sourceRole='primary_reference'
RETURN source.name AS sourceTable,target.name AS targetTable,
  type(r) AS operation,r.unionBranchOrders AS branchOrders,
  r.whereConditions AS whereConditions,r.joinConditions AS joinConditions,
  r.groupExpressions AS groupExpressions,r.aggregateExpressions AS aggregateExpressions,
  r.file AS sourceFile,r.lineStart AS lineStart,r.lineEnd AS lineEnd,r.sql AS sql
ORDER BY r.file,r.lineStart,r.unionBranchOrders
LIMIT 50;
