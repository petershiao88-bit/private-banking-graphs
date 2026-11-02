客戶360共通語意與部門映射 v0.3.0，2026-10-21，設計草案。

最新說明請閱讀同目錄 README.md；接續請閱讀 HANDOFF-ZED-RDF-20261021.md。

RDF／OWL：金控／子公司共通語意。手機、地址及七個欄位均提升至金控，不再保留三家公司重複的通聯定義。
模型來源：holding-core.ttl。
整合輸出：customer360-ontology.ttl、customer360-ontology.owl（相同 RDF 圖的 Turtle／RDF/XML）。
新建置器：tools/build_ontology.py，以 build-config.json 列出的 TTL 為輸入；勿執行 legacy-v0.2.0 的舊建置器。

部門 PG：department-pg/model.json 定義貸款照會手機、客戶訪問地址與待確認底表映射；model.cypher 為離線產生的 Neo4j 5 metadata 腳本，未部署。
PG 不包含客戶資料實例，不執行 OWL 推論；實際部門、底表、欄位及取數規則尚未核定。

目前 RDF：5個Class、2個Object Property、7個Data Property、5個Annotation Property；整合圖100個三元組。
已使用 rdflib 通用解析器檢查格式與圖內容一致；未執行完整 OWL reasoner、SHACL、GUI、SQL 或實際資料測試。

v0.2.0 交付與先前部門 TTL 保存在 archive/before-v0.3.0/，不屬於目前有效模型。
