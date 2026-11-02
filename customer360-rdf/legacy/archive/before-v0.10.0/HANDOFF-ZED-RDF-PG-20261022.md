# 客戶360 RDF／OWL＋部門 PG：v0.9.0 交接

更新：2026-10-22。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 最新範圍澄清（2026-10-22，優先於下方歷史待確認清單）

使用者確認：金控層級的 AUM 與手收模型，只需表達指標及計算所需的必要元素，不需要定義詳細計算公式。詳細估值算式、毛額／淨額算法、選日及月底跨月處理等細節，不列為本階段金控模型的確認前提；仍由子公司／部門負責具體計算口徑。

必要元素依既有指標與來源候選表達，例如 AUM 的金額或數量／價格等估值輸入及快照日期，手收的收入金額／費用組成及收入期間。這些是元素角色的說明，不代表每類商品均須採用相同輸入，也不將既有來源公式核定為金控共同規則。既有 PG 的原始欄位、公式與 SQL 觀察保留為來源證據。

使用者暫緩討論前次清單第 3、4、5 項：客戶與商品識別、幣別與匯率、本階段商品範圍（含台股手收、股票設質等）。既有候選與 pending/null 保留，不自行核定或擴充。下方來源異常與未定事項僅供後續回查，不作為本階段建模的阻塞條件。權限、帳戶模型及畫圖的既有暫緩決議繼續適用。

## 最新決議與結果

使用者同意補私銀的證券部分，並要求銀行補上基金。最新澄清是：**手收用「手收來源商品」連金融商品**。因此銀行與證券手收共用 fh:feeIncomeFromProduct（FeeIncome → FinancialProduct）；AUM 仍共用 fh:measuresProduct（AUM → FinancialProduct）。未新增手收指向 AUM、資產部位、交易實例或額外資產模型。

已完成本地 v0.9.0：銀行 FundProduct；證券 AUM、證券手收與五項商品分類；PG 新增十一項商品指標候選。RDF／PG 輸出、建置契約、來源證據與回歸測試已同步。沒有來源取數 SQL、資料庫連線或 Neo4j 部署。

使用者已指示先不畫圖。outputs/rdf-review-v0.7.0 的 PNG／SVG 僅為歷史圖，未反映 v0.8.0 AUM 調整或本輪基金／證券。

## 分層原則與共通語意

金控／子公司 RDF 定義共同概念、關係、屬性與正式繼承；子公司可以定義自身共同業務語意，不是只能被動繼承。部門 PG 描述業務概念、欄位、語意參照、候選來源與 SQL 觀察，不含客戶、人員、部位或產品資料實例。example.org 為示意命名空間。

- fh:Employee 是金控或旗下子公司職員；bank:BankEmployee 繼承它，bank:FinancialAdvisor 再繼承行員。理專已升級 RDF，取代先前 PG-only 決議，不自動依部門細分理專 subclass。
- bank:employeeId 為行員屬性，domain BankEmployee、range xsd:string，理專沿用；無底表映射仍可定義共同屬性。沒有新增理專 ID 或跨公司唯一性規則。
- fh:serves 是 Employee → Customer；服務關係不代表取得客戶資料閱覽權。
- fh:Metric 的子類為 fh:FeeIncome 與 fh:AUM。銀行 BankFeeIncome／BankAUM、證券 SecuritiesFeeIncome／SecuritiesAUM 分別繼承相應金控指標。Metric 不直接連金融商品。
- fh:feeIncomeFromProduct 是手收來源商品；fh:measuresProduct 是 AUM 衡量金融商品。兩者 domain 分別為 FeeIncome、AUM，range 均為 FinancialProduct，不混用。
- bank:attributedToAdvisor 為 BankFeeIncome → FinancialAdvisor；PG 通用手收、SI、SN 與本輪銀行基金手收參照它。理專資格、收入歸屬與適用期間仍未核定，證券不套用這條銀行關係。
- 金額、幣別、客戶／商品識別、收入期間與快照日期目前是 PG 欄位；除 employeeId 外，不捏造其共同 RDF 屬性 URI。
- **權限由使用者暫緩討論**。不新增內／外部指標分類、揭露標記、可見角色或授權規則，deferred_by_user 只記錄延期。

## RDF 有效來源

build-config.json 明列五份來源，catalog-v001.xml 對應本機 URI 與 v0.9.0。tools/build_ontology.py 產生自含 customer360-ontology.ttl／.owl，勿手改；不連網解析 example.org。

| 來源 | 共同分類／關係 |
|---|---|
| holding-core.ttl | 客戶、金融商品、通聯資訊／手機／地址、職員、指標、手收、AUM；服務、持有、通聯、AUM衡量商品、手收來源商品；七個通聯屬性 |
| bank-deposit.ttl | DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct |
| bank-common.ttl | BankEmployee、FinancialAdvisor、BankFeeIncome、BankAUM、employeeId、attributedToAdvisor |
| bank-investment-products.ttl | StockProduct、BondProduct、FundProduct、OverseasFinancialProduct |
| securities-common.ttl | SecuritiesAUM、SecuritiesFeeIncome；StockProduct、BondProduct、FundProduct、StructuredFinancialProduct、OverseasFinancialProduct |

銀行／證券商品分類均直接繼承 fh:FinancialProduct；證券不繼承銀行商品，未將銀行既有分類搬到金控或宣告兩者等價。海外是分類面向，地域判定依據待確認，不等同外幣。台幣／外幣／結構型存款、海外股票等組合仍留 PG，不新增組合 OWL Class、交集或自動分類。

不加未確認 Hash、必填／格式、基數、互斥、等價、sameAs、keys、反向、property chain、完整推論或 SHACL。分行／數位、帳戶、契約、保單、持有部位仍延後。

## PG 有效模組

六份 active JSON：model.json、deposits.json、advisory-income.json、product-fees.json、product-aum.json、investment-metrics.json。各有 JSON Schema 或 Python executable schema。build_cypher.py 合併產生 Neo4j 5 metadata 腳本 model.cypher；投影只依賴標準函式庫。穩定 ID＋MERGE 支援重複載入，不刪舊資料、不提供完整同步遷移。未知值以 JSON 字串保存 null。

- 通聯：貸款照會手機、客戶訪問地址，七個 Data Property 參照／七個 pending MappingSlot。
- 存款：台幣、外幣、結構型及行員存款，四個 PG 概念與十七欄位。五張原始來源 DEP_NT_ACCT／_HS、DEP_FN_ACCT／_HS、EMP_DEP_NT_ACCT_HS 保留。行員存款指存款人本人為行員，不是行員管理客戶，也不只限優惠方案；不能用 AUM_TMP02.EMP_NO（AO）當存款人員編。pending_semantic_reference 指 BankEmployee，來源本人對照、JOIN、期間仍 null。metadata 的 EMP_NT_ACCT_HS 名稱差異不當成別名；2545 分類、普通分類碼、歷史門檻只是證據。
- 理專／通用手收：PG 理專參照銀行 RDF 理專，保存員編與服務客戶關係。通用商品手收保留欄位及商品／理專關係定義，實際來源未知。
- 第一批手收：境內 SI（SI_PERFO_RPT／_HS 的 FEE_AMOUNT_TWD）及境外 SN（PB_FUND_SPREAD_DAILY 的 BRHREBATEAMT）。SI 不含 ELI／FCI，不是完整境內總手收；兩者不是結構型存款。DEALNO 是交易單號，不當商品 ID；SN 的 FUNDID 適用性待確認。日期 TRADE_DATE／FEEDATE 不是核定 snapshotDate。RM_ID／USER_ID、BAOEMPID／SAOEMPID 的不同角色保留。
- 前批 AUM：台幣／外幣／結構型存款、海外股票、海外債券（信託）、海外債券（自營）、境外結構型，共七項。前三項沿用存款證據，原餘額不自動認定為 AUM。信託投資 PB_FUND_MONTH 依 TRUSTPRD 分類，CurrentTWDValue 是候選；其他國外有價證券歸股票需覆核。自營 BOND_POS_DAY 的 STO_AMT × MKT_PRI ÷ 100 × EXC_RATE 是同一估值的組成，舊 SQL 每月取全體最大日期，不是每客戶最後交易日。

## 本輪 investment-metrics.json：十一項新增候選

| PG 商品範圍 | AUM 候選 | 手收候選 |
|---|---|---|
| 銀行基金 | PB_FUND_MONTH；CurrentTWDValue | PB_FUND_SPREAD_DAILY；BRHREBATEAMT |
| 證券複委託債券 | BONDPOS_SEC／_M；NETQTY ÷ 100 × CPRICE × EXCH_RT | BONDTRADM_SEC／_M；CFEE × FXRATE |
| 證券複委託結構型 | 同債券來源，BOND LIKE TSSN% 分支 | 同債券來源，保留原 CASE 分類 |
| 證券複委託基金 | FUNDPOSIT_SEC／_M；WKB28 × WKB23 × WKB31 | FUNDTRADM_SEC／_M；WKA31 |
| 證券複委託外國股票 | STOCKPOS_SEC／_M；NETQTY × CPRICE × EXCH_RT | STOCKTRADM PM／AM 分支；(CFEE − ABFEE) × FXRATE 淨手收 |
| 證券台股 | YTRMRBP_SEC／_M；YTRMRB110 × YTRMRB150 | 提供來源未見定義，未建立手收概念 |

來源完整表名、欄位、SQL 行號、metadata 儲存格與私銀 productCode 保存在 JSON；SQL cp950，JSON／Turtle UTF-8。商品分類參照只限制 PG 意義，不代表已識別單一產品實例或執行 OWL 交集。

重要待確認事項：

1. 銀行基金 AUM 的 TRUSTPRD 完整基金取值未驗證；不能把整張 FUND 表視為基金。基金與 ETF 在私銀分列，本輪不自動含 ETF。基金手收原 CASE 先判 FHID NOT IN PS／CB／YB／SN，後方 TA／TB／TD／TE 可能被先行條件攔截；保留原順序待覆核，不自行改分類。
2. 證券基金 SQL 用 WKB02 當 cust_id，但 current metadata 是投資人帳號；WKB24 才是客戶身分證字號。兩者不同角色均為候選，客戶對照未核定；current 定義不自動證實歷史表。WKA31 metadata 原文「總手續費(台？)」有幣別疑義。
3. 證券手收用 T_LAST_TWO_WORKDAYS 的 YM／LAST2_WD 將月底最後兩個工作天歸次月，YYYYMM＋01 是歸屬月份標記，不是快照日；工作日曆、收入期間及選日未核定。
4. 基金手收 current 最大日期子查詢引用 BONDTRADM_SEC；外股 current AM FROM AM_SEC_M，最大日期卻查 AM_SEC。保留來源異常，不擅自更換來源或多算 current AM；AM_SEC 僅記為子查詢來源，未當金額候選。
5. 債券 AUM 歷史 PRCS_DT 未加表別且與 FX 同名，來源需釐清；股票歷史日期取 FX PRCS_DT，不直接當部位快照日。月末匯率、current 日期連接與幣別尚未核定。
6. 台股 SQL 先 UNION 投影再 SUM，可能消去相同投影列，原始粒度與去重待確認。股票設質有 Qty × Product_Price，但不能據此認定為投資 AUM、貸款餘額或可融資額；只列 pending_scope。

所有 selected table／column、execution 仍 null；來源是檔案觀察、database_verified=false，認列／估值／快照／收入期間／幣別／去重／聚合／歸屬未核定。不把銀行或證券各項直接相加為總 AUM，不因有服務關係而核定理專或收入歸屬。

## 建置與驗證

沿用 .venv／rdflib 7.6.0，在工作目錄執行：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

目前 **28 Class、6 Object Property、8 Data Property、5 Annotation Property、264 triples**；PG **28 概念、266 metadata 節點、527 關係**。PG 含 137 DataFieldDefinition、27 SourceTable、26 BusinessRelationDefinition、5 MetadataModule；通聯模組沒有獨立 MetadataModule 節點。

RDF 17 項＋PG 49 項通過，無略過。含來源圖／TTL／RDF/XML 同構、前版 RDF／PG 定義保留、來源 SQL／metadata 儲存格、公司歸屬、金額組成、pending 安全、排序確定性及輸出逐位元組比對。未執行完整 OWL reasoner、SHACL、GUI、來源 SQL、真實資料查核或 Neo4j 部署。

新增語意／來源須同步 JSON、驗證器與測試，不只改 model.cypher。tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 是固定範圍的一次性 seeder，拒絕覆寫 active JSON；後續維護 JSON，不當通用 SQL 分析器。不要執行 tools/legacy-v0.2.0。

## 快照與接續

本輪修改前完整來源／工具／測試快照為 archive/before-v0.9.0，不含 venv；先前 before-v0.3.0 至 before-v0.8.0 僅供回查。archive/before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。

私銀 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 與外部同步專案均未修改。沒有 Git 提交、外部部署或已確認雲端備份。

使用繁體中文；區分已確認、已實作與來源候選。使用者已暫緩權限並要求先不用畫圖。專案檔案、建置與測試依客戶360/AGENTS.md 已授權直接執行，不反覆詢問；外部部署與訊息傳送未授權。後續可逐項確認候選的識別、日期、幣別與認列，不自行定案。

可貼到新 Session：

> 請先讀客戶360/AGENTS.md、customer360-rdf-owl/HANDOFF-ZED-RDF-PG-20261022.md 與 README.md，接續 v0.9.0，優先遵守最新範圍澄清。理專已在銀行 RDF，銀行手收歸屬理專；金控 AUM／手收分別由銀行與證券繼承。手收用 feeIncomeFromProduct「手收來源商品」連金融商品，AUM 用 measuresProduct 衡量金融商品。銀行已補基金，證券已補五類商品 AUM／四類手收；各商品指標及來源候選留 PG。金控層級只需計算必要元素，不要求詳細公式或先核定部門計算規則；既有公式僅保留來源證據。客戶與商品識別、幣別匯率及商品範圍先不討論，候選與 pending/null 保留。權限與帳戶模型暫緩，先不用畫圖。先摘要，再依我的指示繼續。
