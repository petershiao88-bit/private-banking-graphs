# 推理報告（v0.16.0）

- 引擎：owlrl 7.6.2（OWL 2 RL）；rdflib 7.6.0
- 輸入 465 triples → 閉包 1122 triples
- 類別 43；宣告的 subClassOf 37 條；蘊含的上下位關係 44 組，其中推理新增 7 組
- 與獨立 subClassOf 走訪交叉驗證：passed
- 循環：0；不可滿足類別：0；一致性：not_checked

## 推理新增的關係

| 類別 | 推出的上層 | 推理路徑 |
|---|---|---|
| 銀行 AUM（`bank:BankAUM`） | 指標（`fh:Metric`） | 銀行 AUM ⊑ AUM ⊑ 指標 |
| 銀行手收指標（`bank:BankFeeIncome`） | 指標（`fh:Metric`） | 銀行手收指標 ⊑ 手收指標 ⊑ 指標 |
| 銀行利收（`bank:BankInterestIncome`） | 指標（`fh:Metric`） | 銀行利收 ⊑ 利收指標 ⊑ 指標 |
| 銀行 LUM（`bank:BankLUM`） | 指標（`fh:Metric`） | 銀行 LUM ⊑ LUM ⊑ 指標 |
| 理專（`bank:FinancialAdvisor`） | 職員（`fh:Employee`） | 理專 ⊑ 行員 ⊑ 職員 |
| 證券 AUM（`securities:SecuritiesAUM`） | 指標（`fh:Metric`） | 證券 AUM ⊑ AUM ⊑ 指標 |
| 證券手收指標（`securities:SecuritiesFeeIncome`） | 指標（`fh:Metric`） | 證券手收指標 ⊑ 手收指標 ⊑ 指標 |

## 限制

- 只推理具名類別的 TBox（rdfs:subClassOf 閉包與 domain 繼承）；沒有個體資料。
- OWL 2 RL 規則集不是完整 OWL DL：未做一致性與可滿足性的完備檢查，只檢查是否有類別被推成 owl:Nothing。
- 只接受 config.reasoner 白名單內的公理；出現其他公理時拒絕發佈，不會忽略後假稱完整。
