# 客戶360 RDF／OWL＋部門 PG：v0.10.0 交接

更新：2026-10-22。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 最新決議與結果

使用者已授權先補可直接承接的銀行項目。本次在 product-fees.json 新增四項手收：銀行海外股票、境內 ELI、境內 FCI、DCI 純手續費。四者沿用 bank:BankFeeIncome、fh:feeIncomeFromProduct 與銀行理專歸屬關係。海外股票參照股票＋海外分類；ELI／FCI／DCI 參照結構型金融商品，不新增 RDF 類別或屬性。

新增底表：DSFND.PB_FUND_SPREAD_DAILY；DSDEP.ELI_PERFO_RPT／_HS；DSDEP.FCI_PERFO_RPT／_HS；DSDEP.DCI_PERFO_RPT／_HS。DCI 只取 INCOME_037 的來源範圍，不納入 INCOME_038／DSTAS.FO108_W 的 TMU 損益，也不等同結構型存款。ELI／FCI 與 SI 保留為獨立指標，不自動加總或新增 AUM。

新四項各有十一個 pending 欄位，table／column 全 null、candidates 全空，共新增 44 個欄位定義。新舊指標的實際理專／商品識別、收入期間、幣別與執行規則均未核定。原有概念、欄位、候選與來源證據保留。共通 RDF 與輸出逐位元組保持 v0.10.0。

對應主體維持 **AUM／手收指標對到底表，不是商品分類對到底表**；欄位映射先不處理。目前共 13 項 AUM、12 項手收有 table_sources，四份指標 JSON、契約、PG 投影與測試已同步。對照清單見 department-pg/METRIC-TABLE-SOURCES.md。

目前有 53 條 HAS_SOURCE_TABLE、3 條 USES_VALUATION_SOURCE、2 條 USES_DATE_LOOKUP_SOURCE，端點為指標 BusinessConcept → SourceTable。共 33 個 SourceTable，未新增商品分類到底表的關係。table_sources_json 保存每個指標的表級來源角色與證據。

通用手收只涵蓋已盤點 SI／SN／銀行基金／海外股票／ELI／FCI／DCI 純手續費來源，仍標 partial_scope，不代表完整銀行總手收或加總規則。證券基金手收的債券表、外股手收的 AM_SEC 僅列日期查詢；未當成額外金額來源。T_LAST_TWO_WORKDAYS 缺 schema／底層定義，四項證券手收僅保留為未釐清輔助關係。這些都是檔案觀察，database_verified=false。

本次銀行手收擴充前快照為 archive/before-bank-fee-extension-20261022/；前次表級對應快照為 archive/before-table-sources-20261022/。先前詢問通聯底表的問題已不適用本次範圍。

使用者確認金控層級的 AUM／手收只需指標與計算必要元素，不要求詳細計算公式。已依確認的設計新增八個金控 Data Property，同步 RDF 整合輸出、PG 語意參照、契約與回歸測試。本輪只做本機 metadata 建模，沒有來源取數 SQL、資料庫連線、Neo4j 部署或新圖。

客戶與商品識別、幣別匯率及本次已核定四項以外的商品範圍維持待討論；保留既有候選與 pending/null，不自行定案。權限、帳戶模型、分行／數位及畫圖繼續暫緩。詳細公式、認列細節、選日與月底跨月規則留在子公司／部門，不再是金控必要元素建模的確認前提。

後續尚待討論：銀行保險 AUM／手收的分類與原始投資金額意義、ETF、集合管理與各種信託／保管、海外債券收入中的交易利得、自營債券收入性質、FX／黃金／DCI 的 TMU 損益、開狀服務，以及利收新分支。這些尚未因本次四項擴充而自動納入。

## 新增八個金控 Data Property

| 屬性 | 中文名稱 | Domain | Range |
|---|---|---|---|
| fh:metricAmount | 指標金額 | fh:Metric | xsd:decimal |
| fh:aumAsOfDate | AUM 基準日 | fh:AUM | xsd:date |
| fh:valuationQuantity | 估值數量 | fh:AUM | xsd:decimal |
| fh:valuationUnitPrice | 估值單價 | fh:AUM | xsd:decimal |
| fh:incomePeriodStart | 收入期間起日 | fh:FeeIncome | xsd:date |
| fh:incomePeriodEnd | 收入期間迄日 | fh:FeeIncome | xsd:date |
| fh:feeBaseAmount | 手收計算基礎金額 | fh:FeeIncome | xsd:decimal |
| fh:feeDeductionAmount | 手收計算扣減金額 | fh:FeeIncome | xsd:decimal |

金控只定義各元素的共通語意。metricAmount 為指標結果；估值數量／單價、手收基礎／扣減金額是按情境適用的輸入。數量單位、價格報價基準與扣減項目的具體意義留在部門 PG 描述。沒有新增必填、固定基數、公式、毛淨額算法、日期邊界算法或單位常數；不要求所有 AUM 都有數量／單價，也不要求所有手收都有扣減。

銀行與證券沿用金控屬性，不各自重複定義同義屬性。八項屬性全部定義於 holding-core.ttl，其他四份來源只同步版本資訊；既有 RDF 概念與屬性定義保持。

## 分層原則與既有語意

金控／子公司 RDF 定義共同概念、關係、屬性與正式繼承；部門 PG 描述業務概念、欄位、語意參照、候選來源與 SQL 觀察。PG 不含客戶、人員、部位或產品資料實例，example.org 是示意命名空間。

- fh:Metric 的子類是 fh:AUM 與 fh:FeeIncome；銀行與證券各有相應子類。metricAmount 的 domain 為 Metric，可適用於這些指標。
- AUM 用 fh:measuresProduct 衡量金融商品；手收用 fh:feeIncomeFromProduct「手收來源商品」連金融商品，兩條關係不混用，也沒有手收指向 AUM 的關係。
- bank:BankEmployee 繼承 fh:Employee；bank:FinancialAdvisor 再繼承行員，沿用 bank:employeeId，不另造理專 ID。
- bank:attributedToAdvisor 是 BankFeeIncome → FinancialAdvisor；銀行通用／SI／SN／基金手收參照它，證券不套用銀行理專關係。理專與收入實際歸屬未核定。
- 銀行與證券商品分類直接繼承 fh:FinancialProduct，治理各屬其子公司；證券不繼承銀行商品。海外不等同外幣，組合商品仍留 PG，不新增組合 OWL Class。
- fh:serves 連職員與客戶，不代表資料閱覽授權。權限由使用者暫緩，deferred_by_user 只記錄延期。
- 不新增未確認的 Hash、必填、基數、互斥、等價、sameAs、keys、反向關係、property chain、SHACL 或額外資產模型。

## RDF 與 PG 有效來源

RDF 五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。build-config.json 明列來源，catalog-v001.xml 對應本機 URI／v0.10.0；tools/build_ontology.py 產生自含 customer360-ontology.ttl／.owl，勿手改，不連網解析 example.org。

PG 六份 active JSON：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。各有 JSON Schema 或 Python executable schema，build_cypher.py 合併產生 Neo4j 5 metadata 腳本 model.cypher；只依賴標準函式庫，未部署。穩定 ID＋MERGE 可重複載入，但不刪舊資料，也不提供完整同步遷移。

本輪 PG 同步：

- 四份指標相關 JSON 的既有 amount 欄位參照 fh:metricAmount，保留舊欄位 ID、型別、來源候選及原始觀察。
- 前次八個共通屬性同步時新增 71 個 pending 欄位；本次四項銀行手收各帶十一個 pending 欄位，再增 44 個。AUM 與手收沿用既有共通元素定義。
- 新增欄位均 pending、table／column 為 null、候選為空。欄位定義表達可用元素，不要求每項實際資料提供全部元素。
- 既有 snapshotDate、incomePeriod 及其來源候選保持，不自動當成 aumAsOfDate 或拆成期間起迄日。匯率日期、交易日、來源快照與 YYYYMM＋01 均未直接選定為新的業務日期。
- 既有 amount 的多個候選可能是同一計算的輸入，不是可各自當成結果的替代金額。原始公式繼續作證據，不變成金控共同計算規則。
- PG 投影的屬性 range 依語意為 string／decimal／date；HAS_DOMAIN_REFERENCE 指到真正 domain。指標金額不以 FIELD_IDENTIFIES_CLASS 當作識別欄位。
- 所有欄位層級 table／column 選擇與 execution 仍為 null；表級來源由 table_sources 記錄。沒有新增資料實例或直接加總銀行／證券 AUM。

## 既有商品與來源證據

目前業務概念共 32 個：通聯 2、存款 4、理專／通用手收 2、銀行個別手收 6（SI／SN／海外股票／ELI／FCI／DCI 純手續費）、前批商品 AUM 7、銀行基金／證券指標 11。

- 通聯保留七個金控 Data Property 參照；存款保留台幣、外幣、結構型、行員存款。行員存款指存款人本人是行員，不能用客戶管理 AO 的 AUM_TMP02.EMP_NO 代替本人識別。
- 前批 AUM 為台幣／外幣／結構型存款、海外股票、海外債券（信託／自營）、境外結構型；保留存款來源及 PB_FUND_MONTH、BOND_POS_DAY 的原始證據。
- 手收 SI 保留 SI_PERFO_RPT／_HS 的 FEE_AMOUNT_TWD，未含 ELI／FCI；SN 與銀行基金保留 PB_FUND_SPREAD_DAILY 的 BRHREBATEAMT。DEALNO 是交易單號，未核定為商品 ID。
- 證券保留複委託債券、結構型、基金、外股的 AUM／手收及台股 AUM。台股手收尚無來源定義；股票設質與 ETF 留待後續。

來源完整表名、欄位、SQL 行號、metadata 儲存格與分類均保留在 JSON；SQL cp950，JSON／Turtle UTF-8。詳細證據說明可回查 archive/before-v0.10.0/ 的 README 與前版交接。

以下只作回查紀錄，本階段不要求先解決：銀行基金 TRUSTPRD 範圍及 ETF 分列；基金 CASE 順序；證券基金 WKB02 投資人帳號與 WKB24 身分證字號角色差異；WKA31 幣別疑義；月底工作日歸屬；基金最大日期引用債券來源；外股 current AM 仍讀 AM_SEC_M；AUM 歷史日期與 FX 日期；台股 UNION 去重及股票設質意義。不得把原始異常或候選自行修成已核定規則。來源均為檔案觀察，database_verified=false。

## 建置與驗證

在工作目錄沿用 .venv／rdflib 7.6.0：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

目前 RDF：28 Class、6 Object Property、16 Data Property、5 Annotation Property、312 triples。PG：32 概念、410 metadata 節點、869 關係，含 252 DataFieldDefinition、33 SourceTable、34 BusinessRelationDefinition、5 MetadataModule。

RDF 18 項＋PG 59 項通過，無略過。包含屬性的 domain／range、跨子公司繼承、AUM／手收適用範圍、日期／數值型別、25 項指標表級來源角色、新四項空欄位候選與 DCI 損益排除、來源 pending、既有定義與欄位映射保留、來源檔案證據、排序確定性及輸出逐位元組比對。未執行完整 OWL reasoner、SHACL、GUI、來源 SQL、真實資料查核或 Neo4j 部署。

新增／修改語意時同步 JSON、驗證器、測試及產生輸出。tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 是舊批次一次性 seeder，不是通用 SQL 分析器；後續直接維護 active JSON，不重跑覆寫。不要執行 tools/legacy-v0.2.0。

表級對應修改後另執行 tools/export_metric_tables.py 重建對照清單，再以 --check 驗證。沒有新增欄位對應的需求時，不將表名填進 fields 的 table／column。

## 快照與接續

修改前來源、工具、文件與測試快照為 archive/before-v0.10.0，不含 venv。更早快照僅供回查；archive/before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。

私銀 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 與外部同步專案均未修改。沒有 Git 提交、外部部署或已確認雲端備份。outputs/rdf-review-v0.7.0 仍為歷史圖，未反映後續變動。

使用繁體中文，區分已確認共通語意、已實作元素與未核定來源。依客戶360/AGENTS.md 已授權本機專案修改、建置與測試，不反覆詢問；外部部署與訊息傳送未授權。

可貼到新 Session：

> 請先讀客戶360/AGENTS.md、customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md 與 README.md，接續共通 RDF v0.10.0。最新 PG 已補銀行海外股票、ELI、FCI 與 DCI 純手續費四項指標及底表；DCI 不含 TMU 損益。現在共 13 項 AUM、12 項手收有 table_sources；來源接在指標上，不接商品分類，清單見 department-pg/METRIC-TABLE-SOURCES.md。新四項欄位全部 pending／null、候選為空，先不對欄位。沿用既有八個金控必要元素，不要求詳細公式；手收用 feeIncomeFromProduct，AUM 用 measuresProduct。理專在銀行 RDF，實際歸屬未核定。通用手收仍是已盤來源的部分覆蓋。識別、幣別匯率及未核定範圍留待討論，權限與帳戶模型暫緩，先不用畫圖。先摘要，再依我的指示繼續。
