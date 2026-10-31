const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = __dirname;
const fixtures = JSON.parse(fs.readFileSync(path.join(root,'test_fixtures.json'),'utf8'));
const wf = JSON.parse(fs.readFileSync(path.join(root,process.argv[2] || 'PB_AUM_Income_KB.json'),'utf8'));
const catalogCode = wf.nodes.find(n=>n.name==='Concept Catalog').parameters.jsCode;
const resultCode = wf.nodes.find(n=>n.name==='KB Result').parameters.jsCode;
const expression = wf.nodes.find(n=>n.name==='Aura - Mappings').parameters.jsonBody.slice(3,-2).trim();
const api = rows => ({data:{fields:Object.keys(rows[0]||{productCode:0,productName:0,domain:0,status:0,mappings:0}),values:rows.map(Object.values)}});
const run = (code,input,prior)=>new Function('$input','$',code)({first:()=>({json:input})},name=>({first:()=>({json:prior[name]})}));
const request = {question:'銀行保險 Income 的來源',domains:['income'],metricCodes:['income_total_customer_month']};
const prior = {'KB Input':request};
const catalog = run(catalogCode,api(fixtures.catalog),prior)[0].json;
prior['Concept Catalog']=catalog;
const makeBody=choice=>new Function('$json','$','return ('+expression+')')({output:choice},name=>({first:()=>({json:prior[name]})}));
let checks=0;
for (const [name,selections] of Object.entries({empty:[],single:[{productCode:'bank_insurance',domain:'income'}],pending:[{productCode:'bank_collective_account',domain:'income'}]})) {
  const choice={selections,message:name==='empty'?'請指定銀行或證券通路。':'已選定產品。'};
  const body=makeBody(choice);
  assert.deepEqual(body.parameters.selections,selections);
  prior['Jev - Select Products']={output:choice};
  const result=run(resultCode,api(fixtures.outputs[name]),prior);
  assert.equal(result.length,1);
  assert.deepEqual(Object.keys(result[0].json),['metricCodes','products','message']);
  assert.deepEqual(result[0].json.metricCodes,request.metricCodes);
  assert.equal(result[0].json.products.length,selections.length);
  if(name==='empty') assert.match(result[0].json.message,/請指定/);
  if(name==='single') { assert.equal(result[0].json.products[0].mappings.length,3); assert.match(result[0].json.message,/待確認/); }
  if(name==='pending') assert.equal(result[0].json.products[0].definitionStatus,'pending_confirmation');
  checks++;
}
for(const selection of [{productCode:'invented',domain:'income'},{productCode:'bank_insurance',domain:'aum'},{productCode:'bank_insurance',domain:"income' MATCH(n) RETURN n"}]) {
  assert.throws(()=>makeBody({selections:[selection],message:''}),/候選範圍/); checks++;
}
assert.throws(()=>run(catalogCode,{errors:[{code:'x'}]},prior),/概念查詢失敗/); checks++;
assert.throws(()=>run(resultCode,{errors:[{code:'x'}]},prior),/映射查詢失敗/); checks++;
const emptyRequest={question:'未知指標',domains:['aum'],metricCodes:['unknown_metric']};
const emptyCatalog=run(catalogCode,api([]),{'KB Input':emptyRequest})[0].json;
assert.deepEqual(emptyCatalog.unmatchedMetricCodes,['unknown_metric']);
const emptyResult=run(resultCode,api([]),{'Concept Catalog':emptyCatalog,'Jev - Select Products':{output:{selections:[],message:'沒有對應'}}})[0].json;
assert.deepEqual(emptyResult.products,[]);
assert.match(emptyResult.message,/unknown_metric/); checks++;
const scopeCatalog=run(catalogCode,api(fixtures.scopeOutputs.securities),{'KB Input':{question:'基金AUM',domains:['aum','income'],metricCodes:['aum_securities_month_end']}})[0].json;
prior['Concept Catalog']=scopeCatalog;
assert.throws(()=>makeBody({selections:[{productCode:'securities_fund',domain:'income'}]}),/候選範圍/); checks++;
assert.throws(()=>makeBody({selections:[{productCode:'bank_fund',domain:'aum'}]}),/候選範圍/); checks++;
const conceptExpression=wf.nodes.find(n=>n.name==='Aura - Concepts').parameters.jsonBody.slice(3,-2).trim();
const conceptBody=new Function('$json','return ('+conceptExpression+')')(emptyRequest);
assert.deepEqual(conceptBody.parameters,{metricCodes:emptyRequest.metricCodes,domains:emptyRequest.domains});
assert(!/Stage|SQL|SourceTable/.test(conceptBody.statement)); checks++;
assert.equal(wf.nodes.filter(n=>/\.if$|\.switch$/.test(n.type)).length,0);
assert.equal(wf.nodes.length,8);
console.log(JSON.stringify({checksPassed:checks,mainSteps:6,modelSubnodes:2,noIfOrSwitch:true}));
