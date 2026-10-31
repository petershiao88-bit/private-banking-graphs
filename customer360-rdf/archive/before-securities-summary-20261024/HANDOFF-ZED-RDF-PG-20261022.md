# 客戶360 RDF／OWL＋私銀部門 PG：v0.16.0 交接

更新2026-10-24。固定沿用本檔名作正式入口；先讀 ../AGENTS.md、本檔、README.md，再讀 department-pg/METRIC-TABLE-SOURCES.md。

工作目錄 C:/Users/petershiao/Desktop/Ontology/客戶360/customer360-rdf-owl。使用者要求先討論實質變更清單、確認再執行；本輪已逐項確認，最後指示「可以，啟動」，已完成本機建置／驗證，沒有部署。方向保持證券優先；可確認來源的證券商品指標已納入。

## 本輪完成的範圍

1. 金控新增 fh:Department、fh:usesMetric（Department → Metric）；銀行新增 bank:PrivateBankingDepartment，直接繼承 Department。原 fh:department 仍為治理註記。五份來源／整合輸出／catalog／active JSON 同步0.16.0。
2. 新增 PG departments.json 及 department_model.py，只有 bank.private_banking（私銀）一層。它是 metadata 概念並參照部門類型，不建立真實組織實例，不拆一部／二部、分行或團隊。
3. 私銀用42條 USES_METRIC 連到全部既有指標，含AUM／手收／LUM／利收及通用部分範圍手收。關係定義參照 RDF usesMetric；PG 保存父類／domain／range參照但不推論。
4. 42項指標顯示名稱加私銀並保留銀行／證券來源；ID、定義、欄位候選、底表、理專關係與計算口徑保持。七份舊 active JSON 除 ontology_version 與指標 name 外完全相同。
5. 採用不等於承作子公司、來源權責、理專歸屬、閱覽權限或自動加總。私銀部門屬銀行；證券指標仍屬證券。原 department_owner=null 等內容不因新增部門而改寫。

本輪備份 archive/before-department-v0.16.0；名稱前後對照與新增 URI 見 department-pg/history/department-v0.16.0.json。前一輪詳細交接完整保存在本輪備份；更早 archive/before-pg-income-extension-20261024、before-v0.15.0 等保持。history 不參與建置，原記錄逐位元組保持。

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

總AUM／總收入、目標達成率等彙總指標留下一輪確認。客戶母體、客戶數／分群、放款額度／人數尚未建模；Organic／Migration／轉介依賴人工來源未確認完整。11.TARGET.sql確實計算達成率；10._INCOME_ROA.sql僅註解寫ROA／ROBA比率，程式只彙整分子／分母，未實作除法。

股票設質退場及舊ID對照保存在history/stock-pledge-aum-retired-v0.15.0.json、changes-v0.15.0.json；SQL範圍查核見sql-scope-review-20261024.json。權限、帳戶、分行／數位、畫圖與實體欄位映射繼續暫緩。

## Active來源與統計

RDF5份：holding-core.ttl、bank-deposit.ttl、bank-common.ttl、bank-investment-products.ttl、securities-common.ttl。PG8份：model、deposits、advisory-income、product-fees、product-aum、investment-metrics、bank-business-metrics、departments，各有schema／Python驗證器。RDF輸出由tools/build_ontology.py產生，PG由department-pg/build_cypher.py合併，只依賴標準函式庫，不手改產生檔、不連網解析example.org。

42項指標：18AUM（銀行13／證券5）、1銀行LUM、21手收（銀行17／證券4）、2銀行利收；新增部門不增加指標數。

RDF：43Class、9Object Property、19Data Property、5Annotation Property、434triples。PG：50BusinessConcept、658節點、1388關係，含413DataFieldDefinition、52SourceTable、61BusinessRelationDefinition、7MetadataModule、7MappingSlot。42USES_METRIC；88HAS_SOURCE_TABLE、3USES_VALUATION_SOURCE、2USES_DATE_LOOKUP_SOURCE。

RDF19＋PG92＝111項測試通過，無略過。精確新增兩Class／一Property、舊語意／JSON保存、42項命名與採用、跨子公司及所有權分離、來源可達、錯誤目標／權限／執行規則反例、確定性與逐位元組產出一致均驗證。24份來源SQL／Excel SHA-256未變。

建置／測試命令見README。未執行來源SQL、真實資料庫查核、完整OWL reasoner、SHACL、GUI、Neo4j部署或Git提交，也沒有已確認雲端備份。

## 維護注意

保存性測試各有歷史基準，不能全域換archive路徑。review_contract_v015.py與review_contract_pg_income.py保留前輪核定差異；review_contract_v016.py僅供測試還原核定顯示名稱、移除三個新增RDF主詞與版本標頭，來源、欄位、型別、權責及規則不忽略。test_departments.py直接驗證本輪精確異動。

歷史一次性seeder與tools/legacy-v0.2.0不可重跑。outputs/department-v0.16.0/apply.py為本輪已執行的維護紀錄，不是建置入口。before-deposit-pg-correction為錯誤組合OWL實作，不可恢復。舊圖與舊文件不代表本版。

Cypher只有MERGE，沒有刪舊資料或自動遷移。未來部署須先確認目標namespace與舊版範圍，不能假設重跑即完整同步。本輪未部署。
