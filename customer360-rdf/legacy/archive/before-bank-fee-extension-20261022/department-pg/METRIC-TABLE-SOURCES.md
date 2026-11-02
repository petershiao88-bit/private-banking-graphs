# AUM／手收指標底表對照

2026-10-22，RDF v0.10.0。共 21 項指標：13 項 AUM、8 項手收。

對應主體為 AUM／手收指標。商品分類維持既有語意參照。此表只列底表及其角色，不新增欄位映射、公式或執行規則；所有來源均為檔案觀察，未查驗資料庫。

| AUM／手收指標 | 金額來源底表 | 輔助／查詢表 | 對應狀態 | 證據 |
|---|---|---|---|---|
| 外幣存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS` | — | 有表級證據 | E1<br>E2 |
| 銀行基金 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E3 |
| 境外結構型商品 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E3 |
| 海外債券（自營）AUM | `DSWTR.BOND_POS_DAY` | — | 有表級證據 | E4 |
| 海外債券（信託）AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E3 |
| 海外股票 AUM | `DSFND.PB_FUND_MONTH` | — | 有表級證據 | E3 |
| 結構型存款 AUM | `DSDEP.DEP_FN_ACCT`<br>`DSDEP.DEP_FN_ACCT_HS`<br>`DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS`<br>`DSDEP.EMP_DEP_NT_ACCT_HS` | — | 有表級證據 | E1<br>E2<br>E5<br>E6<br>E7<br>E8<br>E9 |
| 台幣存款 AUM | `DSDEP.DEP_NT_ACCT`<br>`DSDEP.DEP_NT_ACCT_HS` | — | 有表級證據 | E5<br>E6<br>E7 |
| 境內結構型商品手收（SI） | `DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS` | — | 有表級證據 | E10<br>E11 |
| 銀行基金手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E12<br>E13<br>E14 |
| 境外結構型商品手收 | `DSFND.PB_FUND_SPREAD_DAILY` | — | 有表級證據 | E13<br>E14 |
| 商品手收 | `DSDEP.SI_PERFO_RPT`<br>`DSDEP.SI_PERFO_RPT_HS`<br>`DSFND.PB_FUND_SPREAD_DAILY` | — | 部分範圍 | E10<br>E11<br>E12<br>E13<br>E14 |
| 證券複委託債券 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E15<br>E16 |
| 證券複委託外國股票 AUM | `DSPBM.PB_STOCKPOS_SEC`<br>`DSPBM.PB_STOCKPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E15<br>E16 |
| 證券複委託基金 AUM | `DSPBM.PB_FUNDPOSIT_SEC`<br>`DSPBM.PB_FUNDPOSIT_SEC_M` | — | 有表級證據 | E17 |
| 證券複委託結構型商品 AUM | `DSPBM.PB_BONDPOS_SEC`<br>`DSPBM.PB_BONDPOS_SEC_M` | `DSDEP.FN_EXCH_RT`（估值輔助） | 有表級證據 | E15<br>E16 |
| 證券台股 AUM | `DSPBM.PB_YTRMRBP_SEC`<br>`DSPBM.PB_YTRMRBP_SEC_M` | — | 有表級證據 | E18 |
| 證券複委託債券手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E19 |
| 證券複委託外國股票淨手收 | `DSPBM.PB_STOCKTRADM_AM_SEC_M`<br>`DSPBM.PB_STOCKTRADM_PM_SEC`<br>`DSPBM.PB_STOCKTRADM_PM_SEC_M` | `DSPBM.PB_STOCKTRADM_AM_SEC`（僅日期查詢） | 有表級證據 | E20 |
| 證券複委託基金手收 | `DSPBM.PB_FUNDTRADM_SEC`<br>`DSPBM.PB_FUNDTRADM_SEC_M` | `DSPBM.PB_BONDTRADM_SEC`（僅日期查詢） | 有表級證據 | E21 |
| 證券複委託結構型商品手收 | `DSPBM.PB_BONDTRADM_SEC`<br>`DSPBM.PB_BONDTRADM_SEC_M` | — | 有表級證據 | E19 |

## 覆蓋範圍與來源疑點

- 通用商品手收只對應已盤點的 SI、SN 與銀行基金來源，非完整銀行總手收清冊，也不代表這些來源可直接相加。
- 共用底表可能服務多項指標，表級對應不表示整張表只屬於某個商品，也沒有新增分類條件。
- 證券基金手收的債券交易表只出現在最大日期子查詢，保留為日期查詢來源。
- 證券外股手收的 AM_SEC 僅供日期子查詢；原金額來源仍為 AM_SEC_M，不新增 current AM 金額來源。
- 四項證券手收另引用 T_LAST_TWO_WORKDAYS。現有來源沒有其 schema／底層定義，保留為待釐清的期間輔助關係，未列成已辨識底表。
- 理專、通聯及存款商品概念不在本次新增表級對應範圍。原有欄位候選與尚待確認事項維持。

## 原始證據位置

- E1：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 75–89 行。
- E2：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 108–123 行。
- E3：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 211–230 行。
- E4：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 232–251 行。
- E5：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 59–74 行。
- E6：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.DEP_NT_ACCT_HS`。
- E7：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 91–106 行。
- E8：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.EMP_DEP_NT_ACCT_HS`。
- E9：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 125–136 行。
- E10：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSDEP.SI_PERFO_RPT`。
- E11：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 131–148 行。
- E12：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 62–88 行。
- E13：[收入_metadata.xlsx](<../../../私銀智能問答/sources/metadata/收入_metadata.xlsx>)，工作表 `DSFND.PB_FUND_SPREAD_DAILY`。
- E14：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 191–202 行。
- E15：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 316–361 行。
- E16：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 376–416 行。
- E17：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 364–375 行。
- E18：[1.AUM_DETAIL.sql](<../../../私銀智能問答/sources/sql/1.AUM_DETAIL.sql>)，第 418–431 行。
- E19：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 329–386 行。
- E20：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 429–496 行。
- E21：[8.INCOME_DETAIL.sql](<../../../私銀智能問答/sources/sql/8.INCOME_DETAIL.sql>)，第 387–427 行。

維護來源：四份 active 指標 JSON 內各 concept 的 table_sources。執行 tools/export_metric_tables.py 可重建本表；本表不作為模型輸入。
