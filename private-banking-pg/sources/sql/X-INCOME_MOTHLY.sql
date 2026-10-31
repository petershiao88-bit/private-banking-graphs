/*
AUTHOR : 1121329
MEMO :手續費收入、利息收入
    已將此段改寫，放回每日執行項目
*/

--66 存款利收總量
drop table INCOME_066_TMP_DETAIL_01;
create table INCOME_066_TMP_DETAIL_01
as 
SELECT cust_id,yyyymm || '01'  yyyymmdd, sum(GROSS_INCM)  AMT --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 利息 
FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
where  YYYYMM=to_char(add_months(sysdate,-1),'yyyymm')
group by cust_id,yyyymm;

drop table INCOME_066_TMP_DETAIL_02;
create table INCOME_066_TMP_DETAIL_02
as 
SELECT cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT --* --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
WHERE  YYYYMM=to_char(add_months(sysdate,-1),'yyyymm')
group by cust_id,yyyymm;

drop table INCOME_066_TMP_DETAIL_03;
create table INCOME_066_TMP_DETAIL_03
as 
SELECT  cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT-- TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 
FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
WHERE YYYYMM=to_char(add_months(sysdate,-1),'yyyymm')
group by cust_id,yyyymm;

drop table INCOME_066_TMP_DETAIL_04;
create table INCOME_066_TMP_DETAIL_04
as
     SELECT cust_id,yyyymmdd,sum(AMT) AMT
     FROM (
          select * from  INCOME_066_TMP_DETAIL_01
          union 
          select * from  INCOME_066_TMP_DETAIL_02
          union 
          select * from  INCOME_066_TMP_DETAIL_03     
        )  a 
GROUP BY cust_id,yyyymmdd;

delete  from INCOME_066 where substr(yyyymmdd,1,6) =to_char(add_months(sysdate,-1),'yyyymm');
commit ; 
insert into INCOME_066
select * from INCOME_066_TMP_DETAIL_04 ;
commit ; 

--67 放款利收總量

--INCOME_067

drop table INCOME_067_TMP_DETAIL_01;
create table INCOME_067_TMP_DETAIL_01
as 
SELECT cust_id, yyyymm ||'01'  as yyyymmdd,sum(GROSS_INCM) AMT  -- ACC_CD, SUM(LN_BAL), SUM(GROSS_INCM) FROM (
FROM DSLON.LN_NT_ACCT_HS@anadbp01_dwdbp01 A
WHERE  YYYYMM=to_char(add_months(sysdate,-1),'yyyymm')
group by cust_id,yyyymm;

drop table INCOME_067_TMP_DETAIL_02;
create table INCOME_067_TMP_DETAIL_02
as 
SELECT cust_id, yyyymm || '01' as yyyymmdd, sum(INT_INCM - CB_INT_AMT) AMT --ACC_CD, BAL_AMT, 
FROM DSLON.LN_FN_ACCT_HS@anadbp01_dwdbp01 A
WHERE YYYYMM=to_char(add_months(sysdate,-1),'yyyymm')
group by cust_id,yyyymm;

drop table INCOME_067_TMP_DETAIL_03;
create table INCOME_067_TMP_DETAIL_03
as
select cust_id,yyyymmdd,sum(AMT) AMT
from 
(
   select * from INCOME_067_TMP_DETAIL_01
    UNION ALL
    select * from INCOME_067_TMP_DETAIL_02
)  a 
GROUP BY cust_id,yyyymmdd;

delete  from INCOME_067 where substr(yyyymmdd,1,6) =to_char(add_months(sysdate,-1),'yyyymm');
commit ; 

insert into INCOME_067
select * from INCOME_067_TMP_DETAIL_03 ;
commit ; 
