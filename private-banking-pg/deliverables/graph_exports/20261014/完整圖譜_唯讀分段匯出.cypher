// 唯讀全圖匯出；JSON 分段避免 Query UI 展開大型巢狀物件。
CALL {
 MATCH (n)
 WITH n ORDER BY elementId(n)
 RETURN collect({id:elementId(n),labels:labels(n),properties:properties(n)}) AS nodes
}
CALL {
 MATCH (a)-[r]->(b)
 WITH a,r,b ORDER BY elementId(r)
 RETURN collect({id:elementId(r),source:elementId(a),type:type(r),target:elementId(b),properties:properties(r)}) AS relationships
}
WITH nodes,relationships,apoc.convert.toJson({nodes:nodes,relationships:relationships}) AS text
WITH nodes,relationships,text,toInteger(ceil(toFloat(size(text))/25000)) AS chunkCount
UNWIND range(0,chunkCount-1) AS chunkIndex
RETURN chunkIndex,chunkCount,size(text) AS jsonCharacters,
 size(nodes) AS nodeCount,size(relationships) AS relationshipCount,
 substring(text,chunkIndex*25000,25000) AS chunk
ORDER BY chunkIndex
