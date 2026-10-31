// Name this Code node ConceptCatalog. Run Once for All Items.
// Input: Neo4j Query API JSON body. Return only the explicit business fields.
const body = $input.first().json;
const fields = ['productCode','productName','definition','status','aumStatus','incomeStatus','aumMetrics','incomeMetrics'];
const metricFields = ['metricCode','name','definition','status'];
const fail = () => { throw new Error('Concept catalog unavailable'); };
if (body.errors?.length || !body.data || JSON.stringify(body.data.fields) !== JSON.stringify(fields)) fail();
const cleanMetric = m => {
  if (!m || Object.keys(m).sort().join(',') !== [...metricFields].sort().join(',')) fail();
  if (!metricFields.every(k => typeof m[k] === 'string')) fail();
  return {metricCode:m.metricCode,name:m.name,definition:m.definition,status:m.status};
};
if (!Array.isArray(body.data.values) || body.data.values.length !== 15) fail();
const products = body.data.values.map(row => {
  if (row.length !== fields.length || !row.slice(0,6).every(v => typeof v === 'string')) fail();
  if (!Array.isArray(row[6]) || !row[6].length || !Array.isArray(row[7]) || !row[7].length) fail();
  return {productCode:row[0],productName:row[1],definition:row[2],status:row[3],
    aumStatus:row[4],incomeStatus:row[5],aumMetrics:row[6].map(cleanMetric),incomeMetrics:row[7].map(cleanMetric)};
});
if (new Set(products.map(p => p.productCode)).size !== products.length) fail();
const pending = products.find(p => p.productCode === 'bank_collective_account');
if (!pending || pending.incomeStatus !== 'pending_confirmation') fail();
const technical = /\b(?:SQL|CASE|SELECT|WHERE|JOIN|STAGE|FH_TYP|SUB_TYPE|CUST_ID|AMT|PROD_TYPE|CFEE|ABFEE|TSSN)\b|(?:AUM|INCOME)_[0-9]|DSPMS\.|\b\w+\.\w+\b/i;
if (technical.test(JSON.stringify(products))) fail();
return [{json:{products}}];
