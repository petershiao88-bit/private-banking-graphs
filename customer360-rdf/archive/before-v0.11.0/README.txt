客戶360 RDF／OWL 與部門 PG v0.10.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
金控新增八個共通 Data Property：指標金額、AUM 基準日、估值數量／單價、收入期間起迄日、手收基礎／扣減金額。
數值使用 xsd:decimal，日期使用 xsd:date。銀行與證券沿用；按情境提供，不新增必填、基數或詳細公式。
AUM 沿用 measuresProduct，手收沿用 feeIncomeFromProduct「手收來源商品」；銀行手收歸屬理專關係保持。
前次共通屬性新增71個pending欄位；本次四項手收各增11個pending欄位，另增44個。欄位table／column與execution全null。
最新補銀行海外股票、ELI、FCI、DCI純手續費四項PG指標與底表；DCI不含TMU損益。共通RDF未變。
目前13項AUM、12項手收有表級來源，商品分類不新增底表關係，未新增欄位映射。
清單：department-pg/METRIC-TABLE-SOURCES.md。通用手收擴充至已盤點SI／SN／基金／海外股票／ELI／FCI／DCI純手續費來源，仍為部分範圍。
既有 snapshotDate／incomePeriod 與來源候選保留，不自動轉為新的業務日期。
客戶與商品識別、幣別匯率及商品範圍先不討論；權限、帳戶及畫圖仍暫緩。

RDF來源五份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。
PG來源六份：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。
RDF：28 Class、6 Object Property、16 Data Property、5 Annotation Property、312 triples。
PG：32概念、410 metadata節點、869關係。RDF 18項＋PG 59項測試通過，無略過。
修改前快照：archive/before-v0.10.0/。未執行來源SQL、完整OWL推論或Neo4j部署。
表級對應前快照：archive/before-table-sources-20261022/；RDF版本與輸出保持。
銀行四項手收擴充前快照：archive/before-bank-fee-extension-20261022/。
outputs/rdf-review-v0.7.0 僅供歷史對照，沒有更新圖片。
