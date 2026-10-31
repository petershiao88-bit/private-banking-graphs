const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=__dirname;
const wf=JSON.parse(fs.readFileSync(path.join(root,process.argv[2] || 'PB_AUM_Income_KB.jev.ready.json'),'utf8'));
const main=JSON.parse(fs.readFileSync(path.join(root,process.argv[3] || 'main.jev.ready.json'),'utf8'));
const fixtures=JSON.parse(fs.readFileSync(path.join(root,'test_fixtures.json'),'utf8'));
const code=name=>wf.nodes.find(n=>n.name===name).parameters.jsCode;
const run=(js,input,prior={})=>new Function('$input','$',js)({first:()=>({json:input}),all:()=>[{json:input}]},name=>({first:()=>({json:prior[name]})}))[0].json;
const api=rows=>({data:{fields:Object.keys(rows[0]||{productCode:0,domain:0,status:0,mappings:0}),values:rows.map(Object.values)}});
const request={question:'證券基金 AUM',domains:['aum'],metricCodes:['aum_securities_month_end']};
const actual=JSON.parse(fs.readFileSync(path.join(root,'evidence_live_securities_aum.json'),'utf8'));
const catalog=run(code('Concept Catalog'),actual.concept,{'KB Input':request});
const paths=run(code('Concept Paths'),catalog);
const prepared=run(code('Jev - Prepare Objects'),paths);
let checks=0;
const check=fn=>{fn();checks++;};
const dist=(choice,labels)=>({type:'choice',choice,confidence:0.9,probabilities:Object.fromEntries(labels.map(k=>[k,k===choice?0.9:0.05]))});
const response=(kind='single')=>({id:'fixture',model:'typesafe/jev-1.13-20260917',provider:'TypeSafe',answers:{
  scope:dist(kind==='ambiguous'?'ambiguous':kind==='none'?'none':'clear',['clear','ambiguous','none']),
  ...Object.fromEntries([...prepared.candidates,...prepared.pathCandidates.map(p=>({...p,objectKey:`path::${p.pathKey}`}))].map(c=>[c.objectKey,dist(kind==='ambiguous'?'uncertain':kind==='multiple'||kind==='single'&&c.productCode==='securities_fund'?'included':'excluded',['included','uncertain','excluded'])]))
}});
const prior={'Concept Catalog':catalog,'Jev - Prepare Objects':prepared};
const evaluate=body=>run(code('Jev - Evaluate Objects'),body,prior);
check(()=>assert.equal(prepared.candidates.length,4));
check(()=>assert.equal(Object.keys(prepared.decisionRequest.questions).length,5+paths.pathCandidates.length));
for(const kind of ['single','multiple','ambiguous','none']){
 const body=response(kind),result=evaluate(body);
 check(()=>assert.equal(result.candidateScores.length,4));
 check(()=>assert.deepEqual(result.decision.answers,body.answers));
 check(()=>assert.equal(result.selections.length,kind==='single'?1:kind==='multiple'?4:0));
 check(()=>assert.equal(result.status,kind==='ambiguous'?'needs_clarification':kind==='none'?'no_match':'selected'));
 prior['Jev - Evaluate Objects']=result;
 const mapped=run(code('KB Result'),api([]),prior);
 check(()=>assert.deepEqual(mapped.candidateScores,result.candidateScores));
 check(()=>assert.equal(mapped.products.length,result.selections.length));
}
for(const mutate of [b=>delete b.answers[prepared.candidates[0].objectKey],b=>b.answers.extra={},b=>b.model='typesafe/jev-router',b=>b.error={message:'bad'},b=>b.answers.scope.probabilities.clear='0.9',b=>b.answers.scope.probabilities.clear=-1,b=>b.answers.scope.probabilities.clear=NaN,b=>b.answers.scope.choice='none',b=>b.answers.scope.confidence=Infinity]){
 const body=response();mutate(body);check(()=>assert.throws(()=>evaluate(body)));
}
const empty=run(code('Jev - Prepare Objects'),{...catalog,products:[],pathCandidates:[]});
const allExcluded=response('none'); allExcluded.answers.scope=dist('ambiguous',['clear','ambiguous','none']);
check(()=>assert.equal(evaluate(allExcluded).status,'no_match'));
const emptyResult=run(code('Jev - Evaluate Objects'),{model:'typesafe/jev-1.13',answers:{scope:dist('none',['clear','ambiguous','none'])}},{'Jev - Prepare Objects':empty});
check(()=>assert.deepEqual(emptyResult.candidateScores,[]));
check(()=>assert.equal(emptyResult.status,'no_match'));
const fund=catalog.products.find(c=>c.productCode==='securities_fund');
const pairedProduct=structuredClone(fund);
const incomePath=pairedProduct.conceptEvidence.incomePaths[0];
const incomeCode=incomePath.nodes[1].properties.code;
pairedProduct.matchedScopes=[{domain:'aum',metricCode:'aum_securities_month_end'},{domain:'income',metricCode:incomeCode}];
const paired=run(code('Jev - Prepare Objects'),run(code('Concept Paths'),{...catalog,domains:['aum','income'],products:[pairedProduct]}));
check(()=>assert.equal(paired.candidates.length,2));
const pairedBody={model:'typesafe/jev-1.13',answers:{scope:dist('clear',['clear','ambiguous','none']),...Object.fromEntries([...paired.candidates,...paired.pathCandidates.map(p=>({objectKey:`path::${p.pathKey}`}))].map(c=>[c.objectKey,dist('included',['included','uncertain','excluded'])]))}};
const pairedResult=run(code('Jev - Evaluate Objects'),pairedBody,{'Jev - Prepare Objects':paired});
check(()=>assert.deepEqual(pairedResult.selections.map(s=>s.domain).sort(),['aum','income']));
const expression=wf.nodes.find(n=>n.name==='Aura - Mappings').parameters.jsonBody.slice(3,-2).trim();
const mapping=choice=>new Function('$json','$','return ('+expression+')')(choice,name=>({first:()=>({json:prior[name]})}));
check(()=>assert.throws(()=>mapping({selections:[{productCode:'invented',domain:'aum'}]}),/路徑/));
check(()=>assert.throws(()=>mapping({selections:[{productCode:'securities_fund',domain:'income'}]}),/路徑/));
check(()=>assert.equal(wf.nodes.find(n=>n.name==='Jev - Decisions API').parameters.nodeCredentialType,'openRouterApi'));
check(()=>assert(!wf.nodes.some(n=>n.type.includes('lmChat'))));
const kb=main.nodes.find(n=>n.name==='Product Concept KB');
const sqlExpression=main.nodes.find(n=>n.name==='Execute a SQL query').parameters.query;
check(()=>assert(/^(=)?\{\{/.test(sqlExpression)));
const sqlBody=sqlExpression.replace(/^=/,'').slice(2,-2).trim();
const makeSql=(text,status)=>new Function('$json','$','return ('+sqlBody+')')({text},name=>({first:()=>({json:name==='Product Concept KB'?{status,canGenerateSql:true}:{available_sources:[]}}),item:{json:{available_sources:[]}}}));
check(()=>assert.equal(makeSql("SELECT 'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE' AS error_message;",'selected'),"SELECT 'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE' AS error_message;"));
check(()=>assert.match(makeSql('SELECT 123 AS amount;','needs_clarification'),/KB_PRODUCT_OR_DEFINITION_UNRESOLVED/));
check(()=>assert.equal(kb.type,'n8n-nodes-base.executeWorkflow'));
check(()=>assert.equal(main.connections['Available Source Metadata'].main[0][0].node,'SQL Reasoning Agent'));
check(()=>assert.equal(main.connections.Response.main[0][0].node,'保留候選機率'));
const replyCode=main.nodes.find(n=>n.name==='保留候選機率').parameters.jsCode;
const normalized={candidateScores:evaluate(response()).candidateScores,decision:{model:'typesafe/jev-1.13'},kbStatus:'selected'};
const reply=run(replyCode,{text:'測試回答'},{'Normalize SQL Result':normalized});
check(()=>assert.deepEqual(reply.candidateScores,normalized.candidateScores));
check(()=>assert.equal(reply.text.split('\n').filter(s=>s.startsWith('| ')&&!s.includes('產品')).length,4));
for(const n of wf.nodes.filter(n=>n.type==='n8n-nodes-base.code'))check(()=>new Function('$input','$',n.parameters.jsCode));
console.log(JSON.stringify({checksPassed:checks,liveApi:false,cases:['single','multiple','ambiguous','none','empty','invalid_response','scope_guards','end_to_end_probability_retention']}));
