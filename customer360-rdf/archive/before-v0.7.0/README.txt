客戶360 RDF／OWL 與部門 PG v0.6.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
RDF來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl。
本輪新增股票商品、債券商品、海外金融商品，全部直接繼承金控金融商品；海外地域口徑待確認，非自動等同外幣。
新增職員→行員、行員編號、職員服務客戶、指標→手收→銀行手收及指標對應金融商品。
理專與各商品手收留在部門PG，參照共通語意，不建立組合OWL類別。

PG來源：model.json、deposits.json、advisory-income.json、product-fees.json。
第一批有來源商品手收：境內結構型SI（不含ELI／FCI）、境外結構型SN分行手收。
保留原始欄位與SQL／metadata證據；快照日、收入期間、理專歸屬、幣別及取數規則仍待確認。
權限由使用者暫緩。帳戶及分行／數位仍排除。

RDF：17 Class、4 Object Property、8 Data Property、5 Annotation Property、186 triples。
PG：10概念、94 metadata節點、153關係。RDF 15項＋PG 37項測試通過，無略過。
僅離線建置，未執行真實SQL、完整OWL推論或Neo4j部署。
修改前快照：archive/before-v0.6.0/。勿執行legacy建置器或恢復錯誤組合OWL類別。
