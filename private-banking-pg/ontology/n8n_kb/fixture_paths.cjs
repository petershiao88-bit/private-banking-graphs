// Read-only query fixture, not a Jev decision or a workflow bypass.
const fs=require('node:fs');const {concept,request,productCode}=JSON.parse(fs.readFileSync(0,'utf8'));
const run=(file,input,prior={})=>new Function('$input','$',fs.readFileSync(__dirname+'/'+file,'utf8'))({first:()=>({json:input})},name=>({first:()=>({json:prior[name]})}))[0].json;
const catalog=run('concept_catalog.js',concept,{'KB Input':request});
process.stdout.write(JSON.stringify(run('concept_paths.js',catalog).pathCandidates.filter(p=>p.productCode===productCode)));
