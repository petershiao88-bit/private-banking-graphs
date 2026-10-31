const fs=require('node:fs'),assert=require('node:assert/strict');
const {run,native,concepts,routes,w}=require('./lazy_fixture.cjs');
const read=n=>JSON.parse(fs.readFileSync(__dirname+'/'+n,'utf8'));
const finish=(data,first,second)=>run('KB Result',data.mapping,{'Concept Decision Result':first.choice,'Concept Routes':second.formatted,'Route Decision Result':second.choice});
const outputs={};
for(const [name,selected] of [['deposit_aum',['deposit']],['deposit_income',['deposit']],['securities_aum',['securities_fund']],['deposit_both',['deposit']],['securities_compare',['securities_fund','securities_bond']]]){
 const data=read(`lazy_live_${name}.json`),first=concepts(data.catalog,data.request,selected),second=routes(data.paths,first),result=finish(data,first,second);outputs[name]=result;
 assert.equal(result.contractVersion,'pb_kb_lazy_routes_v4');
 assert.deepEqual(result.selectedConcepts,first.choice.selectedConcepts);
 assert.deepEqual(result.decision.concept.answers,native(first.prepared,k=>first.prepared.candidates.some(c=>c.objectKey===k&&selected.includes(c.productCode))?'included':'excluded').answers);
 assert(!Object.hasOwn(first.prepared.decisionRequest.state,'businessPaths'));
 assert(!Object.hasOwn(first.prepared.decisionRequest.questions,'scope'));
 assert(!Object.hasOwn(second.prepared.decisionRequest.questions,'scope'));
 assert(!Object.hasOwn(result,'canGenerateSql'));
 assert(!Object.hasOwn(result,'evidenceStatus'));
 assert(result.products.every(p=>p.mappings.every(m=>p.conceptEvidence.paths.some(path=>path.pathKey===m.selectedPathKey&&path.anchorConceptKeys.includes(m.bindingConceptKey)))));
 for(const score of result.candidateScores)assert.deepEqual(score.probabilities,result.decision.concept.answers[score.objectKey].probabilities);
 for(const score of result.pathScores)assert.deepEqual(score.probabilities,result.decision.path.answers[`path::${score.pathKey}`].probabilities);
}
assert.equal(outputs.securities_aum.candidateScores.length,4);
assert.equal(outputs.deposit_both.selectedConceptPaths.length,2);
assert.equal(outputs.securities_compare.selectedConceptPaths.length,2);
const income=outputs.deposit_income.products[0].mappings[0];
for(const source of ['DSDEP.DEP_NT_ACCT_HS','DSDEP.DEP_FN_ACCT_HS','DSDEP.EMP_DEP_NT_ACCT_HS'])assert(income.requiredBaseTables.includes(source));
assert(income.sqlEvidence.statements.some(s=>s.properties.statementType==='DELETE'));
assert.equal(new Set(income.sqlEvidence.relationships.filter(r=>r.to.endsWith('INCOME_066_TMP_DETAIL_04')).map(r=>r.from)).size,3);
// A candidate marked uncertain must not suppress an independently included candidate.
const data=read('lazy_live_securities_aum.json'),first=concepts(data.catalog,data.request,['securities_fund']);
const mixed=native(first.prepared,k=>k==='securities_fund::aum'?'included':'uncertain');
mixed.answers['securities_fund::aum'].probabilities={included:0.12,uncertain:0.87,excluded:0.01};
const mixedChoice=run('Concept Decision Result',mixed,{'Jev - Prepare Concepts':first.prepared});
assert.deepEqual(mixedChoice.selectedConcepts.map(c=>c.productCode),['securities_fund']);
assert.equal(mixedChoice.candidateScores.find(c=>c.productCode==='securities_fund').probability,0.12);
// Same concept, two full paths, independent native choices.
const duplicated=structuredClone(data.paths),fields=duplicated.data.fields,row=structuredClone(duplicated.data.values[0]);
row[fields.indexOf('businessPath')].relationships[0].properties.scope='另一個業務範圍';duplicated.data.values.push(row);
const alternatives=routes(duplicated,first);
assert.equal(alternatives.formatted.pathCandidates.length,2);
assert.equal(alternatives.choice.selectedPaths.length,2);
const mixedPaths=native(alternatives.prepared,k=>k===`path::${alternatives.formatted.pathCandidates[0].pathKey}`?'included':'uncertain');
const picked=run('Route Decision Result',mixedPaths,{'Jev - Prepare Paths':alternatives.prepared});
assert.equal(picked.selectedPaths.length,1);
assert.equal(picked.pathScores.filter(p=>p.judgement==='uncertain').length,1);
// Multiple selected concepts can be members of a single full path.
const compare=read('lazy_live_securities_compare.json'),both=concepts(compare.catalog,compare.request,['securities_fund','securities_bond']);
const shared=structuredClone(data.paths),sharedPath=shared.data.values[0][shared.data.fields.indexOf('businessPath')];
const anchor=both.choice.selectedConcepts.find(c=>c.productCode==='securities_bond');
sharedPath.nodes.splice(1,0,{key:anchor.conceptKey,labels:['SharedProduct'],properties:{code:anchor.productCode,name:anchor.productName,ontologyId:'pb_shared'}});
const edge=sharedPath.relationships[0];
sharedPath.relationships.splice(0,1,{from:edge.from,to:anchor.conceptKey,type:'AUM_ROLLS_UP_TO',properties:{}},{...edge,from:anchor.conceptKey});
const sharedResult=routes(shared,both);
assert.equal(sharedResult.choice.selectedPaths.length,1);
assert.equal(sharedResult.choice.selectedConceptPaths[0].anchorConceptKeys.length,2);
assert.equal(sharedResult.choice.selections.length,2);
assert.equal(w.nodes.length,12);
assert(!w.nodes.some(n=>n.type==='n8n-nodes-base.if'));
const names=w.nodes.map(n=>n.name);
for(let i=0;i<names.length-1;i++)assert.deepEqual(w.connections[names[i]].main,[[{node:names[i+1],type:'main',index:0}]]);
for(const node of w.nodes.filter(n=>n.type==='n8n-nodes-base.code')){
 new Function('$input','$',node.parameters.jsCode);
 assert(!node.parameters.jsCode.includes('throw new Error'));
}
const main=read('main.lazy.ready.json');
assert(!main.nodes.some(n=>['KB Route and Evidence Ready','KB Not Ready'].includes(n.name)));
assert.equal(main.connections['Product Concept KB'].main[0][0].node,'Available Source Metadata');
for(const node of main.nodes.filter(n=>n.type==='n8n-nodes-base.code'))new Function('$input','$',node.parameters.jsCode);
const queryExpression=main.nodes.find(n=>n.name==='Execute a SQL query').parameters.query;
const executeQuery=text=>new Function('$json','$','return ('+queryExpression.slice(2,-2).trim()+')')({text},n=>({item:{json:{available_sources:[]}}}));
assert.equal(executeQuery('SELECT 1 AS amount;'),'SELECT 1 AS amount;');
assert.match(executeQuery('DELETE FROM example;'),/KB_SQL_NOT_READ_ONLY/);
const normalizeCode=main.nodes.find(n=>n.name==='Normalize SQL Result').parameters.jsCode;
const normalized=new Function('$input','$',normalizeCode)({all:()=>[{json:{amount:123}}]},n=>n==='Product Concept KB'?{first:()=>({json:outputs.securities_aum})}:{item:{json:{output:{resolved_query:'test',selected_metric_codes:['aum_securities_month_end']}}}})[0].json;
assert.equal(normalized.status,'success');
assert.deepEqual(normalized.candidateScores,outputs.securities_aum.candidateScores);
for(const n of ['Aura - Concept Catalog','Aura - Concept Paths','Aura - Mappings']){
 const body=w.nodes.find(x=>x.name===n).parameters.jsonBody;
 assert(!body.slice(3,-2).includes('}}'));
}
fs.writeFileSync(__dirname+'/simplified_result_examples.json',JSON.stringify(outputs,null,2));
fs.writeFileSync(__dirname+'/lazy_contract_validation.json',JSON.stringify({contract:'pb_kb_lazy_routes_v4',kbNodes:12,mainNodes:main.nodes.length,cases:Object.keys(outputs),syntheticDecisionFixtures:true,liveJev:false,manyRoutesPerConcept:true,manyConceptsPerRoute:true,rawProbabilitiesPreserved:true,mixedUncertainDoesNotBlock:true},null,2));
console.log('Five graph fixtures, mixed uncertain choices, many-to-many paths, raw probabilities and linear workflow passed.');

