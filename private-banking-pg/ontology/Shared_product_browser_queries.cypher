// 1. 共用產品主圖：箭頭皆從產品出發；集合帳戶的Income連線為待確認定義。
MATCH (p:SharedProduct {ontologyId:'pb_shared'})
MATCH a=(p)-[:MEASURED_BY_AUM]->(aum:BusinessMetric)
MATCH i=(p)-[:MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(income:BusinessMetric)
OPTIONAL MATCH aumCustomer=(aum)-[:MEASURES_CUSTOMER]->(:MappingCustomer {key:'pb_shared:customer:customer'})
OPTIONAL MATCH incomeCustomer=(income)-[:MEASURES_CUSTOMER]->(:MappingCustomer {key:'pb_shared:customer:customer'})
RETURN a,i,aumCustomer,incomeCustomer;

// 2. 實際Income分類可達的14個共用概念，排除待確認分支。
MATCH (p:SharedProduct {ontologyId:'pb_shared'})
MATCH a=(p)-[:MEASURED_BY_AUM]->(:BusinessMetric)
MATCH i=(p)-[:MEASURED_BY_INCOME]->(:BusinessMetric)
RETURN a,i;

// 3. 選一個共用產品，查看兩側Stage及原始Ontology Term（可替換code）。
MATCH (p:SharedProduct {key:'pb_shared:product:bank_insurance'})
MATCH metric=(p)-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(:BusinessMetric)
MATCH stage=(p)-[:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY|INCOME_DECLARED_BY]->(s:StagingOutput)
OPTIONAL MATCH evidence=(s)-[:DEPENDS_ON|REFRESHED_FROM*0..8]->(:StagingOutput)-[:DESCRIBED_BY]->(t:Term)
RETURN metric,stage,evidence;

// 4. 從共用層列出映射及計價基礎，不加總AUM與Income。
MATCH (p:SharedProduct {ontologyId:'pb_shared'})
RETURN p.name AS 共用產品,p.status AS 狀態,p.aumStages AS AUM來源,
       p.incomeStages AS Income來源,p.aumValuationBasis AS AUM口徑,
       p.incomeAmountBasis AS Income口徑,p.definition AS 說明
ORDER BY p.displayOrder;
