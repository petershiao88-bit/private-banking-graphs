# 類別組成元件（v0.16.0）

類別 43、Object Property 9、Data Property 19。驗證：0 個錯誤、0 個警告。

## 一個類別由哪些元件組成

| 元件 | RDF 表示 | 要求 |
|---|---|---|
| uri | 類別 URI（命名空間決定所屬層） | 必要 |
| label | rdfs:label（config: components.label_lang） | 必要 |
| definition | skos:definition | 必要 |
| governance_level | fh:governanceLevel，須等於所屬層設定 | 必要 |
| subsidiary | fh:subsidiary，子公司層必填、金控層不得有 | 依層 |
| parents | 具名 rdfs:subClassOf；子公司類別須能接到金控類別 | 子公司層必要 |
| properties | 以本類別為 rdfs:domain 的 Object／Data Property | 選用 |
| module / maturity | 宣告所在模組及其 FIBO 成熟度 | 由 config 決定 |
| deprecated / replaced_by | owl:deprecated true＋dcterms:isReplacedBy | 下架時必要 |

## 金控層（`fh:`，12 類）

| 類別 | ID | 直接上層 | 模組／成熟度 | 以此為 domain 的屬性 | 定義 |
|---|---|---|---|---|---|
| AUM | `fh:AUM` | 指標 | holding-core.ttl／provisional | AUM 基準日、衡量金融商品、估值數量、估值單價 | 衡量指定快照日依管理與認列口徑計算之資產規模的指標。 |
| 地址通聯資訊 | `fh:AddressContactInformation` | 通聯資訊 | holding-core.ttl／provisional | 街道門牌地址、縣市、國家／地區代碼、鄉鎮市區、完整地址、郵遞區號 | 以實體地址聯絡客戶的通聯資訊。 |
| 通聯資訊 | `fh:ContactInformation` | — | holding-core.ttl／provisional | — | 與客戶相關的聯絡資訊。 |
| 客戶 | `fh:Customer` | — | holding-core.ttl／provisional | 具有通聯資訊、持有金融商品 | 集團業務中所服務的客戶。 |
| 部門 | `fh:Department` | — | holding-core.ttl／provisional | 採用指標 | 金控或旗下子公司的業務組織單位類型；具體部門與採用指標範圍由子公司及部門描述。 |
| 職員 | `fh:Employee` | — | holding-core.ttl／provisional | 服務客戶 | 任職於金控或旗下子公司的人員。 |
| 手收指標 | `fh:FeeIncome` | 指標 | holding-core.ttl／provisional | 手收計算基礎金額、手收計算扣減金額、手收來源商品、收入期間迄日、收入期間起日 | 衡量指定收入期間內依業務認列口徑歸入手收的收入指標；具體涵蓋範圍由子公司或部門描述。 |
| 金融商品 | `fh:FinancialProduct` | — | holding-core.ttl／provisional | — | 金融機構提供的金融商品。 |
| 利收指標 | `fh:InterestIncome` | 指標 | holding-core.ttl／provisional | 利收來源商品、利收期間迄日、利收期間起日 | 衡量指定收入期間內依業務認列口徑歸入利收的收入指標；具體收益組成與涵蓋範圍由子公司或部門描述，不限定為純客戶利息。 |
| LUM | `fh:LUM` | 指標 | holding-core.ttl／provisional | LUM 基準日、LUM 衡量金融商品 | 衡量指定基準日納入業務管理範圍之放款或融通餘額的指標；具體涵蓋與認列口徑由子公司或部門描述，不以擔保品估值或未動用額度代替。 |
| 指標 | `fh:Metric` | — | holding-core.ttl／provisional | 指標金額 | 依明確口徑衡量業務狀況的量化項目。 |
| 手機通聯資訊 | `fh:MobileContactInformation` | 通聯資訊 | holding-core.ttl／provisional | 手機號碼 | 以手機號碼聯絡客戶的通聯資訊。 |

## 子公司層－銀行（`bank:`，24 類）

| 類別 | ID | 直接上層 | 模組／成熟度 | 以此為 domain 的屬性 | 定義 |
|---|---|---|---|---|---|
| 銀行 AUM | `bank:BankAUM` | AUM | bank-common.ttl／provisional | — | 衡量指定快照日依銀行管理與認列口徑計算之客戶資產規模的指標。 |
| 行員 | `bank:BankEmployee` | 職員 | bank-common.ttl／provisional | 行員編號 | 任職於銀行的職員。 |
| 銀行手收指標 | `bank:BankFeeIncome` | 手收指標 | bank-common.ttl／provisional | 歸屬理專 | 衡量銀行於指定收入期間內依銀行認列規則形成之手收的指標。 |
| 銀行利收 | `bank:BankInterestIncome` | 利收指標 | bank-common.ttl／provisional | — | 銀行業務中依認列口徑衡量的利收指標；具體涵蓋範圍由部門描述。 |
| 銀行 LUM | `bank:BankLUM` | LUM | bank-common.ttl／provisional | — | 銀行業務中依認列口徑衡量的 LUM 指標；具體涵蓋範圍由部門描述。 |
| 債券商品 | `bank:BondProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 發行人為籌資而發行、約定清償條件的債務型金融商品。 |
| 銀行集合管理投資商品 | `bank:CollectiveManagementProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 銀行依信託約定，將營運範圍或方法相同的信託資金集合管理運用的投資商品；私銀實際涵蓋範圍由部門描述。 |
| 存款商品 | `bank:DepositProduct` | 金融商品 | bank-deposit.ttl／provisional | — | 銀行提供、供客戶依約定存放資金的金融商品。 |
| 銀行 ETF 商品 | `bank:ETFProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 客戶透過銀行通路交易或持有的 ETF 商品；私銀實際涵蓋範圍由部門描述。 |
| 理專 | `bank:FinancialAdvisor` | 行員 | bank-common.ttl／provisional | — | 擔任理財諮詢與金融商品服務職務的銀行行員。 |
| 外幣金融商品 | `bank:ForeignCurrencyFinancialProduct` | 金融商品 | bank-deposit.ttl／provisional | — | 以新臺幣以外貨幣計價的金融商品。 |
| 銀行外匯商品 | `bank:ForeignExchangeProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 本專案依金融商品口徑分類之銀行貨幣兌換與外匯交易業務；來源分類不直接決定收入會計性質。 |
| 基金商品 | `bank:FundProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。 |
| 銀行黃金商品 | `bank:GoldProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 銀行通路提供的黃金類商品；實際承作形式與涵蓋範圍由部門描述。 |
| 銀行保險商品 | `bank:InsuranceProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 銀行通路提供的保險商品；實際納入私人銀行業務的保險範圍由部門描述。 |
| 銀行開狀商品 | `bank:LetterOfCreditProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 本專案依金融商品口徑分類之銀行開狀及相關貿易支付安排業務。 |
| 銀行放款商品 | `bank:LoanProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 銀行依授信安排提供客戶使用資金的融資商品；不以放款餘額直接認定為 AUM。 |
| 海外金融商品 | `bank:OverseasFinancialProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 銀行業務中歸入海外投資範圍的金融商品。 |
| 銀行規劃型信託商品 | `bank:PlannedTrustProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 本專案依金融商品口徑分類之規劃型信託業務，依信託目的與契約安排管理或運用客戶財產；私銀實際涵蓋的一般信託與員工持股信託範圍由部門描述。 |
| 私人銀行部門 | `bank:PrivateBankingDepartment` | 部門 | bank-common.ttl／provisional | — | 銀行從事私人銀行業務的部門類型；具體指標採用範圍在部門 PG 描述，暫不細分一部、二部、分行或團隊。 |
| 股票商品 | `bank:StockProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 代表公司股權的金融商品。 |
| 結構型金融商品 | `bank:StructuredFinancialProduct` | 金融商品 | bank-deposit.ttl／provisional | — | 報酬條件依約定公式連結金融指標或標的表現的金融商品。 |
| 台幣金融商品 | `bank:TWDFinancialProduct` | 金融商品 | bank-deposit.ttl／provisional | — | 以新臺幣計價的金融商品。 |
| 銀行信託保管商品 | `bank:TrustCustodyProduct` | 金融商品 | bank-investment-products.ttl／provisional | — | 本專案依金融商品口徑分類之信託保管業務，依約提供客戶資產保管；實際管理資產與收入範圍由部門描述。 |

## 子公司層－證券（`securities:`，7 類）

| 類別 | ID | 直接上層 | 模組／成熟度 | 以此為 domain 的屬性 | 定義 |
|---|---|---|---|---|---|
| 債券商品 | `securities:BondProduct` | 金融商品 | securities-common.ttl／provisional | — | 發行人為籌資而發行、約定清償條件的債務型金融商品。 |
| 基金商品 | `securities:FundProduct` | 金融商品 | securities-common.ttl／provisional | — | 透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。 |
| 海外金融商品 | `securities:OverseasFinancialProduct` | 金融商品 | securities-common.ttl／provisional | — | 證券業務中歸入海外投資範圍的金融商品。 |
| 證券 AUM | `securities:SecuritiesAUM` | AUM | securities-common.ttl／provisional | — | 衡量指定快照日依證券公司管理與認列口徑計算之客戶資產規模的指標。 |
| 證券手收指標 | `securities:SecuritiesFeeIncome` | 手收指標 | securities-common.ttl／provisional | — | 衡量證券公司於指定收入期間內依其認列規則形成之手收的指標。 |
| 股票商品 | `securities:StockProduct` | 金融商品 | securities-common.ttl／provisional | — | 代表公司股權的金融商品。 |
| 結構型金融商品 | `securities:StructuredFinancialProduct` | 金融商品 | securities-common.ttl／provisional | — | 依商品契約將金融工具組合，形成特定收益或風險條件的金融商品。 |

## 屬性

| 屬性 | ID | 種類 | domain | range |
|---|---|---|---|---|
| 歸屬理專 | `bank:attributedToAdvisor` | object | 銀行手收指標 | 理專 |
| 手收來源商品 | `fh:feeIncomeFromProduct` | object | 手收指標 | 金融商品 |
| 具有通聯資訊 | `fh:hasContactPoint` | object | 客戶 | 通聯資訊 |
| 持有金融商品 | `fh:holds` | object | 客戶 | 金融商品 |
| 利收來源商品 | `fh:interestIncomeFromProduct` | object | 利收指標 | 金融商品 |
| LUM 衡量金融商品 | `fh:lumMeasuresProduct` | object | LUM | 金融商品 |
| 衡量金融商品 | `fh:measuresProduct` | object | AUM | 金融商品 |
| 服務客戶 | `fh:serves` | object | 職員 | 客戶 |
| 採用指標 | `fh:usesMetric` | object | 部門 | 指標 |
| 行員編號 | `bank:employeeId` | datatype | 行員 | xsd:string |
| 街道門牌地址 | `fh:addressLine` | datatype | 地址通聯資訊 | xsd:string |
| AUM 基準日 | `fh:aumAsOfDate` | datatype | AUM | xsd:date |
| 縣市 | `fh:city` | datatype | 地址通聯資訊 | xsd:string |
| 國家／地區代碼 | `fh:countryCode` | datatype | 地址通聯資訊 | xsd:string |
| 鄉鎮市區 | `fh:district` | datatype | 地址通聯資訊 | xsd:string |
| 手收計算基礎金額 | `fh:feeBaseAmount` | datatype | 手收指標 | xsd:decimal |
| 手收計算扣減金額 | `fh:feeDeductionAmount` | datatype | 手收指標 | xsd:decimal |
| 完整地址 | `fh:fullAddress` | datatype | 地址通聯資訊 | xsd:string |
| 收入期間迄日 | `fh:incomePeriodEnd` | datatype | 手收指標 | xsd:date |
| 收入期間起日 | `fh:incomePeriodStart` | datatype | 手收指標 | xsd:date |
| 利收期間迄日 | `fh:interestPeriodEnd` | datatype | 利收指標 | xsd:date |
| 利收期間起日 | `fh:interestPeriodStart` | datatype | 利收指標 | xsd:date |
| LUM 基準日 | `fh:lumAsOfDate` | datatype | LUM | xsd:date |
| 指標金額 | `fh:metricAmount` | datatype | 指標 | xsd:decimal |
| 手機號碼 | `fh:mobileNumber` | datatype | 手機通聯資訊 | xsd:string |
| 郵遞區號 | `fh:postalCode` | datatype | 地址通聯資訊 | xsd:string |
| 估值數量 | `fh:valuationQuantity` | datatype | AUM | xsd:decimal |
| 估值單價 | `fh:valuationUnitPrice` | datatype | AUM | xsd:decimal |
