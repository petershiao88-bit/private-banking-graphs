# AUM／手收指標底表對照

2026-10-22，RDF v0.13.0。共 30 項指標：16 項 AUM、14 項手收。

對應主體為 AUM／手收指標。商品分類維持既有語意參照。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。

| AUM／手收指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |
|---|---|---|---|---|
| 銀行集合管理帳戶 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 銀行 ETF AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 外幣存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS` | — | 有表級證據 | E2<br>E3 |
| 銀行基金 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 銀行保險 AUM | `DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT` | — | 有表級證據 | E4<br>E5 |
| 境外結構型商品 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 海外債券（自營）AUM | `DSWTR.BOND_POS_DAY` | — | 有表級證據 | E6 |
| 海外債券（信託）AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 海外股票 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 結構型存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS`<br>`DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS`<br>`DSDEP.EMP_DEP_NT_ACCT_HS` | — | 有表級證據 | E2<br>E3<br>E7<br>E8<br>E9<br>E10<br>E11 |
| 台幣存款 AUM | `DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS` | — | 有表級證據 | E7<br>E8<br>E9 |
| 銀行 DCI 手續費收入 | `DSDEP.DCI_PERFO_RPT`<br>`DSDEP.DCI_PERFO_RPT_HS` | — | 有表級證據 | E12<br>E13 |
| 境內結構型商品手收（ELI） | `DSDEP.ELI_PERFO_RPT`<br>`DSDEP.ELI_PERFO_RPT_HS` | — | 有表級證據 | E14<br>E15 |
| 境內結構型商品手收（FCI） | `DSDEP.FCI_PERFO_RPT`<br>`DSDEP.FCI_PERFO_RPT_HS` | — | 有表級證據 | E16<br>E17 |
| 境內結構型商品手收（SI） | `DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS` | — | 有表級證據 | E18<br>E19 |
| 銀行 ETF 手續費收入 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E20 |
| 銀行基金手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E20<br>E21<br>E22 |
| 銀行保險手續費收入 | `DSINS.INSU_RPT_Q01` | — | 部分範圍 | E23<br>E24 |
| 境外結構型商品手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E21<br>E22 |
| 銀行海外股票手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E20<br>E21 |
| 商品手收 | `DSDEP.DCI_PERFO_RPT`<br>`DSDEP.DCI_PERFO_RPT_HS`<br>`DSDEP.ELI_PERFO_RPT`<br>`DSDEP.ELI_PERFO_RPT_HS`<br>`DSDEP.FCI_PERFO_RPT`<br>`DSDEP.FCI_PERFO_RPT_HS`<br>`DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS`<br>`DSFND.PB_FUND_SPREAD_DAILY`<br>`DSINS.INSU_RPT_Q01` | — | 部分範圍 | E12<br>E13<br>E14<br>E15<br>E16<br>E17<br>E18<br>E19<br>E20<br>E21<br>E22<br>E23<br>E24 |
| 證券複委託債券 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E25<br>E26 |
| 證券複委託外國股票 AUM | `DSPBM.PB_STOCKPOS_SEC`<br>`DSPBM.PB_STOCKPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E25<br>E26 |
| 證券複委託基金 AUM | `DSPBM.PB_FUNDPOSIT_SEC`<br>`DSPBM.PB_FUNDPOSIT_SEC_M` | — | 有表級證據 | E27 |
| 證券複委託結構型商品 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E25<br>E26 |
| 證券台股 AUM | `DSPBM.PB_YTRMRBP_SEC`<br>`DSPBM.PB_YTRMRBP_SEC_M` | — | 有表級證據 | E28 |
| 證券複委託債券手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E29 |
| 證券複委託外國股票淨手收 | `DSPBM.PB_STOCKTRADM_AM_SEC_M`<br>`DSPBM.PB_STOCKTRADM_PM_SEC`<br>`DSPBM.PB_STOCKTRADM_PM_SEC_M` | `DSPBM.PB_STOCKTRADM_AM_SEC`（僅日期查詢） | 有表級證據 | E30 |
| 證券複委託基金手收 | `DSPBM.PB_FUNDTRADM_SEC`<br>`DSPBM.PB_FUNDTRADM_SEC_M` | `DSPBM.PB_BONDTRADM_SEC`（僅日期查詢） | 有表級證據 | E31 |
| 證券複委託結構型商品手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E29 |

## 覆蓋範圍與來源疑點

- 通用商品手收只對應已盤點的 SI、SN、銀行基金、ETF、海外股票、ELI、FCI、DCI 純手續費及保險日報手收來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。
- 新增四項銀行手收只建立指標與底表，欄位候選為空；DCI 不含 TMU 損益，ELI／FCI 與 SI 各自獨立，沒有新增 AUM 或自動合計規則。
- 銀行保險 AUM 的來源意義保留為原始投資金額，不直接視為保單市值或現金價值。保險手收目前僅涵蓋日報；兩項月檔的客戶貢獻度未併入，仍為部分範圍。保單／契約及欄位映射保持暫緩。
- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。
- 銀行 ETF 直接繼承金控金融商品；PG 基金與 ETF 指標分列且不自動合計。ETF AUM 的實際分類取值仍待確認，手收保留來源 SQL 的 ETF 分支觀察；新欄位均 pending／null、候選為空。
- 集合管理帳戶 AUM 參照銀行集合管理投資商品，直接繼承金控金融商品；來源 SQL 有集合分類，僅記表級來源。手收業務定義空白且原 CASE 順序有疑點，列為待確認，沒有新增手收指標、來源關係或欄位映射。
- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。
- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。
- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。
- 理專、通聯及存款商品概念不在本次新增表級對應範圍。原有欄位候選與尚待確認事項維持。

## 原始證據位置

- E1：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 211–230 行。
- E2：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 75–89 行。
- E3：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 108–123 行。
- E4：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 184–207 行。
- E5：[2._AUM_SUMY.sql](<../../../私銀智能問答/sources/sql/2._AUM_SUMY.sql>)，第 21–39 行。
- E6：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 232–251 行。
- E7：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 59–74 行。
- E8：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.DEP_NT_ACCT_HS`。
- E9：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 91–106 行。
- E10：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.EMP_DEP_NT_ACCT_HS`。
- E11：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 125–136 行。
- E12：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.DCI_PERFO_RPT`。
- E13：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 90–115 行。
- E14：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.ELI_PERFO_RPT`。
- E15：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 150–167 行。
- E16：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.FCI_PERFO_RPT`。
- E17：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 169–188 行。
- E18：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.SI_PERFO_RPT`。
- E19：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 131–148 行。
- E20：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 62–88 行。
- E21：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSFND.PB_FUND_SPREAD_DAILY`。
- E22：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 191–202 行。
- E23：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSINS.INSU_RPT_Q01`。
- E24：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 8–16 行。
- E25：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 316–361 行。
- E26：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 376–416 行。
- E27：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 364–375 行。
- E28：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 418–431 行。
- E29：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 329–386 行。
- E30：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 429–496 行。
- E31：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 387–427 行。

維護來源：四份 active 指標 JSON 內各 concept 的 table_sources。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。
