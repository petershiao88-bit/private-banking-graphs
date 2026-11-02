"""Update current documentation only; never touch historical baselines."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
intro='''## 本輪 PG 收入擴充（2026-10-24，已依確認清單完成）

修訂識別：`pg-income-extension-20261024`。RDF 及 ontology_version 維持 v0.15.0；五份 RDF 來源、Turtle／OWL 輸出、build-config 與 catalog 均逐位元組未變。

- 新增銀行存款利收 `bank.deposit_interest_income`、海外債券信託手收 `bank.overseas_bond_trust_fee_income`、外國債券自營手收 `bank.overseas_bond_proprietary_fee_income`，放在 bank-business-metrics.json。
- 沿用 `bank.dci_fee_income`、`bank.insurance_fee_income` 的原 ID，分別擴充 DCD／TMU 及兩項保險月檔來源，名稱改為銀行 DCI 手收、銀行保險手收。
- SQL 作業務字典；圖譜保存分類與來源 metadata，計算仍由 Tool 承接。沒有新增 Tool 綁定、欄位映射或可執行公式。
- 新增兩項債券手收沿用理專關係；存款利收不新增理專歸屬。通用商品手收仍維持原 partial_scope，沒有跟著擴大來源。

新備份：archive/before-pg-income-extension-20261024。修訂證據與來源雜湊：department-pg/history/pg-income-extension-20261024.json。僅本機建置／驗證，沒有資料庫部署。

'''

for rel in ('README.md','department-pg/README.md'):
 p=ROOT/rel
 text=p.read_text(encoding='utf-8')
 first,rest=text.split('\n',1)
 text=first+'\n\n'+intro+rest.lstrip('\n')
 replacements={
 '本次沒有新增或調整指標、欄位、關係與計算規則，版本維持 v0.15.0。':'該次範圍查核未新增指標；本輪另外完成上列五項收入範圍調整，RDF 版本維持 v0.15.0。',
 '本輪依使用者確認的七項變更清單執行；本機來源與輸出已更新，未部署 Neo4j。':'RDF 語意沿用既有確認版；本輪僅擴充 PG 收入範圍，本機輸出已更新，未部署 Neo4j。',
 'bank-business-metrics.json 共九項指標、85 個必要元素。':'bank-business-metrics.json 現共十二項指標、115 個必要元素。',
 '本輪九項商品指標的 department_context':'本模組十二項商品指標的 department_context',
 '本輪五項手收（規劃型信託、保管、外匯、開狀、黃金）':'本模組七項手收（規劃型信託、保管、外匯、開狀、黃金、債券信託、債券自營）',
 '放款利收未新增理專歸屬關係。':'存款與放款利收未新增理專歸屬關係。',
 '未順帶新增：存款利收、海外債券收入、DCI TMU、保險月檔客戶貢獻度、證券／人壽 LUM。':'尚未新增：證券／人壽 LUM、總收入彙總、額度／人數及 ROA／ROBA 指標。',
 '日報手收 partial_scope，月檔客戶貢獻度未併入。':'手收已包含日報及兩項月檔，PS 保留客戶貢獻度意義，不認定可直接加總。',
 'DCI 只有純手續費報表，不含 TMU。':'DCI 手收已含純手續費及 DCD／TMU 分支。',
 '本輪五項商品手收分列':'本模組七項商品手收分列',
 '本輪六類商品、九項 AUM／LUM／手收／利收':'十二項 AUM／LUM／手收／利收，含存款與兩項債券收入',
 '目前 39 項指標：**18 AUM、1 LUM、19 手收、1 利收**。49 SourceTable；79 HAS_SOURCE_TABLE':'目前 42 項指標：**18 AUM、1 LUM、21 手收、2 利收**。52 SourceTable；88 HAS_SOURCE_TABLE',
 '**46 業務概念、611 metadata 節點、1245 關係**，含 383 DataFieldDefinition、55 BusinessRelationDefinition':'**49 業務概念、652 metadata 節點、1338 關係**，含 413 DataFieldDefinition、60 BusinessRelationDefinition',
 '**RDF 19＋PG 78＝97 項測試通過，無略過**':'**RDF 19＋PG 85＝104 項測試通過，無略過**',
 'SI／SN、海外股票、ELI／FCI、DCI 純手續費':'SI／SN、海外股票、ELI／FCI、DCI 手收（含 DCD／TMU）',
 '規劃型信託／保管／外匯／開狀／黃金／放款九項指標':'規劃型信託／保管／外匯／開狀／黃金／放款／存款／債券十二項指標',
 '## 本輪九項指標':'## bank-business-metrics 十二項指標',
 '本模組兩項 AUM 各八個、五項手收各十一個、LUM 六個、利收八個，共 85 個 DataFieldDefinition':'本模組兩項 AUM 各八個、七項手收各十一個、LUM 六個、兩項利收各八個，共 115 個 DataFieldDefinition',
 '本輪五項手收都參照':'本模組七項手收都參照',
 '放款利收不新增理專關係。':'存款與放款利收不新增理專關係。',
 '39 項指標：18 AUM、1 LUM、19 手收、1 利收。46 BusinessConcept、611 metadata 節點、1245 關係，含 383 DataFieldDefinition、49 SourceTable、55 BusinessRelationDefinition':'42 項指標：18 AUM、1 LUM、21 手收、2 利收。49 BusinessConcept、652 metadata 節點、1338 關係，含 413 DataFieldDefinition、52 SourceTable、60 BusinessRelationDefinition',
 '79 HAS_SOURCE_TABLE':'88 HAS_SOURCE_TABLE',
 '本輪 PG 78 項測試通過，無略過；RDF 另 19 項，共 97 項。':'本輪 PG 85 項測試通過，無略過；RDF 另 19 項，共 104 項。',
 }
 for old,new in replacements.items():text=text.replace(old,new)
 if rel=='department-pg/README.md':
  text=text.replace('| bank.loan_income | 銀行利收 | LoanProduct |', '''| bank.loan_income | 銀行利收 | LoanProduct |
| bank.deposit_interest_income | 銀行利收 | DepositProduct |
| bank.overseas_bond_trust_fee_income | 銀行手收 | BondProduct＋OverseasFinancialProduct |
| bank.overseas_bond_proprietary_fee_income | 銀行手收 | BondProduct＋OverseasFinancialProduct |''')
 text+='''
## PG 收入擴充的來源差異與保存驗證

存款 INCOME_066 有三項歷史表與外幣 current 表；不補台幣 current 利收來源。初建與上月替換的私銀條件、UNION ALL／UNION、日期涵蓋不同；原 TMP01 定義註解疑點保留。債券信託 INCOME_031 取 BRHREBATEAMT + WKR028/100；自營 INCOME_032 逐筆 ABS 後加總，不改寫正負號或空值規則。

DCI INCOME_038 僅取 FO108_W 的 DCD，既有 FX 排除 DCD／Cash Bond。保險 INCOME_029／030 取 PS，保留客戶貢獻度意義；次月歸屬、IU／OFI 條件差異、日月重疊與 UNION 整列去重只作觀察。所有 execution 仍為 null，Tool 綁定未完成。

review_contract_pg_income.py 只供歷史測試正規化兩項核定擴充的名稱、定義、來源觀察、底表涵蓋及關係名稱，不忽略 Class、欄位候選或關係語意。test_pg_income.py 另直接檢查本輪來源規則、三項新指標、兩項擴充、RDF 逐位元組未變及來源雜湊。
'''
 p.write_text(text,encoding='utf-8')

(ROOT/'README.txt').write_text('''客戶360 RDF／OWL v0.15.0；PG 修訂 pg-income-extension-20261024。
最新說明 README.md；固定交接 HANDOFF-ZED-RDF-PG-20261022.md。
本輪只修改 PG：新增存款利收、債券信託手收、債券自營手收，擴充 DCI 及保險手收。
RDF 五份來源、輸出、版本與 catalog 均逐位元組保持。
DCI 補 DCD／TMU；保險補兩項 PS 月檔，保留客戶貢獻度性質。
依 SQL 作業務字典；圖譜記語意與來源，計算由 Tool 承接，Tool 綁定未實作。
新欄位映射 pending／null、候選空白；既有候選保留，execution 全 null。
42 項指標：18 AUM、1 LUM、21 手收、2 利收；52 張 SourceTable。
PG：49 業務概念、652 metadata 節點、1338 關係、413 DataFieldDefinition。
RDF：41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples。
RDF19＋PG85＝104項測試通過，無略過；24份來源SQL／Excel雜湊未變。
備份 archive/before-pg-income-extension-20261024；修訂紀錄 department-pg/history/pg-income-extension-20261024.json。
股票設質LUM、台股手收缺來源先不放；集合管理手收 CASE 遮蔽維持 pending，原台股與集合AUM保留。
外匯／開狀／黃金只保留手收；放款有LUM與利收，沒有放款AUM。
無Git提交、來源SQL執行或Neo4j部署；權限、帳戶、畫圖與欄位映射繼續暫緩。
''',encoding='utf-8')
print('Updated current README files')
