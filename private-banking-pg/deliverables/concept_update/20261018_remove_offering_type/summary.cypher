CALL { MATCH (n:PBConcept) RETURN count(n) AS conceptNodes }
CALL { MATCH (:PBConcept)-[r]->(:PBConcept) RETURN count(r) AS conceptRelationships }
MATCH (p:PBConcept:PBConceptProduct)
RETURN 'offeringType 已全部移除' AS 狀態,
       count(p) AS 商品節點數,
       count(p.offeringType) AS 欄位剩餘數,
       conceptNodes AS 概念節點數,
       conceptRelationships AS 關係數
