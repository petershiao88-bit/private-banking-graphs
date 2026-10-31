/*
Author : 1121329
create date :20250626
memo : 客戶動用LUM 狀況，計算LUM  客戶數漏斗圖
儀表盤頁籤：LUM
*/

--放款
drop table PB_CUST_TMP04;
create table PB_CUST_TMP04
as 
 SELECT YYYYMM, CUST_ID FROM 台幣放款_私銀
 UNION 
 SELECT YYYYMM, CUST_ID FROM 外幣放款_私銀
 UNION
 SELECT to_number(TO_CHAR(SYSDATE-1, 'YYYYMM')) YYYYMM, CUST_ID   FROM 台幣放款_私銀CURRENT
 UNION 
 SELECT to_number(TO_CHAR(SYSDATE-1, 'YYYYMM')) YYYYMM, CUST_ID FROM 外幣放款_私銀CURRENT;

drop table PB_CUST_TMP05;
create table PB_CUST_TMP05
as 
SELECT  A.*,
        CASE WHEN B.CUST_ID IS NOT NULL THEN 1 else 0 end as LOAN_FLG
FROM PB_CUST_TMP03 A --客戶狀態  --28470
LEFT JOIN PB_CUST_TMP04 b --放款   --28470
ON A.CUST_ID=B.CUST_ID AND A.YYYYMM=B.YYYYMM;
      
--有額度
drop table PB_CUST_TMP06;
create table PB_CUST_TMP06
as      
SELECT a.*,
       case when b.id_no is not null then 1 else 0 end as QUOTA_FLG
from PB_CUST_TMP05 a --28470
left join (
          select  id_no,min(fac_node_create_date) fac_node_create_date ,max(fac_expiry_date)  fac_expiry_date
      from  DSWBS.V_FAC_main@anadbp01_dwdbp01 where fac_node_create_date>='20230101'
      group by id_no
          ) b   --28470
on a.cust_id=b.id_no and a.yyyymm >= substr(b.fac_node_create_date,1,6) and a.yyyymm<= substr(b.fac_expiry_date,1,6);

drop table PB_CUST;
create table PB_CUST
as 
select yyyymm,
       emp_no,
       sht_nm,
        '私人銀行'||sht_sub_nm as sht_sub_nm,
       pb_flg,
       ASSET,
       ASSET_SUB,
       flg as Obu_flg,
       STS_FLG,
       count(*) CNT,
       sum(QUOTA_FLG) QUOTA_FLG,
       sum(LOAN_FLG) LOAN_FLG
from PB_CUST_TMP06 a 
group by yyyymm,
       emp_no,
       sht_nm,
       sht_sub_nm,
       pb_flg,
       flg ,
       ASSET,
       ASSET_SUB,
       STS_FLG;
       
EXIT;       
