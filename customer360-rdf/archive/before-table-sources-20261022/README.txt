客戶360 RDF／OWL 與部門 PG v0.10.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
金控新增八個共通 Data Property：指標金額、AUM 基準日、估值數量／單價、收入期間起迄日、手收基礎／扣減金額。
數值使用 xsd:decimal，日期使用 xsd:date。銀行與證券沿用；按情境提供，不新增必填、基數或詳細公式。
AUM 沿用 measuresProduct，手收沿用 feeIncomeFromProduct「手收來源商品」；銀行手收歸屬理專關係保持。
PG 新增 71 個 pending 元素欄位；amount 參照 metricAmount。來源選擇與 execution 仍全 null。
既有 snapshotDate／incomePeriod 與來源候選保留，不自動轉為新的業務日期。
客戶與商品識別、幣別匯率及商品範圍先不討論；權限、帳戶及畫圖仍暫緩。

RDF來源五份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。
PG來源六份：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。
RDF：28 Class、6 Object Property、16 Data Property、5 Annotation Property、312 triples。
PG：28概念、348 metadata節點、698關係。RDF 18項＋PG 51項測試通過，無略過。
修改前快照：archive/before-v0.10.0/。未執行來源SQL、完整OWL推論或Neo4j部署。
outputs/rdf-review-v0.7.0 僅供歷史對照，沒有更新圖片。
