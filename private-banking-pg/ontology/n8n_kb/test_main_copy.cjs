const fs=require('node:fs');
const assert=require('node:assert/strict');
const w=JSON.parse(fs.readFileSync(__dirname+'/main.copy.deployed.json','utf8'));
const node=name=>w.nodes.find(n=>n.name===name);
const code=node('Normalize SQL Result').parameters.jsCode;
const router={resolved_query:'2026 年 9 月證券基金 AUM',selected_metric_codes:['aum_securities_month_end']};
const run=rows=>new Function('$input','$',code)({all:()=>rows.map(json=>({json}))},()=>({item:{json:{output:router}}}))[0].json;
const cases=[
 ['success',[{total:123}],1],
 ['no_data',[{}],0],
 ['unsupported',[{error_message:'UNSUPPORTED_METRIC_OR_MISSING_SOURCE_TABLE'}],0],
 ['needs_clarification',[{error_message:'KB_PRODUCT_OR_DEFINITION_UNRESOLVED'}],0],
 ['needs_clarification',[{error_message:'KB_METRIC_UNRESOLVED'}],0],
 ['error',[{error:'relation does not exist'}],0],
 ['error',[{error_message:'KB_LOOKUP_FAILED'}],0],
];
for(const [status,rows,count] of cases){const r=run(rows);assert.equal(r.status,status);assert.equal(r.row_count,count);assert.equal(r.user_query,router.resolved_query);}
assert(!node('SQL KB')); assert(!node('If'));
assert.equal(w.connections['Product Concept KB'].ai_tool[0][0].node,'SQL Reasoning Agent');
assert.deepEqual(node('Execute a SQL query').parameters.options,{});
assert.equal(node('Execute a SQL query').onError,'continueRegularOutput');
assert.equal(w.connections.Switch.main.length,4);
assert.equal(node('Switch').parameters.options.fallbackOutput,'extra');
assert(!node('Product Concept KB').parameters.workflowInputs.value.metricCodes.includes('[0]'));
assert.equal(Object.keys(w.pinData||{}).length,0);
const expr=node('Execute a SQL query').parameters.query.replace(/^=/,'').slice(2,-2).trim();
const prepare=q=>new Function('$json','$','return ('+expr+')')({output:q},()=>({item:{json:{available_sources:[{schema_name:'dsdep',table_name:'dep_nt_acct'}]}}}));
assert.match(prepare('SELECT * FROM DSPBM.PB_FUNDPOSIT_SEC_M'),/UNSUPPORTED/);
assert.match(prepare('SELECT * FROM "dspbm"."pb_fundposit_sec_m"'),/UNSUPPORTED/);
assert.match(prepare('SELECT * FROM dsdep.dep_nt_acct a JOIN dspbm.missing b ON true'),/UNSUPPORTED/);
assert.equal(prepare('SELECT * FROM dsdep.dep_nt_acct'),'SELECT * FROM dsdep.dep_nt_acct');
assert.match(prepare('SELECT SUM(amt) FROM AUM_025'),/UNSUPPORTED/);
assert.equal(prepare('WITH x AS (SELECT * FROM dsdep.dep_nt_acct), y AS (SELECT * FROM x) SELECT * FROM y'),'WITH x AS (SELECT * FROM dsdep.dep_nt_acct), y AS (SELECT * FROM x) SELECT * FROM y');
assert.equal(prepare("SELECT 'KB_METRIC_UNRESOLVED' AS error_message;"),"SELECT 'KB_METRIC_UNRESOLVED' AS error_message;");
console.log(JSON.stringify({resultCasesPassed:cases.length,connectionAndContractChecks:'passed'}));
