/*
Author : 1121329
create date :20250626
memo : AUM彙整指標
*/

drop table AUM;
create table AUM
as
select    
    TYP,
    '銀行'  COMP,
    DETAIL as PROD,
    TYP_SUB_DTL,
    cust_id,
    LST_MTN_DT AS YYYYMMDD,
    存款AUM AMT
from AUM_005_007_008_009  --存款AUM 總量、台幣存款AUM總量、結構型
where DETAIL is not null
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '保險'  PROD,
    NULL AS TYP_SUB_DTL,
    CUST_ID,
    YYYYMMDD,
    amt 
FROM aum_012  --【銀行】保險_原始投資金額
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '保險'  PROD,
    NULL AS TYP_SUB_DTL,
    CUST_ID,
    YYYYMMDD,
    amt 
FROM aum_012
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    trustprd PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    CurrentTWDValue as AMT
from AUM_013_015_015_016_017_018
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '海外債券(自營)' PROD,
    NULL AS TYP_SUB_DTL,
    cust_id ,
    YYYYMMDD,
    amt 
from  AUM_019 --19.銀行_外國債券(自營平台)_AUM總量
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '規劃型信託' PROD,
    NULL AS TYP_SUB_DTL,
    cust_id ,
    yyyymmdd,
    amt 
from  AUM_020 --銀行_規劃型信託_AUM總量
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '規劃型信託' PROD,
    NULL AS TYP_SUB_DTL,
    cust_id ,
    yyyymmdd,
    amt 
from  AUM_021 --銀行_規劃型信託_AUM總量--【銀行】股票及金錢信託_市值
union 
select 
    '投資'  TYP,
    '銀行'  COMP,
    '信託保管' PROD,
    NULL AS TYP_SUB_DTL,
    cust_id ,
    yyyymmdd,
    amt 
from  AUM_022  --銀行_信託保管_AUM總量
union 
select 
    '投資'  TYP,
    '證券'  COMP,
    nm  as PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    AMT
from AUM_023_024--證券_複委託債券_AUM總量
union 
select 
    '投資'  TYP,
    '證券'  COMP,
    '基金'  as PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    AMT
from AUM_025  ----25.證券_基金_AUM總量
union 
select 
    '投資'  TYP,
    '證券'  COMP,
    '外國股票'  as PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    AMT
from AUM_026  --26.證券_外國股票_AUM總量
union 
select 
    '投資'  TYP,
    '證券'  COMP,
    '台股'  as PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    AMT
from AUM_027   --27.證券_台股_AUM總量
union 
select 
    '投資'  TYP,
    '證券'  COMP,
    '台股'  as PROD,
    NULL AS TYP_SUB_DTL,
    cust_id,
    yyyymmdd,
    AMT
from AUM_028   ----28.股票設質
;
