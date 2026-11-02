# 客戶360共通語意整合本體：agent context｜角色 理專（`rm`）

本體 `https://example.org/ontology/customer360/0.17.0`（design draft，2026-10-31），與已發佈 release 一致（bundle `3feb3af815a6`）。知識指紋 `c3e8b80da471`。
權限已套用：本文件只列出「理專」可用的指標與詞條。不在清單中的項目，一律視為目前不可用。

## 使用規則

1. 只能使用本文件列出的類別與屬性 ID，不得自行新增類別或關係。
2. 判斷「X 是否屬於 Y」只能依各類別的「上層鏈」。不在鏈上表示目前本體無法證明，不代表兩者互斥。
3. 標為 provisional 的類別是設計草案，回答時要註明。
4. 標為 deprecated 的類別不可用於新的回答，改用其取代者。
5. 本體只提供概念、範圍與關係；金額、計算與資料查詢交給工具，不可依本文件推算數值。
6. 回答時引用類別 ID 與本體版本。
7. 指標只能用「指標清單」裡的 ID。清單沒有的指標，回答「目前可用範圍內沒有這項指標」，不要猜測，也不要改用名稱相近的指標代替。
8. 銀行與證券有同名商品（基金、債券、股票、結構型、海外）。問題沒有指明子公司，而兩邊都有對應指標時，先澄清；若使用者要的是全部，就兩邊並列並分開說明。
9. 標 Σ 的是總指標，只涵蓋列出的分項；總指標與其分項不可再一起加總，也不可把分項自行相加當成總指標。
10. 問題落在「待定範圍」時，說明目前尚未定義，不可用相近指標代替。
11. 「不包含／不屬於／排除」這類條件要依類別階層判斷：不在上層鏈上的才可視為排除。

## 推理步驟

1. 把問題中的業務名詞對應到類別：以名稱與定義比對，列出候選類別 ID。
2. 若候選不只一個或找不到，先說明歧義或無對應，不要猜。
3. 查每個候選類別的上層鏈，確認它屬於哪個金控共通概念、哪個子公司。
4. 查可用屬性（自身與繼承），確認問題要的資訊有對應屬性。
5. 依上述結果作答，引用類別 ID 與版本；超出本體範圍的部分明確說明。

## 類別階層

縮排代表 rdfs:subClassOf（是一種）。OWL 推理已確認：上層的上層也成立，例如銀行手收指標 ⊑ 手收指標 ⊑ 指標。

- 通聯資訊 `fh:ContactInformation`：與客戶相關的聯絡資訊。
  - 地址通聯資訊 `fh:AddressContactInformation`：以實體地址聯絡客戶的通聯資訊。
  - 手機通聯資訊 `fh:MobileContactInformation`：以手機號碼聯絡客戶的通聯資訊。
- 客戶 `fh:Customer`：集團業務中所服務的客戶。
- 部門 `fh:Department`：金控或旗下子公司的業務組織單位類型；具體部門與採用指標範圍由子公司及部門描述。
  - 私人銀行部門 `bank:PrivateBankingDepartment`：銀行從事私人銀行業務的部門類型；具體指標採用範圍在部門 PG 描述，暫不細分一部、二部、分行或團隊。
- 職員 `fh:Employee`：任職於金控或旗下子公司的人員。
  - 行員（銀行） `bank:BankEmployee`：任職於銀行的職員。
    - 理專（銀行） `bank:FinancialAdvisor`：擔任理財諮詢與金融商品服務職務的銀行行員。
- 金融商品 `fh:FinancialProduct`：金融機構提供的金融商品。
  - 債券商品（銀行） `bank:BondProduct`：發行人為籌資而發行、約定清償條件的債務型金融商品。
  - 銀行集合管理投資商品 `bank:CollectiveManagementProduct`：銀行依信託約定，將營運範圍或方法相同的信託資金集合管理運用的投資商品；私銀實際涵蓋範圍由部門描述。
  - 存款商品（銀行） `bank:DepositProduct`：銀行提供、供客戶依約定存放資金的金融商品。
  - 銀行 ETF 商品 `bank:ETFProduct`：客戶透過銀行通路交易或持有的 ETF 商品；私銀實際涵蓋範圍由部門描述。
  - 外幣金融商品（銀行） `bank:ForeignCurrencyFinancialProduct`：以新臺幣以外貨幣計價的金融商品。
  - 銀行外匯商品 `bank:ForeignExchangeProduct`：本專案依金融商品口徑分類之銀行貨幣兌換與外匯交易業務；來源分類不直接決定收入會計性質。
  - 基金商品（銀行） `bank:FundProduct`：透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。
  - 銀行黃金商品 `bank:GoldProduct`：銀行通路提供的黃金類商品；實際承作形式與涵蓋範圍由部門描述。
  - 銀行保險商品 `bank:InsuranceProduct`：銀行通路提供的保險商品；實際納入私人銀行業務的保險範圍由部門描述。
  - 銀行開狀商品 `bank:LetterOfCreditProduct`：本專案依金融商品口徑分類之銀行開狀及相關貿易支付安排業務。
  - 銀行放款商品 `bank:LoanProduct`：銀行依授信安排提供客戶使用資金的融資商品；不以放款餘額直接認定為 AUM。
  - 海外金融商品（銀行） `bank:OverseasFinancialProduct`：銀行業務中歸入海外投資範圍的金融商品。
  - 銀行規劃型信託商品 `bank:PlannedTrustProduct`：本專案依金融商品口徑分類之規劃型信託業務，依信託目的與契約安排管理或運用客戶財產；私銀實際涵蓋的一般信託與員工持股信託範圍由部門描述。
  - 股票商品（銀行） `bank:StockProduct`：代表公司股權的金融商品。
  - 結構型金融商品（銀行） `bank:StructuredFinancialProduct`：報酬條件依約定公式連結金融指標或標的表現的金融商品。
  - 台幣金融商品（銀行） `bank:TWDFinancialProduct`：以新臺幣計價的金融商品。
  - 銀行信託保管商品 `bank:TrustCustodyProduct`：本專案依金融商品口徑分類之信託保管業務，依約提供客戶資產保管；實際管理資產與收入範圍由部門描述。
  - 債券商品（證券） `securities:BondProduct`：發行人為籌資而發行、約定清償條件的債務型金融商品。
  - 基金商品（證券） `securities:FundProduct`：透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。
  - 海外金融商品（證券） `securities:OverseasFinancialProduct`：證券業務中歸入海外投資範圍的金融商品。
  - 股票商品（證券） `securities:StockProduct`：代表公司股權的金融商品。
  - 結構型金融商品（證券） `securities:StructuredFinancialProduct`：依商品契約將金融工具組合，形成特定收益或風險條件的金融商品。
- 指標 `fh:Metric`：依明確口徑衡量業務狀況的量化項目。
  - AUM `fh:AUM`：衡量指定快照日依管理與認列口徑計算之資產規模的指標。
    - 銀行 AUM `bank:BankAUM`：衡量指定快照日依銀行管理與認列口徑計算之客戶資產規模的指標。
    - 證券 AUM `securities:SecuritiesAUM`：衡量指定快照日依證券公司管理與認列口徑計算之客戶資產規模的指標。
  - 手收指標 `fh:FeeIncome`：衡量指定收入期間內依業務認列口徑歸入手收的收入指標；具體涵蓋範圍由子公司或部門描述。
    - 銀行手收指標 `bank:BankFeeIncome`：衡量銀行於指定收入期間內依銀行認列規則形成之手收的指標。
    - 證券手收指標 `securities:SecuritiesFeeIncome`：衡量證券公司於指定收入期間內依其認列規則形成之手收的指標。
  - 利收指標 `fh:InterestIncome`：衡量指定收入期間內依業務認列口徑歸入利收的收入指標；具體收益組成與涵蓋範圍由子公司或部門描述，不限定為純客戶利息。
    - 銀行利收 `bank:BankInterestIncome`：銀行業務中依認列口徑衡量的利收指標；具體涵蓋範圍由部門描述。
  - LUM `fh:LUM`：衡量指定基準日納入業務管理範圍之放款或融通餘額的指標；具體涵蓋與認列口徑由子公司或部門描述，不以擔保品估值或未動用額度代替。
    - 銀行 LUM `bank:BankLUM`：銀行業務中依認列口徑衡量的 LUM 指標；具體涵蓋範圍由部門描述。

## 關係屬性

- 銀行手收指標 `bank:BankFeeIncome` —歸屬理專 `bank:attributedToAdvisor`→ 理專 `bank:FinancialAdvisor`：銀行手收歸屬於理專的關係。
- 手收指標 `fh:FeeIncome` —手收來源商品 `fh:feeIncomeFromProduct`→ 金融商品 `fh:FinancialProduct`：手收來自其所對應金融商品的關係。
- 客戶 `fh:Customer` —具有通聯資訊 `fh:hasContactPoint`→ 通聯資訊 `fh:ContactInformation`：客戶具有通聯資訊。
- 客戶 `fh:Customer` —持有金融商品 `fh:holds`→ 金融商品 `fh:FinancialProduct`：客戶持有金融商品。
- 利收指標 `fh:InterestIncome` —利收來源商品 `fh:interestIncomeFromProduct`→ 金融商品 `fh:FinancialProduct`：依業務認列口徑歸入利收的收入來自其所對應金融商品的關係。
- LUM `fh:LUM` —LUM 衡量金融商品 `fh:lumMeasuresProduct`→ 金融商品 `fh:FinancialProduct`：LUM 衡量其所對應金融商品之放款或融通餘額。
- AUM `fh:AUM` —衡量金融商品 `fh:measuresProduct`→ 金融商品 `fh:FinancialProduct`：AUM 衡量其所對應金融商品的資產規模。
- 職員 `fh:Employee` —服務客戶 `fh:serves`→ 客戶 `fh:Customer`：職員向客戶提供業務服務的關係。
- 部門 `fh:Department` —採用指標 `fh:usesMetric`→ 指標 `fh:Metric`：部門採用某項指標衡量業務狀況；不因此決定承作子公司、來源資料權責、理專歸屬或自動加總方式。

資料屬性（欄位概念，子類別會繼承）：

- 行員 `bank:BankEmployee`：行員編號 `bank:employeeId`
- AUM `fh:AUM`：AUM 基準日 `fh:aumAsOfDate`、估值數量 `fh:valuationQuantity`、估值單價 `fh:valuationUnitPrice`
- 地址通聯資訊 `fh:AddressContactInformation`：街道門牌地址 `fh:addressLine`、縣市 `fh:city`、國家／地區代碼 `fh:countryCode`、鄉鎮市區 `fh:district`、完整地址 `fh:fullAddress`、郵遞區號 `fh:postalCode`
- 手收指標 `fh:FeeIncome`：手收計算基礎金額 `fh:feeBaseAmount`、手收計算扣減金額 `fh:feeDeductionAmount`、收入期間迄日 `fh:incomePeriodEnd`、收入期間起日 `fh:incomePeriodStart`
- 利收指標 `fh:InterestIncome`：利收期間迄日 `fh:interestPeriodEnd`、利收期間起日 `fh:interestPeriodStart`
- LUM `fh:LUM`：LUM 基準日 `fh:lumAsOfDate`
- 指標 `fh:Metric`：指標金額 `fh:metricAmount`
- 手機通聯資訊 `fh:MobileContactInformation`：手機號碼 `fh:mobileNumber`

## 指標清單（44 項）

類別欄是指標所屬的本體類別；商品欄是指標衡量或收入來源的商品類別。底表只到表級，欄位與計算口徑由工具承接。

### 銀行｜AUM

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `bank.collective_account_aum` | 私銀－銀行集合管理帳戶 AUM | `bank:BankAUM` | `bank:CollectiveManagementProduct` | 私銀集合管理帳戶 AUM，參照銀行集合管理投資商品；先建立表級來源，實際認列與欄位映射尚待確認。 | DSFND.PB_FUND_MONTH |
| `bank.etf_aum` | 私銀－銀行 ETF AUM | `bank:BankAUM` | `bank:ETFProduct` | 私銀銀行 ETF AUM；先記共用底表來源，ETF 實際分類取值及認列範圍尚待確認。 | DSFND.PB_FUND_MONTH |
| `bank.foreign_currency_deposit_aum` | 私銀－銀行外幣存款 AUM | `bank:BankAUM` | `bank:DepositProduct`＋`bank:ForeignCurrencyFinancialProduct` | 外幣存款 AUM所描述的客戶資產規模指標。 | DSDEP.DEP_FN_ACCT、DSDEP.DEP_FN_ACCT_HS |
| `bank.fund_aum` | 私銀－銀行基金 AUM | `bank:BankAUM` | `bank:FundProduct` | 銀行基金 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSFND.PB_FUND_MONTH |
| `bank.insurance_aum` | 私銀－銀行保險 AUM | `bank:BankAUM` | `bank:InsuranceProduct` | 私銀銀行保險 AUM 的來源觀察；來源彙總 SQL 註明原始投資金額，不直接等同保單市值或現金價值。 | DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT |
| `bank.offshore_structured_aum` | 私銀－銀行境外結構型商品 AUM | `bank:BankAUM` | `bank:StructuredFinancialProduct`＋`bank:OverseasFinancialProduct` | 境外結構型商品 AUM所描述的客戶資產規模指標。 | DSFND.PB_FUND_MONTH |
| `bank.overseas_bond_proprietary_aum` | 私銀－銀行海外債券（自營）AUM | `bank:BankAUM` | `bank:BondProduct`＋`bank:OverseasFinancialProduct` | 海外債券（自營）AUM所描述的客戶資產規模指標。 | DSWTR.BOND_POS_DAY |
| `bank.overseas_bond_trust_aum` | 私銀－銀行海外債券（信託）AUM | `bank:BankAUM` | `bank:BondProduct`＋`bank:OverseasFinancialProduct` | 海外債券（信託）AUM所描述的客戶資產規模指標。 | DSFND.PB_FUND_MONTH |
| `bank.overseas_stock_aum` | 私銀－銀行海外股票 AUM | `bank:BankAUM` | `bank:StockProduct`＋`bank:OverseasFinancialProduct` | 海外股票 AUM所描述的客戶資產規模指標。 | DSFND.PB_FUND_MONTH |
| `bank.planned_trust_aum` | 私銀－銀行規劃型信託 AUM | `bank:BankAUM` | `bank:PlannedTrustProduct` | 銀行規劃型信託 AUM；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSEBS.EBTS_ACT_CntAUMBal_PB、DSTAM.TRUCONTRACT_PB |
| `bank.structured_deposit_aum` | 私銀－銀行結構型存款 AUM | `bank:BankAUM` | `bank:DepositProduct`＋`bank:StructuredFinancialProduct` | 結構型存款 AUM所描述的客戶資產規模指標。 | DSDEP.DEP_FN_ACCT、DSDEP.DEP_FN_ACCT_HS、DSDEP.DEP_NT_ACCT、DSDEP.DEP_NT_ACCT_HS、DSDEP.EMP_DEP_NT_ACCT_HS |
| `bank.trust_custody_aum` | 私銀－銀行信託保管 AUM | `bank:BankAUM` | `bank:TrustCustodyProduct` | 銀行信託保管 AUM；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSPMS.PB_PMS_AUM |
| `bank.twd_deposit_aum` | 私銀－銀行台幣存款 AUM | `bank:BankAUM` | `bank:DepositProduct`＋`bank:TWDFinancialProduct` | 台幣存款 AUM所描述的客戶資產規模指標。 | DSDEP.DEP_NT_ACCT、DSDEP.DEP_NT_ACCT_HS |

### 銀行｜LUM

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `bank.loan_lum` | 私銀－銀行放款 LUM | `bank:BankLUM` | `bank:LoanProduct` | 私銀依既有 LUM SQL 管理口徑衡量的銀行放款餘額指標；不以授信額度、利收或擔保品估值代替。 | DSLON.LN_FN_ACCT、DSLON.LN_FN_ACCT_HS、DSLON.LN_NT_ACCT、DSLON.LN_NT_ACCT_HS |

### 銀行｜手收

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `bank.dci_fee_income` | 私銀－銀行 DCI 手收 | `bank:BankFeeIncome` | `bank:StructuredFinancialProduct` | 依私銀 SQL 手收分類，涵蓋 DCI 手續費報表及 DCD 的 TMU 損益；沿用結構型金融商品分類，不認定為結構型存款。 | DSDEP.DCI_PERFO_RPT、DSDEP.DCI_PERFO_RPT_HS、DSTAS.FO108_W |
| `bank.domestic_structured_eli_fee_income` | 私銀－銀行境內結構型商品手收（ELI） | `bank:BankFeeIncome` | `bank:StructuredFinancialProduct` | 私銀境內結構型商品中的 ELI 手續費來源；與 SI、FCI 分開保留。 | DSDEP.ELI_PERFO_RPT、DSDEP.ELI_PERFO_RPT_HS |
| `bank.domestic_structured_fci_fee_income` | 私銀－銀行境內結構型商品手收（FCI） | `bank:BankFeeIncome` | `bank:StructuredFinancialProduct` | 私銀境內結構型商品中的 FCI 手續費來源；與 SI、ELI 分開保留。 | DSDEP.FCI_PERFO_RPT、DSDEP.FCI_PERFO_RPT_HS |
| `bank.domestic_structured_si_fee_income` | 私銀－銀行境內結構型商品手收（SI） | `bank:BankFeeIncome` | `bank:StructuredFinancialProduct` | 銀行境內 SI 結構型商品業務的手續費收入。 | DSDEP.SI_PERFO_RPT、DSDEP.SI_PERFO_RPT_HS |
| `bank.etf_fee_income` | 私銀－銀行 ETF 手續費收入 | `bank:BankFeeIncome` | `bank:ETFProduct` | 私銀銀行 ETF 手續費收入；先記來源 SQL 中的 ETF 分支與共用底表，不核定欄位或分類執行規則。 | DSFND.PB_FUND_SPREAD_DAILY |
| `bank.fund_fee_income` | 私銀－銀行基金手收 | `bank:BankFeeIncome` | `bank:FundProduct` | 銀行基金手收；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSFND.PB_FUND_SPREAD_DAILY |
| `bank.fx_fee_income` | 私銀－銀行外匯手收 | `bank:BankFeeIncome` | `bank:ForeignExchangeProduct` | 銀行外匯手收；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSTAS.FO108_W、DSWBS.PB_SPOT_Daily、DSWBS.PB_SPOT_Daily_HS |
| `bank.gold_fee_income` | 私銀－銀行黃金手收 | `bank:BankFeeIncome` | `bank:GoldProduct` | 銀行黃金手收；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSDEP.GD_PERFO_RPT、DSDEP.GD_PERFO_RPT_HS |
| `bank.insurance_fee_income` | 私銀－銀行保險手收 | `bank:BankFeeIncome` | `bank:InsuranceProduct` | 依私銀 SQL 手收分類，涵蓋保險日報 COMM_AMT 與兩項月檔 PS；PS 的客戶貢獻度性質另行保留，不宣稱均為純手續費。 | DSINS.INSU_RPT_Q01、DSKPI.KPI_DET_IU_002_NEW、DSKPI.KPI_DET_OFI_001 |
| `bank.lc_fee_income` | 私銀－銀行開狀手收 | `bank:BankFeeIncome` | `bank:LetterOfCreditProduct` | 銀行開狀手收；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSWBS.IMPM007、DSWBS.IMPM007_HS |
| `bank.offshore_structured_fee_income` | 私銀－銀行境外結構型商品手收 | `bank:BankFeeIncome` | `bank:StructuredFinancialProduct` | 銀行境外結構型商品業務的分行手續費收入。 | DSFND.PB_FUND_SPREAD_DAILY |
| `bank.overseas_bond_proprietary_fee_income` | 私銀－銀行外國債券（自營）手收 | `bank:BankFeeIncome` | `bank:BondProduct`＋`bank:OverseasFinancialProduct` | 銀行外國債券（自營）手收；依私銀 SQL 業務字典記錄來源範圍，計算由 Tool 承接。 | DSWTR.BOND_TXN |
| `bank.overseas_bond_trust_fee_income` | 私銀－銀行海外債券（信託）手收 | `bank:BankFeeIncome` | `bank:BondProduct`＋`bank:OverseasFinancialProduct` | 銀行海外債券（信託）手收；依私銀 SQL 業務字典記錄來源範圍，計算由 Tool 承接。 | DSFND.PB_FUND_SPREAD_DAILY |
| `bank.overseas_stock_fee_income` | 私銀－銀行海外股票手收 | `bank:BankFeeIncome` | `bank:StockProduct`＋`bank:OverseasFinancialProduct` | 私銀來源將海外股票列為獨立手收分支；本指標只參照該分支的底表，不將全表視為海外股票。 | DSFND.PB_FUND_SPREAD_DAILY |
| `bank.planned_trust_fee_income` | 私銀－銀行規劃型信託手收 | `bank:BankFeeIncome` | `bank:PlannedTrustProduct` | 銀行規劃型信託手收；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSEBS.EBTS_ACT_CntAUMBal_PB、DSTAM.TRUCONTRACT_PB |
| `bank.product_fee_income` | 私銀－銀行商品手收 | `bank:BankFeeIncome` | — | 對應金融商品之銀行手續費收入的部門業務概念。 | DSDEP.SI_PERFO_RPT、DSDEP.SI_PERFO_RPT_HS、DSFND.PB_FUND_SPREAD_DAILY、DSDEP.ELI_PERFO_RPT、DSDEP.ELI_PERFO_RPT_HS、DSDEP.FCI_PERFO_RPT、DSDEP.FCI_PERFO_RPT_HS、DSDEP.DCI_PERFO_RPT、DSDEP.DCI_PERFO_RPT_HS、DSINS.INSU_RPT_Q01 |
| `bank.trust_custody_fee_income` | 私銀－銀行信託保管手收 | `bank:BankFeeIncome` | `bank:TrustCustodyProduct` | 銀行信託保管手收；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSPMS.PB_PMS_AUM |

### 銀行｜利收

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `bank.deposit_interest_income` | 私銀－銀行存款利收 | `bank:BankInterestIncome` | `bank:DepositProduct` | 銀行存款利收；依私銀 SQL 業務字典記錄來源範圍，計算由 Tool 承接。 | DSDEP.DEP_NT_ACCT_HS、DSDEP.DEP_FN_ACCT_HS、DSDEP.EMP_DEP_NT_ACCT_HS、DSDEP.DEP_FN_ACCT |
| `bank.loan_income` | 私銀－銀行放款利收（來源業務收益口徑） | `bank:BankInterestIncome` | `bank:LoanProduct` | 銀行放款利收（來源業務收益口徑）；沿用私銀 SQL 的業務分類，僅對應指標到底表，實際認列與欄位映射待確認。 | DSLON.LN_FN_ACCT_HS、DSLON.LN_NT_ACCT_HS、DSLON.LN_FN_ACCT |

### 證券｜AUM

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `securities.bond_aum` | 私銀－證券複委託債券 AUM | `securities:SecuritiesAUM` | `securities:BondProduct`＋`securities:OverseasFinancialProduct` | 證券複委託債券 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSDEP.FN_EXCH_RT（估值輔助）、DSPBM.PB_BONDPOS_SEC、DSPBM.PB_BONDPOS_SEC_M |
| `securities.foreign_stock_aum` | 私銀－證券複委託外國股票 AUM | `securities:SecuritiesAUM` | `securities:StockProduct`＋`securities:OverseasFinancialProduct` | 證券複委託外國股票 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSDEP.FN_EXCH_RT（估值輔助）、DSPBM.PB_STOCKPOS_SEC、DSPBM.PB_STOCKPOS_SEC_M |
| `securities.fund_aum` | 私銀－證券複委託基金 AUM | `securities:SecuritiesAUM` | `securities:FundProduct` | 證券複委託基金 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_FUNDPOSIT_SEC、DSPBM.PB_FUNDPOSIT_SEC_M |
| `securities.structured_aum` | 私銀－證券複委託結構型商品 AUM | `securities:SecuritiesAUM` | `securities:StructuredFinancialProduct` | 證券複委託結構型商品 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSDEP.FN_EXCH_RT（估值輔助）、DSPBM.PB_BONDPOS_SEC、DSPBM.PB_BONDPOS_SEC_M |
| `securities.taiwan_stock_aum` | 私銀－證券台股 AUM | `securities:SecuritiesAUM` | `securities:StockProduct` | 證券台股 AUM；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_YTRMRBP_SEC、DSPBM.PB_YTRMRBP_SEC_M |
| `securities.total_aum` | Σ 私銀－證券總 AUM | `securities:SecuritiesAUM` | 分項：`securities.bond_aum`、`securities.structured_aum`、`securities.fund_aum`、`securities.foreign_stock_aum`、`securities.taiwan_stock_aum` | 私銀－證券總 AUM；僅涵蓋目前已納入私銀模型的證券商品分項，金額與期間口徑待 Tool 定義。 | 沿分項 |

### 證券｜手收

| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |
|---|---|---|---|---|---|
| `securities.bond_fee_income` | 私銀－證券複委託債券手收 | `securities:SecuritiesFeeIncome` | `securities:BondProduct`＋`securities:OverseasFinancialProduct` | 證券複委託債券手收；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_BONDTRADM_SEC、DSPBM.PB_BONDTRADM_SEC_M |
| `securities.foreign_stock_fee_income` | 私銀－證券複委託外國股票淨手收 | `securities:SecuritiesFeeIncome` | `securities:StockProduct`＋`securities:OverseasFinancialProduct` | 證券複委託外國股票淨手收；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_STOCKTRADM_AM_SEC（僅日期查詢）、DSPBM.PB_STOCKTRADM_AM_SEC_M、DSPBM.PB_STOCKTRADM_PM_SEC、DSPBM.PB_STOCKTRADM_PM_SEC_M |
| `securities.fund_fee_income` | 私銀－證券複委託基金手收 | `securities:SecuritiesFeeIncome` | `securities:FundProduct` | 證券複委託基金手收；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_BONDTRADM_SEC（僅日期查詢）、DSPBM.PB_FUNDTRADM_SEC、DSPBM.PB_FUNDTRADM_SEC_M |
| `securities.structured_fee_income` | 私銀－證券複委託結構型商品手收 | `securities:SecuritiesFeeIncome` | `securities:StructuredFinancialProduct` | 證券複委託結構型商品手收；依私銀既有產品範圍記錄的指標候選，認列與來源映射尚待確認。 | DSPBM.PB_BONDTRADM_SEC、DSPBM.PB_BONDTRADM_SEC_M |
| `securities.total_fee_income` | Σ 私銀－證券總手收 | `securities:SecuritiesFeeIncome` | 分項：`securities.bond_fee_income`、`securities.structured_fee_income`、`securities.fund_fee_income`、`securities.foreign_stock_fee_income` | 私銀－證券總手收；僅涵蓋目前已納入私銀模型的證券商品分項，金額與期間口徑待 Tool 定義。 | 沿分項 |


## 待定範圍（尚未定義，不可用相近指標代替）

- `securities.taiwan_stock_fee_income`：原產品收入定義空白，提供的 SQL 未見台股手收分支；不推論現實業務沒有手收。
- `bank.collective_account_fee_income`：私銀 bank_collective_account 的 incomeDefinition 空白；來源手收 SQL 雖有 TA／TB／TD／TE 集合管理分支，但前方 FHID NOT IN ('PS','CB','YB','SN') 可能先將其歸入基金，保留原順序且不新增手收指標或修正分類規則。
- `securities.stock_pledge_lum`：股票設質退出 AUM；現有 DSCSD.PBCMS_REPORTA03 證據支持股票估值，實際借款／融通餘額底表尚未確認，不將估值改名為 LUM。

## 其他業務詞條（對應到類別，非指標）

- 客戶訪問地址 `bank.customer_visit_address` → 地址通聯資訊 `fh:AddressContactInformation`
- 行員存款 `bank.employee_deposit` → 存款商品 `bank:DepositProduct`
- 理專 `bank.financial_advisor` → 理專 `bank:FinancialAdvisor`
- 外幣存款 `bank.foreign_currency_deposit` → 存款商品 `bank:DepositProduct`＋外幣金融商品 `bank:ForeignCurrencyFinancialProduct`
- 貸款照會手機 `bank.loan_verification_mobile` → 手機通聯資訊 `fh:MobileContactInformation`
- 私銀 `bank.private_banking` → 私人銀行部門 `bank:PrivateBankingDepartment`
- 結構型存款 `bank.structured_deposit` → 存款商品 `bank:DepositProduct`＋結構型金融商品 `bank:StructuredFinancialProduct`
- 台幣存款 `bank.twd_deposit` → 存款商品 `bank:DepositProduct`＋台幣金融商品 `bank:TWDFinancialProduct`
