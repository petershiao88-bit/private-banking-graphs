# CHANGELOG v0.17.0（2026-10-31）

比對基準：v0.16.0（release 0.16.0）。
變更需要的升版等級：**minor**；實際升版：**minor**。

發佈門檻：通過。

## 模組重整（定義不變，只換宣告所在的模組）

| 原模組 | 新模組 | 類別／屬性 |
|---|---|---|
| bank-common.ttl | ontology/bank/metrics.ttl | `bank:BankAUM`、`bank:BankFeeIncome`、`bank:BankInterestIncome`、`bank:BankLUM`、`bank:attributedToAdvisor` |
| bank-common.ttl | ontology/bank/organization.ttl | `bank:PrivateBankingDepartment` |
| bank-common.ttl | ontology/bank/parties.ttl | `bank:BankEmployee`、`bank:FinancialAdvisor`、`bank:employeeId` |
| bank-deposit.ttl | ontology/bank/products.ttl | `bank:DepositProduct`、`bank:ForeignCurrencyFinancialProduct`、`bank:StructuredFinancialProduct`、`bank:TWDFinancialProduct` |
| bank-investment-products.ttl | ontology/bank/products.ttl | `bank:BondProduct`、`bank:CollectiveManagementProduct`、`bank:ETFProduct`、`bank:ForeignExchangeProduct`、`bank:FundProduct`、`bank:GoldProduct`、`bank:InsuranceProduct`、`bank:LetterOfCreditProduct`、`bank:LoanProduct`、`bank:OverseasFinancialProduct`、`bank:PlannedTrustProduct`、`bank:StockProduct`、`bank:TrustCustodyProduct` |
| holding-core.ttl | ontology/holding/metrics.ttl | `fh:AUM`、`fh:FeeIncome`、`fh:InterestIncome`、`fh:LUM`、`fh:Metric`、`fh:aumAsOfDate`、`fh:feeBaseAmount`、`fh:feeDeductionAmount`、`fh:feeIncomeFromProduct`、`fh:incomePeriodEnd`、`fh:incomePeriodStart`、`fh:interestIncomeFromProduct`、`fh:interestPeriodEnd`、`fh:interestPeriodStart`、`fh:lumAsOfDate`、`fh:lumMeasuresProduct`、`fh:measuresProduct`、`fh:metricAmount`、`fh:valuationQuantity`、`fh:valuationUnitPrice` |
| holding-core.ttl | ontology/holding/organization.ttl | `fh:Department`、`fh:usesMetric` |
| holding-core.ttl | ontology/holding/parties.ttl | `fh:AddressContactInformation`、`fh:ContactInformation`、`fh:Customer`、`fh:Employee`、`fh:MobileContactInformation`、`fh:addressLine`、`fh:city`、`fh:countryCode`、`fh:district`、`fh:fullAddress`、`fh:hasContactPoint`、`fh:mobileNumber`、`fh:postalCode`、`fh:serves` |
| holding-core.ttl | ontology/holding/products.ttl | `fh:FinancialProduct`、`fh:holds` |
| securities-common.ttl | ontology/securities/metrics.ttl | `securities:SecuritiesAUM`、`securities:SecuritiesFeeIncome` |
| securities-common.ttl | ontology/securities/products.ttl | `securities:BondProduct`、`securities:FundProduct`、`securities:OverseasFinancialProduct`、`securities:StockProduct`、`securities:StructuredFinancialProduct` |
