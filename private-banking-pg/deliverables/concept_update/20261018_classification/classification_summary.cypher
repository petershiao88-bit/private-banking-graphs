MATCH (p:PBConcept:PBConceptProduct)
UNWIND ['subsidiary','currencyType','structureType','fundType','marketRegion','dealingMode'] AS field
WITH p,field WHERE p[field] IS NOT NULL
RETURN '商品分類更新完成' AS 狀態, field AS 分類欄位, count(p) AS 已填商品數, collect(DISTINCT p[field]) AS 分類值
ORDER BY 分類欄位
