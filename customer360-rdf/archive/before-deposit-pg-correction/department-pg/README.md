# 部門 PG：通聯與存款的 metadata 模型 v0.4.0

**金控／子公司 RDF/OWL 定義共通語意，部門 Property Graph 描述業務概念、資料欄位定義與底表映射候選。** 本目錄只建置 metadata，不包含任何客戶、存款、手機、地址或行員資料實例；不執行 SQL、RDF 推論或資料庫操作。

## Active 格式與檔案

| 檔案 | 用途／schema 選擇 |
| --- | --- |
| `model.json` | 保留既有兩個通聯概念與原有 contact shape，僅將 ontology_version 更新為 0.4.0 |
| `model.schema.json` | 通聯 JSON Schema Draft 2020-12；結構、完整 URI、pending/null 限制 |
| `deposits.json` | **active** 存款模組：五項共用欄位定義、四個概念、逐欄位候選、五張已觀察底表、證據與限制 |
| `deposit_model.py` | 存款模組的 **stdlib executable schema／驗證器** 與 PG projection；不另維護重複的 JSON Schema |
| `build_cypher.py` | 載入兩個 active 模組，合併及產生 Neo4j 5 metadata Cypher |
| `model.cypher` | 已產生結果，不手改、不自動部署 |
| `test_model.py`、`test_deposits.py` | 通聯回歸、存款契約、唯讀證據與合併輸出測試 |
| `drafts/employee-deposit.json` | 保留歷史草稿，已標記 superseded；**不是建置輸入**，active source 是 `deposits.json` |

`deposits.json` 是人工維護的 canonical 存款來源，不由 SQL 自動反推。驗證器拒絕未知概念／欄位／表／候選、缺漏／重複欄位、不正確分類碼、假 RDF URI、未核定的執行規則、無證據候選及資料實例擴充。這是受限且可審閱的 metadata 契約，不是通用 ETL 引擎。新增來源或核定規則時需同步審查 JSON、驗證器及測試。

## 共通語意參照不是實例映射

模型儲存完整 URI；以下 `fh:` 是 `https://example.org/ontology/holding#`，`bank:` 是 `https://example.org/ontology/bank#`。`example.org` 為示意命名空間，建置不解析 URL。

| 業務概念 ID | 名稱 | 類別參照 | 欄位定義／屬性參照 |
| --- | --- | --- | --- |
| `bank.loan_verification_mobile` | 貸款照會手機 | `fh:MobileContactInformation` | 既有 RDF 屬性參照 `fh:mobileNumber` |
| `bank.customer_visit_address` | 客戶訪問地址 | `fh:AddressContactInformation` | 既有 `fh:countryCode`、`city`、`district`、`addressLine`、`postalCode`、`fullAddress` |
| `bank.twd_deposit` | 台幣存款 | `bank:TWDDepositProduct` | `customerId`、`currency`、`balance`、`snapshotDate` |
| `bank.foreign_currency_deposit` | 外幣存款 | `bank:ForeignCurrencyDepositProduct` | 同上四項 |
| `bank.structured_deposit` | 結構型存款 | `bank:StructuredDepositProduct` | 同上四項 |
| `bank.employee_deposit` | 行員存款 | `bank:DepositProduct` | 同上四項及 `employeeId` |

六個概念的 subsidiary 均為 `bank`，department_owner 均為 `null`。通聯七個屬性仍參照原有 mobile/address domain 與 xsd:string range，七個 contact MappingSlot 的來源仍全部 pending/null。

**存款的 4／5 個欄位是資料欄位定義與映射 metadata，不是 product class 的 RDF datatype properties，更不是某客戶的欄位值。** 因此不建立 `bank:customerId` 等假 URI，也不替存款欄位填 product domain/range。`data_type_hint` 僅是設計提示，不是實體欄位型別承諾或自動轉型指令；snapshotDate 的 hint 保持 null。

父層 `bank-deposit.ttl` 負責 DepositProduct、三種金融商品面向及三種存款商品的 OWL 繼承；本 PG 只參照用到的四個商品類別，不複製繼承圖、不做分類推論或自動等價。`REFERS_TO_CLASS` 等 PG 關係不產生 RDF 三元組，不將資料列映射成 rdf:type，也不表示 owl:sameAs、owl:equivalentClass 或 rdfs:subClassOf。

## 行員存款的已確認定義

行員存款指 **存款人本人為銀行行員的存款**，不是由行員／AO 管理的客戶存款，亦不限於員工優惠方案。這與台幣／外幣／結構型概念可能重疊，不是互斥分類。

- 尚未核准 Employee 類別，因此保留一個 `PendingSemanticReference`，class_uri、relation_uri、source_table、source_column、join_rules 全部 null，不捏造 RDF URI。
- `employeeId` 來源、欄位及身分關聯未確認；候選為空、join_rules 為 null。
- **不得使用 `AUM_TMP02.EMP_NO`**：唯讀 SQL 證據顯示該員編來自 PB_CUST_005 的客戶管理 AO，不代表存款人本人。該來源只記為 rejected observation，不建立來源表節點或映射。
- 唯一觀察到的行員存款底表是 `DSDEP.EMP_DEP_NT_ACCT_HS`；是否涵蓋所有行員本人存款未知。

## 底表與分類證據

下列是本地檔案觀察，不是資料庫查核結果。SourceTable 的 `database_verified_json` 固定為 JSON `false`。

| 已觀察表名 | customerId 原始欄位 | balance 原始欄位 | SQL 使用日期 | 分類證據 |
| --- | --- | --- | --- | --- |
| `DSDEP.DEP_NT_ACCT` | CUST_ID | BAL_AMT | DATA_DT | ACT_CD |
| `DSDEP.DEP_NT_ACCT_HS` | CUST_ID | BAL_AMT | LST_MTN_DT | ACT_CD |
| `DSDEP.DEP_FN_ACCT` | CUST_ID | AVAIL_BAL | LST_MTN_DT | ACC_CD |
| `DSDEP.DEP_FN_ACCT_HS` | CUST_ID | AVAIL_BAL | LST_MTN_DT | ACC_CD |
| `DSDEP.EMP_DEP_NT_ACCT_HS` | CUST_ID | BAL_AMT | LST_MTN_DT | ACT_CD |

- 台幣 ordinary 分類碼：2311、2321、2322、2331、2332、2333、2335、2336。
- 外幣 ordinary 分類碼：2317、2327。
- 結構型碼：2545；NT、FN 與 employee 分支均為候選，**不假設可直接 UNION、互斥或套用既有時間窗**。
- employee 分支的 ACT_CD 同時有上述 NT ordinary 碼及 2545；這只記錄來源分類，不能當作行員本人身分認定或完整來源篩選規則。

`customerId`、`balance` 的 mapping 狀態為 `observed_raw_candidate`；已觀察欄位不表示已核定完整取數方案。每個 mapping 的 selected `table`、`column`、`constant` 都保留 null，`candidates` 明列表、欄位、意義與 evidence ID。餘額只對應底表原始欄位，不沿用舊 SQL 的 SUM／group by；跨來源客戶識別、列粒度、聚合與金額幣別均未核定。

### 幣別及快照日期仍待確認

- **四個概念的 currency 全部 pending，含台幣存款**；沒有已核對的幣別欄位或計價幣別，也不填 TWD 常數。FN SQL 的 TYP_DTL 寫台幣，employee 分支寫外幣卻含台幣 DETAIL，不能當來源幣別碼。
- NT current SQL 使用 DATA_DT；其餘四張表的分支使用 LST_MTN_DT。這只是 SQL 使用證據，snapshotDate 並未選定該欄位。
- `收入_metadata.xlsx` 的 `DSDEP.DEP_NT_ACCT_HS`：row 22 DATA_DT 為資料日期；row 39 LST_MTN_DT 沒有業務定義；row 78 YYYYMM 為 Snapshot年月。
- 同檔 `DSDEP.EMP_DEP_NT_ACCT_HS` 的對應列為 22、39、77。年月與某日不等價；不補月初／月底，不把 LST_MTN_DT 解讀為已核定快照日。
- `AUM_metadata.xlsx` 使用 `DSDEP.EMP_NT_ACCT_HS` 工作表名稱，與 SQL 不同；只保留命名差異證據，不新增另一張已確認表或自動別名。

### 證據與執行計畫分離

`deposits.json.evidence` 保存完整專案相對路徑及 SQL 行範圍／工作表與列號：current 59–89、historical 91–123、employee 125–136、union 140–182，以及上述 metadata 與 AO 區別證據。歷史條件 YYYYMM >= 202506 僅保存在 `observations.historical_filter`，不是 operational default。

整個 deposit module 的 `execution` 中 sql、join_rules、filter_rules、union_rules、aggregation_rules、row_grain、partition_windows 全部 null。沒有來源執行 SQL、帳戶模型／鍵、分行或數位分類。證據中的分類碼及日期字串是規格證據，不是客戶資料實例。

## 合併 PG schema

所有節點另有 `MetadataNode` 標籤與 `scope: metadata_only`。

| 固定標籤 | 數量 | 說明 |
| --- | ---: | --- |
| BusinessConcept | 6 | 兩個通聯＋四個存款概念 |
| OntologyClassReference | 6 | 兩個通聯＋四個存款類別 URI |
| OntologyPropertyReference | 7 | 僅既有通聯屬性 URI |
| MappingSlot | 7 | 僅既有通聯 pending mapping |
| MetadataModule | 1 | active deposit module、全域 evidence／observations／execution JSON |
| DataFieldDefinition | 17 | 每概念獨立的 4／4／4／5 個資料欄位定義與 mapping JSON |
| SourceTable | 5 | 只建立已有檔案證據的底表參照 |
| PendingSemanticReference | 1 | 未核准的存款人行員語意關聯，無 RDF URI |

| 固定關係類型 | 起點 → 終點 | 數量 |
| --- | --- | ---: |
| REFERS_TO_CLASS | BusinessConcept → OntologyClassReference | 6 |
| HAS_MAPPING | BusinessConcept → MappingSlot | 7 |
| REFERS_TO_PROPERTY | MappingSlot → OntologyPropertyReference | 7 |
| HAS_DOMAIN_REFERENCE | OntologyPropertyReference → OntologyClassReference | 7 |
| HAS_CONCEPT | MetadataModule → BusinessConcept | 4 |
| HAS_FIELD_DEFINITION | BusinessConcept → DataFieldDefinition | 17 |
| CANDIDATE_SOURCE | DataFieldDefinition → SourceTable | 30 |
| HAS_PENDING_REFERENCE | BusinessConcept → PendingSemanticReference | 1 |

合計 **50 節點、79 關係**。同一欄位在同一表有多個日期候選時仍只有一條 CANDIDATE_SOURCE 關係，細節保存在 mapping_json；currency 和 employeeId 不連來源表。

ID 穩定：欄位為 `<concept-id>.<field-name>`，表為 `source:<schema.table>`，RDF 參照 ID 即完整 URI，關係為 `<source-id>|<type>|<target-id>`。Neo4j 不保存 null property，因此未知值、巢狀 metadata 與布林查核狀態以 JSON 字串保存，讀取時用 JSON parser 還原。輸出安全 escaping，不把模型值當 label/type 或 Cypher 語法。

輸出以 `MetadataNode.id` 唯一約束和穩定 ID MERGE，可重複載入同一 metadata；不刪除舊節點／關係、不提供遷移或完整同步，也不會連線或部署 Neo4j。

## 離線建置與測試

在 `customer360-rdf-owl` 執行：

```sh
python -B department-pg/build_cypher.py
python -B -m unittest discover -s department-pg -v
./.venv/Scripts/python.exe -B -m unittest discover -s department-pg -v
```

只需標準函式庫即可建置及跑主要測試；不安裝套件。建置只寫自身目錄的 `model.cypher`，UTF-8／LF、無時間戳記；即使概念、來源、欄位、候選及證據集合重排，輸出仍確定一致。`load_model()`、`build_graph(model)`、`render_cypher(model)` 保留通聯 API；新增 `build_combined_graph()`、`render_combined_cypher()` 與 main 載入兩個模組。

測試涵蓋既有通聯、4／5 欄位契約、來源／分類證據、pending 日期／幣別／員工身分、禁止 AO 當存款人、禁止假 RDF property、端點、固定 label/type、escaping、確定性及產生檔逐位元組比對；可唯讀檢查本地 SQL 與 XLSX，不查資料庫。

若環境已有 rdflib，額外解析父層 holding-core.ttl 與 bank-deposit.ttl 驗證所有 RDF 參照及核准的產品繼承；不啟動 reasoner。缺少選用 rdflib 或父層尚未提供 bank-deposit.ttl 時，相關測試明確 skip；通聯交叉檢查接受既有 v0.3.0 或新版 v0.4.0 核心。父層負責核心、catalog、export 與 root docs；本目錄不修改它們。
