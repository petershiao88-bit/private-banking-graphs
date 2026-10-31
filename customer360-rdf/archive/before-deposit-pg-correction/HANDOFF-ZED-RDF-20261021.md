# 客戶360 RDF／OWL 與部門 PG：最新交接

更新：2026-10-22；目前版本 **v0.4.0，設計草案**。保留原交接檔名作為穩定入口。

## 接續依據與授權

工作目錄：`C:\Users\petershiao\Desktop\Ontology\客戶360\customer360-rdf-owl`。依本文件、README、現有模型與使用者後續指示接續。上層 `客戶360/AGENTS.md` 適用；專案內相關程式、建置及測試直接執行，不逐項詢問，但不繞過工具核准或擅自外部部署。

修改前快照：v0.4.0實作前的核心、輸出、文件、測試及PG在 `archive/before-v0.4.0/`；更早公司別通聯與部門OWL設計在 `archive/before-v0.3.0/`。歷史快照與legacy工具不參與建置。

## 已確認設計

1. 金控／子公司用RDF／OWL定義共通語意，部門用Property Graph描述業務概念、欄位定義及底表映射。
2. PG是metadata圖，不是客戶資料實例圖；資料留在來源系統。RDF概念URI參照不是實例URI、subclass、等價或自動推論。
3. 手機、地址及七個共用欄位在金控，不按公司重複定義；客戶至通聯使用Object Property，手機／地址至通聯使用subclass。
4. 子公司定義用Annotation記治理歸屬，不必多建「銀行金融商品」中間類別。
5. 存款商品種類、幣別、結構為不同面向；具體存款商品可多重繼承，未加交集等價或反向推論。
6. 行員存款指「存款人本人為銀行行員的存款」，不限定優惠方案。它在PG可關聯人員與商品，不把人與商品做OWL交集。
7. 存款本輪：台幣、外幣、結構型各四個資料欄位（customerId、currency、balance、snapshotDate）；行員存款另有employeeId。
8. 分行／數位分類、帳戶模型與帳戶識別明確排除本輪；不擴大範圍。
9. 定義精簡，限制與未定案內容另寫文件／observations。無Hash、有效註記，golden record及去重仍由來源系統處理。

## 已實作 RDF

來源：`holding-core.ttl`（5個金控Class）及新增 `bank-deposit.ttl`（7個銀行Class）。金控本輪只更新版本標頭，通聯模型語意不變。

銀行四個直接父層Class：DepositProduct、TWDFinancialProduct、ForeignCurrencyFinancialProduct、StructuredFinancialProduct，均直接subClassOf fh:FinancialProduct。

三個多重繼承Class：

- TWDDepositProduct → DepositProduct ＋ TWDFinancialProduct。
- ForeignCurrencyDepositProduct → DepositProduct ＋ ForeignCurrencyFinancialProduct。
- StructuredDepositProduct → DepositProduct ＋ StructuredFinancialProduct。

全部銀行概念使用 `https://example.org/ontology/bank#`，治理層級子公司、歸屬銀行。無BankFinancialProduct中間層、行員存款OWL類別或Employee類別。

整合模型：12 Class、2 Object Property、7 Data Property、5 Annotation Property、145 triples。Data Property仍只限金控通聯欄位；餘額、快照日、客戶與員編不放在商品上。

`build-config.json`列來源、版本與日期；`tools/build_ontology.py`讀取來源產生整合TTL／RDF/XML，catalog已更新到0.4.0。勿分別手改整合輸出或執行legacy-v0.2.0建置器。

## 已實作部門 PG

- `department-pg/model.json`保留兩個通聯概念；schema與版本契約已更新。
- `department-pg/deposits.json`為新增的有效存款模組，四個業務概念與17個欄位定義；`deposit_model.py`提供受限的可執行格式驗證，不是通用ETL。
- `build_cypher.py`合併兩模組產生`model.cypher`，共50 metadata節點、79關係、6個業務概念。保留既有通聯metadata，不連資料庫、不部署。
- 五張有檔案證據的SourceTable：DSDEP.DEP_NT_ACCT、DEP_NT_ACCT_HS、DEP_FN_ACCT、DEP_FN_ACCT_HS、EMP_DEP_NT_ACCT_HS。前述表名皆以DSDEP為schema。
- CUST_ID／BAL_AMT或AVAIL_BAL是來源欄位候選，不代表完整可執行映射或可直接合併。每個selected mapping保持null，候選含證據。
- currency未確認，不填TWD常數。SQL的FN與employee分支TYP_DTL有矛盾，不能當幣別碼。
- snapshotDate仍在DATA_DT、LST_MTN_DT、YYYYMM候選間待確認，年月不擅自補成某日。
- employeeId與本人身分JOIN均未確認；**AUM_TMP02.EMP_NO是管理客戶的AO，不可拿來當存款人本人員編**。
- 員工來源是否涵蓋全部行員存款未知；AUM metadata的EMP_NT_ACCT_HS工作表名不同，未當成第二張來源表。
- 分類碼、舊時間門檻、UNION、SQL日期與SUM只保留證據；執行SQL、JOIN、filter、union、aggregation、粒度及時間窗均null。
- 台幣／外幣普通來源分支的分類碼不代表與結構型概念互斥，也不代表已完整涵蓋所有來源；資料覆蓋仍需確認。
- 行員人員概念以PendingSemanticReference留空，不捏造RDF URI。原`drafts/employee-deposit.json`標記superseded，建置只讀active來源。

## 驗證與命令

本專案`.venv`使用rdflib 7.6.0，requirements.txt已釘版，不修改系統Python。

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

使用通用RDF解析器與圖同構比較；檢查正式繼承、金控通聯語意未變、catalog、來源驅動建置、PG類別／屬性參照、來源欄位證據、待確認值、Cypher escaping及確定性。三元組數量不是固定目標。本輪 RDF 13 項、PG 29 項測試全部通過，無略過；6 份有效 Python 及 5 份 JSON 語法檢查通過。

未執行完整OWL reasoner、一致性／可滿足性檢查、SHACL、GUI、SQL或真實資料；Cypher只離線產生，未驗證Neo4j實際部署。已知編輯器可能仍使用錯誤Python，命令列均使用本地.venv。

## 後續與未定案

先完成存款來源缺口確認，或依使用者下一項指示收斂其他商品；不自動擴充帳戶、職員或其他產品。私銀25個產品與服務只是盤點，不等於全部已核定為金融商品Class。

基金、ETF、其他股票／債券／保險、帳戶／契約／保單／持有部位及集團職員／行員完整模型尚未實作。結構型存款未直接等同DCI，無保本條件或互斥公理。Customer聚焦自然人情境但未形式化等同NaturalPerson。持有認定與時間範圍仍待確認。

不自行加入基數、等價、sameAs、反向、keys、property chain、SHACL、必填、唯一性或碼表。example.org仍為示意URI。

來源Excel、私銀SQL／metadata／圖譜、外部ChatGPT同步專案與sources、其他PoC均未修改；未製作簡報或雲端備份，不宣稱已部署或同步。
