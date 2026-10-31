// 正式獨立概念圖：41 個節點、69 條關係。
MATCH (n:PBConcept)
OPTIONAL MATCH (n)-[r]->(m:PBConcept)
RETURN n, r, m;
