客戶360共通語意與部門映射 v0.4.0，2026-10-22，設計草案。

最新說明：README.md；新Session接續入口：HANDOFF-ZED-RDF-PG-20261022.md。舊HANDOFF-ZED-RDF-20261021.md僅保留轉向入口。

RDF來源：holding-core.ttl、bank-deposit.ttl。
銀行僅定義4個共通Class：存款商品、台幣／外幣／結構型金融商品。台幣／外幣／結構型存款的組合只留在部門PG，用一般關係分別參照共通概念，不建立OWL子類別或多重繼承。
沒有銀行金融商品中間層。行員存款留在部門PG，不是OWL子類別。
整合輸出：customer360-ontology.ttl、customer360-ontology.owl（相同模型的Turtle／RDF/XML）。
建置器：tools/build_ontology.py，以build-config.json列出的TTL為輸入；勿執行legacy-v0.2.0舊建置器。

部門PG來源：department-pg/model.json（通聯）、department-pg/deposits.json（存款）。
台幣／外幣／結構型存款：客戶識別、幣別、餘額、快照日期。
行員存款：同上加行員識別，指存款人本人是行員，不是管理客戶的AO。
底表候選與已知欄位有私銀SQL／metadata證據；幣別、日期、本人行員識別、JOIN、聚合與執行規則仍待確認，不猜測填入。
model.cypher為離線產生的Neo4j 5 metadata腳本，沒有客戶資料實例，尚未部署。

目前RDF：9個Class、2個Object Property、7個Data Property、5個Annotation Property；整合圖124個三元組。
PG：6個業務概念、50個metadata節點、82條關係；17個存款欄位定義。
分行／數位、帳戶及其他商品不納入本輪。

使用rdflib通用解析器與結構測試，不宣稱完整OWL推論、SHACL、GUI、SQL或真實資料驗證。
v0.3.0修改前快照：archive/before-v0.4.0/；更早快照：archive/before-v0.3.0/。
