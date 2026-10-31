# 討論中的 PG 擴充草稿

本目錄不在正式 `model.json`／`model.schema.json`／`build_cypher.py` 的輸入範圍內。這些 JSON 是模型與來源欄位的設計 metadata，不是客戶資料實例，也尚未產生或部署 PG。

## 本輪存款範圍

已確認先處理台幣存款、外幣存款、結構型存款及行員存款。這些是討論項目，可能交叉，不代表互斥分類或每項都要建立 OWL 類別。

- 台幣、外幣、結構型存款的映射資料先共用四個欄位：`customerId`（客戶識別）、`currency`（幣別）、`balance`（餘額）、`snapshotDate`（快照日期）。這是欄位設計共識，尚未全部寫入 JSON 或接入來源。
- 行員存款另外保留 `employeeId`（行員識別），指存款人本人是行員，不是管理客戶的 AO；來源映射缺口繼續保留。
- **分行／數位分類明確移出本輪範圍，後續再討論；目前不新增相關類別、Property 或來源映射。**
- 帳戶識別與帳戶模型延後；不把來源表的帳戶欄位自行加入這輪業務欄位清單。

## 行員存款

`employee-deposit.json` 依使用者指定列出五個業務欄位：客戶識別、行員識別、幣別、餘額、快照日期。JSON 的 `properties` 保存欄位定義與映射，不是某人的真實欄位值，也不是可直接原樣寫入 Neo4j 的巢狀 property map。

來源查核：

- 私銀 AUM SQL 非註解的員工分支直接讀取 `DSDEP.EMP_DEP_NT_ACCT_HS`，產生 `AUM_005_007_008_009_TMP08`，再參與總存款合併表。
- `CUST_ID` 與 `BAL_AMT` 有 SQL 及 `收入_metadata.xlsx` 同名工作表的證據。後者是存款餘額，不是 GROSS_INCM 收入。
- 沒有確認到行員識別欄位，不以 AO_ID 或 CUST_NO 替代；不猜人事主檔與 JOIN。
- 幣別沒有可確認來源；員工分支 TYP_DTL 固定寫外幣，DETAIL 卻含台幣存款分類，保留矛盾待查。
- 快照日期保留 YYYYMM（Snapshot年月）、DATA_DT（資料日期）、LST_MTN_DT（SQL使用但metadata無定義）三種候選，不擅自選用或補成月初／月底。
- AUM metadata 工作表名為 `DSDEP.EMP_NT_ACCT_HS`，與 SQL 不同；不把這個命名差異當成第二張已確認底表。
- 舊SQL的聚合、group by、時間門檻只記為歷史證據，不直接套成新版取數規則。五項業務欄位也不是已驗證唯一鍵。

銀行行員、存款商品的 RDF 定義仍未實作，因此 RDF URI 保持 null。草稿定案後需另行擴充正式 PG schema、建置器及測試；不可直接將本文件視為既有建置器輸入。

本次僅檢查檔案與metadata，未查詢資料庫、未執行來源SQL，未修改私銀專案。
