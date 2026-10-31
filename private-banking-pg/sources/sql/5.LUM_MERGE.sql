/*
Author : 1121619
create date :20250626
memo : LUM 彙整歷史資料與CURRENT 資料
*/
--彙總----------------------------------------------------------------------------------------------
--彙總----------------------------------------------------------------------------------------------
--彙總----------------------------------------------------------------------------------------------
--彙總----------------------------------------------------------------------------------------------
DROP TABLE 放款餘額_私銀 PURGE;
--放款餘額
CREATE TABLE 放款餘額_私銀 AS
SELECT YYYYMMDD
, CASE WHEN PRFT_CNTR_CD IN ('2E3000', '2E3100', '2E3200', '2E3500', '2E3600', '2E3800') THEN '私人銀行一部'
       WHEN PRFT_CNTR_CD IN ('2E3300', '2E3400', '2E3700', '2E3900') THEN '私人銀行二部' ELSE PRFT_CNTR_CD END 組織
, 類型
, CASE WHEN 會科 = '1313' THEN '短期放款' 
       WHEN 會科 = '1322' THEN '短期擔保放款' 
       WHEN 會科 = '1331' THEN '中期放款' 
       WHEN 會科 = '1341' THEN '中期擔保放款' 
       WHEN 會科 = '1886' THEN '應付保證' ELSE 會科 END 會科
, SUM(餘額) 餘額
, SUM(有餘額人數) 有餘額人數
FROM (
  SELECT TO_CHAR(LAST_DAY(TO_DATE(A.YYYYMM, 'YYYYMM')), 'YYYYMMDD') YYYYMMDD, 
  A.PRFT_CNTR_CD, 類型, ACC_CD 會科, SUM(LN_BAL) 餘額, COUNT(DISTINCT A.CUST_ID) 有餘額人數 
  FROM (
    SELECT * FROM 私銀客戶
  ) A INNER JOIN (
      SELECT YYYYMM, CUST_ID, ACC_CD, '臺幣' 類型, PRFT_CNTR_CD, LN_BAL FROM 台幣放款_私銀
      UNION ALL
      SELECT YYYYMM, CUST_ID, ACC_CD, '外幣' 類型, PRFT_CNTR_CD, BAL_AMT FROM 外幣放款_私銀
  ) B ON A.CUST_ID = B.CUST_ID AND A.YYYYMM = B.YYYYMM
  GROUP BY TO_CHAR(LAST_DAY(TO_DATE(A.YYYYMM, 'YYYYMM')), 'YYYYMMDD'), A.PRFT_CNTR_CD, 類型, ACC_CD
  UNION ALL
  SELECT TO_CHAR(SYSDATE-1, 'YYYYMMDD') YYYYMMDD, A.PRFT_CNTR_CD, 類型, ACC_CD 會科, SUM(LN_BAL) 餘額, COUNT(DISTINCT A.CUST_ID) 有餘額人數 FROM (
    SELECT * FROM 私銀客戶CURRENT
  ) A INNER JOIN (
      SELECT CUST_ID, ACC_CD, '臺幣' 類型, PRFT_CNTR_CD, LN_BAL FROM 台幣放款_私銀CURRENT
      UNION ALL
      SELECT CUST_ID, ACC_CD, '外幣' 類型, PRFT_CNTR_CD, BAL_AMT FROM 外幣放款_私銀CURRENT
  ) B ON A.CUST_ID = B.CUST_ID
  GROUP BY TO_CHAR(SYSDATE-1, 'YYYYMMDD'), A.PRFT_CNTR_CD, 類型, ACC_CD
)
GROUP BY YYYYMMDD
, CASE WHEN PRFT_CNTR_CD IN ('2E3000', '2E3100', '2E3200', '2E3500', '2E3600', '2E3800') THEN '私人銀行一部'
       WHEN PRFT_CNTR_CD IN ('2E3300', '2E3400', '2E3700', '2E3900') THEN '私人銀行二部' ELSE PRFT_CNTR_CD END
, 類型
, CASE WHEN 會科 = '1313' THEN '短期放款' 
       WHEN 會科 = '1322' THEN '短期擔保放款' 
       WHEN 會科 = '1331' THEN '中期放款' 
       WHEN 會科 = '1341' THEN '中期擔保放款' 
       WHEN 會科 = '1886' THEN '應付保證' ELSE 會科 END
;

drop table 放款額度_私銀;
--放款額度
CREATE TABLE 放款額度_私銀 AS 
SELECT A.*, B.餘額 FROM (
  SELECT YYYYMMDD
  , CASE WHEN PRFT_CNTR_CD IN ('2E3000', '2E3100', '2E3200', '2E3500', '2E3600', '2E3800') THEN '私人銀行一部'
         WHEN PRFT_CNTR_CD IN ('2E3300', '2E3400', '2E3700', '2E3900') THEN '私人銀行二部' ELSE PRFT_CNTR_CD END 組織
  , SUM(放款總額度) 放款總額度
  , SUM(有額度人數) 有額度人數
  FROM (
    SELECT TO_CHAR(SYSDATE-1, 'YYYYMMDD') YYYYMMDD, A.PRFT_CNTR_CD
    , SUM(FAC_APPV_AMOUNT_TWD) 放款總額度
    , COUNT(DISTINCT CUST_ID) 有額度人數
    FROM (
      SELECT * FROM 私銀客戶CURRENT
    ) A INNER JOIN (
      SELECT DISTINCT ID_NO, FAC_APPV_CURRENCY, FAC_APPV_AMOUNT_TWD FROM 動用率_私銀CURRENT
    ) B ON A.CUST_ID = ID_NO
    GROUP BY TO_CHAR(SYSDATE-1, 'YYYYMMDD'), A.PRFT_CNTR_CD  
    UNION ALL
    SELECT  TO_CHAR(LAST_DAY(TO_DATE(A.YYYYMM, 'YYYYMM')), 'YYYYMMDD') YYYYMMDD, A.PRFT_CNTR_CD
    , SUM(FAC_APPV_AMOUNT_TWD) 放款總額度
    , COUNT(DISTINCT CUST_ID) 有額度人數
    FROM (
      SELECT * FROM 私銀客戶
    ) A INNER JOIN (
      SELECT DISTINCT  ID_NO, FAC_APPV_CURRENCY, FAC_APPV_AMOUNT_TWD FROM 動用率_私銀
    ) B ON A.CUST_ID = B.ID_NO 
    GROUP BY  TO_CHAR(LAST_DAY(TO_DATE(A.YYYYMM, 'YYYYMM')), 'YYYYMMDD'), A.PRFT_CNTR_CD 
  )
  GROUP BY YYYYMMDD
  , CASE WHEN PRFT_CNTR_CD IN ('2E3000', '2E3100', '2E3200', '2E3500', '2E3600', '2E3800') THEN '私人銀行一部'
         WHEN PRFT_CNTR_CD IN ('2E3300', '2E3400', '2E3700', '2E3900') THEN '私人銀行二部' ELSE PRFT_CNTR_CD END
) A LEFT JOIN (
  SELECT YYYYMMDD, 組織, SUM(餘額) 餘額 FROM 放款餘額_私銀
  GROUP BY YYYYMMDD, 組織
) B ON A.YYYYMMDD = B.YYYYMMDD AND A.組織 = B.組織
;
EXIT;







