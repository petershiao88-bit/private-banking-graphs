const fs=require('node:fs'),assert=require('node:assert/strict');
const read=name=>JSON.parse(fs.readFileSync(__dirname+'/'+name,'utf8'));
const workflow=read('PB_AUM_Income_KB.single_jev.ready.json');
const {native}=require('./full_graph_fixture.cjs');
function run(name,input,prior={}){return new Function('$input','$',workflow.nodes.find(n=>n.name===name).parameters.jsCode)({first:()=>({json:input})},n=>({first:()=>({json:prior[n]})}))[0].json;}
function first(data,choose){
 const prepared=run('Jev - Prepare Concept Paths',data.graph,{'KB Input':data.request});
 const answer=native(prepared.conceptPathCandidates,'pathKey',choose||(p=>data.select.some(s=>s.domain===p.domain&&p.productCodes.includes(s.productCode))?'included':'excluded'));
 return {prepared,answer,choice:run('Concept Path Result',answer,{'Jev - Prepare Concept Paths':prepared})};
}
const cases={},examples={};
for(const name of ['deposit_aum','deposit_income','securities_fund','securities_all','deposit_both']){
 const data=read(`full_graph.live_${name}.json`),concept=first(data);
 const result=run('KB Result',data.mappings,{'Concept Path Result':concept.choice});
 assert.equal(concept.prepared.conceptGraph.nodes.length,27);
 assert.equal(concept.prepared.conceptPathCandidates.length,30);
 assert.equal(result.products.length,data.select.length);
 assert(result.mappingPaths.length>=data.select.length);
 assert(!JSON.stringify(concept.prepared.decisionRequest).match(/StagingOutput|SqlTable|SELECT |AUM_025|DSPBM\./));
 for(const score of result.conceptPathScores)assert.deepEqual(score.probabilities,concept.answer.answers[score.pathKey].probabilities);
 assert(result.mappingPaths.every(p=>p.conceptPathKeys.every(k=>result.selectedConceptPaths.some(s=>s.pathKey===k))));
 assert.equal(new Set(result.sqlEvidence.statements.map(s=>s.statementKey)).size,result.sqlEvidence.statements.length);
 assert(!('mappingPathScores' in result));assert(!('mapping' in result.decision));
 const keys=new Set(result.sqlEvidence.tables.map(t=>t.key)),edges=new Set(result.sqlEvidence.relationships.map(e=>e.id));
 assert(result.mappingPaths.every(p=>p.tableKeys.every(k=>keys.has(k))&&p.relationshipIds.every(k=>edges.has(k))));
 cases[name]={conceptCandidates:30,selectedConceptPaths:result.selectedConceptPaths.length,mappingPaths:result.mappingPaths.length,sqlStatements:result.sqlEvidence.statements.length};examples[name]=result;
}
const fund=examples.securities_fund;
assert.equal(fund.mappingPaths.length,2);assert.equal(examples.securities_all.mappingPaths.length,17);assert.equal(examples.deposit_both.mappingPaths.length,12);
for(const source of ['DSPBM.PB_FUNDPOSIT_SEC','DSPBM.PB_FUNDPOSIT_SEC_M'])assert(fund.sqlEvidence.tables.some(t=>t.properties.name===source));
assert(fund.sqlEvidence.statements.some(s=>/wkb02\s+as\s+cust_id/i.test(s.properties.sql)));
const data=read('full_graph.live_securities_fund.json'),concept=first(data);
const key=concept.choice.selectedConceptPaths[0].pathKey;
concept.answer.answers[key].probabilities={included:0.12,uncertain:0.87,excluded:0.01};
const low=run('Concept Path Result',concept.answer,{'Jev - Prepare Concept Paths':concept.prepared});
assert.equal(low.selectedConceptPaths.length,1);assert.equal(low.conceptPathScores.find(s=>s.pathKey===key).probability,0.12);
const duplicate=structuredClone(data),fields=duplicate.graph.data.fields,paths=duplicate.graph.data.values[0][fields.indexOf('businessPaths')];
const path=paths.find(p=>p.nodeKeys[0]==='securities_fund'&&p.domain==='aum'),alt=structuredClone(path);alt.relationshipIds[0]+='-alternative';paths.push(alt);
const graph=duplicate.graph.data.values[0][fields.indexOf('conceptGraph')],edge=structuredClone(graph.relationships.find(e=>e.id===path.relationshipIds[0]));edge.id=alt.relationshipIds[0];graph.relationships.push(edge);
const many=first(duplicate),row=structuredClone(duplicate.mappings.data.values[0]);row[duplicate.mappings.data.fields.indexOf('pathKey')]=many.choice.selectedConceptPaths.find(p=>p.relationshipIds[0].endsWith('-alternative')).pathKey;duplicate.mappings.data.values.push(row);
const shared=run('KB Result',duplicate.mappings,{'Concept Path Result':many.choice});
assert.equal(shared.mappingPaths.length,2);assert(shared.mappingPaths.every(p=>p.conceptPathKeys.length===2));
const empty=first(data,()=> 'excluded'),none=run('KB Result',{data:{fields:data.mappings.data.fields,values:[]}}, {'Concept Path Result':empty.choice});
assert.deepEqual(none.mappingPaths,[]);assert.deepEqual(none.products,[]);assert.equal(none.conceptPathScores.length,30);
assert.equal(workflow.nodes.length,7);assert.equal(workflow.nodes.filter(n=>n.type==='n8n-nodes-base.httpRequest').length,3);
assert.equal(workflow.nodes.filter(n=>n.parameters.url?.includes('/decisions')).length,1);assert(!workflow.nodes.some(n=>n.type==='n8n-nodes-base.if'));
for(let i=0;i<6;i++)assert.equal(workflow.connections[workflow.nodes[i].name].main[0][0].node,workflow.nodes[i+1].name);
const main=read('main.single_jev.ready.json'),old=read('main.before_single_jev.saved.json');
assert.equal(main.nodes.length,32);assert.deepEqual(main.connections,old.connections);
assert.deepEqual(main.nodes.filter(n=>JSON.stringify(n.parameters)!==JSON.stringify(old.nodes.find(o=>o.name===n.name).parameters)).map(n=>n.name).sort(),['Normalize SQL Result','SQL Reasoning Agent','保留候選機率'].sort());
const router={resolved_query:'測試',selected_metric_codes:['aum_securities_month_end']};
const normalized=new Function('$input','$',main.nodes.find(n=>n.name==='Normalize SQL Result').parameters.jsCode)({all:()=>[{json:{error_message:'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE'}}]},()=>({first:()=>({json:fund}),item:{json:{output:router}}}))[0].json;
assert.deepEqual(normalized.mappingPaths,fund.mappingPaths);assert.equal(normalized.status,'unsupported');
const reply=new Function('$input','$',main.nodes.find(n=>n.name==='保留候選機率').parameters.jsCode)({first:()=>({json:{text:'測試'}})},()=>({first:()=>({json:normalized})}))[0].json;
assert.deepEqual(reply.conceptPathScores,fund.conceptPathScores);assert(!reply.text.includes('映射路徑的納入機率'));
fs.writeFileSync(__dirname+'/single_jev.contract_validation.json',JSON.stringify({sevenNodes:true,singleJev:true,syntheticDecisions:true,cases,manyToMany:true,allDependenciesRetained:true,emptySelection:true,customerKeySqlPreserved:true},null,2));
fs.writeFileSync(__dirname+'/single_jev.result_examples.json',JSON.stringify(examples,null,2));
console.log(JSON.stringify(cases));
