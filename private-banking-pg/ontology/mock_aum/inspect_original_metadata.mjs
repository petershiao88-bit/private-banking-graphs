import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

for (const path of process.argv.slice(2)) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  console.log(JSON.stringify({ path }));
  console.log((await workbook.inspect({ kind: 'sheet', include: 'id,name', maxChars: 6000 })).ndjson);
  if (path.endsWith('AUM_metadata.xlsx')) {
    const sheet = workbook.worksheets.getItem('DSDEP.EMP_NT_ACCT_HS');
    const rows = sheet.getRange('A1:G77').values;
    const selected = rows.map((row, i) => ({range:`A${i+1}:G${i+1}`, values:row})).filter(({values:r}) =>
      /^(Yes|Y)$/i.test(String(r[3])) || /CUST_ID|ACCT_NO|LST_MTN_DT|DATA_DT|ACT_CD|ACC_CD|PRFT|BAL_AMT|YYYYMM|CURR|CURRENCY|AVAIL/.test(String(r[1])));
    console.log(JSON.stringify({sheet:sheet.name, header:rows[0], selected}));
    console.log(JSON.stringify({sheet:sheet.name, columnNames:rows.slice(1).map(r=>r[1])}));
  } else if (path.endsWith('AUM_20250516.xlsx')) {
    const sheet = workbook.worksheets.getItem('建議調整版');
    console.log(JSON.stringify({sheet:sheet.name, range:'A1:AD9', values:sheet.getRange('A1:AD9').values}));
  } else if (path.endsWith('收入_metadata.xlsx')) {
    for (const name of ['DSDEP.DEP_NT_ACCT_HS','DSDEP.EMP_DEP_NT_ACCT_HS']) {
      const rows = workbook.worksheets.getItem(name).getRange('A1:G78').values;
      console.log(JSON.stringify({sheet:name, header:rows[0], selected:rows.map((r,i)=>({range:`A${i+1}:G${i+1}`,values:r})).filter(({values:r})=>
        /^(Yes|Y)$/i.test(String(r[3])) || /CUST_ID|ACCT_NO|LST_MTN_DT|DATA_DT|ACT_CD|ACC_CD|PRFT|BAL_AMT|YYYYMM|CURR|CURRENCY|AVAIL/.test(String(r[1]))),
        columnNames:rows.slice(1).map(r=>r[1])}));
    }
  }
}
