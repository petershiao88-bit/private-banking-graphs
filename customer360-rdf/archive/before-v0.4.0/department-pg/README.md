# 部門 Property Graph：業務概念與實體映射中繼資料

本目錄採用 **金控／子公司 RDF/OWL 定義共同語意，部門 PG 描述業務概念及資料來源映射** 的分工。只處理 metadata，不包含客戶、手機、地址等資料實例，也不新增公司通聯類別、部門 OWL 子類別或推論規則。

語意契約對應核心 **v0.3.0**，完整命名空間為 `https://example.org/ontology/holding#`。`example.org` 是示意 URI，不是實際服務；建置不解析 URI、不連網、不連資料庫。

## 檔案與唯一編輯來源

| 檔案 | 用途 |
| --- | --- |
| `model.json` | canonical 業務概念與待確認實體映射模型；人工編輯來源 |
| `model.schema.json` | JSON Schema Draft 2020-12；結構、完整 URI、pending/null 限制 |
| `build_cypher.py` | Python 標準函式庫建置器；驗證契約、產生 PG 節點／關係與 Cypher |
| `model.cypher` | 確定性產生的 Neo4j 5 metadata DDL/DML；不要手改 |
| `test_model.py` | 標準函式庫 unittest；可選擇利用既有 rdflib 交叉檢查核心 |

Schema 描述結構；建置器另檢查概念／映射 ID 唯一性、完整欄位集合、類別／屬性／domain 對應與 xsd:string range。這是刻意限定的第一版契約，不是通用 ETL 設定語言；不需要安裝 jsonschema 或 rdflib 才能建置。新增已確認的來源或概念時，必須同步審查模型、schema、建置器契約和測試，不可只將 pending 改成 resolved。

## 擴充草稿

使用者新增討論的「行員存款」及五個業務欄位位於 `drafts/employee-deposit.json`，詳見 `drafts/README.md`。這是含私銀來源證據的獨立格式草稿，不是本目錄現行建置器的輸入，不會改變下述兩個通聯概念或已產生的 Cypher。

## 兩個業務概念

以下簡寫 `fh:` 僅供閱讀；`model.json` 與 PG 參照皆儲存完整 RDF URI。

| 穩定概念 ID | 業務名稱 | 參照共同類別 | 屬性參照 |
| --- | --- | --- | --- |
| `bank.loan_verification_mobile` | 貸款照會手機 | `fh:MobileContactInformation` | `fh:mobileNumber` |
| `bank.customer_visit_address` | 客戶訪問地址 | `fh:AddressContactInformation` | `fh:countryCode`、`fh:city`、`fh:district`、`fh:addressLine`、`fh:postalCode`、`fh:fullAddress` |

兩個概念的 `subsidiary` 均為 `bank`，`department_owner` 均為 JSON `null`，不以「貸款」或「訪問」猜測負責部門。

`mobileNumber` 的 domain 是 `MobileContactInformation`；六個地址屬性的 domain 是 `AddressContactInformation`；七個屬性的 range 均為 `http://www.w3.org/2001/XMLSchema#string`。這些是對核心語意契約的參照，而非重新定義。核心另有 `Customer`、`FinancialProduct`、`ContactInformation`，但本 PG 不為未使用的類別建立節點。

## 語意與實體映射的界線

- 業務概念回答「部門業務稱呼是什麼、參照哪個共通語意」。它不是 OWL class，也不是某客戶的一筆通聯資料。
- 每個屬性有一個 `MappingSlot`，回答「將來需要確認哪項來源映射」。穩定 ID 為 `<concept-id>.<property-local-name>`。
- 每個槽的 `source` 固定為 `status: "pending"`，`table`、`field`、`sql`、`join_rules`、`filter_rules` 全部為 `null`。**未知不代表無需 join/filter**；不放假表名、假欄位、空規則、SQL 模板或可執行 SQL。
- 一個槽不保證未來對應一個實體欄位，也未假設每個地址欄位來自同一表。例如 `fullAddress` 的實體取得／組合方式尚未確認。
- 不建立 `SourceTable`／`SourceField` 節點，因為尚無已知實體來源。七個槽不是七筆資料，也不是七個已確認欄位。
- `REFERS_TO_CLASS`、`REFERS_TO_PROPERTY` 與 `HAS_DOMAIN_REFERENCE` 全是 PG metadata 關係。它們**不產生 RDF 三元組、不執行 OWL 推論、不表示 owl:sameAs / owl:equivalentClass / rdfs:subClassOf，也不將資料列自動對應為 rdf:type 實例**。
- `range_uri` 只描述參照的 RDF datatype，不會自動轉型、查詢、匯入、更新或驗證客戶資料。未提供客戶 ID、個體 UUID、員工、商品或貸款事件模型。

## PG graph schema

所有節點另具有共用標籤 `MetadataNode` 與 `scope: "metadata_only"`。

| 固定節點標籤 | 數量 | ID／主要屬性 |
| --- | ---: | --- |
| `BusinessConcept` | 2 | 概念 ID；`name`、`subsidiary`、`department_owner_json` |
| `OntologyClassReference` | 2 | ID 即完整類別 URI；`uri` |
| `OntologyPropertyReference` | 7 | ID 即完整屬性 URI；`uri`、`range_uri` |
| `MappingSlot` | 7 | 概念 ID + 屬性名稱；`status`、`source_json` |

| 固定關係類型 | 起點 → 終點 | 數量 |
| --- | --- | ---: |
| `REFERS_TO_CLASS` | BusinessConcept → OntologyClassReference | 2 |
| `HAS_MAPPING` | BusinessConcept → MappingSlot | 7 |
| `REFERS_TO_PROPERTY` | MappingSlot → OntologyPropertyReference | 7 |
| `HAS_DOMAIN_REFERENCE` | OntologyPropertyReference → OntologyClassReference | 7 |

合計 **18 節點、23 關係**。關係 ID 為 `<source-id>|<relationship-type>|<target-id>`；節點與關係依 ID 排序，JSON object key 亦排序，不含時間戳記。

Neo4j 不儲存 null property；因此 `department_owner_json` 儲存 JSON 字串 `"null"`，`source_json` 儲存包含所有 null slot 的完整 JSON 字串，避免遺失「未知」的明確表達。讀取時以 JSON parser 還原；不是 SQL，也不是客戶資料。JSON 字串再以字串 literal escaping 寫入 Cypher，正確處理引號、反斜線及換行；不將模型值插入 label/type 或 Cypher 語法。

輸出先建立 `MetadataNode.id` 唯一性約束，再依穩定 ID `MERGE` 節點／關係。重複執行同一輸出不應新增重複 metadata；不提供刪除過期節點／關係或遷移功能，不應視為完整資料庫同步。此標籤與 constraint 名稱為本 metadata 模型保留，既有不一致資料仍可能導致 constraint 失敗。輸出沒有連線設定、APOC 呼叫、部署步驟或來源查詢；是否在 Neo4j 執行由使用者另行決定。

## 離線建置與測試

在 `customer360-rdf-owl` 目錄執行：

```sh
python -B department-pg/build_cypher.py
python -B -m unittest discover -s department-pg -v
```

建置器僅寫入自身目錄的 `model.cypher`，無論從哪個工作目錄啟動；UTF-8、LF，位元組結果固定。`-B` 避免產生 Python bytecode cache。

測試包含 graph endpoints、穩定 ID、完整類別／屬性／domain 契約、pending source 安全性、禁止 instance/inference、Cypher MERGE 與約束、JSON escaping、輸入陣列重排的確定性，以及已產生檔案的逐位元組比對。

若執行測試的 Python 環境已有 rdflib，額外以唯讀方式解析上層 `holding-core.ttl`，檢查 v0.3.0 的 OWL class、datatype property、domain、range。rdflib 不存在、核心不存在或核心仍為舊版時，該項測試會明確 skip；其餘 stdlib 契約測試照常執行。這不會修改核心、安裝套件或啟動 reasoner。
