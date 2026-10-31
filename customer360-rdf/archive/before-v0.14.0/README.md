# 客戶360：共通 RDF／OWL 與部門 Property Graph

目前共通 RDF 版本：**v0.13.0，2026-10-22，設計草案**。本輪證券 PG 補股票設質 AUM 與底表，沿用既有 RDF 類別；台股手收仍缺來源定義。修改前快照為 `archive/before-securities-extension-20261022/`。

## 最新更新：證券股票設質 AUM

本輪為證券 PG 擴充，RDF 沿用 v0.13.0，來源與整合 RDF／OWL 均未修改。新增 securities.stock_pledge_aum（證券台股〔股票設質〕AUM），沿用 sec:SecuritiesAUM／sec:StockProduct、product_code=securities_taiwan_stock，以 fh:measuresProduct 表達衡量股票商品，不另造設質或借款商品分類。

需求文件 AUM_20250516.xlsx 的「建議調整版」第 28 列，將股票設質列為證券台股 AUM，描述為庫存股數與月底收盤價形成的估值；2._AUM_SUMY.sql 第 131–139 行也把 AUM_028 歸入證券／台股。據此解除原 securities.stock_pledge 的業務意義待定紀錄，補成 AUM 分項。金額意義是設質股票估值，不視為借款餘額或可融資額。

底表為 DSCSD.PBCMS_REPORTA03，角色 primary，來源觀察為 observed_in_files／database_verified=false。新 AUM 八欄位全部 pending、table／column 全 null、candidates 全空。需求文件的分類與估值只是證據，沒有加入欄位映射或執行公式。

SQL 使用 APPLYDATE，需求表描述月底收盤價，日期意義仍需對齊；與原台股庫存 AUM 的涵蓋重疊尚未確認，既有指標不變，不新增自動加總或去重。所有 execution 仍為 null。

台股手收仍保留 securities.taiwan_stock_fee_income／pending_source_definition：原產品收入定義空白，現有收入 SQL 與明細需求只有複委託債券、結構型、基金、外股四項，未找到可辨識的台股手收底表；不推論實際業務沒有收入。補齊這項仍需要台股手收底表及業務範圍，不能沿用外股表代替。

## 集合管理帳戶（已完成）

bank:CollectiveManagementProduct（銀行集合管理投資商品）直接繼承 fh:FinancialProduct，治理歸銀行，與基金、ETF 各自分列。這是本專案的商品分類，不新增帳戶、契約實例或基金繼承關係。

PG 新增 bank.collective_account_aum（銀行集合管理帳戶 AUM），product_code=bank_collective_account，參照 bank:BankAUM／bank:CollectiveManagementProduct，以 fh:measuresProduct 表達衡量商品。底表為 DSFND.PB_FUND_MONTH，角色 primary；關係起點是 AUM 指標，不是商品分類。

來源 SQL 將 TRUSTPRD 的集合類別標為集合管理帳戶，僅保留為分類觀察。新 AUM 八個欄位全部 pending、table／column 全 null、candidates 全空；不新增欄位映射、公式、篩選或與其他指標的自動加總規則。來源仍是 observed_in_files、database_verified=false。

集合管理手收列為 pending_scope：bank.collective_account_fee_income，status=pending_business_semantics。原產品 incomeDefinition 空白；手收 SQL 的集合管理分支位於一般基金條件之後，分類可能已被前方條件攔截。保留原 SQL 順序與證據，沒有建立集合管理手收指標、手收來源關係或擴大通用手收涵蓋範圍。規劃型信託與信託保管的商品／服務分類留待下一步討論。

## 銀行 ETF（v0.12.0 已完成）

bank:ETFProduct 依使用者決議直接繼承 fh:FinancialProduct，不繼承 bank:FundProduct；治理歸銀行。PG 的 bank.etf_aum／bank.etf_fee_income 與既有基金指標分列，不自動合計。

| PG 指標 | RDF 指標／商品參照 | 金額來源底表 |
|---|---|---|
| bank.etf_aum，銀行 ETF AUM | bank:BankAUM／bank:ETFProduct | DSFND.PB_FUND_MONTH |
| bank.etf_fee_income，銀行 ETF 手續費收入 | bank:BankFeeIncome／bank:ETFProduct | DSFND.PB_FUND_SPREAD_DAILY |

僅新增表級來源及必要元素，AUM 八欄位、手收十一欄位全部 pending、table／column 全 null、candidates 全空。AUM 用 fh:measuresProduct，手收用 fh:feeIncomeFromProduct；銀行手收沿用 bank:attributedToAdvisor，實際理專歸屬仍待定。來源接在指標上，商品分類沒有底表關係。

手收 SQL 有 ETF 分支；AUM SQL 共用底表並保留 ELSE TRUSTPRD，ETF 實際分類取值仍待確認。兩項來源皆為檔案觀察，database_verified=false；不把全表視為 ETF、不新增分類執行規則。既有基金及其他指標、欄位候選與關係保持。通用手收補充 ETF 涵蓋說明，沿用相同共用底表，仍是 partial_scope。

## 銀行保險（v0.11.0 已完成）

bank:InsuranceProduct 泛指銀行通路提供的保險商品，直接繼承 fh:FinancialProduct；私銀實際涵蓋哪些保險留在 PG 描述。治理歸銀行，不限定為某類或投資型保險，沒有新增保單／契約模型。類別放在既有 bank-investment-products.ttl，模組顯示名稱改為銀行共通商品分類；沿用檔名與 URI 不代表所有保險都屬投資型。

| 新增 PG 指標 | 沿用 RDF 指標／關係 | 金額來源底表及意義 |
|---|---|---|
| 銀行保險 AUM | bank:BankAUM／fh:measuresProduct | DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT；來源註記為原始投資金額，不直接視為保單市值或現金價值 |
| 銀行保險手續費收入 | bank:BankFeeIncome／fh:feeIncomeFromProduct | DSINS.INSU_RPT_Q01；目前僅涵蓋明確標示手收的日報，標 partial_scope |

兩項指標分別有八個、十一個 pending 欄位，table／column 全 null、candidates 全空。收入期間、選日、認列、幣別、識別與實際理專歸屬仍待定。保險日報來源另有 current 資料月份限制的原始註記，未查驗完整時間覆蓋。

DSKPI.KPI_DET_IU_002_NEW 與 DSKPI.KPI_DET_OFI_001 的月檔在 metadata 是客戶貢獻度，保留 SQL／metadata 證據供後續討論，不併入手續費金額來源。通用手收同步納入日報來源，仍是已盤來源的部分覆蓋。

## 銀行四項手收與來源底表

已新增四個 bank:BankFeeIncome 的 PG 業務概念，手收來源商品沿用 fh:feeIncomeFromProduct，銀行理專關係沿用 bank:attributedToAdvisor；實際商品、人員與欄位映射仍 pending。

| 新增手收指標 | 沿用商品分類 | 金額來源底表 |
|---|---|---|
| 銀行海外股票手收 | 股票＋海外金融商品 | DSFND.PB_FUND_SPREAD_DAILY |
| 境內 ELI 手收 | 結構型金融商品 | DSDEP.ELI_PERFO_RPT／_HS |
| 境內 FCI 手收 | 結構型金融商品 | DSDEP.FCI_PERFO_RPT／_HS |
| DCI 手續費收入 | 結構型金融商品 | DSDEP.DCI_PERFO_RPT／_HS |

新增指標各有十一個 pending 欄位，table／column 全 null、candidates 全空；原有欄位與來源候選保持。本次只補指標及底表。DCI 僅含手續費報表 INCOME_037 的來源，不納入 INCOME_038／DSTAS.FO108_W 的 TMU 損益，也不當成結構型存款；ELI／FCI 與 SI 分開保留，不自動合計或新增 AUM。

目前共有 **17 項 AUM、14 項手收指標**，底表關係為 60 條 HAS_SOURCE_TABLE、3 條 USES_VALUATION_SOURCE、2 條 USES_DATE_LOOKUP_SOURCE，共 36 個 SourceTable。商品分類本身不新增底表關係。通用手收涵蓋已盤點 SI／SN／銀行基金／ETF／海外股票／ELI／FCI／DCI 純手續費及保險日報來源，仍為 partial_scope，不是完整銀行總手收來源或加總規則。

可閱讀 [AUM／手收底表對照](department-pg/METRIC-TABLE-SOURCES.md)。四項證券手收的 T_LAST_TWO_WORKDAYS 仍保留為未辨識的期間輔助關係。欄位、認列、日期、幣別、識別與實際歸屬繼續待定，execution 全 null。先前表級對應快照為 archive/before-table-sources-20261022/，前批四項銀行手收快照為 archive/before-bank-fee-extension-20261022/。

## AUM／手收共通 Data Property（v0.10.0）

| 金控屬性 | 名稱 | Domain | Range |
|---|---|---|---|
| fh:metricAmount | 指標金額 | fh:Metric | xsd:decimal |
| fh:aumAsOfDate | AUM 基準日 | fh:AUM | xsd:date |
| fh:valuationQuantity | 估值數量 | fh:AUM | xsd:decimal |
| fh:valuationUnitPrice | 估值單價 | fh:AUM | xsd:decimal |
| fh:incomePeriodStart | 收入期間起日 | fh:FeeIncome | xsd:date |
| fh:incomePeriodEnd | 收入期間迄日 | fh:FeeIncome | xsd:date |
| fh:feeBaseAmount | 手收計算基礎金額 | fh:FeeIncome | xsd:decimal |
| fh:feeDeductionAmount | 手收計算扣減金額 | fh:FeeIncome | xsd:decimal |

銀行與證券沿用金控定義。數量、單價與扣減金額按情境適用；沒有必填、固定基數或計算公式。數量單位、價格報價基準與扣減項目意義留在部門 PG 描述；不因新增元素而核定來源口徑。

PG 的 amount 欄位參照 fh:metricAmount；AUM 有 aumAsOfDate、valuationQuantity、valuationUnitPrice，手收有 incomePeriodStart、incomePeriodEnd、feeBaseAmount、feeDeductionAmount。前次共通屬性同步新增 71 個 pending 欄位定義，本次四項手收另各帶十一個 pending 欄位，共 44 個。table／column 為 null、來源候選為空。欄位定義表達可用元素，不要求每項實際資料提供所有元素。

既有 snapshotDate 與 incomePeriod 保留作來源觀察；不自動把資料快照、交易日、匯率日或 YYYYMM＋01 轉成新的業務基準日／收入起迄日。既有 amount 的候選清單可能包含同一計算的多個輸入，仍是證據；metricAmount 表達結果金額，不代表這些輸入各自就是結果。欄位映射的 table／column 選擇與 execution 仍全部 null；指標的表級來源另由 table_sources 記錄。

## 最新建模範圍（2026-10-22）

金控層級的 AUM／手收只需保留指標與計算所需的必要元素；例如 AUM 的金額或數量／價格等估值輸入及快照日期，手收的收入金額／費用組成及收入期間。各元素按商品需要表達，不要求各商品採相同輸入。詳細計算公式、毛額／淨額算法、選日及跨月規則由子公司／部門處理，不列為本階段金控模型的確認前提。既有 PG 公式與原始欄位繼續作為來源證據，不視為已核定的共同計算規則。

客戶與商品識別、幣別與匯率、商品範圍先不討論；既有候選及 pending/null 保留，不自行定案。下方待確認與來源異常清單供後續回查，不阻塞本階段必要元素建模。詳見最新交接檔的「最新範圍澄清」。

## 共通語意與部門分工

金控／子公司 RDF 定義共通概念、關係、屬性與正式繼承；部門 PG 描述業務概念、欄位、語意參照及來源映射。真實資料留在來源系統，PG 只建 metadata。example.org 為示意命名空間。

- `bank:BankEmployee` 繼承 `fh:Employee`；`bank:employeeId` 的 domain 為行員、range 為 xsd:string。無底表映射仍可定義共通屬性。
- `bank:BankFeeIncome` 繼承 `fh:FeeIncome`，再繼承 `fh:Metric`。
- `fh:serves` 連職員與客戶；`fh:measuresProduct` 連 AUM 與金融商品。domain/range 不構成必填、基數或資料閱覽授權。
- `bank:FinancialAdvisor` 是銀行 RDF 的理專 Class，繼承 `bank:BankEmployee`，間接繼承 `fh:Employee`；沿用行員編號，不另造理專 ID。PG 保留部門理專概念，改為參照這個共通 Class。
- `bank:attributedToAdvisor` 是銀行手收歸屬理專的 Object Property，domain 為 `bank:BankFeeIncome`、range 為 `bank:FinancialAdvisor`。通用商品手收與兩項具來源商品手收均在 PG 參照此關係；理專資格與實際歸屬映射仍待確認。
- 此決議取代先前「理專只放 PG」的設計。尚未細分理專子類別，不以部門名稱自動建立 subclass。
- 手收與金融商品透過關係連接；各商品手收留在 PG。收入期間與快照日期分開，日／月／年累計口徑尚未核定。
- **權限由使用者暫緩討論**。未新增內外部指標類別、可見角色、揭露標記或授權規則；JSON 的 deferred_by_user 只記錄延期狀態。

## 新增銀行投資商品分類

四個 Class 全部直接繼承金控 fh:FinancialProduct，治理歸屬為銀行：

| Class | 名稱 | 定義 |
|---|---|---|
| bank:StockProduct | 股票商品 | 代表公司股權的金融商品。 |
| bank:BondProduct | 債券商品 | 發行人為籌資而發行、約定清償條件的債務型金融商品。 |
| bank:FundProduct | 基金商品 | 透過集合投資方式，由專業管理機構依基金契約管理運用資產的金融商品。 |
| bank:OverseasFinancialProduct | 海外金融商品 | 銀行業務中歸入海外投資範圍的金融商品。 |

股票／債券是商品種類，海外是可與商品種類組合的分類面向；海外的具體地域判定（例如發行地或交易市場）仍待確認，沒有自動映射判定規則，也不等同外幣分類。

海外股票、海外債券等組合留在 PG 參照多個共通概念。前批已新增其 AUM 情境，沒有新增組合商品 OWL Class；本輪另補銀行基金及證券，見下節。

## 證券與銀行基金（v0.9.0）

`securities-common.ttl` 新增證券 AUM（sec:SecuritiesAUM）繼承 fh:AUM，證券手收（sec:SecuritiesFeeIncome）繼承 fh:FeeIncome。證券商品的 StockProduct、BondProduct、FundProduct、StructuredFinancialProduct、OverseasFinancialProduct 均直接繼承 fh:FinancialProduct，治理歸屬證券，不繼承銀行商品 Class。海外的地域判定依據仍待確認。

使用者已再次確認：**手收用「手收來源商品」連金融商品**。銀行與證券均沿用 fh:feeIncomeFromProduct（FeeIncome → FinancialProduct）；AUM 沿用 fh:measuresProduct（AUM → FinancialProduct）。各商品指標留在 PG，沒有新增持有部位、資產實例或手收指向 AUM 的關係。

新增的 `department-pg/investment-metrics.json` 共十一項業務概念：

| 商品範圍 | AUM | 手收及金額觀察 |
|---|---|---|
| 銀行基金 | PB_FUND_MONTH；CurrentTWDValue | PB_FUND_SPREAD_DAILY；BRHREBATEAMT |
| 證券複委託債券 | BONDPOS_SEC／_M；NETQTY ÷ 100 × CPRICE × 匯率 | BONDTRADM_SEC／_M；CFEE × FXRATE |
| 證券複委託結構型商品 | 同債券來源，BOND LIKE TSSN% 的分支 | 同債券來源，保留原 CASE 分類順序 |
| 證券複委託基金 | FUNDPOSIT_SEC／_M；WKB28 × WKB23 × WKB31 | FUNDTRADM_SEC／_M；WKA31 |
| 證券複委託外國股票 | STOCKPOS_SEC／_M；NETQTY × CPRICE × 匯率 | STOCKTRADM PM／AM 分支；(CFEE − ABFEE) × FXRATE，淨手收 |
| 證券台股 | YTRMRBP_SEC／_M；YTRMRB110 × YTRMRB150 | 提供的來源未見定義，未建立台股手收概念 |

上述都是來源觀察，不是已核定公式。來源完整表名、原始欄位、SQL 行號、metadata 儲存格與未定案值均保存在 JSON。銀行基金手收另參照既有 attributedToAdvisor，員編候選 BAOEMPID／SAOEMPID 保留不同角色；證券手收不套用銀行理專關係。

- 銀行基金 AUM 的 TRUSTPRD 完整取值尚未驗證，不能將整張 PB_FUND_MONTH 視為基金。私銀將基金、ETF 分列；本輪不自動含 ETF。基金手收的原 CASE 先判一般基金，後方 TA／TB／TD／TE 條件可能被先行條件攔截，保留待覆核。
- 證券基金 AUM 的 WKB02 在 SQL 當 cust_id，但 current metadata 是「投資人帳號」；WKB24 是「客戶身分證字號」。兩者不視為同一識別，歷史表語意也未獨立確認。
- 證券手收以工作日曆將月底最後兩個工作天移至次月；YYYYMM＋01 是收入歸屬月份標記，不是快照日期。基金 current 最大日期卻查 BONDTRADM；外股 current AM 分支仍 FROM AM_SEC_M、最大日期查 AM_SEC，均保留原文異常，未自行修正來源。
- 台股 SQL 先 UNION 投影列再 SUM，需覆核去重與原始粒度。股票設質已依需求表與彙總 SQL 補為證券台股 AUM 分項，金額意義為設質股票估值；與原台股庫存的重疊與日期仍待確認，不作借款／可融資額或直接加總。

來源選擇、幣別、收入期間、快照、認列、估值、去重與歸屬仍 pending/null，execution 全 null。沒有把銀行與證券 AUM 自動加總，也沒有把商品分類參照當成已匹配的單一商品實例。

## AUM 與各商品 AUM

- 金控 `fh:AUM` 繼承 `fh:Metric`；銀行 `bank:BankAUM` 繼承 `fh:AUM`。
- `fh:measuresProduct` 的 domain 改為 `fh:AUM`，range 仍為 `fh:FinancialProduct`。Metric 不再直接定義對金融商品的關係。
- 手收改用獨立的 `fh:feeIncomeFromProduct`（手收來源商品），domain 為 `fh:FeeIncome`。通用手收及 SI／SN 的 PG 參照已同步切換，避免手收因沿用 AUM 關係而被推成 AUM。
- 各商品 AUM 留在部門 PG，參照 `bank:BankAUM`，以 AUM 衡量關係及商品分類參照描述對應商品；不新增各商品 AUM 的組合 OWL Class。

第一批共七項，金額均是待核定認列的候選：

| PG AUM | 商品分類參照 | 原始來源與估值觀察 |
|---|---|---|
| 台幣存款 AUM | 存款＋台幣金融商品 | 沿用已盤 NT current／HS；BAL_AMT |
| 外幣存款 AUM | 存款＋外幣金融商品 | 沿用已盤 FN current／HS；AVAIL_BAL |
| 結構型存款 AUM | 存款＋結構型金融商品 | 沿用既有五張存款來源的 2545 分類證據 |
| 海外股票 AUM | 股票＋海外金融商品 | DSFND.PB_FUND_MONTH；CurrentTWDValue，依既有 TRUSTPRD 分類 |
| 海外債券（信託）AUM | 債券＋海外金融商品 | 同上，TRUSTPRD='海外債券' |
| 海外債券（自營）AUM | 債券＋海外金融商品 | DSWTR.BOND_POS_DAY；STO_AMT × MKT_PRI ÷ 100 × EXC_RATE |
| 境外結構型商品 AUM | 結構型＋海外金融商品 | DSFND.PB_FUND_MONTH；CurrentTWDValue，TRUSTPRD='結構型商品' |

`department-pg/product-aum.json` 保留原有五個欄位定義：customerId、productId、amount、currency、snapshotDate，另增 aumAsOfDate、valuationQuantity、valuationUnitPrice。amount 狀態為 pending_aum_recognition，selected table／column 均 null；不把存款原始餘額直接認定為核定 AUM，也不將欄位名稱中的 TWD 直接轉成幣別常數。

既有 PB_FUND_MONTH SQL 將「其他-國外有價證券」等分類歸為海外股票，需覆核分類範圍；TRUSTPRD 是類型，不代替單一商品識別。自營債券的三個欄位是同一估值公式的輸入，不是任選金額。其舊 SQL 取全體每月最大日期，不是各客戶最後交易日，也不自動成為新版預設選日規則。

商品分類與來源可能重疊；七項不是完整銀行 AUM 清冊，不自動相加成銀行 AUM。認列、幣別、快照日、跨來源識別、去重及聚合仍待確認；execution 全部 null。來源 SQL 只作唯讀文字證據。

## 既有存款邊界保持

既有銀行四個商品 Class：DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct，仍全部直接繼承 fh:FinancialProduct。沒有「銀行金融商品」中間層。

台幣／外幣／結構型存款與行員存款只在部門 PG，使用一般關係參照共通分類。不得恢復 TWDDepositProduct、ForeignCurrencyDepositProduct、StructuredDepositProduct 等組合 OWL Class。

行員存款指存款人本人是行員。行員 RDF 語意現在已建立，但本人識別、JOIN 與適用期間仍未解決；deposits.json 的 pending reference 已填 bank:BankEmployee，狀態改為 pending_depositor_identity_mapping。仍不得用客戶管理 AO 的 AUM_TMP02.EMP_NO 代替存款人行員識別。

既有存款五張來源、分類與原始欄位證據保留；幣別、日期、跨來源識別、聚合與完整覆蓋仍待確認。分行／數位、帳戶與帳戶識別繼續排除。

## 第一批商品手收

第一批僅選「結構型金融商品」可承接、且有私銀 SQL／metadata 證據的兩項；本輪擴充另見上方證券與銀行基金。

| PG 概念 | 原始來源及金額 | 範圍 |
|---|---|---|
| 境內結構型商品手收（SI） | DSDEP.SI_PERFO_RPT、DSDEP.SI_PERFO_RPT_HS；FEE_AMOUNT_TWD | INCOME_039 的 SI 分支；未納入 ELI／FCI，不是完整境內總手收 |
| 境外結構型商品手收 | DSFND.PB_FUND_SPREAD_DAILY；BRHREBATEAMT | INCOME_042：FHID='SN'、BAOPCCCODE LIKE '2E%' 的既有 SQL 範圍 |

兩者均參照 bank:BankFeeIncome，並透過 fh:feeIncomeFromProduct 的關係定義指向 bank:StructuredFinancialProduct，沒有把它們視為「結構型存款」。原始欄位、SQL 範圍、metadata 列號與限制保存在 `department-pg/product-fees.json`。

- SI 的 TRADE_DATE 是交易日；SN 的 FEEDATE 是手續費發生日。兩者均未被選為 snapshotDate。
- SI current metadata 的 FEE_AMOUNT_TWD 定義為「手續費換算台幣」；HS 語意未獨立確認。SN 的 BRHREBATEAMT 只定義為「分行手續費」，計價幣別未確認。selected currency 均保持 null。
- SI current 的 RM_ID／USER_ID，及 SN 的 BAOEMPID／SAOEMPID，只記錄為不同人員角色的候選；不自動認定理專角色或收入歸屬。
- SN 的 FUNDID 在 metadata 是基金代碼，對 SN 商品識別的適用性待確認；SI 的 DEALNO 是交易單號，不代替商品 ID。
- 舊 SQL 的 SUM、GROUP BY、UNION、日期轉換及篩選只保存為觀察，不變成新版執行規則。舊彙總未保留員編與商品識別，不能直接還原理專／單一商品手收。
- 私銀存款收入目前屬利收，未硬塞進手收。銀行基金、ETF 已各自建立 PG 指標；ETF 共通分類直接繼承金融商品。

## 有效來源與輸出

| 檔案 | 用途 |
|---|---|
| holding-core.ttl | 金控共通語意：既有通聯、客戶、金融商品、職員、指標、AUM 與手收，及八個共通指標 Data Property |
| bank-deposit.ttl | 四個銀行共通商品分類 |
| bank-common.ttl | 行員、理專、行員編號、銀行 AUM、銀行手收及歸屬理專關係 |
| bank-investment-products.ttl | 股票、債券、基金、海外金融商品及銀行保險五個共通分類 |
| securities-common.ttl | 證券 AUM、手收及五個商品分類 |
| build-config.json、catalog-v001.xml | 明列五份來源與本機 URI／版本對應 |
| customer360-ontology.ttl、.owl | 自含整合輸出，由 tools/build_ontology.py 產生，勿手改 |
| department-pg/model.json | 通聯 PG |
| department-pg/deposits.json | 存款 PG 與原始來源證據 |
| department-pg/advisory-income.json | 理專、服務客戶關係及通用商品手收欄位架構 |
| department-pg/product-fees.json | 六項銀行手收：SI／SN、海外股票、ELI／FCI 與 DCI 純手續費 |
| department-pg/product-aum.json | 七項商品 AUM、來源估值與分類證據候選 |
| department-pg/investment-metrics.json | 銀行基金、銀行保險與證券，共十三項指標候選 |
| department-pg/model.cypher | 六個 PG 模組合併產生的 Neo4j 5 metadata 腳本；未部署 |
| HANDOFF-ZED-RDF-PG-20261022.md | 最新交接入口 |

共 **31 Class、6 Object Property、16 Data Property、5 Annotation Property、330 triples**。PG 共 **38 個業務概念、484 metadata 節點、1014 關係**。數字僅描述目前版本，不是未來固定基準。各模組的 executable schema 與測試需隨擴充同步更新。

## 建置與驗證

在本目錄執行，沿用本地 .venv／rdflib 7.6.0：

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

本輪 RDF 19 項＋PG 68 項通過，無略過，含股票設質需求表／彙總 SQL 的來源意義與台股手收缺口、舊通聯／存款回歸、既有定義保留、集合管理 AUM／手收延期、ETF 直接繼承金融商品與基金範圍保持、保險廣義分類與原始投資金額／客戶貢獻度的來源意義、跨子公司參照與繼承、日期／數值型別、31 項指標表級來源、新增空欄位映射、DCI 損益排除、檔案證據及確定性輸出。未執行完整 OWL reasoner、SHACL、GUI、SQL、真實資料或 Neo4j 部署。

不新增未確認的 Hash、有效註記、基數、互斥、等價、sameAs、keys、反向關係、property chain 或格式／必填限制。不要執行 tools/legacy-v0.2.0。tools/seed_product_fees.py 是本批固定內容的一次性初始產生器，會拒絕覆寫 active JSON；後續維護 product-fees.json，不把產生器當成通用 SQL 分析器。

私銀來源 SQL／metadata／圖譜、需求 Excel、asset-financial-ontology HTML、其他 PoC 均未修改。沒有 Git 提交、外部部署或已確認雲端備份。

## 歷史 RDF 圖（v0.7.0）

[PNG 結構圖](outputs/rdf-review-v0.7.0/rdf-graph.png)／[SVG 向量圖](outputs/rdf-review-v0.7.0/rdf-graph.svg) 僅供歷史對照，未反映 v0.8.0 的 AUM 關係調整。使用者已指示先不畫圖，本輪沒有新產生圖片。


`tools/seed_product_aum.py` 是本批固定內容的初始產生器，拒絕覆寫 active JSON；後續維護 product-aum.json、product_aum_model.py 與測試。它不是通用 SQL 反推器。

`tools/seed_investment_metrics.py` 是本輪一次性初始產生器，同樣拒絕覆寫 active JSON；後續維護 investment-metrics.json、investment_metrics_model.py 與測試，不重跑 seeder 覆蓋人工維護內容。
