客戶360 RDF／OWL 與部門 PG v0.9.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
RDF來源五份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。
金控AUM繼承指標，銀行AUM與證券AUM分別繼承金控AUM，沿用measuresProduct衡量金融商品。
銀行手收與證券手收分別繼承金控手收，均用feeIncomeFromProduct「手收來源商品」連金融商品。
本輪補銀行FundProduct、證券AUM／手收及五項證券商品分類。銀行手收歸屬理專關係維持，證券不套用銀行理專。

PG來源六份：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。
保留原有通聯、存款、理專、通用手收、SI／SN手收及七項商品AUM。
新增銀行基金AUM／手收；證券複委託債券、結構型、基金、外國股票AUM／手收，以及台股AUM，共十一概念。
外國股票手收保留扣除上手手續費後淨額。台股手收、股票設質語意與ETF留待後續。
原始來源只是候選；客戶識別、幣別、日期、認列、去重、聚合及執行規則待確認，不自動加總。
權限、帳戶及分行／數位仍延後，未新增資產部位或交易實例。

RDF：28 Class、6 Object Property、8 Data Property、5 Annotation Property、264 triples。
PG：28概念、266 metadata節點、527關係。RDF 17項＋PG 49項測試通過，無略過。
未執行來源SQL、完整OWL推論或Neo4j部署。修改前快照：archive/before-v0.9.0/。
使用者已指示不用畫圖，本輪沒有新圖片；outputs/rdf-review-v0.7.0 僅供歷史對照。
