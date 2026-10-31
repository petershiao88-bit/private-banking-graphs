const fs=require('node:fs'),assert=require('node:assert/strict');
const {run,native,workflow}=require('./full_graph_fixture.cjs');
const read=name=>JSON.parse(fs.readFileSync(__dirname+'/'+name,'utf8'));
function first(data,choose){
 const prepared=run('Jev - Prepare Concept Paths',data.graph,{'KB Input':data.request});
 const answer=native(prepared.conceptPathCandidates,'pathKey',choose|| (path=>data.select.some(s=>s.domain===path.domain&&path.productCodes.includes(s.productCode))?'included':'excluded'));
 return {prepared,answer,choice:run('Concept Path Result',answer,{'Jev - Prepare Concept Paths':prepared})};
}
function second(data,concept,choose=()=> 'included'){
 const prepared=run('Jev - Prepare Mapping Paths',data.mappings,{'Concept Path Result':concept.choice});
 const answer=native(prepared.mappingPathCandidates,'mappingPathKey',choose);
 return {prepared,answer,result:run('KB Result',answer,{'Jev - Prepare Mapping Paths':prepared})};
}
const report={},examples={};
for(const name of ['deposit_aum','deposit_income','securities_fund','securities_all','deposit_both']){
 const data=read(`full_graph.live_${name}.json`),concept=first(data),mapping=second(data,concept);
 const result=mapping.result;
 assert.equal(concept.prepared.conceptGraph.nodes.length,27);
 assert.equal(concept.prepared.conceptGraph.relationships.length,40);
 assert.equal(concept.prepared.conceptPathCandidates.length,30);
 assert.equal(concept.choice.selectedConceptPaths.length,data.select.length);
 assert.equal(result.products.length,data.select.length);
 assert(result.selectedMappingPaths.length>=data.select.length);
 assert(!JSON.stringify(concept.prepared.decisionRequest).match(/StagingOutput|SqlTable|SELECT |AUM_025|DSPBM\./));
 for(const score of result.conceptPathScores)assert.deepEqual(score.probabilities,concept.answer.answers[score.pathKey].probabilities);
 for(const score of result.mappingPathScores)assert.deepEqual(score.probabilities,mapping.answer.answers[score.mappingPathKey].probabilities);
 assert(result.selectedMappingPaths.every(path=>path.conceptPathKeys.every(key=>result.selectedConceptPaths.some(p=>p.pathKey===key))));
 assert.equal(new Set(result.sqlEvidence.statements.map(statement=>statement.statementKey)).size,result.sqlEvidence.statements.length);
 const state=mapping.prepared.decisionRequest.state;
 assert.equal(state.mappingPaths.length,mapping.prepared.mappingPathCandidates.length);
 assert.equal(state.technicalGraph.relationships.length,mapping.prepared.sqlEvidence.relationships.length);
 assert.deepEqual(state.technicalGraph.statements.map(s=>s.sql),mapping.prepared.sqlEvidence.statements.map(s=>s.properties.sql));
 const edges=new Set(state.technicalGraph.relationships.map(e=>e.id));
 const tables=new Set(state.technicalGraph.tables.map(t=>t.id));
 assert(state.mappingPaths.every(p=>p.tables.every(t=>tables.has(t))&&p.relationships.every(e=>edges.has(e))));
 report[name]={conceptCandidates:30,selectedConceptPaths:result.selectedConceptPaths.length,mappingCandidates:mapping.prepared.mappingPathCandidates.length,
  selectedMappingPaths:result.selectedMappingPaths.length,conceptStateChars:JSON.stringify(concept.prepared.decisionRequest).length,mappingStateChars:JSON.stringify(mapping.prepared.decisionRequest).length};
 examples[name]=result;
}
// Independent included/uncertain outcomes, without a numerical cutoff or top-one truncation.
const data=read('full_graph.live_securities_fund.json'),concept=first(data);
const mixed=native(concept.prepared.conceptPathCandidates,'pathKey',path=>path.productCodes.includes('securities_fund')&&path.domain==='aum'?'included':'uncertain');
const key=concept.choice.selectedConceptPaths[0].pathKey;
mixed.answers[key].probabilities={included:0.12,uncertain:0.87,excluded:0.01};
const low=run('Concept Path Result',mixed,{'Jev - Prepare Concept Paths':concept.prepared});
assert.equal(low.selectedConceptPaths.length,1);
assert.equal(low.conceptPathScores.find(score=>score.pathKey===key).probability,0.12);
assert.equal(low.conceptPathScores.filter(score=>score.choice==='uncertain').length,29);
const prepared=second(data,concept).prepared;
const one=native(prepared.mappingPathCandidates,'mappingPathKey',(_,i)=>'uncertain');
const firstKey=prepared.mappingPathCandidates[0].mappingPathKey;
one.answers[firstKey]={type:'choice',choice:'included',probabilities:{included:0.12,uncertain:0.87,excluded:0.01},confidence:0.2};
const retained=run('KB Result',one,{'Jev - Prepare Mapping Paths':prepared});
assert.equal(retained.selectedMappingPaths.length,1);
assert.equal(retained.mappingPathScores.filter(score=>score.choice==='uncertain').length,prepared.mappingPathCandidates.length-1);
// A single selected source path retains both required UNION inputs from the selected implementation.
for(const source of ['DSPBM.PB_FUNDPOSIT_SEC','DSPBM.PB_FUNDPOSIT_SEC_M'])assert(retained.sqlEvidence.tables.some(table=>table.properties.name===source));
assert(retained.sqlEvidence.statements.some(statement=>JSON.stringify(statement).includes('union')));
// Two business paths can share one implementation/source path without duplicate SQL or candidate questions.
const duplicate=structuredClone(data),fields=duplicate.graph.data.fields;
const paths=duplicate.graph.data.values[0][fields.indexOf('businessPaths')];
const path=paths.find(p=>p.nodeKeys[0]==='securities_fund'&&p.domain==='aum');
const alternative=structuredClone(path);alternative.relationshipIds[0]+='-alternative';paths.push(alternative);
const graph=duplicate.graph.data.values[0][fields.indexOf('conceptGraph')];
const edge=structuredClone(graph.relationships.find(edge=>edge.id===path.relationshipIds[0]));edge.id=alternative.relationshipIds[0];edge.properties.scope='alternate';graph.relationships.push(edge);
const many=first(duplicate),secondRow=structuredClone(duplicate.mappings.data.values[0]);
secondRow[duplicate.mappings.data.fields.indexOf('pathKey')]=many.choice.selectedConceptPaths.find(p=>p.relationshipIds[0].endsWith('-alternative')).pathKey;
duplicate.mappings.data.values.push(secondRow);
const shared=second(duplicate,many);
assert.equal(many.choice.selectedConceptPaths.length,2);
assert(shared.prepared.mappingPathCandidates.every(path=>path.conceptPathKeys.length===2));
assert.equal(shared.prepared.mappingPathCandidates.length,prepared.mappingPathCandidates.length);
// No included concepts produces no mapping candidates or fabricated decision probabilities.
const empty=first(data,()=> 'excluded');
const noMappings={data:{fields:data.mappings.data.fields,values:[]}};
const emptyPrepared=run('Jev - Prepare Mapping Paths',noMappings,{'Concept Path Result':empty.choice});
const emptyResult=run('KB Result',{error:{message:'No typed candidate questions'}},{'Jev - Prepare Mapping Paths':emptyPrepared});
assert.equal(emptyResult.selectedMappingPaths.length,0);
assert.equal(emptyResult.conceptPathScores.length,30);
assert.deepEqual(emptyResult.decision.mapping.error,{message:'No typed candidate questions'});
assert.equal(workflow.nodes.length,9);
assert.equal(workflow.nodes.filter(node=>node.type==='n8n-nodes-base.httpRequest').length,4);
assert(!workflow.nodes.some(node=>node.type==='n8n-nodes-base.if'));
assert.deepEqual(workflow.pinData,{});
for(const node of workflow.nodes.filter(node=>node.type==='n8n-nodes-base.code'))new Function('$input','$',node.parameters.jsCode);
for(let i=0;i<8;i++)assert.equal(workflow.connections[workflow.nodes[i].name].main[0][0].node,workflow.nodes[i+1].name);
for(const name of ['Aura - Full Concept Graph','Aura - Mapping Paths']){
 const expression=workflow.nodes.find(node=>node.name===name).parameters.jsonBody;
 const value=new Function('$json','return ('+expression.slice(3,-2)+')')({selectedPaths:concept.choice.selectedPaths});
 assert(value.statement.startsWith(name==='Aura - Full Concept Graph'?'CALL':'UNWIND'));
}
fs.writeFileSync(__dirname+'/full_graph.contract_validation.json',JSON.stringify({nineNodes:true,liveGraphFixtures:true,syntheticDecisions:true,liveJev:false,cases:report,
 rawProbabilitiesPreserved:true,multiSelection:true,manyToMany:true,sqlDependenciesRetained:true,noMappingInConceptState:true,noPreselection:true},null,2));
fs.writeFileSync(__dirname+'/full_graph.result_examples.json',JSON.stringify(examples,null,2));
const main=read('main.full_graph.ready.json'),oldMain=read('main.simplified.saved.json');
assert.equal(main.nodes.length,32);
assert.deepEqual(main.connections,oldMain.connections);
const changed=main.nodes.filter(n=>JSON.stringify(n.parameters)!==JSON.stringify(oldMain.nodes.find(o=>o.name===n.name).parameters)).map(n=>n.name);
assert.deepEqual(changed.sort(),['Normalize SQL Result','SQL Reasoning Agent','保留候選機率'].sort());
const router={resolved_query:'測試',selected_metric_codes:['aum_securities_month_end']};
const normalized=new Function('$input','$',main.nodes.find(n=>n.name==='Normalize SQL Result').parameters.jsCode)(
 {all:()=>[{json:{error_message:'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE'}}]},name=>({first:()=>({json:examples.securities_fund}),item:{json:{output:router}}}))[0].json;
assert.deepEqual(normalized.conceptPathScores,examples.securities_fund.conceptPathScores);
assert.deepEqual(normalized.mappingPathScores,examples.securities_fund.mappingPathScores);
assert.equal(normalized.status,'unsupported');
const reply=new Function('$input','$',main.nodes.find(n=>n.name==='保留候選機率').parameters.jsCode)(
 {first:()=>({json:{text:'測試回答'}})},()=>({first:()=>({json:normalized})}))[0].json;
assert.deepEqual(reply.decision,examples.securities_fund.decision);
assert.deepEqual(reply.mappingPathScores,normalized.mappingPathScores);
assert(reply.text.includes('映射路徑的納入機率'));
console.log(JSON.stringify(report));
