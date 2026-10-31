# 客戶360 RDF／OWL＋部門 PG：v0.13.0／最新證券 PG 交接

更新：2026-10-22。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 新 Session 先讀這裡

本檔為目前正式交接入口，已包含本 session 的銀行 ETF、集合管理與證券股票設質進度。最後一個使用者指示是「寫交接檔，準備開新的 session」；本次交接整理沒有再改 RDF／PG 模型。

先讀上層 ../AGENTS.md、本檔及 README.md；表級清單看 department-pg/METRIC-TABLE-SOURCES.md。沿用使用者最後選定的「證券優先」方向，先簡短摘要現況，再依新指示接續，不重做已完成項目。

目前證券有六個 AUM 分項、四個手收指標。股票設質的業務意義已獲來源文件支持並完成補入，不能再當成整項尚未建模。這輪證券的項目缺口是台股手收：尚缺可辨識底表與業務範圍；現有檔案找不到來源不代表現實沒有收入，也不能推成使用者決定排除。

| 議題 | 目前狀態 | 接續原則 |
|---|---|---|
| 證券股票設質 | 已補 AUM 與 DSCSD.PBCMS_REPORTA03 | 沿用股票商品；日期與台股庫存重疊仍待定，不直接相加 |
| 證券台股手收 | pending_source_definition，未建立 active 指標 | 需要底表名稱／來源文件及涵蓋範圍；不能借用複委託外股表 |
| 銀行集合管理帳戶 | 商品分類與 AUM 已補 | 與基金／ETF 分列；手收另為 pending_business_semantics |
| 銀行 ETF | 商品分類、AUM／手收已補 | 使用者指定直接繼承金融商品；AUM 分類取值待確認 |
| 銀行保險 | 商品分類、AUM／日報手收已補 | AUM 保留原始投資金額意義；月檔客戶貢獻度未當手收 |

PG 的 pending_scope 目前只有兩筆：securities.taiwan_stock_fee_income 與 bank.collective_account_fee_income。舊 securities.stock_pledge 待定紀錄已被新 active securities.stock_pledge_aum 取代。

使用者已明確決定：先對 AUM／手收到底表，不對商品到底表，也不開始對欄位。金控只定義必要元素，不需要詳細計算公式。新指標的欄位全部 pending／null、候選為空；既有欄位候選不清除。不要為了補齊模型自行核定日期、幣別、身分或收入歸屬。

## 最新決議與結果：證券股票設質 AUM

本輪為證券 PG 擴充，RDF 沿用 v0.13.0，來源與整合 RDF／OWL 均未修改。新增 securities.stock_pledge_aum（證券台股〔股票設質〕AUM），沿用 sec:SecuritiesAUM／sec:StockProduct、product_code=securities_taiwan_stock，以 fh:measuresProduct 表達衡量股票商品，不另造設質或借款商品分類。

需求文件 AUM_20250516.xlsx 的「建議調整版」第 28 列，將股票設質列為證券台股 AUM，描述為庫存股數與月底收盤價形成的估值；2._AUM_SUMY.sql 第 131–139 行也把 AUM_028 歸入證券／台股。據此解除原 securities.stock_pledge 的業務意義待定紀錄，補成 AUM 分項。金額意義是設質股票估值，不視為借款餘額或可融資額。

底表為 DSCSD.PBCMS_REPORTA03，角色 primary，來源觀察為 observed_in_files／database_verified=false。新 AUM 八欄位全部 pending、table／column 全 null、candidates 全空。需求文件的分類與估值只是證據，沒有加入欄位映射或執行公式。

SQL 使用 APPLYDATE，需求表描述月底收盤價，日期意義仍需對齊；與原台股庫存 AUM 的涵蓋重疊尚未確認，既有指標不變，不新增自動加總或去重。所有 execution 仍為 null。

台股手收仍保留 securities.taiwan_stock_fee_income／pending_source_definition：原產品收入定義空白，現有收入 SQL 與明細需求只有複委託債券、結構型、基金、外股四項，未找到可辨識的台股手收底表；不推論實際業務沒有收入。補齊這項仍需要台股手收底表及業務範圍，不能沿用外股表代替。

本輪證券查證位置（私銀來源皆唯讀）：

- 私銀智能問答/sources/metadata/AUM_20250516.xlsx，「建議調整版」H28:R28；H28 為證券台股 AUM、N28 為設質股票估值描述、P28 為完整底表名、R28 為來源分類觀察。
- 私銀智能問答/sources/sql/1.AUM_DETAIL.sql 第 432–438 行為 AUM_028 與 DSCSD.PBCMS_REPORTA03；2._AUM_SUMY.sql 第 131–139 行為證券／台股歸類。SQL 使用 cp950 讀取，未執行。
- PG evidence ID：stock_pledge_pending（原明細 SQL，名稱沿用）、stock_pledge_requirements（上述需求表儲存格）、stock_pledge_summary（上述彙總 SQL）。
- AUM_metadata.xlsx 雖有 DSCSD.PBCMS_REPORTA03 工作表，本輪未抽到欄位定義；不可寫成該 metadata 已核定欄位或金額意義。實際支持來自需求表與 SQL。
- 台股手收查核過現有收入 SQL、收入 metadata 工作表清單、收入_20250527.xlsx 的原表與建議調整版本，以及 private product graph；仍缺台股手收底表。原收入表的「證券股票手收」泛稱不能直接當成台股來源。

最新新增測試為 department-pg/test_securities_stock_pledge.py；驗證需求表／SQL 的業務意義、表級來源、新八欄位空映射、舊指標保留及台股手收待定。

## 前批集合管理帳戶決議與結果

bank:CollectiveManagementProduct（銀行集合管理投資商品）直接繼承 fh:FinancialProduct，治理歸銀行，與基金、ETF 各自分列。這是本專案的商品分類，不新增帳戶、契約實例或基金繼承關係。

PG 新增 bank.collective_account_aum（銀行集合管理帳戶 AUM），product_code=bank_collective_account，參照 bank:BankAUM／bank:CollectiveManagementProduct，以 fh:measuresProduct 表達衡量商品。底表為 DSFND.PB_FUND_MONTH，角色 primary；關係起點是 AUM 指標，不是商品分類。

來源 SQL 將 TRUSTPRD 的集合類別標為集合管理帳戶，僅保留為分類觀察。新 AUM 八個欄位全部 pending、table／column 全 null、candidates 全空；不新增欄位映射、公式、篩選或與其他指標的自動加總規則。來源仍是 observed_in_files、database_verified=false。

集合管理手收列為 pending_scope：bank.collective_account_fee_income，status=pending_business_semantics。原產品 incomeDefinition 空白；手收 SQL 的集合管理分支位於一般基金條件之後，分類可能已被前方條件攔截。保留原 SQL 順序與證據，沒有建立集合管理手收指標、手收來源關係或擴大通用手收涵蓋範圍。規劃型信託與信託保管的商品／服務分類留待下一步討論。

## 前批 ETF 決議與結果（v0.12.0）

bank:ETFProduct 依使用者決議直接繼承 fh:FinancialProduct，不繼承 bank:FundProduct；治理歸銀行。PG 的 bank.etf_aum／bank.etf_fee_income 與既有基金指標分列，不自動合計。

| PG 指標 | RDF 指標／商品參照 | 金額來源底表 |
|---|---|---|
| bank.etf_aum，銀行 ETF AUM | bank:BankAUM／bank:ETFProduct | DSFND.PB_FUND_MONTH |
| bank.etf_fee_income，銀行 ETF 手續費收入 | bank:BankFeeIncome／bank:ETFProduct | DSFND.PB_FUND_SPREAD_DAILY |

僅新增表級來源及必要元素，AUM 八欄位、手收十一欄位全部 pending、table／column 全 null、candidates 全空。AUM 用 fh:measuresProduct，手收用 fh:feeIncomeFromProduct；銀行手收沿用 bank:attributedToAdvisor，實際理專歸屬仍待定。來源接在指標上，商品分類沒有底表關係。

手收 SQL 有 ETF 分支；AUM SQL 共用底表並保留 ELSE TRUSTPRD，ETF 實際分類取值仍待確認。兩項來源皆為檔案觀察，database_verified=false；不把全表視為 ETF、不新增分類執行規則。既有基金及其他指標、欄位候選與關係保持。通用手收補充 ETF 涵蓋說明，沿用相同共用底表，仍是 partial_scope。

## 前批保險決議與結果（v0.11.0）

使用者確認：銀行保險共通分類泛指銀行通路提供的保險商品，私銀實際涵蓋哪些保險留在 PG。已新增 bank:InsuranceProduct，直接繼承 fh:FinancialProduct，治理歸銀行；不限定投資型或其他特定保險，不建立保單／契約模型。定義放在既有 bank-investment-products.ttl，模組顯示名稱改為銀行共通商品分類；沿用舊檔名與 URI 不代表所有保險都是投資型。

investment-metrics.json 新增兩項指標：

| PG 指標 | RDF 指標／商品參照 | 金額來源底表 | 來源性質 |
|---|---|---|---|
| bank.insurance_aum，銀行保險 AUM | bank:BankAUM／bank:InsuranceProduct | DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT | 彙總 SQL 註記原始投資金額，不直接視為保單市值或現金價值 |
| bank.insurance_fee_income，銀行保險手續費收入 | bank:BankFeeIncome／bank:InsuranceProduct | DSINS.INSU_RPT_Q01 | 目前僅涵蓋明確標示手收的日報，status=partial_scope |

新 AUM 八個、手收十一個欄位均 pending，table／column 全 null、candidates 全空。AUM 用 fh:measuresProduct，手收用 fh:feeIncomeFromProduct；銀行手收另參照 bank:attributedToAdvisor，實際歸屬未核定。

DSKPI.KPI_DET_IU_002_NEW、DSKPI.KPI_DET_OFI_001 的 PS 在 metadata 定義為客戶貢獻度，不直接併入手續費金額來源。其 SQL 與 metadata 證據保留在 observations／evidence，沒有建立金額來源表關係。日報 current 金額的特定月份限制也保留，未查驗完整時間覆蓋，不視為完整保險收入清冊。

保險 AUM 的 metadata 工作表名稱截短為 DSKPI.AFAUM_AFCUST_MON_ASSET_RE；完整底表名依 SQL 記錄，未宣告資料庫別名。原始投資金額意義可追溯到 2._AUM_SUMY.sql 第 21–39 行。來源只是檔案觀察，database_verified=false。

## 已完成的銀行與證券指標

目前 17 項 AUM、14 項手收都有 table_sources，來源接在指標 BusinessConcept 上，不接商品分類。清單見 department-pg/METRIC-TABLE-SOURCES.md。

- 銀行 AUM：台幣／外幣／結構型存款、海外股票、海外債券（信託／自營）、境外結構型、基金、保險、ETF、集合管理帳戶，共十一項。
- 證券 AUM：複委託債券、結構型、基金、外股、台股庫存、台股股票設質，共六項。
- 銀行手收：通用手收、SI、SN、基金、海外股票、ELI、FCI、DCI 純手續費、保險日報手收、ETF，共十項。
- 證券手收：複委託債券、結構型、基金、外股，共四項。台股手收仍缺來源定義。

前批新增的海外股票／ELI／FCI／DCI 手收保留。DCI 只涵蓋 INCOME_037 的手續費報表來源，不包含 INCOME_038／DSTAS.FO108_W 的 TMU 損益，不等同結構型存款；ELI／FCI 與 SI 分開，不自動合計，也沒有新增其 AUM。四項手收的 44 個欄位仍全部 pending／null，候選為空。

通用手收已納入盤點過的保險日報底表，前輪另補 ETF 涵蓋說明，仍標 partial_scope，不代表完整銀行總手收來源或直接加總。既有概念、欄位、候選、來源與關係保留；本輪同步 ontology_version 至 0.13.0。

## 最新範圍澄清

金控層級只需 AUM／手收指標與計算必要元素，不要求詳細公式。公式、毛淨額算法、選日與月底跨月規則留在子公司／部門，不是本階段共通建模的確認前提。

欄位映射先不處理。客戶／商品識別、幣別匯率、收入期間與實際理專歸屬繼續待定；權限、帳戶模型、分行／數位及畫圖仍暫緩。未確認範圍不自行擴充，不把來源 SQL 當執行規則。

後續待討論：集合管理手收定義及分類、規劃型信託、員工持股與信託保管；海外債券收入中的交易利得與自營收入性質；FX／黃金／DCI 的 TMU 損益；開狀服務；存款／放款利收；保險月檔客戶貢獻度。集合管理商品分類與 AUM、ETF 商品分類與兩項指標、保險通用商品分類與日報手收已完成，不應再列為整項尚未納入。

## 共通語意與必要元素

金控／子公司 RDF 定義共通概念、屬性、關係與正式繼承；PG 保存部門概念、欄位、商品分類參照與來源觀察，沒有客戶、人員、商品、部位或交易資料實例。example.org 是示意命名空間。

- fh:Metric 的子類為 fh:AUM、fh:FeeIncome；銀行／證券各有對應子類。AUM 用 measuresProduct，手收用 feeIncomeFromProduct，不混用，也沒有手收指向 AUM 的關係。
- bank:BankEmployee 繼承 fh:Employee，bank:FinancialAdvisor 再繼承行員，沿用 bank:employeeId，不另造理專 ID。銀行手收可參照 attributedToAdvisor；證券不套用銀行理專關係。
- fh:serves 連職員與客戶，不表示資料閱覽授權。權限 deferred_by_user 只記錄延期。
- 銀行與證券商品分類治理各屬其子公司，直接繼承 fh:FinancialProduct；證券不繼承銀行商品，不宣告兩者等價。海外不等同外幣；組合商品留 PG。
- 行員存款指存款人本人為行員，不得用管理客戶的 AO 員編代替本人識別。

八個金控 Data Property 繼續沿用：

| 屬性 | Domain | Range |
|---|---|---|
| fh:metricAmount | fh:Metric | xsd:decimal |
| fh:aumAsOfDate | fh:AUM | xsd:date |
| fh:valuationQuantity | fh:AUM | xsd:decimal |
| fh:valuationUnitPrice | fh:AUM | xsd:decimal |
| fh:incomePeriodStart | fh:FeeIncome | xsd:date |
| fh:incomePeriodEnd | fh:FeeIncome | xsd:date |
| fh:feeBaseAmount | fh:FeeIncome | xsd:decimal |
| fh:feeDeductionAmount | fh:FeeIncome | xsd:decimal |

元素按情境適用，不新增必填、固定基數或公式。metricAmount 是結果金額；舊 amount 候選可能包含同一計算的多個輸入，不把輸入各自當成結果。舊 snapshotDate／incomePeriod 保留，不自動轉成新的業務基準日／期間起迄日。數量單位、報價基準與扣減項目的具體意義留 PG。

不新增未確認 Hash、互斥、等價、sameAs、keys、反向關係、property chain、完整推論、SHACL 或額外保單／契約／資產模型。

## 有效來源、輸出與表級對應

RDF 五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。build-config.json 明列來源，catalog-v001.xml 對應本機 URI／v0.13.0。tools/build_ontology.py 產生自含 customer360-ontology.ttl／.owl，勿手改，不連網解析 example.org。

PG 六份 active JSON：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。各有 JSON Schema 或 Python executable schema；build_cypher.py 合併產生 Neo4j 5 metadata 腳本 model.cypher，只依賴標準函式庫，未部署。穩定 ID＋MERGE 支援重複載入，但不刪舊資料，也不提供完整同步遷移。

目前有 60 條 HAS_SOURCE_TABLE、3 條 USES_VALUATION_SOURCE、2 條 USES_DATE_LOOKUP_SOURCE，來源表共 36 個。表級記錄 tables 僅有 table、role、evidence，不新增欄位映射。SourceTable 節點沿用穩定 ID。來源 SQL cp950，JSON／Turtle UTF-8。

證券基金手收的債券表與外股 AM_SEC 只供日期查詢，不是額外金額來源；原始異常保持。四項證券手收引用的 T_LAST_TWO_WORKDAYS 缺 schema／底層定義，只保留為未辨識期間輔助關係。基金 WKB02／WKB24 角色、ETF AUM 分類取值、日期／FX、UNION 去重、股票設質日期與涵蓋重疊等疑點仍留供後續，不阻塞本階段必要元素建模。

## 建置與驗證

沿用 .venv／rdflib 7.6.0，在工作目錄執行：

```powershell
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s department-pg -v
```

目前 RDF：31 Class、6 Object Property、16 Data Property、5 Annotation Property、330 triples。PG：38 概念、484 metadata 節點、1014 關係，含 306 DataFieldDefinition、36 SourceTable、42 BusinessRelationDefinition、5 MetadataModule。

RDF 19 項＋PG 68 項通過，無略過。涵蓋股票設質需求表與彙總 SQL 的交叉證據、台股手收待定、集合管理商品分類／AUM 與手收延期、保險廣義分類、原始投資金額／手收／客戶貢獻度意義、來源檔案與 metadata 儲存格、ETF 直接繼承金融商品與基金範圍保持、原有 RDF／PG 定義及欄位保留、空欄位候選與來源角色、跨公司參照、pending 安全、確定性與輸出逐位元組比對。未執行完整 OWL reasoner、SHACL、GUI、來源 SQL、真實資料查核或 Neo4j 部署。

維護時同步 JSON、驗證器、測試、RDF 整合輸出及底表對照清單。tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 是舊批次一次性 seeder，不是通用 SQL 分析器；不重跑覆寫 active JSON。不要執行 tools/legacy-v0.2.0。

87 項測試是上一輪模型完成後的實際結果（RDF 19＋PG 68，無略過）；本次僅整理交接文件，沒有因此重跑測試。RDF 與表級清單的 --check、Cypher 與 active JSON 的逐位元組比對也已在模型完成後通過。後續只有文件調整時，不必為相同模型重複跑整套測試。

各保留性測試使用不同歷史快照：test_metric_tables.py 以 before-v0.13.0 為基準，test_bank_etf.py 使用 before-v0.12.0，test_securities_stock_pledge.py 使用 before-securities-extension-20261022，較早的投影保留測試仍引用 before-v0.10.0。不要為了版本一致而全域替換這些歷史路徑。一次性修改腳本已移除，維護 active JSON／驗證器即可。

## 快照與接續

本輪證券 PG 修改前完整來源、工具、文件、測試快照為 archive/before-securities-extension-20261022，不含 venv。集合管理商品新增前為 before-v0.13.0。前輪 ETF 快照為 before-v0.12.0。保險快照為 before-v0.11.0。前批銀行四手收快照為 before-bank-fee-extension-20261022，初次表級對應為 before-table-sources-20261022，更早版本供回查。before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。

私銀 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 與外部同步專案未修改。沒有 Git 提交、外部部署或已確認雲端備份。outputs/rdf-review-v0.7.0 仍為歷史圖，不代表目前模型。

使用繁體中文，區分共通語意、已實作指標與來源候選。依客戶360/AGENTS.md 已授權本機專案修改、建置與測試，不反覆詢問；外部部署及訊息傳送未授權。

可貼到新 Session：

> 請先閱讀 C:/Users/petershiao/Desktop/Ontology/客戶360/AGENTS.md，以及 customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md 與 README.md，接續 RDF v0.13.0／最新證券 PG。沿用證券優先：股票設質 AUM 與底表已補，台股手收仍缺底表與業務範圍；不要把已完成的股票設質再列為整項待建模。銀行 ETF、集合管理 AUM、保險等決議均已記在交接檔。先簡短摘要，再依我的指示繼續；維持只對指標到底表、不對欄位，金控不需要詳細公式。
