/*
Author : 1121329
create date :20250626
memo : 
     ROA :  總收入/AUM
     ROBA : 放款客戶總收入/LUM
*/


drop table ROA_TMP_01;
create table ROA_TMP_01
as 
select a.*,b.amt as INCOME,
       c.AUM as AUM ,
       d.ln_amt 
from PB_CUST_TMP06 a  --客戶  28470
left join  ( select cust_id,substr(yyyymmdd,1,6) yyyymm,sum(amt) amt from INCOME_TMP02 group by cust_id,substr(yyyymmdd,1,6) ) b  --收入 28470
on a.yyyymm=b.yyyymm and a.cust_id=b.cust_id
left join (select substr(yyyymmdd,1,6) yyyymm,cust_id,sum(amt) AUM from AUM_TMP02 group by cust_id,substr(yyyymmdd,1,6)) c --AUM  --28470
on a.yyyymm=c.yyyymm and a.cust_id=c.cust_id
left join 
        ( 
         select yyyymm,cust_id,sum(ln_amt) ln_amt
         from 
         (
           SELECT yyyymm,cust_id,ln_bal ln_amt  FROM 台幣放款_私銀
           UNION 
           SELECT yyyymm,cust_id,bal_amt ln_amt  FROM 外幣放款_私銀
           UNION
           SELECT to_number(TO_CHAR(SYSDATE-1, 'YYYYMM')) YYYYMM,cust_id,ln_bal ln_amt  FROM 台幣放款_私銀CURRENT
           UNION 
           SELECT to_number(TO_CHAR(SYSDATE-1, 'YYYYMM')) YYYYMM, CUST_ID,bal_amt ln_amt FROM 外幣放款_私銀CURRENT
          ) a
         group by yyyymm,cust_id
          ) d
  on a.yyyymm=d.yyyymm and a.cust_id=d.cust_id;
  
  

drop table ROA_TMP;
create table ROA_TMP
as 
select yyyymm,sht_sub_nm,loan_flg,quota_flg,sum(income) income,sum(aum) aum,sum(ln_amt) ln_amt
from ROA_TMP_01
group by yyyymm,sht_sub_nm,loan_flg,quota_flg;

EXIT;