// Code node: Run Once for All Items. Do not return raw API errors or metadata.
const body = $input.first().json;
const fields = ['productCode','productName','domain','status','mappingActive','calculationAuthorized','mappings'];
if (body.errors?.length || !body.data || JSON.stringify(body.data.fields) !== JSON.stringify(fields)) {
  throw new Error('Mapping lookup unavailable');
}
if (!Array.isArray(body.data.values) || body.data.values.length !== 1) throw new Error('Mapping not found');
const [productCode,productName,domain,status,mappingActive,calculationAuthorized,mappings] = body.data.values[0];
if (body.data.values[0].length!==fields.length || typeof productCode!=='string' || typeof productName!=='string' || !['aum','income'].includes(domain) || typeof status!=='string' || typeof mappingActive!=='boolean' || !Array.isArray(mappings) || !mappings.length || calculationAuthorized !== false) throw new Error('Invalid mapping result');
if(status==='mapping_draft_rules'){
 for(const mapping of mappings){
  if(mapping.mappingFormat!=='mapping_draft_rules'||typeof mapping.sourceTable!=='string'||!mapping.sourceTable||typeof mapping.calculationRules!=='string')throw new Error('Invalid draft mapping rules');
  let rules;try{rules=JSON.parse(mapping.calculationRules);}catch{throw new Error('Invalid draft mapping rules');}
  if(!Array.isArray(rules)||!rules.length)throw new Error('Invalid draft mapping rules');
 }
}
if (productCode === 'bank_collective_account' && domain === 'income' && (status !== 'pending_confirmation' || mappingActive !== false)) {
  throw new Error('Pending definition must be retained');
}
return [{json:{productCode,productName,domain,status,mappingActive,calculationAuthorized,mappings}}];
