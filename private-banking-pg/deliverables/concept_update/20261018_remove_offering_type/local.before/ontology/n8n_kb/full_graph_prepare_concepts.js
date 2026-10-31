const response=$input.first().json,input=$('KB Input').first().json;
const fail=()=>{throw new Error('Business concept graph unavailable');};
if(response.errors?.length||!response.data||JSON.stringify(response.data.fields)!==JSON.stringify(['conceptGraph','businessPaths'])||response.data.values?.length!==1)fail();
let {conceptGraph,businessPaths}=graphRows(response)[0];
if(!conceptGraph||!Array.isArray(conceptGraph.nodes)||!Array.isArray(conceptGraph.relationships)||!Array.isArray(businessPaths))fail();
const fieldsByLabel={
 PBConceptProduct:['productCode','name','aumDefinition','incomeDefinition','offeringType','definition','productCategory','businessChannel','customerNeed','serviceDescription'],
 PBConceptMetric:['metricCode','name','definition'],
 PBConceptCustomer:['conceptCode','name','definition','businessRole','customerId','customerName','customerNumber'],
 PBConceptAdvisor:['conceptCode','name','definition','roleResponsibilities','serviceDescription','advisorId','advisorName','employeeNumber'],
 PBConceptOrganization:['conceptCode','name','definition','aliases','organizationType','businessPurpose','targetCustomer','serviceScope']
};
const allBusinessFields=new Set(Object.values(fieldsByLabel).flat());
const technical=/\b(?:SQL|CASE|SELECT|WHERE|JOIN|STAGE|FH_TYP|SUB_TYPE|CUST_ID|AMT|PROD_TYPE|CFEE|ABFEE|TSSN)\b|(?:AUM|INCOME)_[0-9]|DSPMS\.|\b\w+\.\w+\b/i;
conceptGraph={nodes:conceptGraph.nodes.map(node=>{
 if(!node||!Array.isArray(node.labels)||!node.labels.includes('PBConcept')||!node.properties)fail();
 const kinds=Object.keys(fieldsByLabel).filter(label=>node.labels.includes(label));
 if(kinds.length!==1)fail();
 // Explicit Cypher projections return null for absent fields of other node kinds.
 for(const [field,value] of Object.entries(node.properties))if(!allBusinessFields.has(field)||(value!=null&&!fieldsByLabel[kinds[0]].includes(field)))fail();
 const properties=Object.fromEntries(Object.entries(node.properties).filter(([,value])=>value!=null));
 for(const [field,value] of Object.entries(properties)){
  if(['aliases','roleResponsibilities'].includes(field)){if(!Array.isArray(value)||!value.length||!value.every(v=>typeof v==='string'&&v))fail();}
  else if(typeof value!=='string')fail();
 }
 const code=properties.productCode||properties.metricCode||properties.conceptCode;
 if(node.key!==code||!properties.name||!code)fail();
 if(technical.test(JSON.stringify(properties)))fail();
 return {key:node.key,labels:node.labels,properties};
}),relationships:conceptGraph.relationships.map(edge=>{
 if(!edge||!edge.id||!edge.from||!edge.to||!edge.properties)fail();
 if(Object.keys(edge.properties).some(field=>!['definition','businessConstraint'].includes(field)))fail();
 if(!['PB_AUM_MEASURED_BY','PB_INCOME_MEASURED_BY','PB_AUM_ROLLS_UP_TO','PB_INCOME_ROLLS_UP_TO','PB_HAS_MEASUREMENT_SUBJECT','PB_SUBCATEGORY_OF','PB_ASSIGNED_TO','PB_SCOPED_TO'].includes(edge.type))fail();
 const properties=Object.fromEntries(Object.entries(edge.properties).filter(([,value])=>value!=null));
 if(typeof properties.definition!=='string'||!properties.definition||Object.values(properties).some(v=>typeof v!=='string')||technical.test(JSON.stringify(properties)))fail();
 return {...edge,properties};
})};
if(new Set(conceptGraph.nodes.map(n=>n.key)).size!==conceptGraph.nodes.length||new Set(conceptGraph.relationships.map(r=>r.id)).size!==conceptGraph.relationships.length)fail();
if(conceptGraph.relationships.some(r=>!conceptGraph.nodes.some(n=>n.key===r.from)||!conceptGraph.nodes.some(n=>n.key===r.to)))fail();
const conceptPathCandidates=uniqueBy(businessPaths.map(path=>{
 if(!['aum','income'].includes(path.domain)||!Array.isArray(path.nodeKeys)||!Array.isArray(path.relationshipIds)||path.nodeKeys.length!==path.relationshipIds.length+1)fail();
 const nodes=path.nodeKeys.map(key=>conceptGraph.nodes.find(node=>node.key===key));
 const relationships=path.relationshipIds.map(id=>conceptGraph.relationships.find(edge=>edge.id===id));
 if(nodes.some(n=>!n)||relationships.some(r=>!r)||!nodes[0].properties.productCode||nodes.slice(1).some(n=>!n.properties.metricCode))fail();
 if(!nodes[0].properties[path.domain+'Definition']||nodes.at(-1).properties.metricCode!==(path.domain==='aum'?'aum_total':'income_total'))fail();
 for(let i=0;i<relationships.length;i++){
  const expected=i===0?(path.domain==='aum'?'PB_AUM_MEASURED_BY':'PB_INCOME_MEASURED_BY'):(path.domain==='aum'?'PB_AUM_ROLLS_UP_TO':'PB_INCOME_ROLLS_UP_TO');
  if(relationships[i].from!==nodes[i].key||relationships[i].to!==nodes[i+1].key||relationships[i].type!==expected)fail();
 }
 const productNodes=nodes.filter(node=>node.properties.productCode);
 const metricNodes=nodes.filter(node=>node.properties.metricCode);
 return {pathKey:stableKey('concept',[path.nodeKeys,path.relationshipIds]),domain:path.domain,nodeKeys:path.nodeKeys,relationshipIds:path.relationshipIds,
  productCodes:productNodes.map(node=>node.properties.productCode),anchorConceptKeys:productNodes.map(node=>node.key),
  metricCodes:metricNodes.map(node=>node.properties.metricCode),nodes,relationships};
}),path=>path.pathKey);
const decisionRules='依 conceptGraph 的業務定義、方向、產品或服務類型、業務分類、通路、客戶需求與服務內容，以及 AUM／Income 領域，判斷路徑是否為回答 question 所需的業務路徑之一。產品的基本意義使用 definition，領域意義使用 aumDefinition 或 incomeDefinition，關係的 definition 與 businessConstraint 必須一併理解。客戶需求描述是一般業務需求，不表示個別客戶需求或適合度。路徑已延伸到最上層，上層節點提供上下文，問題不必要求根指標才可納入。依 question 指定的顆粒度判斷，不能因共享上層指標而納入所有兄弟產品。可同時納入多條，共享節點不代表互斥。父產品與子分類可能包含相同業務範圍，不可據多條路徑重複加總。客戶、AO、私銀組織與分類關係只作業務上下文，不是金額計算根節點或額外加總路徑；服務對應不表示唯一 AO、正式任職或業績分攤。只判斷業務概念，不猜實體表或 SQL。';
const questions=Object.fromEntries(conceptPathCandidates.map(path=>[path.pathKey,{type:'choice',
 instructions:`依 state.decisionRules 評估 businessPaths 中 pathKey=${path.pathKey} 的完整路徑。`,
 criteria:{included:'符合問題，是所需業務範圍的一部分。',uncertain:'可能符合，但業務範圍、通路或領域不足以確定。',excluded:'不符合問題，或不在問題要求的範圍。'}}]));
return [{json:{question:input.question,domains:input.domains||[],metricCodes:input.metricCodes||[],conceptGraph,conceptPathCandidates,
 decisionRequest:{model:'typesafe/jev-1.13',state:{question:input.question,decisionRules,contextHints:{domains:input.domains||[],metricCodes:input.metricCodes||[]},conceptGraph,
  businessPaths:conceptPathCandidates.map(({nodes,relationships,...path})=>path)},questions}}}];
