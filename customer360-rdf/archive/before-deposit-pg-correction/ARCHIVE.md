# 存款層級更正前的錯誤實作快照

此快照曾誤把台幣存款、外幣存款、結構型存款建立為OWL多重繼承類別。使用者已明確更正：這三個組合只在部門PG，以一般關係分別參照共同概念。

本目錄僅供回查，**不是核定版本，不可恢復到有效RDF或PG輸出**。有效bank-deposit.ttl只保留DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct四個共通Class。接續以專案根目錄README及交接為準。
