// Name this Code node ConceptCatalog. Run Once for All Items.
// Input: Neo4j Query API JSON body. Return only the explicit business fields.
const body = $input.first().json;
const legacyFields = ['productCode','productName','aumDefinition','incomeDefinition','aumMetrics','incomeMetrics'];
const businessFields = ['definition','productCategory','businessChannel','customerNeed','serviceDescription'];
const classificationFields = ['subsidiary','currencyType','structureType','depositorType','fundType','marketRegion','dealingMode'];
const expandedFields = [...legacyFields.slice(0,4),...businessFields,...legacyFields.slice(4)];
const currentFields = [...legacyFields.slice(0,4),...businessFields,...classificationFields,...legacyFields.slice(4)];
const archivedFields = [...legacyFields.slice(0,4),'offeringType',...businessFields,...legacyFields.slice(4)];
const fields = body.data?.fields;
const metricFields = ['metricCode','name','definition'];
const fail = () => { throw new Error('Concept catalog unavailable'); };
if (body.errors?.length || !body.data || ![legacyFields,expandedFields,currentFields,archivedFields].some(schema=>JSON.stringify(fields)===JSON.stringify(schema))) fail();
const cleanMetric = m => {
  if (!m || Object.keys(m).sort().join(',') !== [...metricFields].sort().join(',')) fail();
  if (!metricFields.every(k => typeof m[k] === 'string')) fail();
  return {metricCode:m.metricCode,name:m.name,definition:m.definition};
};
if (!Array.isArray(body.data.values) || !body.data.values.length) fail();
const products = body.data.values.map(row => {
  if (!Array.isArray(row) || row.length !== fields.length) fail();
  const p=Object.fromEntries(fields.map((field,i)=>[field,row[i]]));
  if (!legacyFields.slice(0,4).every(k=>typeof p[k]==='string') || !p.productName || !/^[a-z][a-z0-9_]*$/.test(p.productCode)) fail();
  if (!Array.isArray(p.aumMetrics) || !Array.isArray(p.incomeMetrics) || !(p.aumMetrics.length+p.incomeMetrics.length)) fail();
  if (Boolean(p.aumDefinition)!==Boolean(p.aumMetrics.length) || Boolean(p.incomeDefinition)!==Boolean(p.incomeMetrics.length)) fail();
  for (const field of [...businessFields,...classificationFields]) if (p[field]!=null && typeof p[field]!=='string') fail();
  const out={productCode:p.productCode,productName:p.productName,aumDefinition:p.aumDefinition,incomeDefinition:p.incomeDefinition};
  for (const field of [...businessFields,...classificationFields]) if (p[field]!=null) out[field]=p[field];
  return {...out,aumMetrics:p.aumMetrics.map(cleanMetric),incomeMetrics:p.incomeMetrics.map(cleanMetric)};
});
if (new Set(products.map(p => p.productCode)).size !== products.length) fail();
const pending = products.find(p => p.productCode === 'bank_collective_account');
if (pending && (pending.incomeDefinition !== '' || pending.incomeMetrics.length)) fail();
const technical = /\b(?:SQL|CASE|SELECT|WHERE|JOIN|STAGE|FH_TYP|SUB_TYPE|CUST_ID|AMT|PROD_TYPE|CFEE|ABFEE|TSSN)\b|(?:AUM|INCOME)_[0-9]|DSPMS\.|\b\w+\.\w+\b/i;
if (technical.test(JSON.stringify(products))) fail();
return [{json:{products}}];
