# AUM／LUM／手收／利收指標底表對照

2026-10-24，RDF v0.16.0。共 42 項指標：18 項 AUM、1 項 LUM、21 項手收、2 項利收。

對應主體為指標，範圍統一參照金融商品。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。
42 項指標均由 PG 私銀（bank.private_banking）採用，顯示名稱統一加上私銀並保留銀行／證券來源。採用範圍來自 departments.json，不代表資料權責、理專歸屬或可自動加總；指標 ID 保留。

| 指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |
|---|---|---|---|---|
| 私銀－銀行集合管理帳戶 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行 ETF AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行外幣存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS` | — | 有表級證據 | E2<br>E3 |
| 私銀－銀行基金 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行保險 AUM | `DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT` | — | 有表級證據 | E4<br>E5 |
| 私銀－銀行境外結構型商品 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行海外債券（自營）AUM | `DSWTR.BOND_POS_DAY` | — | 有表級證據 | E6 |
| 私銀－銀行海外債券（信託）AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行海外股票 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E1 |
| 私銀－銀行規劃型信託 AUM | `DSEBS.EBTS_ACT_CntAUMBal_PB`<br>`DSTAM.TRUCONTRACT_PB` | — | 有表級證據 | E7 |
| 私銀－銀行結構型存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS`<br>`DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS`<br>`DSDEP.EMP_DEP_NT_ACCT_HS` | — | 有表級證據 | E2<br>E3<br>E8<br>E9<br>E10<br>E11<br>E12 |
| 私銀－銀行信託保管 AUM | `DSPMS.PB_PMS_AUM` | — | 有表級證據 | E13 |
| 私銀－銀行台幣存款 AUM | `DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS` | — | 有表級證據 | E8<br>E9<br>E10 |
| 私銀－銀行 DCI 手收 | `DSDEP.DCI_PERFO_RPT`<br>`DSDEP.DCI_PERFO_RPT_HS`<br>`DSTAS.FO108_W` | — | 有表級證據 | E14<br>E15<br>E16 |
| 私銀－銀行存款利收 | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS`<br>`DSDEP.DEP_NT_ACCT_HS`<br>`DSDEP.EMP_DEP_NT_ACCT_HS` | — | 有表級證據 | E17<br>E18<br>E19<br>E20 |
| 私銀－銀行境內結構型商品手收（ELI） | `DSDEP.ELI_PERFO_RPT`<br>`DSDEP.ELI_PERFO_RPT_HS` | — | 有表級證據 | E21<br>E22 |
| 私銀－銀行境內結構型商品手收（FCI） | `DSDEP.FCI_PERFO_RPT`<br>`DSDEP.FCI_PERFO_RPT_HS` | — | 有表級證據 | E23<br>E24 |
| 私銀－銀行境內結構型商品手收（SI） | `DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS` | — | 有表級證據 | E25<br>E26 |
| 私銀－銀行 ETF 手續費收入 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E27 |
| 私銀－銀行基金手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E27<br>E28<br>E29 |
| 私銀－銀行外匯手收 | `DSTAS.FO108_W`<br>`DSWBS.PB_SPOT_Daily`<br>`DSWBS.PB_SPOT_Daily_HS` | — | 有表級證據 | E30 |
| 私銀－銀行黃金手收 | `DSDEP.GD_PERFO_RPT`<br>`DSDEP.GD_PERFO_RPT_HS` | — | 有表級證據 | E31 |
| 私銀－銀行保險手收 | `DSINS.INSU_RPT_Q01`<br>`DSKPI.KPI_DET_IU_002_NEW`<br>`DSKPI.KPI_DET_OFI_001` | — | 有表級證據 | E32<br>E33<br>E34<br>E35<br>E36 |
| 私銀－銀行開狀手收 | `DSWBS.IMPM007`<br>`DSWBS.IMPM007_HS` | — | 有表級證據 | E37 |
| 私銀－銀行放款利收（來源業務收益口徑） | `DSLON.LN_FN_ACCT`<br>`DSLON.LN_FN_ACCT_HS`<br>`DSLON.LN_NT_ACCT_HS` | — | 有表級證據 | E38<br>E39 |
| 私銀－銀行放款 LUM | `DSLON.LN_FN_ACCT`<br>`DSLON.LN_FN_ACCT_HS`<br>`DSLON.LN_NT_ACCT`<br>`DSLON.LN_NT_ACCT_HS` | — | 有表級證據 | E40<br>E41 |
| 私銀－銀行境外結構型商品手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E28<br>E29 |
| 私銀－銀行外國債券（自營）手收 | `DSWTR.BOND_TXN` | — | 有表級證據 | E42 |
| 私銀－銀行海外債券（信託）手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E43 |
| 私銀－銀行海外股票手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E27<br>E28 |
| 私銀－銀行規劃型信託手收 | `DSEBS.EBTS_ACT_CntAUMBal_PB`<br>`DSTAM.TRUCONTRACT_PB` | — | 有表級證據 | E44 |
| 私銀－銀行商品手收 | `DSDEP.DCI_PERFO_RPT`<br>`DSDEP.DCI_PERFO_RPT_HS`<br>`DSDEP.ELI_PERFO_RPT`<br>`DSDEP.ELI_PERFO_RPT_HS`<br>`DSDEP.FCI_PERFO_RPT`<br>`DSDEP.FCI_PERFO_RPT_HS`<br>`DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS`<br>`DSFND.PB_FUND_SPREAD_DAILY`<br>`DSINS.INSU_RPT_Q01` | — | 部分範圍 | E14<br>E15<br>E21<br>E22<br>E23<br>E24<br>E25<br>E26<br>E27<br>E28<br>E29<br>E32<br>E33 |
| 私銀－銀行信託保管手收 | `DSPMS.PB_PMS_AUM` | — | 有表級證據 | E45 |
| 私銀－證券複委託債券 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E46<br>E47 |
| 私銀－證券複委託外國股票 AUM | `DSPBM.PB_STOCKPOS_SEC`<br>`DSPBM.PB_STOCKPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E46<br>E47 |
| 私銀－證券複委託基金 AUM | `DSPBM.PB_FUNDPOSIT_SEC`<br>`DSPBM.PB_FUNDPOSIT_SEC_M` | — | 有表級證據 | E48 |
| 私銀－證券複委託結構型商品 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E46<br>E47 |
| 私銀－證券台股 AUM | `DSPBM.PB_YTRMRBP_SEC`<br>`DSPBM.PB_YTRMRBP_SEC_M` | — | 有表級證據 | E49 |
| 私銀－證券複委託債券手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E50 |
| 私銀－證券複委託外國股票淨手收 | `DSPBM.PB_STOCKTRADM_AM_SEC_M`<br>`DSPBM.PB_STOCKTRADM_PM_SEC`<br>`DSPBM.PB_STOCKTRADM_PM_SEC_M` | `DSPBM.PB_STOCKTRADM_AM_SEC`（僅日期查詢） | 有表級證據 | E51 |
| 私銀－證券複委託基金手收 | `DSPBM.PB_FUNDTRADM_SEC`<br>`DSPBM.PB_FUNDTRADM_SEC_M` | `DSPBM.PB_BONDTRADM_SEC`（僅日期查詢） | 有表級證據 | E52 |
| 私銀－證券複委託結構型商品手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E50 |

## 覆蓋範圍與來源疑點

- 六類統一納為金融商品。規劃型信託／信託保管有 AUM 與手收；外匯、開狀、黃金只有手收；放款有 LUM 與利收。不新增外匯、開狀、黃金或放款 AUM。
- 外匯／黃金依 SQL 歸手收，PG 保留兌換／TMU／黃金損益性質；放款依 SQL 歸利收，保留毛利及利息收入減聯行息的來源口徑。共通手收／利收不限定為純手續費／純客戶利息。
- 本批使用／定義部門為私人銀行，承作子公司另列；資料權責部門仍待定。bank-business-metrics 的七項手收參照銀行理專歸屬，實際員編映射未定；存款與放款利收不新增理專歸屬。
- 規劃型信託的員工持股費用原文註記累計；與一般信託及保管分列，不核定差分、加總或去重。
- FX 保留現貨 current／HS 分行條件差異及 TMU 排除 DCD／Cash Bond 的觀察，不將完整 FO108_W 視為外匯來源；不含 DCI TMU。開狀的攤提與換算疑點維持待定。
- 放款 LUM 取數來源為台外幣 current／歷史四表；來源 LN_BAL／BAL_AMT、分行條件、日期標記與彙總會科範圍只作觀察。利收另補外幣 current 分支，日期與歷史覆蓋仍待定，兩指標不混用金額。
- 通用商品手收只對應已盤點的 SI、SN、銀行基金、ETF、海外股票、ELI、FCI、DCI 純手續費及保險日報手收來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。
- DCI 沿用原指標 ID，涵蓋 INCOME_037 純手續費及 INCOME_038 的 DCD／TMU 損益；FO108_W 只取 DCD 分支，與 FX 分支區分。ELI／FCI 與 SI 各自獨立，欄位候選為空，沒有新增 AUM 或自動合計規則。
- 銀行保險 AUM 保留原始投資金額，不直接視為保單市值或現金價值。保險手收沿用原 ID，涵蓋 INCOME_028 日報及 INCOME_029／030 月檔；PS 的客戶貢獻度性質保留。月檔移至次月、日月重疊及 UNION 整列去重只作來源觀察，不認定可直接加總。
- 存款利收新增 INCOME_066 的三項歷史與外幣 current 金額來源；不把台幣 current 表作利收來源。GROSS_INCM 保留為業務收益；歷史初建與上月替換的私銀條件、UNION ALL／UNION 及日期範圍差異待 Tool 承接。
- 銀行海外債券信託手收取 INCOME_031 的 BRHREBATEAMT + WKR028/100；自營手收取 INCOME_032 的 SUM(ABS(INC_AMT_NT))。信託／自營留在 PG，均沿用債券及海外商品分類；來源性質、空值與正負號規則不擅改。
- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。
- 銀行 ETF 直接繼承金控金融商品；PG 基金與 ETF 指標分列且不自動合計。ETF AUM 的實際分類取值仍待確認，手收保留來源 SQL 的 ETF 分支觀察；新欄位均 pending／null、候選為空。
- 集合管理帳戶 AUM 參照銀行集合管理投資商品，直接繼承金控金融商品；來源 SQL 有集合分類，僅記表級來源。手收業務定義空白且原 CASE 順序有疑點，列為待確認，沒有新增手收指標、來源關係或欄位映射。
- 依使用者決議移出證券股票設質 AUM；DSCSD.PBCMS_REPORTA03 的股票估值證據存於 history/stock-pledge-aum-retired-v0.15.0.json，不接為 LUM 金額來源。股票設質 LUM 與台股手收均待可確認底表；原台股庫存 AUM 保留。
- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。
- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。
- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。
- 底表只對應指標，理專、通聯及商品概念不直接連底表。原有欄位候選維持；本批新增欄位皆空映射。SQL 執行及計算由 Tool 承接，Tool 綁定與實作尚未完成。

## 原始證據位置

- E1：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 211–230 行。
- E2：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 75–89 行。
- E3：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 108–123 行。
- E4：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 184–207 行。
- E5：[2._AUM_SUMY.sql](<../../../私銀智能問答/sources/sql/2._AUM_SUMY.sql>)，第 21–39 行。
- E6：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 232–251 行。
- E7：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 254–294 行。
- E8：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 59–74 行。
- E9：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.DEP_NT_ACCT_HS`。
- E10：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 91–106 行。
- E11：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.EMP_DEP_NT_ACCT_HS`。
- E12：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 125–136 行。
- E13：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 295–314 行。
- E14：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.DCI_PERFO_RPT`。
- E15：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 90–115 行。
- E16：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 116–128 行。
- E17：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 583–600 行。
- E18：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 546–581 行。
- E19：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 602–644 行。
- E20：[X-INCOME_MOTHLY.sql](<../../../私銀智能問答/sources/sql/X-INCOME_MOTHLY.sql>)，第 7–49 行。
- E21：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.ELI_PERFO_RPT`。
- E22：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 150–167 行。
- E23：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.FCI_PERFO_RPT`。
- E24：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 169–188 行。
- E25：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.SI_PERFO_RPT`。
- E26：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 131–148 行。
- E27：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 62–88 行。
- E28：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSFND.PB_FUND_SPREAD_DAILY`。
- E29：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 191–202 行。
- E30：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 204–247 行。
- E31：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 303–327 行。
- E32：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSINS.INSU_RPT_Q01`。
- E33：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 8–16 行。
- E34：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSKPI.KPI_DET_IU_002_NEW`。
- E35：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 17–38 行。
- E36：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSKPI.KPI_DET_OFI_001`。
- E37：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 249–272 行。
- E38：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 719–726 行。
- E39：[X-INCOME_MOTHLY.sql](<../../../私銀智能問答/sources/sql/X-INCOME_MOTHLY.sql>)，第 51–88 行。
- E40：[3.LUM_by_day.sql](<../../../私銀智能問答/sources/sql/3.LUM_by_day.sql>)，第 37–65 行。
- E41：[4.LUM_BY_HS.sql](<../../../私銀智能問答/sources/sql/4.LUM_BY_HS.sql>)，第 36–66 行。
- E42：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 54–61 行。
- E43：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 39–51 行。
- E44：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 274–293 行。
- E45：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 295–301 行。
- E46：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 316–361 行。
- E47：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 376–416 行。
- E48：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 364–375 行。
- E49：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 418–431 行。
- E50：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 329–386 行。
- E51：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 429–496 行。
- E52：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 387–427 行。

維護來源：五份 active 指標 JSON 的 table_sources；departments.json 驗證私銀採用範圍。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。
