# 客戶360共通語意整合本體：agent context（v0.17.0）

本體版本 `https://example.org/ontology/customer360/0.17.0`（design draft，2026-10-31）。release 包 SHA-256 `3feb3af815a6639d`；推理引擎 owlrl 7.6.2（OWL 2 RL）。

## 使用規則

1. 只能使用本文件列出的類別與屬性 ID，不得自行新增類別或關係。
2. 判斷「X 是否屬於 Y」只能依各類別的「上層鏈」。不在鏈上表示目前本體無法證明，不代表兩者互斥。
3. 標為 provisional 的類別是設計草案，回答時要註明。
4. 標為 deprecated 的類別不可用於新的回答，改用其取代者。
5. 本體只提供概念、範圍與關係；金額、計算與資料查詢交給工具，不可依本文件推算數值。
6. 回答時引用類別 ID 與本體版本。

## 推理步驟

1. 把問題中的業務名詞對應到類別：以名稱與定義比對，列出候選類別 ID。
2. 若候選不只一個或找不到，先說明歧義或無對應，不要猜。
3. 查每個候選類別的上層鏈，確認它屬於哪個金控共通概念、哪個子公司。
4. 查可用屬性（自身與繼承），確認問題要的資訊有對應屬性。
5. 依上述結果作答，引用類別 ID 與版本；超出本體範圍的部分明確說明。

## 金控層（`fh:`）

### AUM `fh:AUM`（provisional）

- 定義：衡量指定快照日依管理與認列口徑計算之資產規模的指標。
- 上層鏈：AUM ⊑ 指標
- 直接子類：銀行 AUM `bank:BankAUM`、證券 AUM `securities:SecuritiesAUM`
- 可用屬性：AUM 基準日 `fh:aumAsOfDate` → xsd:date；衡量金融商品 `fh:measuresProduct` → 金融商品；估值數量 `fh:valuationQuantity` → xsd:decimal；估值單價 `fh:valuationUnitPrice` → xsd:decimal；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 地址通聯資訊 `fh:AddressContactInformation`（provisional）

- 定義：以實體地址聯絡客戶的通聯資訊。
- 上層鏈：地址通聯資訊 ⊑ 通聯資訊
- 可用屬性：街道門牌地址 `fh:addressLine` → xsd:string；縣市 `fh:city` → xsd:string；國家／地區代碼 `fh:countryCode` → xsd:string；鄉鎮市區 `fh:district` → xsd:string；完整地址 `fh:fullAddress` → xsd:string；郵遞區號 `fh:postalCode` → xsd:string

### 通聯資訊 `fh:ContactInformation`（provisional）

- 定義：與客戶相關的聯絡資訊。
- 上層鏈：無（頂層類別）
- 直接子類：地址通聯資訊 `fh:AddressContactInformation`、手機通聯資訊 `fh:MobileContactInformation`

### 客戶 `fh:Customer`（provisional）

- 定義：集團業務中所服務的客戶。
- 上層鏈：無（頂層類別）
- 可用屬性：具有通聯資訊 `fh:hasContactPoint` → 通聯資訊；持有金融商品 `fh:holds` → 金融商品

### 部門 `fh:Department`（provisional）

- 定義：金控或旗下子公司的業務組織單位類型；具體部門與採用指標範圍由子公司及部門描述。
- 上層鏈：無（頂層類別）
- 直接子類：私人銀行部門 `bank:PrivateBankingDepartment`
- 可用屬性：採用指標 `fh:usesMetric` → 指標

### 職員 `fh:Employee`（provisional）

- 定義：任職於金控或旗下子公司的人員。
- 上層鏈：無（頂層類別）
- 直接子類：行員 `bank:BankEmployee`
- 可用屬性：服務客戶 `fh:serves` → 客戶

### 手收指標 `fh:FeeIncome`（provisional）

- 定義：衡量指定收入期間內依業務認列口徑歸入手收的收入指標；具體涵蓋範圍由子公司或部門描述。
- 上層鏈：手收指標 ⊑ 指標
- 直接子類：銀行手收指標 `bank:BankFeeIncome`、證券手收指標 `securities:SecuritiesFeeIncome`
- 可用屬性：手收計算基礎金額 `fh:feeBaseAmount` → xsd:decimal；手收計算扣減金額 `fh:feeDeductionAmount` → xsd:decimal；手收來源商品 `fh:feeIncomeFromProduct` → 金融商品；收入期間迄日 `fh:incomePeriodEnd` → xsd:date；收入期間起日 `fh:incomePeriodStart` → xsd:date；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 金融商品 `fh:FinancialProduct`（provisional）

- 定義：金融機構提供的金融商品。
- 上層鏈：無（頂層類別）
- 直接子類：債券商品 `bank:BondProduct`、銀行集合管理投資商品 `bank:CollectiveManagementProduct`、存款商品 `bank:DepositProduct`、銀行 ETF 商品 `bank:ETFProduct`、外幣金融商品 `bank:ForeignCurrencyFinancialProduct`、銀行外匯商品 `bank:ForeignExchangeProduct`、基金商品 `bank:FundProduct`、銀行黃金商品 `bank:GoldProduct`、銀行保險商品 `bank:InsuranceProduct`、銀行開狀商品 `bank:LetterOfCreditProduct`、銀行放款商品 `bank:LoanProduct`、海外金融商品 `bank:OverseasFinancialProduct`、銀行規劃型信託商品 `bank:PlannedTrustProduct`、股票商品 `bank:StockProduct`、結構型金融商品 `bank:StructuredFinancialProduct`、台幣金融商品 `bank:TWDFinancialProduct`、銀行信託保管商品 `bank:TrustCustodyProduct`、債券商品 `securities:BondProduct`、基金商品 `securities:FundProduct`、海外金融商品 `securities:OverseasFinancialProduct`、股票商品 `securities:StockProduct`、結構型金融商品 `securities:StructuredFinancialProduct`

### 利收指標 `fh:InterestIncome`（provisional）

- 定義：衡量指定收入期間內依業務認列口徑歸入利收的收入指標；具體收益組成與涵蓋範圍由子公司或部門描述，不限定為純客戶利息。
- 上層鏈：利收指標 ⊑ 指標
- 直接子類：銀行利收 `bank:BankInterestIncome`
- 可用屬性：利收來源商品 `fh:interestIncomeFromProduct` → 金融商品；利收期間迄日 `fh:interestPeriodEnd` → xsd:date；利收期間起日 `fh:interestPeriodStart` → xsd:date；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### LUM `fh:LUM`（provisional）

- 定義：衡量指定基準日納入業務管理範圍之放款或融通餘額的指標；具體涵蓋與認列口徑由子公司或部門描述，不以擔保品估值或未動用額度代替。
- 上層鏈：LUM ⊑ 指標
- 直接子類：銀行 LUM `bank:BankLUM`
- 可用屬性：LUM 基準日 `fh:lumAsOfDate` → xsd:date；LUM 衡量金融商品 `fh:lumMeasuresProduct` → 金融商品；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 指標 `fh:Metric`（provisional）

- 定義：依明確口徑衡量業務狀況的量化項目。
- 上層鏈：無（頂層類別）
- 直接子類：AUM `fh:AUM`、手收指標 `fh:FeeIncome`、利收指標 `fh:InterestIncome`、LUM `fh:LUM`
- 可用屬性：指標金額 `fh:metricAmount` → xsd:decimal

### 手機通聯資訊 `fh:MobileContactInformation`（provisional）

- 定義：以手機號碼聯絡客戶的通聯資訊。
- 上層鏈：手機通聯資訊 ⊑ 通聯資訊
- 可用屬性：手機號碼 `fh:mobileNumber` → xsd:string


## 子公司層－銀行（`bank:`）

### 銀行 AUM `bank:BankAUM`（provisional）

- 定義：衡量指定快照日依銀行管理與認列口徑計算之客戶資產規模的指標。
- 上層鏈（含推理）：銀行 AUM ⊑ AUM ⊑ 指標
- 可用屬性：衡量金融商品 `fh:measuresProduct` → 金融商品（繼承自AUM）；AUM 基準日 `fh:aumAsOfDate` → xsd:date（繼承自AUM）；估值數量 `fh:valuationQuantity` → xsd:decimal（繼承自AUM）；估值單價 `fh:valuationUnitPrice` → xsd:decimal（繼承自AUM）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 行員 `bank:BankEmployee`（provisional）

- 定義：任職於銀行的職員。
- 上層鏈：行員 ⊑ 職員
- 直接子類：理專 `bank:FinancialAdvisor`
- 可用屬性：行員編號 `bank:employeeId` → xsd:string；服務客戶 `fh:serves` → 客戶（繼承自職員）

### 銀行手收指標 `bank:BankFeeIncome`（provisional）

- 定義：衡量銀行於指定收入期間內依銀行認列規則形成之手收的指標。
- 上層鏈（含推理）：銀行手收指標 ⊑ 手收指標 ⊑ 指標
- 可用屬性：歸屬理專 `bank:attributedToAdvisor` → 理專；手收來源商品 `fh:feeIncomeFromProduct` → 金融商品（繼承自手收指標）；手收計算基礎金額 `fh:feeBaseAmount` → xsd:decimal（繼承自手收指標）；手收計算扣減金額 `fh:feeDeductionAmount` → xsd:decimal（繼承自手收指標）；收入期間迄日 `fh:incomePeriodEnd` → xsd:date（繼承自手收指標）；收入期間起日 `fh:incomePeriodStart` → xsd:date（繼承自手收指標）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 銀行利收 `bank:BankInterestIncome`（provisional）

- 定義：銀行業務中依認列口徑衡量的利收指標；具體涵蓋範圍由部門描述。
- 上層鏈（含推理）：銀行利收 ⊑ 利收指標 ⊑ 指標
- 可用屬性：利收來源商品 `fh:interestIncomeFromProduct` → 金融商品（繼承自利收指標）；利收期間迄日 `fh:interestPeriodEnd` → xsd:date（繼承自利收指標）；利收期間起日 `fh:interestPeriodStart` → xsd:date（繼承自利收指標）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 銀行 LUM `bank:BankLUM`（provisional）

- 定義：銀行業務中依認列口徑衡量的 LUM 指標；具體涵蓋範圍由部門描述。
- 上層鏈（含推理）：銀行 LUM ⊑ LUM ⊑ 指標
- 可用屬性：LUM 衡量金融商品 `fh:lumMeasuresProduct` → 金融商品（繼承自LUM）；LUM 基準日 `fh:lumAsOfDate` → xsd:date（繼承自LUM）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 債券商品 `bank:BondProduct`（provisional）

- 定義：發行人為籌資而發行、約定清償條件的債務型金融商品。
- 上層鏈：債券商品 ⊑ 金融商品

### 銀行集合管理投資商品 `bank:CollectiveManagementProduct`（provisional）

- 定義：銀行依信託約定，將營運範圍或方法相同的信託資金集合管理運用的投資商品；私銀實際涵蓋範圍由部門描述。
- 上層鏈：銀行集合管理投資商品 ⊑ 金融商品

### 存款商品 `bank:DepositProduct`（provisional）

- 定義：銀行提供、供客戶依約定存放資金的金融商品。
- 上層鏈：存款商品 ⊑ 金融商品

### 銀行 ETF 商品 `bank:ETFProduct`（provisional）

- 定義：客戶透過銀行通路交易或持有的 ETF 商品；私銀實際涵蓋範圍由部門描述。
- 上層鏈：銀行 ETF 商品 ⊑ 金融商品

### 理專 `bank:FinancialAdvisor`（provisional）

- 定義：擔任理財諮詢與金融商品服務職務的銀行行員。
- 上層鏈（含推理）：理專 ⊑ 行員 ⊑ 職員
- 可用屬性：行員編號 `bank:employeeId` → xsd:string（繼承自行員）；服務客戶 `fh:serves` → 客戶（繼承自職員）

### 外幣金融商品 `bank:ForeignCurrencyFinancialProduct`（provisional）

- 定義：以新臺幣以外貨幣計價的金融商品。
- 上層鏈：外幣金融商品 ⊑ 金融商品

### 銀行外匯商品 `bank:ForeignExchangeProduct`（provisional）

- 定義：本專案依金融商品口徑分類之銀行貨幣兌換與外匯交易業務；來源分類不直接決定收入會計性質。
- 上層鏈：銀行外匯商品 ⊑ 金融商品

### 基金商品 `bank:FundProduct`（provisional）

- 定義：透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。
- 上層鏈：基金商品 ⊑ 金融商品

### 銀行黃金商品 `bank:GoldProduct`（provisional）

- 定義：銀行通路提供的黃金類商品；實際承作形式與涵蓋範圍由部門描述。
- 上層鏈：銀行黃金商品 ⊑ 金融商品

### 銀行保險商品 `bank:InsuranceProduct`（provisional）

- 定義：銀行通路提供的保險商品；實際納入私人銀行業務的保險範圍由部門描述。
- 上層鏈：銀行保險商品 ⊑ 金融商品

### 銀行開狀商品 `bank:LetterOfCreditProduct`（provisional）

- 定義：本專案依金融商品口徑分類之銀行開狀及相關貿易支付安排業務。
- 上層鏈：銀行開狀商品 ⊑ 金融商品

### 銀行放款商品 `bank:LoanProduct`（provisional）

- 定義：銀行依授信安排提供客戶使用資金的融資商品；不以放款餘額直接認定為 AUM。
- 上層鏈：銀行放款商品 ⊑ 金融商品

### 海外金融商品 `bank:OverseasFinancialProduct`（provisional）

- 定義：銀行業務中歸入海外投資範圍的金融商品。
- 上層鏈：海外金融商品 ⊑ 金融商品

### 銀行規劃型信託商品 `bank:PlannedTrustProduct`（provisional）

- 定義：本專案依金融商品口徑分類之規劃型信託業務，依信託目的與契約安排管理或運用客戶財產；私銀實際涵蓋的一般信託與員工持股信託範圍由部門描述。
- 上層鏈：銀行規劃型信託商品 ⊑ 金融商品

### 私人銀行部門 `bank:PrivateBankingDepartment`（provisional）

- 定義：銀行從事私人銀行業務的部門類型；具體指標採用範圍在部門 PG 描述，暫不細分一部、二部、分行或團隊。
- 上層鏈：私人銀行部門 ⊑ 部門
- 可用屬性：採用指標 `fh:usesMetric` → 指標（繼承自部門）

### 股票商品 `bank:StockProduct`（provisional）

- 定義：代表公司股權的金融商品。
- 上層鏈：股票商品 ⊑ 金融商品

### 結構型金融商品 `bank:StructuredFinancialProduct`（provisional）

- 定義：報酬條件依約定公式連結金融指標或標的表現的金融商品。
- 上層鏈：結構型金融商品 ⊑ 金融商品

### 台幣金融商品 `bank:TWDFinancialProduct`（provisional）

- 定義：以新臺幣計價的金融商品。
- 上層鏈：台幣金融商品 ⊑ 金融商品

### 銀行信託保管商品 `bank:TrustCustodyProduct`（provisional）

- 定義：本專案依金融商品口徑分類之信託保管業務，依約提供客戶資產保管；實際管理資產與收入範圍由部門描述。
- 上層鏈：銀行信託保管商品 ⊑ 金融商品


## 子公司層－證券（`securities:`）

### 債券商品 `securities:BondProduct`（provisional）

- 定義：發行人為籌資而發行、約定清償條件的債務型金融商品。
- 上層鏈：債券商品 ⊑ 金融商品

### 基金商品 `securities:FundProduct`（provisional）

- 定義：透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。
- 上層鏈：基金商品 ⊑ 金融商品

### 海外金融商品 `securities:OverseasFinancialProduct`（provisional）

- 定義：證券業務中歸入海外投資範圍的金融商品。
- 上層鏈：海外金融商品 ⊑ 金融商品

### 證券 AUM `securities:SecuritiesAUM`（provisional）

- 定義：衡量指定快照日依證券公司管理與認列口徑計算之客戶資產規模的指標。
- 上層鏈（含推理）：證券 AUM ⊑ AUM ⊑ 指標
- 可用屬性：衡量金融商品 `fh:measuresProduct` → 金融商品（繼承自AUM）；AUM 基準日 `fh:aumAsOfDate` → xsd:date（繼承自AUM）；估值數量 `fh:valuationQuantity` → xsd:decimal（繼承自AUM）；估值單價 `fh:valuationUnitPrice` → xsd:decimal（繼承自AUM）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 證券手收指標 `securities:SecuritiesFeeIncome`（provisional）

- 定義：衡量證券公司於指定收入期間內依其認列規則形成之手收的指標。
- 上層鏈（含推理）：證券手收指標 ⊑ 手收指標 ⊑ 指標
- 可用屬性：手收來源商品 `fh:feeIncomeFromProduct` → 金融商品（繼承自手收指標）；手收計算基礎金額 `fh:feeBaseAmount` → xsd:decimal（繼承自手收指標）；手收計算扣減金額 `fh:feeDeductionAmount` → xsd:decimal（繼承自手收指標）；收入期間迄日 `fh:incomePeriodEnd` → xsd:date（繼承自手收指標）；收入期間起日 `fh:incomePeriodStart` → xsd:date（繼承自手收指標）；指標金額 `fh:metricAmount` → xsd:decimal（繼承自指標）

### 股票商品 `securities:StockProduct`（provisional）

- 定義：代表公司股權的金融商品。
- 上層鏈：股票商品 ⊑ 金融商品

### 結構型金融商品 `securities:StructuredFinancialProduct`（provisional）

- 定義：依商品契約將金融工具組合，形成特定收益或風險條件的金融商品。
- 上層鏈：結構型金融商品 ⊑ 金融商品
