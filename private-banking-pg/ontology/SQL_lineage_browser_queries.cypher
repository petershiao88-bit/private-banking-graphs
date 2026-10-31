// 每次選一段執行。節點是表，SQL 運算是表與表之間的連線。
// 點連線看 sql、whereConditions、joinConditions、groupExpressions、
// aggregateExpressions、caseExpressions、unionBranchOrders、ruleSteps。

// 1. 保險 Income：底表 → staging → UNION → INCOME_TMP01。
MATCH p=(src:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->
  (:SqlTable {name:'INCOME_TMP01'})
WHERE src.name IN ['DSINS.INSU_RPT_Q01','DSKPI.KPI_DET_IU_002_NEW','DSKPI.KPI_DET_OFI_001']
AND all(r IN relationships(p) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
RETURN p;

// 2. 保險 AUM 完整上游。
MATCH p=(src:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->
  (:SqlTable {name:'AUM_012'})
WHERE src.tableKind='external_source'
AND all(r IN relationships(p) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
RETURN p;

// 3. 選一張輸出表，看直接來源；可換成 INCOME_TMP01 或 AUM。
MATCH p=(:SqlTable)-[r]->(:SqlTable {name:'INCOME_066_TMP_DETAIL_04'})
WHERE r.origin='sql_lineage_v1' AND r.status='active_sql' AND r.sourceRole='primary_reference'
RETURN p;

// 4. 客戶月份 LEFT JOIN：點連線查看 ON 條件與左右輸入角色。
MATCH p=(:SqlTable)-[r:LEFT_JOIN]->(:SqlTable {name:'INCOME_TMP02'})
WHERE r.status='active_sql' AND r.sourceRole='primary_reference'
RETURN p;

// 5. 共用保險概念映射至 AUM／Income SQL 血緣。
MATCH business=(p:SharedProduct {code:'bank_insurance'})
  -[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY]->(stage:StagingOutput)
MATCH mapping=(stage)-[:REPRESENTS_SQL_TABLE]->(target:SqlTable)
MATCH lineage=(source:SqlTable)
  -[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|INSERT_FROM*1..8]->(target)
WHERE source.tableKind='external_source'
AND all(r IN relationships(lineage) WHERE r.status='active_sql' AND r.sourceRole='primary_reference')
RETURN business,mapping,lineage;

// 6. 被註解的歷史初始化 UNION ALL。
MATCH p=(:SqlTable)-[r:UNION_ALL]->(:SqlTable {name:'INCOME_066_TMP01'})
WHERE r.status='commented_out_sql'
RETURN p;

// 7. 月更新：DELETE_ROWS 自連線與 INSERT_FROM 輸入連線。
MATCH deletion=(t:SqlTable {name:'INCOME_066'})-[d:DELETE_ROWS]->(t)
MATCH insertion=(:SqlTable)-[i:INSERT_FROM]->(t)
MATCH (ds:SqlStatement {key:d.statementKey})-[:NEXT_STATEMENT]->(ins:SqlStatement {key:i.statementKey})
WHERE d.status='active_sql' AND i.status='active_sql'
RETURN deletion,insertion;

// 8. 原始 SQL 語句與來源行號。
MATCH (s:SqlStatement {output:'INCOME_TMP01'})
RETURN s.file AS 來源檔案,s.lineStart AS 起始行,s.lineEnd AS 結束行,
  s.status AS 語句狀態,s.sourceRole AS 來源版本,s.sql AS 原始SQL
ORDER BY s.file,s.lineStart;

// 9. AUM_TMP02 定義只出現在備份版本。
MATCH (s:SqlStatement {output:'AUM_TMP02'})
RETURN s.file AS 來源檔案,s.status AS 狀態,s.sql AS 原始SQL;

// 10. 原始檔全文與雜湊。
MATCH (f:SqlSourceFile)
RETURN f.name AS 檔名,f.sourceRole AS 版本角色,f.encoding AS 編碼,
  f.sha256 AS 檔案雜湊,f.rawSql AS 原始檔案全文
ORDER BY f.name;
