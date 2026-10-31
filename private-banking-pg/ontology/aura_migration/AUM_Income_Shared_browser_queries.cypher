// 每次選一段執行。這些查詢只讀取資料，不新增或刪除節點。

// 1. AUM 業務主圖：總 AUM、各層分類及 AUM 產品。
MATCH a = (root:BusinessMetric {key: 'aum:metric:aum_total_month_end'})
  -[:HAS_COMPONENT*0..3]->(m:BusinessMetric)
OPTIONAL MATCH p = (m)
  -[:INCLUDES_PRODUCT]->(:ProductCategory {ontologyId: 'aum'})
RETURN a, p;

// 2. Income 業務主圖：總收入、各層分類及 Income 產品。
// DECLARES_PRODUCT 保留集合管理帳戶的待確認業務定義。
MATCH i = (root:BusinessMetric {key: 'income:metric:income_total_customer_month'})
  -[:HAS_COMPONENT*0..3]->(m:BusinessMetric)
OPTIONAL MATCH p = (m)
  -[:INCLUDES_PRODUCT|DECLARES_PRODUCT]->(:ProductCategory {ontologyId: 'income'})
RETURN i, p;

// 3. 共用產品主圖：產品指向 AUM 與 Income，保留兩側所有中間彙總層。
// INCOME_DEFINITION_PENDING 是集合管理帳戶的待確認收入映射。
MATCH a = (p:SharedProduct {ontologyId: 'pb_shared'})
  -[:MEASURED_BY_AUM|AUM_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key: 'aum:metric:aum_total_month_end'})
MATCH i = (p)
  -[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO*1..5]->
  (:BusinessMetric {key: 'income:metric:income_total_customer_month'})
RETURN a, i;
