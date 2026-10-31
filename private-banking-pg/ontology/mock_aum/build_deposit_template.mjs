import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const outputDir = 'deliverables/mock_aum/group1';
const aumPath = 'sources/metadata/AUM_metadata.xlsx';
const incomePath = 'sources/metadata/收入_metadata.xlsx';
const aum = await SpreadsheetFile.importXlsx(await FileBlob.load(aumPath));
const income = await SpreadsheetFile.importXlsx(await FileBlob.load(incomePath));
const active = new Map([
  ['DSDEP.DEP_NT_ACCT_HS', ['TMP01', 'TMP06']],
  ['DSDEP.DEP_FN_ACCT_HS', ['TMP02', 'TMP07']],
  ['DSDEP.EMP_DEP_NT_ACCT_HS', ['TMP03', 'TMP08']],
  ['DSDEP.DEP_NT_ACCT', ['TMP04']],
  ['DSDEP.DEP_FN_ACCT', ['TMP05']],
]);

const tables = [];
for (const [sheetName, range] of [['DSDEP.DEP_NT_ACCT','A1:G16'],['DSDEP.DEP_FN_ACCT','A1:G17']]) {
  const rows = aum.worksheets.getItem(sheetName).getRange(range).values;
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r[0] || !r[1]) continue;
    const tableName = `${r[0]}.${r[1]}`;
    tables.push({tableName, description:r[2] ?? null, sourceSystem:r[3] ?? null,
      overseasNote:r[6] ?? null,
      stagingUsage:active.has(tableName) ? 'referenced' : 'not_referenced',
      stagingReferences:(active.get(tableName) ?? []).map(s=>`AUM_005_007_008_009_${s}`),
      columnDefinitionStatus:'not_provided_in_available_original_metadata',
      originalColumns:[],
      source:{file:aumPath,sheet:sheetName,range:`A${i+1}:G${i+1}`}});
  }
}
for (const [tableName, end] of [['DSDEP.DEP_NT_ACCT_HS',78],['DSDEP.EMP_DEP_NT_ACCT_HS',77]]) {
  const t = tables.find(t=>t.tableName===tableName);
  const rows = income.worksheets.getItem(tableName).getRange(`A1:G${end}`).values;
  t.originalColumns=rows.slice(1).map((r,i)=>({
    name:r[1],originalDataType:r[2] ?? null,primaryKeyDesignation:r[3] ?? null,
    descriptions:r.slice(4), source:{file:incomePath,sheet:tableName,range:`B${i+2}:G${i+2}`},
  })).filter(c=>c.name);
  t.columnDefinitionStatus='original_column_list_available';
}

const template={
  group:'group1_deposit', version:'proposal_v1', deploymentStatus:'not_deployed',
  calculationBasis:'reproduce_original_staging_sql',
  sourceFiles:[aumPath,incomePath,'sources/metadata/AUM_20250516.xlsx','sources/sql/1.AUM_DETAIL.sql','sources/sql/2._AUM_SUMY.sql'],
  tables,
  proposal:{
    retainOriginalSchemasAndTableNames:true,
    preserveAllProvidedOriginalColumnDefinitions:true,
    accountSnapshots:'Reuse the same account across months; retain separate customer accounts.',
    historicalPrimaryKey:'ACCT_NO + YYYYMM, where confirmed by original metadata.',
    dates:'Retain DATA_DT, LST_MTN_DT and YYYYMM separately; do not infer they are always equal.',
    amountSelection:'Use BAL_AMT or AVAIL_BAL as specified by each SQL branch; do not substitute BAL_AMT2 or AVAIL_AMT.',
    nonReferencedTables:'Include every metadata catalog entry. Do not infer a full physical schema from a table name or add it to AUM calculations without SQL evidence.',
    syntheticColumns:'Keep proposed PostgreSQL types and mock assumptions separate from original definitions.',
  },
  stagingBranches:[
    {branch:'TMP01',source:'DSDEP.DEP_NT_ACCT_HS',status:'commented_out_sql',date:'LST_MTN_DT',conditions:["TRIM(PRFT_CNTR_CD) IN ('2E3000','2E3200','2E3300','2E3400')","LST_MTN_DT >= '20231201'"],historicalInitialization:'Requires an explicit reconstruction/frozen-snapshot policy.'},
    {branch:'TMP02',source:'DSDEP.DEP_FN_ACCT_HS',status:'commented_out_sql',date:'LST_MTN_DT',conditions:["TRIM(PRFT_CNTR_CD) IN ('2E3000','2E3200','2E3300','2E3400')","LST_MTN_DT >= '20231201'"]},
    {branch:'TMP03',source:'DSDEP.EMP_DEP_NT_ACCT_HS',status:'commented_out_sql',date:'LST_MTN_DT',conditions:["TRIM(PRFT_CNTR_CD) IN ('2E3000','2E3200','2E3300','2E3400')","LST_MTN_DT >= '20231201'"]},
    {branch:'TMP04',source:'DSDEP.DEP_NT_ACCT',status:'active_sql',date:'DATA_DT',conditions:[]},
    {branch:'TMP05',source:'DSDEP.DEP_FN_ACCT',status:'active_sql',date:'LST_MTN_DT',conditions:[]},
    {branch:'TMP06',source:'DSDEP.DEP_NT_ACCT_HS',status:'active_sql',date:'LST_MTN_DT',conditions:["YYYYMM >= '202506'"]},
    {branch:'TMP07',source:'DSDEP.DEP_FN_ACCT_HS',status:'active_sql',date:'LST_MTN_DT',conditions:["YYYYMM >= '202506'"]},
    {branch:'TMP08',source:'DSDEP.EMP_DEP_NT_ACCT_HS',status:'active_sql',date:'LST_MTN_DT',conditions:["YYYYMM >= '202506'"]},
  ],
  reviewItems:[
    {item:'AVAIL_AMT versus AVAIL_BAL',decision:'Keep SQL AVAIL_BAL; original physical definition of foreign-currency tables is not available.'},
    {item:'Foreign-currency amount unit',decision:'Original available metadata does not establish AVAIL_BAL currency basis. Any TWD-equivalent fixture must be explicitly a test assumption.'},
    {item:'Employee PRFT_CNTR_CD',decision:'Required by SQL, absent from employee original column list; retain as a proposed mock field with SQL provenance.'},
    {item:'Employee TYP_DTL',decision:"Preserve SQL literal '外幣'; select deposit classes via the evidenced DETAIL/product mapping."},
    {item:'Historical initialization',decision:'Do not activate commented TMP01-03 silently; confirm reconstruction policy before older-period tests.'},
    {item:'Existing metadata UNION ALL comments',decision:'Correct to branch aggregation followed by original UNION distinct semantics.'},
  ],
  coverage:{originalCatalogTables:tables.length,stagingReferencedTables:tables.filter(t=>t.stagingUsage==='referenced').length,
    additionalMetadataTables:tables.filter(t=>t.stagingUsage==='not_referenced').length,
    tablesWithOriginalColumnLists:tables.filter(t=>t.originalColumns.length).length},
};
if(tables.length!==31 || active.size!==5 || new Set(tables.map(t=>t.tableName)).size!==tables.length)
  throw new Error('Original catalog coverage does not reconcile.');
for(const key of active.keys()) if(!tables.some(t=>t.tableName===key)) throw new Error(`Missing source ${key}`);
await fs.mkdir(outputDir,{recursive:true});
await fs.writeFile(`${outputDir}/deposit_template.json`,JSON.stringify(template,null,2)+'\n','utf8');
console.log(JSON.stringify({coverage:template.coverage,additionalTables:tables.filter(t=>t.stagingUsage==='not_referenced').map(t=>t.tableName)},null,2));
