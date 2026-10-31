// 為兩種業務指標加入分色標籤；保留既有BusinessMetric及所有關係。
MATCH (m:BusinessMetric {ontologyId:'aum'})
SET m:AUMMetric;

MATCH (m:BusinessMetric {ontologyId:'income'})
SET m:IncomeMetric;

// 驗證：AUM 6個指標，Income 9個指標；主圖使用其中兩側各6個。
MATCH (m:BusinessMetric)
WHERE m.ontologyId IN ['aum','income']
RETURN m.ontologyId AS 業務,count(m) AS 指標數,collect(DISTINCT labels(m)) AS 標籤;
