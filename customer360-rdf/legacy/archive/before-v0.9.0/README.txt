客戶360 RDF／OWL 與部門 PG v0.8.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
RDF來源四份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl。
金控AUM繼承指標，銀行AUM繼承金控AUM。measuresProduct的domain改為AUM，Metric不再直接指向金融商品。
手收使用獨立feeIncomeFromProduct連來源金融商品，銀行手收歸屬理專關係維持。
職員／行員／理專與既有商品分類保持，部門組合與來源映射留PG。

PG來源五份：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json。
七項商品AUM：台幣存款、外幣存款、結構型存款、海外股票、海外債券（信託）、海外債券（自營）、境外結構型商品。
原始餘額／估值輸入只是候選；認列、幣別、快照日、去重、聚合及執行規則待確認，不直接加總成銀行AUM。
兩項既有商品手收範圍與理專歸屬候選保持。權限、帳戶及分行／數位仍延後。

RDF：20 Class、6 Object Property、8 Data Property、5 Annotation Property、216 triples。
PG：17概念、156 metadata節點、299關係。RDF 17項＋PG 43項測試通過，無略過。
未執行來源SQL、完整OWL推論或Neo4j部署。修改前快照：archive/before-v0.8.0/。
使用者已指示不用畫圖，本輪沒有新圖片；outputs/rdf-review-v0.7.0 僅供歷史對照。
