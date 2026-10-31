MATCH (p:PBConcept:PBConceptProduct)
WHERE p.productCode IN ['bank_structured_domestic','bank_structured_offshore',
                       'bank_collective_account','bank_planned_trust','bank_trust_custody']
RETURN p.name AS 商品, p.marketRegion AS 市場地區, p.dealingMode AS 承作方式
ORDER BY p.productCode
