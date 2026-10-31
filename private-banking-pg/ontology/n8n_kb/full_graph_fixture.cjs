const fs=require('node:fs');
const workflow=JSON.parse(fs.readFileSync(__dirname+'/PB_AUM_Income_KB.full_graph.ready.json','utf8'));
function run(name,input,prior={}){
 const node=workflow.nodes.find(node=>node.name===name);
 return new Function('$input','$',node.parameters.jsCode)({first:()=>({json:input})},name=>({first:()=>({json:prior[name]})}))[0].json;
}
function native(candidates,key,choose){return {id:'synthetic-contract-fixture',model:'typesafe/jev-1.13',provider:'synthetic-test-only',answers:Object.fromEntries(candidates.map(candidate=>{
 const choice=choose(candidate);
 return [candidate[key],{type:'choice',choice,probabilities:{included:choice==='included'?0.86:0.06,uncertain:choice==='uncertain'?0.86:0.08,excluded:choice==='excluded'?0.86:0.06},confidence:0.8}];
}))};}
if(require.main===module){
 const data=JSON.parse(fs.readFileSync(0,'utf8'));
 const prepared=run('Jev - Prepare Concept Paths',data.graph,{'KB Input':data.request});
 const answer=native(prepared.conceptPathCandidates,'pathKey',path=>data.select.some(selection=>selection.domain===path.domain&&path.productCodes.includes(selection.productCode))?'included':'excluded');
 const choice=run('Concept Path Result',answer,{'Jev - Prepare Concept Paths':prepared});
 process.stdout.write(JSON.stringify({prepared,choice}));
}
module.exports={run,native,workflow};
