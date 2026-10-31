# 客戶360 RDF／OWL＋私銀部門 PG：v0.16.0 交接

## 本輪：證券總指標涵蓋範圍（securities-summary-20261024）

使用者確認後完成本機 PG 實作。RDF 與 ontology_version 保持 v0.16.0，五份 RDF、Turtle／OWL、build-config、catalog 均逐位元組未變。原七份指標／通聯 JSON 逐位元組保持；departments.json 僅在原42項採用清單加入下列兩項。

| PG ID／名稱 | 沿用類別 | 涵蓋分項 |
|---|---|---|
| securities.total_aum／私銀－證券總 AUM | SecuritiesAUM | 複委託債券、結構型、基金、外國股票、台股5項 AUM |
| securities.total_fee_income／私銀－證券總手收 | SecuritiesFeeIncome | 複委託債券、結構型、基金、外國股票4項手收 |

新增 securities-summary-metrics.json 及 securities_summary_model.py（第九份 active JSON）。9條 HAS_COMPONENT_METRIC 是 PG 分項涵蓋 metadata，不新增 RDF Property，也不代表可直接 SUM。總指標的 lineage_mode=via_component_metrics、coverage_status=included_products_only、calculation_status=pending_tool_definition。

總指標經分項追溯既有金額／估值／日期來源；沒有另造 SourceTable 或新增總指標到底表的直接連線。原分項仍各自保留，總指標與其分項不得再次一起加總。「總」僅代表目前納入私銀模型的證券商品範圍，不宣稱證券公司全部業務。

兩項總指標只有7個結果元素：AUM為amount／currency／aumAsOfDate，手收為amount／currency／incomePeriodStart／End。均pending、table／column=null、candidates=[]，不帶入分項估值數量／單價、單一客戶或商品識別；execution全null，沒有新增Tool綁定、理專關係或可執行計算。

總 AUM 排除股票設質。舊SQL把AUM_027與AUM_028同標證券／台股，不能只篩COMP／PROD取本輪總額，須保留來源分支血緣。AUM_TMP02／AUM_REPORT完整產製邏輯未提供，字典「各分類月內最新日期」仍屬draft_metric_query，不當正式月底或同日口徑。

總手收先不含缺來源的台股手收；外國股票保留淨手收、月底最後兩工作天移至次月及UNION投影去重觀察。來源日曆、基金current取債券日期、外股current AM仍讀AM_SEC_M、私銀客戶歸屬連接等疑點不改寫。

新備份 archive/before-securities-summary-20261024；修訂與來源SHA-256見 department-pg/history/securities-summary-20261024.json。本輪沒有執行來源SQL、資料庫查核、Git提交或Neo4j部署。

更新2026-10-24。固定沿用本檔名作正式入口；先讀 ../AGENTS.md、本檔、README.md，再讀 department-pg/METRIC-TABLE-SOURCES.md。

工作目錄 C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。使用者要求先討論實質變更清單、確認再執行；本輪已逐項確認，最後指示「可以，啟動」，已完成本機建置／驗證，沒有部署。方向保持證券優先；可確認來源的證券商品指標已納入。

## 前輪 v0.16.0 部門基礎（本輪證券總指標見上列）

1. 金控新增 fh:Department、fh:usesMetric（Department → Metric）；銀行新增 bank:PrivateBankingDepartment，直接繼承 Department。原 fh:department 仍為治理註記。五份來源／整合輸出／catalog／active JSON 同步0.16.0。
2. 新增 PG departments.json 及 department_model.py，只有 bank.private_banking（私銀）一層。它是 metadata 概念並參照部門類型，不建立真實組織實例，不拆一部／二部、分行或團隊。
3. 私銀原有42條採用連線保持，本輪增為44條 USES_METRIC，連到原指標及兩項證券總指標，含AUM／手收／LUM／利收及通用部分範圍手收。關係定義參照 RDF usesMetric；PG 保存父類／domain／range參照但不推論。
4. 42項指標顯示名稱加私銀並保留銀行／證券來源；ID、定義、欄位候選、底表、理專關係與計算口徑保持。七份舊 active JSON 除 ontology_version 與指標 name 外完全相同。
5. 採用不等於承作子公司、來源權責、理專歸屬、閱覽權限或自動加總。私銀部門屬銀行；證券指標仍屬證券。原 department_owner=null 等內容不因新增部門而改寫。

前輪備份 archive/before-department-v0.16.0；名稱前後對照與新增 URI 見 department-pg/history/department-v0.16.0.json。前一輪詳細交接完整保存在本輪備份；更早 archive/before-pg-income-extension-20261024、before-v0.15.0 等保持。history 不參與建置，原記錄逐位元組保持。

## 架構與原有決議保持

RDF 定義共通／子公司類別和正式繼承；PG 描述部門、具體指標、商品範圍與來源 metadata。圖譜保存定義，SQL 執行與計算交給 Tool。Tool 綁定及實作尚未完成；所有 execution=null，實體欄位映射待定，舊候選保留，新增候選空白。SourceTable observed_in_files、database_verified=false；原SQL cp950，JSON／Turtle UTF-8。

AUM、LUM、FeeIncome（手收）、InterestIncome（利收）直接繼承Metric；商品關係分別measuresProduct、lumMeasuresProduct、feeIncomeFromProduct、interestIncomeFromProduct，domain分離、range=FinancialProduct。RDF銀行／證券指標Class不加私銀前綴。指標的底表關係保持，不從部門或商品Class直接接底表。

規劃型信託、保管、外匯、開狀、黃金、放款先統一金融商品；規劃型信託／保管有AUM及手收，外匯／開狀／黃金只有手收，放款有LUM與利收，沒有放款AUM。FinancialService及服務專屬關係已退出。ETF、基金、集合管理分列，SI／ELI／FCI分列。證券不繼承銀行商品分類，也不套用銀行理專關係。

前輪已補存款利收、債券信託／自營手收；DCI擴充DCD／TMU、保險擴充兩項PS月檔，ID保留。收入按SQL業務分類，手收不限定純手續費，利收不限定純客戶利息。通用商品手收維持原partial_scope，不是完整總手收或可直接相加清單。

bank-business-metrics共12項、115欄位定義，全部pending／null、candidates=[]。使用／定義部門原為私人銀行，來源權責待定；七項手收沿用理專關係，存款／放款利收未加理專歸屬。行員存款須識別存款人本人為行員，不以AO員編代替；serves不代表閱覽授權。

來源疑點保持：存款GROSS_INCM、初建私銀條件與月替換差異、TMP01註解問題；債券信託BRHREBATEAMT+WKR028/100、自營SUM(ABS(INC_AMT_NT))；DCI只取FO108_W的DCD，FX排除DCD／Cash Bond；保險PS為客戶貢獻度、跨次月、日月重疊與UNION投影去重；保險AUM原始投資金額；ETF AUM分類取值；信託累計費用；LUM會科1886／應付保證及日期／匯率；證券WKB02／WKB24識別、日期、FX與UNION等。均為檔案觀察，不擅改原SQL。

證券基金BONDTRADM_SEC、外股AM_SEC僅日期查詢；T_LAST_TWO_WORKDAYS缺schema／底層定義，維持unresolved_supporting_relations，不補造來源表。

## 三項pending及後續範圍

pending_scope精確保持三筆，均不是active指標：

- securities.stock_pledge_lum：pending_source_definition，股票設質只有Qty×Product_Price估值，缺實際借款／融通餘額，不建AUM或LUM。
- securities.taiwan_stock_fee_income：pending_source_definition，未找到可辨識收入分支，先不建；原台股AUM保留。
- bank.collective_account_fee_income：pending_business_semantics，TA／TB／TD／TE先被前方基金CASE遮蔽，先不另建，不改SQL；原集合AUM保留。

銀行總AUM／總收入、目標達成率等留下一輪確認；本輪證券總指標僅定涵蓋，不核定計算。客戶母體、客戶數／分群、放款額度／人數尚未建模；Organic／Migration／轉介依賴人工來源未確認完整。11.TARGET.sql確實計算達成率；10._INCOME_ROA.sql僅註解寫ROA／ROBA比率，程式只彙整分子／分母，未實作除法。

股票設質退場及舊ID對照保存在history/stock-pledge-aum-retired-v0.15.0.json、changes-v0.15.0.json；SQL範圍查核見sql-scope-review-20261024.json。權限、帳戶、分行／數位、畫圖與實體欄位映射繼續暫緩。

## Active來源與統計

RDF5份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。PG9份：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments、securities-summary-metrics，各有schema／Python驗證器。RDF輸出由tools/build_ontology.py產生，PG由department-pg/build_cypher.py合併，只依賴標準函式庫，不手改產生檔、不連網解析example.org。

44項指標：19AUM（銀行13／證券6）、1銀行LUM、22手收（銀行17／證券5）、2銀行利收；本輪新增兩項總指標涵蓋定義，原42項保持。

RDF：43Class、9Object Property、19Data Property、5Annotation Property、434triples。PG：52BusinessConcept、668節點、1415關係，含420DataFieldDefinition、52SourceTable、61BusinessRelationDefinition、8MetadataModule、7MappingSlot。44USES_METRIC、9HAS_COMPONENT_METRIC；88HAS_SOURCE_TABLE、3USES_VALUATION_SOURCE、2USES_DATE_LOOKUP_SOURCE。

RDF19＋PG101＝120項測試通過，無略過。前輪部門新增與命名保持驗證；本輪RDF／原七份JSON逐位元組未變，兩項總指標／九條涵蓋／44項採用正確，跨子公司及所有權分離、來源可達、錯誤目標／權限／執行規則反例、確定性與產出一致均通過。24份來源SQL／Excel SHA-256未變。

建置／測試命令見README。未執行來源SQL、真實資料庫查核、完整OWL reasoner、SHACL、GUI、Neo4j部署或Git提交，也沒有已確認雲端備份。

## 維護注意

保存性測試各有歷史基準，不能全域換archive路徑。review_contract_v015.py與review_contract_pg_income.py保留前輪核定差異；review_contract_v016.py僅供測試還原核定顯示名稱、移除三個新增RDF主詞與版本標頭，來源、欄位、型別、權責及規則不忽略。test_departments.py直接驗證本輪精確異動。

歷史一次性seeder與tools/legacy-v0.2.0不可重跑。outputs/department-v0.16.0/apply.py為本輪已執行的維護紀錄，不是建置入口。before-deposit-pg-correction為錯誤組合OWL實作，不可恢復。舊圖與舊文件不代表本版。

Cypher只有MERGE，沒有刪舊資料或自動遷移。未來部署須先確認目標namespace與舊版範圍，不能假設重跑即完整同步。本輪未部署。

## 本輪總指標驗證與查閱

test_securities_summary.py 直接驗證兩項／九條精確涵蓋、RDF逐位元組未變、原七份JSON與歷史不變、部門只新增兩個採用ID、既有節點／關係保存、七個空映射、SQL證據／草稿狀態、原來源角色、錯誤範圍／公式反例及產出確定性。底表清單把兩項總指標標成「沿分項追溯」；同一表在不同分項可同時作金額來源及日期查詢，分角色呈現。

```cypher
MATCH (d:BusinessConcept {id: 'bank.private_banking'})-[:USES_METRIC]->(t:BusinessConcept)
MATCH (t)-[:HAS_COMPONENT_METRIC]->(c:BusinessConcept)
OPTIONAL MATCH (c)-[:HAS_SOURCE_TABLE|USES_VALUATION_SOURCE|USES_DATE_LOOKUP_SOURCE]->(s:SourceTable)
RETURN d, t, c, s;
```

此查詢供未來已載入metadata的Neo4j Browser查閱，本輪未執行。HAS_COMPONENT_METRIC只表涵蓋，不是可執行SUM、正式RDF繼承或資料實例。產生器只MERGE，沒有部署／刪舊資料或自動遷移。銀行總量及目標比較繼續暫緩。

## Fabric 視覺化接續（2026-10-24，本機準備）

使用者要求把目前 RDF＋PG 轉成 Microsoft Fabric 可視圖譜。新增 `tools/export_fabric_graph.py`、`tools/fabric_graph_runtime.py`、`tests/test_fabric_export.py`、`FABRIC-GRAPH.md` 與獨立 `outputs/fabric-v0.16.0/` 匯入包；原 RDF、PG、SQL、欄位映射及版本均未變更。

圖投影為 677 nodes／1,498 edges（原 PG 668／1,415 全部保留），13 node types／43 edge types，另保存434個RDF triples及原始TTL／OWL。59張Delta表含56張型別表與3張audit表。PG完整properties放`properties_json`，原label放`pg_label`；RDF與PG用相同URI合併。`RDF_DECLARED_*`僅domain/range視覺化，不是實例事實。GQL查詢先看私銀證券，再看總指標分項及來源；不執行金額或業務SQL。

Fabric Graph使用OneLake Delta資料。原生Fabric Ontology只能承接部分OWL，不足以直接串起本次PG，故本次採Graph model。尚無Fabric專用connector；使用Chrome分頁開啟app.fabric.microsoft.com，目前停在登入頁，已請使用者自行登入並提供工作區名稱／連結。**沒有雲端建表、Notebook執行、Graph model部署或capacity啟用。** 下一步先取得工作區與Lakehouse實際UUID及可用Graph環境，再匯入Notebook；不能宣稱本機測試等於Fabric驗收。

Notebook內嵌資料，預設workspace／lakehouse UUID空白、CREATE_GRAPH_MODEL=False；驗證runtime context符合指定目標。建表只新增快照表，既有相同內容可略過續跑、不同內容先停止；建Graph只新增、同名則停止，不覆蓋既有model。token只在Fabric執行時由NotebookUtils取用，不寫入檔案或輸出。

實作依Fabric公開JSON Schema（dataSources1.1用item reference＋相對路徑、graphDefinition無filter），部分官方頁範例與Schema有出入。官方共用identifiers Schema回傳404，結構檢查只能部分完成，詳`validation/schema-validation.json`；不得宣稱完整官方驗證。需登入目標Fabric後驗證Graph建立、來源同步、GQL及互動圖。
