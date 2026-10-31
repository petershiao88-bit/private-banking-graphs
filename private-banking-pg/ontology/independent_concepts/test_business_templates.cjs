// Run the actual local templates against old and new graph projections. No network.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'deliverables/concept_build/20261013');
const read=p=>fs.readFileSync(p,'utf8'),json=p=>JSON.parse(read(p));
const run=(file,input,contexts={})=>new Function('$input','$',read(file))({first:()=>({json:input})},name=>{
 if(!(name in contexts))throw new Error('Missing trusted context');
 return {first:()=>({json:contexts[name]})};
});
const prepareFile=path.join(root,'ontology/n8n_kb/full_graph_prepare_concepts.js');
const common=read(path.join(root,'ontology/n8n_kb/full_graph_common.js'));
const prepare=(input,question='請查客戶相關業務')=>new Function('$input','$',common+'\n'+read(prepareFile))({first:()=>({json:input})},name=>{
 assert.equal(name,'KB Input');return {first:()=>({json:{question,domains:[],metricCodes:[]}})};
})[0].json;
const reports=[];
for(const [version,templateDir,expectedCount,expectedPaths] of [
 ['legacy',__dirname,15,29],['business_v2',path.join(out,'business_v2/templates'),25,39]
]){
 const fixture=json(path.join(out,version+'.fixture.json'));
 const catalog=run(path.join(templateDir,'n8n_01_project_output.js'),fixture.catalogResponse)[0].json;
 assert.deepEqual(catalog,fixture.catalog);
 assert.equal(catalog.products.length,expectedCount);
 let supported=0,rejected=0,draftRoutes=0;
 for(const product of catalog.products)for(const domain of ['aum','income']){
  const input={productCode:product.productCode,domain};
  if(!product[domain+'Metrics'].length){assert.throws(()=>run(path.join(templateDir,'n8n_02_prepare.js'),input,{ConceptCatalog:catalog}));rejected++;continue;}
  const prepared=run(path.join(templateDir,'n8n_02_prepare.js'),input,{ConceptCatalog:catalog})[0].json;
  assert.deepEqual(Object.keys(prepared).sort(),['parameters','statement']);
  assert.equal(prepared.parameters.productCode,product.productCode);
  assert.equal(prepared.parameters.domain,domain);
  if(prepared.parameters.productKey){
   assert.match(prepared.statement,/MappingDraftProduct/);
   assert.equal(prepared.parameters.productKey,'draft:pb:20261012:product:'+product.productCode);
   assert.ok(prepared.parameters.metricKey.startsWith('draft:pb:20261012:metric:'));
   draftRoutes++;
  }else{assert.match(prepared.statement,/SharedProduct/);assert.deepEqual(Object.keys(prepared.parameters).sort(),['domain','productCode']);}
  supported++;
 }
 assert.equal(supported,expectedPaths);
 const context=prepare(fixture.graphResponse);
 assert.equal(context.conceptPathCandidates.length,expectedPaths);
 assert.ok(context.conceptGraph.nodes.every(n=>Object.values(n.properties).every(v=>v!=null)));
 assert.ok(context.conceptPathCandidates.every(p=>p.nodes.every(n=>n.properties.productCode||n.properties.metricCode)));
 if(version==='business_v2'){
  assert.equal(draftRoutes,10);
  assert.equal(rejected,11);
  const by=new Map(context.conceptGraph.nodes.map(n=>[n.key,n]));
  assert.ok(context.conceptGraph.nodes.every(node=>!('offeringType' in node.properties)));
  assert.ok(by.get('advisor').properties.roleResponsibilities.length);
  assert.equal(by.get('private_banking').properties.organizationType,'業務單位');
  assert.ok(context.conceptGraph.relationships.find(r=>r.type==='PB_ASSIGNED_TO').properties.businessConstraint);
 }
 reports.push({version,products:expectedCount,paths:expectedPaths,supportedPairs:supported,unsupportedPairsRejected:rejected,draftRoutes});
}
const fixture=json(path.join(out,'business_v2.fixture.json'));
for(const input of [
 {productCode:'loan',domain:'income',statement:'MATCH (n) RETURN n'},
 {productCode:'loan',domain:'all'},
 {productCode:"' MATCH (n) RETURN n //",domain:'income'}
])assert.throws(()=>run(path.join(out,'business_v2/templates/n8n_02_prepare.js'),input,{ConceptCatalog:fixture.catalog}));
const leaked=structuredClone(fixture.catalogResponse);leaked.data.values[0][10][0].sql='SELECT hidden';
assert.throws(()=>run(path.join(out,'business_v2/templates/n8n_01_project_output.js'),leaked));
const emptySide=structuredClone(fixture.catalogResponse);const loan=emptySide.data.values.find(r=>r[0]==='loan');loan[10]=[emptySide.data.values.find(r=>r[0]==='deposit')[10][0]];
assert.throws(()=>run(path.join(out,'business_v2/templates/n8n_01_project_output.js'),emptySide));
const badGraph=structuredClone(fixture.graphResponse);badGraph.data.values[0][0].nodes[0].properties.sql='SELECT hidden';assert.throws(()=>prepare(badGraph));
const contextPath=structuredClone(fixture.graphResponse),graph=contextPath.data.values[0][0];
const assignment=graph.relationships.find(r=>r.type==='PB_ASSIGNED_TO');
contextPath.data.values[0][1].push({domain:'aum',nodeKeys:[assignment.from,assignment.to],relationshipIds:[assignment.id]});
assert.throws(()=>prepare(contextPath));
const classificationPath=structuredClone(fixture.graphResponse),g=classificationPath.data.values[0][0];
const classification=g.relationships.find(r=>r.type==='PB_SUBCATEGORY_OF'),deposit=g.relationships.find(r=>r.from==='deposit'&&r.type==='PB_AUM_MEASURED_BY');
const original=classificationPath.data.values[0][1].find(p=>p.nodeKeys[0]==='deposit'&&p.domain==='aum');
classificationPath.data.values[0][1].push({domain:'aum',nodeKeys:[classification.from,...original.nodeKeys],relationshipIds:[classification.id,...original.relationshipIds]});
assert.throws(()=>prepare(classificationPath));
// Keep selected business properties and explicit parent/child overlap in the result,
// even when mappings are empty; absence of mappings is not fabricated evidence.
const prepared=prepare(fixture.graphResponse);
const selected=prepared.conceptPathCandidates.filter(p=>p.domain==='aum'&&['deposit','deposit_twd'].includes(p.productCodes[0]));
const resultContext={...prepared,selectedConceptPaths:selected,conceptPathScores:[],conceptDecision:{model:'offline-fixture'}};
const result=new Function('$input','$',common+'\n'+read(path.join(root,'ontology/n8n_kb/single_jev_result.js')))({first:()=>({json:{data:{fields:['pathKey','productCode','productName','domain','mappings'],values:[]}}})},name=>{
 assert.equal(name,'Concept Path Result');return {first:()=>({json:resultContext})};
})[0].json;
assert.equal(result.products.length,2);
assert.ok(result.products.every(p=>p.businessProperties.customerNeed));
assert.equal(result.queryPlan.overlappingProductScopes.length,1);
assert.equal(result.queryPlan.overlappingProductScopes[0].childProductCode,'deposit_twd');
assert.equal(result.mappingResolution.mappingCount,0);
assert.equal(result.mappingResolution.complete,false);
assert.equal(result.mappingResolution.unresolvedSelections.length,2);
const draftMapping={data:{fields:['productCode','productName','domain','status','mappingActive','calculationAuthorized','mappings'],values:[['loan','放款','income','mapping_draft_rules',true,false,[{mappingFormat:'mapping_draft_rules',sourceTable:'DSLON.LN_FN_ACCT',calculationRules:'[{"purpose":"來源規則"}]'}]]]} };
assert.equal(run(path.join(__dirname,'n8n_02_project_output.js'),draftMapping)[0].json.calculationAuthorized,false);
const invalidRules=structuredClone(draftMapping);invalidRules.data.values[0][6][0].calculationRules='not-json';assert.throws(()=>run(path.join(__dirname,'n8n_02_project_output.js'),invalidRules));
const legacyFixture=json(path.join(out,'legacy.fixture.json'));
const historicalEvidenceCases={};
for(const name of ['deposit_aum','deposit_income','securities_fund','securities_all','deposit_both']){
 const data=json(path.join(root,'ontology/n8n_kb/full_graph.live_'+name+'.json'));
 const context=prepare(legacyFixture.graphResponse,data.request.question);
 const answers={answers:Object.fromEntries(context.conceptPathCandidates.map(p=>[p.pathKey,{type:'choice',choice:data.select.some(s=>s.domain===p.domain&&p.productCodes.includes(s.productCode))?'included':'excluded',probabilities:{included:0.12,uncertain:0.87,excluded:0.01},confidence:0.8}])),model:'offline-fixture'};
 const choice=new Function('$input','$',common+'\n'+read(path.join(root,'ontology/n8n_kb/full_graph_concept_result.js')))({first:()=>({json:answers})},n=>{assert.equal(n,'Jev - Prepare Concept Paths');return {first:()=>({json:context})};})[0].json;
 const mappingData=structuredClone(data.mappings),fields=mappingData.data.fields;
 for(const row of mappingData.data.values){
  const candidate=choice.selectedConceptPaths.find(p=>p.domain===row[fields.indexOf('domain')]&&p.productCodes.includes(row[fields.indexOf('productCode')]));
  assert.ok(candidate);row[fields.indexOf('pathKey')]=candidate.pathKey;
 }
 const response=new Function('$input','$',common+'\n'+read(path.join(root,'ontology/n8n_kb/single_jev_result.js')))({first:()=>({json:mappingData})},n=>{assert.equal(n,'Concept Path Result');return {first:()=>({json:choice})};})[0].json;
 assert.equal(response.products.length,data.select.length);
 assert.equal(response.mappingResolution.complete,true);
 assert.ok(response.mappingPaths.every(p=>p.conceptPathKeys.every(k=>response.selectedConceptPaths.some(s=>s.pathKey===k))));
 assert.equal(new Set(response.sqlEvidence.statements.map(s=>s.statementKey)).size,response.sqlEvidence.statements.length);
 assert.ok(response.conceptPathScores.filter(p=>p.choice==='included').every(p=>p.probability===0.12));
 historicalEvidenceCases[name]={mappingPaths:response.mappingPaths.length,sqlStatements:response.sqlEvidence.statements.length};
}
assert.equal(historicalEvidenceCases.securities_fund.mappingPaths,2);
assert.equal(historicalEvidenceCases.securities_all.mappingPaths,17);
assert.equal(historicalEvidenceCases.deposit_both.mappingPaths,12);
const report={scenarios:reports,historicalEvidenceCases,injectedStatementsRejected:true,technicalPropertiesRejected:true,unsupportedSideRejected:true,roleAndClassificationCalculationPathsRejected:true,selectedBusinessPropertiesRetained:true,parentChildOverlapRetained:true,unresolvedMappingsReported:true,draftRulesValidated:true,networkUsed:false};
fs.writeFileSync(path.join(out,'template_validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
