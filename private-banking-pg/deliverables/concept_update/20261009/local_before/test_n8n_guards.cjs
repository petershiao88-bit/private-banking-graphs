// Runs actual Code-node source with minimal n8n inputs, without network calls.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const read = f => fs.readFileSync(path.join(__dirname,f),'utf8');
const run = (file,input,catalog) => new Function('$input','$',read(file))(
  {first:() => ({json:input})}, name => {
    assert.equal(name,'ConceptCatalog');
    if (!catalog) throw new Error('No first-query result in this execution');
    return {first:() => ({json:catalog})};
  });
const catalog = JSON.parse(read('01_output.json'));
const fields = ['productCode','productName','definition','status','aumStatus','incomeStatus','aumMetrics','incomeMetrics'];
const response = {data:{fields,values:catalog.products.map(p => fields.map(f => p[f]))},bookmarks:['not-for-the-agent']};
assert.deepEqual(run('n8n_01_project_output.js',response)[0].json,catalog);
assert.deepEqual(run('n8n_01_prepare.js',{statement:'MATCH (n) RETURN n'})[0].json,JSON.parse(read('01_request.json')));
let successfulPairs = 0;
for (const p of catalog.products) for (const domain of ['aum','income']) {
  const prepared = run('n8n_02_prepare.js',{productCode:p.productCode,domain},catalog)[0].json;
  assert.equal(prepared.statement,read('02_lookup_mapping.cypher').trim());
  assert.deepEqual(prepared.parameters,{productCode:p.productCode,domain});
  successfulPairs++;
}
const invalid = [
  {productCode:'bank_insurance',domain:'income',statement:'MATCH (n) RETURN n'},
  {productCode:"' MATCH (n) RETURN n //",domain:'income'},
  {productCode:'bank_insurance',domain:'all'},
  {productCode:[],domain:'income'},
  {domain:'aum'},
];
for (const input of invalid) assert.throws(() => run('n8n_02_prepare.js',input,catalog));
assert.throws(() => run('n8n_02_prepare.js',{productCode:'bank_insurance',domain:'income'}));
const leaked = structuredClone(response);
leaked.data.values[0][6][0].sql = 'SELECT secret FROM hidden';
assert.throws(() => run('n8n_01_project_output.js',leaked));
const leakedText = structuredClone(response);
leakedText.data.values[0][2] = 'INCOME_028';
assert.throws(() => run('n8n_01_project_output.js',leakedText));
assert.throws(() => run('n8n_01_project_output.js',{errors:[{message:'SQL internals'}]}));
const mappingFields = ['productCode','productName','domain','status','mappingActive','calculationAuthorized','mappings'];
for (const example of Object.values(JSON.parse(read('02_output_examples.json')))) {
  const out = run('n8n_02_project_output.js',{data:{fields:mappingFields,values:[mappingFields.map(f => example[f])]}});
  assert.deepEqual(out[0].json,example);
}
const report = {successfulPairs,invalidInputsRejected:invalid.length,missingCatalogRejected:true,
  firstRequestIgnoresInjectedStatement:true,extraMetricPropertyRejected:true,technicalTextRejected:true,
  rawApiErrorsNotForwarded:true,exampleProjections:4,liveN8nExecution:false};
fs.writeFileSync(path.join(__dirname,'n8n_guard_validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
