# 客戶360 RDF／OWL＋部門 PG：v0.15.0／已確認修正版交接

更新：2026-10-24。固定沿用此檔名作正式交接入口。工作目錄：C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。

## 新 Session 先讀這裡

先讀 ../AGENTS.md、本檔、README.md；逐項底表見 department-pg/METRIC-TABLE-SOURCES.md。前版完整交接文字保存在 archive/before-v0.15.0/HANDOFF-ZED-RDF-PG-20261022.md，不再把其中 v0.14.0 的服務分類／一般損益指標方案當成現況。

本輪使用者先逐項討論並確認變更清單，最後指示「可以，啟動」。以下 v0.15.0 已依核定清單完成本機實作、建置與驗證，未對外部署。使用者希望實質模型變更先說明方案與範圍，再確認執行；本輪例行建置／測試已授權，不要反覆詢問。

原方向維持證券優先；本輪同意修正前批六類銀行商品與指標。不得擅自擴充後續商品／收入範圍。

## 本輪確定的分類與行為

1. 規劃型信託、信託保管、外匯、開狀、黃金、放款先統一納為銀行金融商品，直接繼承 fh:FinancialProduct。FinancialService、四個服務 Class 與兩個服務專屬關係已移除。後續資訊足夠才再討論是否拆分商品／服務。
2. 金控共通指標為 AUM、LUM、FeeIncome（手收）、InterestIncome（利收），均直接繼承 Metric。LUM 正式採此名稱；銀行新增 BankLUM、BankInterestIncome。證券／人壽尚未新增 LUM 分項。
3. 收入分類以原 SQL 為主：外匯、黃金歸手收，放款收入歸利收。保留既有 FeeIncome URI；名稱／定義由純手續費改採業務手收。PG 保留兌換、TMU、黃金損益以及放款毛利等實際金額性質，不改寫來源。
4. 使用者曾詢問外匯／開狀／黃金 AUM，查核後明確決定「先不要 AUM，維持手收」。三類不新增 active AUM 或 AUM 候選。原始需求 AUM 工作表雖曾列開狀 AUM，也不能據此恢復本輪已排除的範圍。
5. 放款規模用 LUM，放款收入用利收，兩者分列。沒有放款 AUM。
6. 股票設質退出 AUM；既有證據是設質股票估值，不能直接改名成 LUM。實際借款餘額來源待確認。原台股庫存 AUM 保留。
7. 私銀先承接使用／定義部門，承作子公司另外保留，來源資料權責部門待定。本輪五項手收先歸屬理專；放款利收不新增理專歸屬。實際員編映射未定。

## 本輪六類／九項銀行指標

來源為 department-pg/bank-business-metrics.json，executable schema 為 bank_business_model.py。

| PG ID | 種類／商品分類 | 金額來源底表 |
|---|---|---|
| bank.planned_trust_aum | BankAUM／PlannedTrustProduct | DSEBS.EBTS_ACT_CntAUMBal_PB、DSTAM.TRUCONTRACT_PB |
| bank.planned_trust_fee_income | BankFeeIncome／PlannedTrustProduct | 同上 |
| bank.trust_custody_aum | BankAUM／TrustCustodyProduct | DSPMS.PB_PMS_AUM |
| bank.trust_custody_fee_income | BankFeeIncome／TrustCustodyProduct | DSPMS.PB_PMS_AUM |
| bank.fx_fee_income | BankFeeIncome／ForeignExchangeProduct | DSWBS.PB_SPOT_Daily／_HS、DSTAS.FO108_W 的 FX 分支 |
| bank.lc_fee_income | BankFeeIncome／LetterOfCreditProduct | DSWBS.IMPM007／_HS |
| bank.gold_fee_income | BankFeeIncome／GoldProduct | DSDEP.GD_PERFO_RPT／_HS |
| bank.loan_lum | BankLUM／LoanProduct | DSLON.LN_NT_ACCT／LN_FN_ACCT 及各自 _HS |
| bank.loan_income | BankInterestIncome／LoanProduct | DSLON.LN_NT_ACCT_HS、LN_FN_ACCT_HS、LN_FN_ACCT |

department_context：using_department／definition_department 均為私人銀行、source_data_owner=null；概念的 department_owner=null、subsidiary=bank。這是指標使用／定義脈絡，不代表來源資料權責歸私銀，也沒有新增部門 Class 或真實組織資料。

五項手收（規劃型信託、保管、外匯、開狀、黃金）都參照 bank:attributedToAdvisor。放款利收沒有此關係。HAS_BUSINESS_SCOPE 是 PG metadata 商品範圍參照，非 RDF Object Property、實例或繼承推論。

本模組九項指標共 85 個必要元素：兩項 AUM 各八、五項手收各十一、LUM 六、利收八。新舊分類調整後的本模組欄位均 pending、table／column=null、candidates=[]、execution 全 null；serviceId 已改為 productId，不建立實體欄位映射。

## 共通關係與元素

- AUM 使用 measuresProduct（AUM → FinancialProduct），元素為 metricAmount、aumAsOfDate、valuationQuantity、valuationUnitPrice。
- LUM 使用 lumMeasuresProduct（LUM → FinancialProduct），元素為 metricAmount、lumAsOfDate。
- 手收使用 feeIncomeFromProduct（FeeIncome → FinancialProduct），元素為 metricAmount、incomePeriodStart／End、feeBaseAmount／DeductionAmount。
- 利收使用 interestIncomeFromProduct（InterestIncome → FinancialProduct），元素為 metricAmount、interestPeriodStart／End。

既有 AUM／手收關係與日期／計算元素的 domain／range 保持，未放寬成 Metric。metricAmount 的 domain=Metric、range=decimal，定義文字同步含 AUM／LUM／手收／利收。日期 range=date。元素按情境適用，不新增必填、固定基數或詳細公式。

欄位映射先不做；舊候選保留。客戶／商品識別、幣別／匯率、日期、收入期間、實際員編與歸屬均未核定。snapshotDate／incomePeriod 保留來源觀察，不自動轉為共通基準日或期間起迄。

## 來源查核與尚未核定之口徑

- 銀行 LUM 已有原 SQL：3.LUM_by_day.sql 第 37–65 行、4.LUM_BY_HS.sql 第 36–66 行，分別取 current／歷史台外幣四表；5.LUM_MERGE.sql 彙總放款餘額；10._INCOME_ROA.sql 另以 ln_amt 保留放款規模，註記 ROBA 與 LUM。不能再寫成銀行 LUM 完全沒有來源。
- LUM 觀察 LN_BAL／BAL_AMT，但原彙總會科有 1886／應付保證標示，實際範圍仍待核對。分行條件、非零餘額、歷史月份、SYSDATE-1、UNION／UNION ALL 與台外幣換算均未核定為執行規則，不自動宣稱是純借款本金或跨公司完整 LUM。
- 放款利收 INCOME_067：台幣歷史取 GROSS_INCM（metadata 為毛利），外幣歷史／current 取 INT_INCM 減 CB_INT_AMT（利息收入減聯行息收入）。8.INCOME_DETAIL.sql 第 719–726 行的外幣 current 分支已補為表級來源；月更新來自 X-INCOME_MOTHLY.sql 第 51–88 行。分支日期、分行條件與時間覆蓋差異保留，不當成完整一致資料。
- FX INCOME_043 為 BAL_AMT_TWD（兌換損益），current／HS 的 2E 篩選不同；INCOME_044 為 TMUPROFIT，排除 DCD／Cash Bond。9.INCOME_SMY.sql 將兩者歸手收／銀行／FX。未把全張 FO108_W 或 DCI TMU 納入。
- 黃金 INCOME_049 為 PLAMT_TWD，metadata 為損益等值台幣；彙總 SQL 歸手收／銀行／黃金。開狀 INCOME_045 為 FEE_AMT，原攤提／換算與日期條件疑點保留。
- 規劃型信託 AUM_020／021 為員工福利及股票／金錢信託；INCOME_047 費用原文註記累計。保管 INCOME_048 原彙總併規劃型信託，但本模型依既有商品範圍分列。涵蓋、累計轉單期與跨商品加總未核定。

所有 evidence 在 JSON，原 SQL cp950、JSON／Turtle UTF-8。來源仍 observed_in_files／database_verified=false。只對指標到底表，不對商品到底表；source tables 記錄只含 table／role／evidence。

## 股票設質退場與新舊 ID

securities.stock_pledge_aum、其 AUM 關係與 DSCSD.PBCMS_REPORTA03 的有效來源已從 active 模型移除。完整原指標、關係、來源與證據另存 department-pg/history/stock-pledge-aum-retired-v0.15.0.json。原始需求仍記股票設質估值且舊報表歸 AUM，這是歷史證據，不覆蓋使用者本輪決議。

新舊 ID／URI 對照見 department-pg/history/changes-v0.15.0.json：四個 *Service Class 改為 *Product；bank.fx_trading_pnl → bank.fx_fee_income；bank.gold_trading_pnl → bank.gold_fee_income；bank.loan_income ID 保留但改參照 BankInterestIncome；新增 bank.loan_lum。

history/ 不參與建置，這些是離線變更紀錄，不是部署或自動遷移腳本。Cypher 產生器只 MERGE、不刪舊資料，未來若部署至曾載入舊版的資料庫，必須另做限定範圍遷移，不能把重跑 MERGE 當成完整同步。本輪沒有資料庫連線或部署。

## 原有決議與待辦保持

證券現有五項 AUM：複委託債券、結構型、基金、外股、台股庫存；四項手收為前四類，外股保留淨手收。證券不繼承銀行商品分類，不套用銀行理專關係。銀行與證券不自動加總。

pending_scope 共三筆：

- securities.stock_pledge_lum／pending_source_definition：待實際借款／融通餘額來源，不借用 DSCSD 股票估值。
- securities.taiwan_stock_fee_income／pending_source_definition：缺底表與業務範圍，使用者接受先不放，不代表現實沒有收入或永久排除。
- bank.collective_account_fee_income／pending_business_semantics：收入定義空白，原 CASE 分支可能被前方基金條件攔截，未新增 active 手收。

銀行 ETF 直接繼承金融商品、與基金分列；ETF AUM 分類取值未定。集合管理商品與 AUM 已完成，與基金／ETF 分列。保險為廣義銀行通路商品，AUM 保留原始投資金額，日報手收 partial_scope，月檔客戶貢獻度未併入。SI／ELI／FCI 分列，DCI 只有純手續費，不含 TMU。通用銀行手收維持原 partial_scope，本輪五項商品手收分列，未擴大通用來源。

證券基金手收 BONDTRADM_SEC、外股手收 AM_SEC 僅供日期查詢；T_LAST_TWO_WORKDAYS 缺 schema／底層定義，仍保留未辨識期間輔助關係。WKB02／WKB24 識別角色、日期、FX、UNION 去重等來源疑點保持。

尚未擴充：存款利收、海外債券收入（交易利得／自營收益性質）、DCI TMU、保險月檔客戶貢獻度、證券／人壽 LUM。權限、帳戶、分行／數位與畫圖仍暫緩。行員存款須識別存款人本人為行員，不得借用管理客戶的 AO 員編。

## 有效來源、輸出與驗證

RDF 五份來源：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl；build-config.json／catalog-v001.xml 同步 v0.15.0。customer360-ontology.ttl／.owl 由 tools/build_ontology.py 產生，勿手改，不連網解析 example.org。

PG 七份 active JSON：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics。各有 JSON Schema 或 Python executable schema，合併產生 Neo4j 5 metadata 腳本 model.cypher，只依賴標準函式庫。

目前 39 項指標：18 AUM（銀行 13、證券 5）、1 銀行 LUM、19 手收（銀行 15、證券 4）、1 銀行利收。49 SourceTable，79 HAS_SOURCE_TABLE、3 USES_VALUATION_SOURCE、2 USES_DATE_LOOKUP_SOURCE。

RDF：41 Class、8 Object Property、19 Data Property、5 Annotation Property、418 triples。PG：46 概念、611 metadata 節點、1245 關係，含 383 DataFieldDefinition、49 SourceTable、55 BusinessRelationDefinition、6 MetadataModule、7 MappingSlot。通聯沒有獨立 MetadataModule。

本輪 RDF 19＋PG 78＝97 項測試通過，無略過。涵蓋來源 SQL／metadata 儲存格、四種指標 domain、五項手收理專歸屬、私銀使用／定義與資料權責區分、股票設質退場完整保存、既有欄位／候選保留、新映射空白、錯誤型別／來源／規則反例拒絕、確定性及輸出逐位元組比對。修改前 24 份來源 SQL／Excel 的 SHA-256 已保存於快照，測試確認未變。

建置與檢查命令：

```powershell
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py
.venv\Scripts\python.exe -X utf8 -B tools\build_ontology.py --check
.venv\Scripts\python.exe -X utf8 -B department-pg\build_cypher.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py
.venv\Scripts\python.exe -X utf8 -B tools\export_metric_tables.py --check
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s department-pg -v
```

RDF 與表級清單 --check、Cypher 逐位元組比對已通過。未執行來源 SQL、真實資料庫查核、完整 OWL reasoner、SHACL、GUI 或 Neo4j 部署。沒有資料實例，也未新增 Hash、互斥、等價、sameAs、keys、反向關係、property chain、必填／基數或執行公式。

## 保存與維護注意

本輪修改前快照為 archive/before-v0.15.0，包含來源、工具、文件與測試，不含 venv、歷史 archive、outputs。before-v0.14.0 為新增六類前；更早快照保持。before-deposit-pg-correction 是錯誤組合 OWL 實作，不可恢復。

舊五份未涉本輪分類的 active JSON 除 ontology_version 外完全保持。investment-metrics.json 只做核定的股票設質退場與 pending 增補，其他概念／關係／證據保持。本輪銀行九項必要元素全為空映射。

保存性測試各有原歷史基準，不為版本一致而替換 before-v0.13.0、before-v0.12.0、before-v0.10.0 等路徑。review_contract_v015.py 僅正規化本輪核定的名稱／定義文字差異；型別、繼承、domain／range 不忽略。stock-pledge 測試已改為驗證歷史完整及 active 退場，不能改回舊版「必須存在 AUM」契約。

tools/seed_product_fees.py、seed_product_aum.py、seed_investment_metrics.py 為歷史一次性 seeder，不可重跑覆寫 active JSON；tools/legacy-v0.2.0 不可執行。後續維護 JSON、驗證器、測試、整合輸出與底表清單。

私銀來源 SQL、metadata、需求 Excel、圖譜、其他 PoC 與外部同步專案未修改。無 Git 提交、外部部署或已確認雲端備份。outputs/rdf-review-v0.7.0 為歷史圖，不代表目前模型。以繁體中文簡短說明結果，區分共通語意、部門指標與來源觀察。
