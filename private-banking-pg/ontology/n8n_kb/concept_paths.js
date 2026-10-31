const context=$input.first().json;
const canonical=v=>Array.isArray(v)?v.map(canonical):v && typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const hash=s=>{let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0).toString(16).padStart(8,'0');};
const pathCandidates=[],pathCatalogIssues=[],seen=new Map();
for(const product of context.products){
 for(const domain of [...new Set(product.matchedScopes.map(s=>s.domain))]){
  const objectKey=`${product.productCode}::${domain}`;
  const raw=product.conceptEvidence || {};
  for(const path of raw[`${domain}Paths`] || []){
   const nodes=path.nodes || [],relationships=path.relationships || [];
   const rootKey=domain==='aum'?'aum:metric:aum_total_month_end':'income:metric:income_total_customer_month';
   const firstTypes=domain==='aum'?['MEASURED_BY_AUM']:['MEASURED_BY_INCOME','INCOME_DEFINITION_PENDING'];
   if(nodes.length<2 || relationships.length!==nodes.length-1 || nodes[0].key!==raw.sharedProduct?.key ||
      nodes[0].properties?.code!==product.productCode || nodes.at(-1).key!==rootKey ||
      new Set(nodes.map(n=>n.key)).size!==nodes.length ||
      nodes.slice(1).some(n=>!n.labels?.includes('BusinessMetric') || n.properties?.ontologyId!==domain) ||
      relationships.some((r,i)=>r.from!==nodes[i].key || r.to!==nodes[i+1].key ||
        !(i===0?firstTypes:[domain==='aum'?'AUM_ROLLS_UP_TO':'INCOME_ROLLS_UP_TO']).includes(r.type))){
    pathCatalogIssues.push({objectKey,code:'invalid_business_path',detail:'概念路徑缺少節點、方向不一致或未抵達領域上層指標。'});continue;
   }
   for(const metricCode of [...new Set(product.matchedScopes.filter(s=>s.domain===domain).map(s=>s.metricCode))]){
    const target=nodes.slice(1).find(n=>n.properties?.code===metricCode);if(!target)continue;
    const signature=JSON.stringify(canonical({objectKey,queryMetricKey:target.key,nodes,relationships}));
    const pathKey=`${objectKey}::${metricCode}::${hash(signature)}`;
    if(seen.has(pathKey)){if(seen.get(pathKey)!==signature)throw new Error('概念路徑識別衝突。');continue;}
    seen.set(pathKey,signature);
    pathCandidates.push({pathKey,objectKey,productCode:product.productCode,productName:product.productName,domain,
     queryMetricCode:metricCode,queryMetricKey:target.key,rootKey,nodeKeys:nodes.map(n=>n.key),
     relationshipTypes:relationships.map(r=>r.type),relationshipProperties:relationships.map(r=>r.properties || {}),nodes,relationships});
   }
  }
 }
}
return [{json:{...context,pathCandidates:pathCandidates.sort((a,b)=>a.pathKey.localeCompare(b.pathKey)),pathCatalogIssues}}];
