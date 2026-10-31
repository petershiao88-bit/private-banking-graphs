AUM／Income SQL 血緣（2026-10-06 修正版）

節點是底表、暫存表與彙總表。SQL 規則是表與表之間的連線。
不匯入 SqlOperation 節點；運算樹只作為解析器內部處理資料。
連線種類：TRANSFORMS_TO、UNION、UNION_ALL、LEFT_JOIN、INNER_JOIN、
INSERT_FROM、DELETE_ROWS。DELETE_ROWS 是目標表的自連線。
方向：來源表 → 輸出表；INSERT_FROM 也採用此資料流方向。

連線的 sql 保存原始語句；file、lineStart、lineEnd 保存來源位置。
whereConditions、havingConditions、selectExpressions、groupExpressions、
aggregateExpressions、caseExpressions、joinConditions、joinInputRoles
保存篩選、投影、彙總、分類與 JOIN 規則。
unionBranchOrders 保存分支順序；unionDeduplication 保存去重語意。
ruleSteps 與 inputSteps 是 JSON 字串，保存依序套用及巢狀規則。
一條連線包含多種運算時，優先顯示 UNION／UNION_ALL，其次 JOIN；
全部運算保存在 operationTypes 與 ruleSteps 中。
ruleSteps 的片段是解析器重建文字；sql 與 SqlStatement.sql 是來源原文。

SqlSourceFile 保存完整 cp950 解碼原文，可還原原始位元組與 SHA-256。
SqlStatement 保存語句與來源證據；它們不出現在預設表血緣圖中。
NEXT_STATEMENT 只保留同一檔案內被解析的語句順序。
現有 86 個 StagingOutput 透過 REPRESENTS_SQL_TABLE 映射至 SQL 表。
業務指標、產品與既有關係在匯入前後保持相同。

狀態：active_sql、commented_out_sql、auxiliary_reference_sql、alternate_file_sql。
有效 SQL 不等於已核定或已部署的生產規則。
AUM_TMP02 只在備份檔有定義，沒有推測 AUM → AUM_TMP02 的轉換。
UNION 去除投影後完全相同的列，不是依客戶或保單去重。
INCOME_TMP01 保留 24 分支；AUM 保留 13 分支，包括兩個 AUM_012 分支。
保險收入来源是否互斥仍沿用既有業務字典的待確認狀態。
這是靜態 SQL 血緣，不執行 Oracle SQL，不建立實際客戶餘額資料。

重建：
python -X utf8 ontology/build_sql_lineage_graph.py
python -X utf8 ontology/verify_sql_lineage_plan.py
設定 NEO4J_PASSWORD 後：
python -X utf8 ontology/import_sql_lineage_graph.py --check-only
python -X utf8 ontology/import_sql_lineage_graph.py

匯入器只移除同 namespace 與 origin 的舊版運算節點。
查詢：SQL_lineage_browser_queries.cypher。
驗證：SQL_lineage_plan_validation.json、SQL_lineage_graph_validation.json。
