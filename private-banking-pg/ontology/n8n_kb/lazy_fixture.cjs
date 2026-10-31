// Synthetic native choices for contract/read-only graph tests; not live Jev output.
const fs=require('node:fs');const w=JSON.parse(fs.readFileSync(__dirname+'/PB_AUM_Income_KB.lazy.ready.json','utf8'));
const run=(name,input,prior={})=>new Function('$input','$',w.nodes.find(n=>n.name===name).parameters.jsCode)({first:()=>({json:input}),all:()=>[{json:input}]},n=>({first:()=>({json:prior[n]}),item:{json:prior[n]}}))[0].json;
const native=(context,choose)=>({model:'typesafe/jev-1.13-20260917',id:'synthetic-fixture',answers:Object.fromEntries(Object.entries(context.decisionRequest.questions).map(([key,q])=>{
 const labels=Object.keys(q.criteria),choice=key==='scope'?'clear':choose(key);return [key,{type:'choice',choice,confidence:0.9,probabilities:Object.fromEntries(labels.map(k=>[k,k===choice?0.9:0.05]))}];}))});
function concepts(catalog,request,products){
 const prepared=run('Jev - Prepare Concepts',catalog,{'KB Input':request});
 const choice=run('Concept Decision Result',native(prepared,key=>prepared.candidates.some(c=>c.objectKey===key&&products.includes(c.productCode))?'included':'excluded'),{'Jev - Prepare Concepts':prepared});
 return {prepared,choice};
}
function routes(paths,concept){
 const formatted=run('Concept Routes',paths,{'Concept Decision Result':concept.choice});
 const prepared=run('Jev - Prepare Paths',formatted);
 const choice=run('Route Decision Result',native(prepared,()=> 'included'),{'Jev - Prepare Paths':prepared});
 return {formatted,prepared,choice};
}
module.exports={run,native,concepts,routes,w};
if(require.main===module){const v=JSON.parse(fs.readFileSync(0,'utf8'));const first=concepts(v.catalog,v.request,v.products);process.stdout.write(JSON.stringify(v.paths?{concept:first,...routes(v.paths,first)}:first));}
