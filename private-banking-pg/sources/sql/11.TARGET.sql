/*
目標達成率彙整表
目標:
  客戶數 : PB客戶數
  AUM : 投資AUM 、存款AUM 、總AUM 
  LUM : 
  收入: 手收、利收、總收入
日期 : 20250603
*/

drop table PB_TAR_TMP_01;
create table PB_TAR_TMP_01
as
select 
       4 AS ORD
       ,'投資AUM' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , AUM_INVEST  TARGET
       , AMT ACTUAL
       , AMT/AUM_INVEST as RATIO
 from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,typ,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
       from AUM_REPORT
      where TYP='投資'
      group by yyyymm,typ,
      sht_sub_nm) b on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);
--  select * from PB_TAR_TMP_01
-- 存款AUM AUM_DEPOSIT
drop table PB_TAR_TMP_02;
create table PB_TAR_TMP_02
as
select 
       5 AS ORD
       ,'存款AUM' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , AUM_DEPOSIT  TARGET
       , AMT ACTUAL
       , AMT/AUM_DEPOSIT as RATIO
 from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,typ,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
       from AUM_REPORT
      where TYP='存款'
      group by yyyymm,typ,
      sht_sub_nm) b on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);   
--  總AUM   
drop table PB_TAR_TMP_03;
create table PB_TAR_TMP_03
as
select 
       6 AS NUM
       ,'總AUM' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , AUM_TOTAL  TARGET
       , AMT ACTUAL
       , AMT/AUM_TOTAL as RATIO
 from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
      from AUM_REPORT
      group by yyyymm,
      sht_sub_nm) b on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);     

---- 總收入  INCOME_TOTAL
drop table PB_TAR_TMP_04;
create table PB_TAR_TMP_04
as
select 
       3 AS ORD
       ,'總收入' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , INCOME_TOTAL  TARGET
       , AMT ACTUAL
       , AMT/INCOME_TOTAL as RATIO
 from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
      from INCOME_REPORT
      group by yyyymm,
      sht_sub_nm) b on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);    
      
----  手收  INCOME_FEE      
drop table PB_TAR_TMP_05;
create table PB_TAR_TMP_05
as
select 
       1 AS ORD
       ,'手收' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , INCOME_FEE  TARGET
       , AMT ACTUAL
       , AMT/INCOME_FEE as RATIO
from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
      from INCOME_REPORT
      where typ='手收'
      group by yyyymm,
      sht_sub_nm) b 
 on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);         

-- 利收 INCOMW_INTEREST
drop table PB_TAR_TMP_06;
create table PB_TAR_TMP_06
as
select 
       2 AS ORD
       ,'利收' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , INCOME_INTEREST  TARGET
       , AMT ACTUAL
       , AMT/INCOME_INTEREST as RATIO
from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(AMT)  AMT 
      from INCOME_REPORT
      where typ='利收'
      group by yyyymm,
      sht_sub_nm) b 
 on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);         

--PB 客戶數 
drop table PB_TAR_TMP_07;
create table PB_TAR_TMP_07
as
select 
       8 AS ORD  
       ,'PB客戶數' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , PB_CUST_COUNT  TARGET
       , AMT ACTUAL
       , AMT/PB_CUST_COUNT as RATIO
from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select yyyymm,
       TRIM(sht_sub_nm) sht_sub_nm,
       sum(CNT)  AMT 
      from PB_CUST
      where PB_FLG='已開PB帳戶'
      group by yyyymm,
      sht_sub_nm) b 
 on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.sht_sub_nm);    
 
----LUM
drop table PB_TAR_TMP_08;
create table PB_TAR_TMP_08
as
select 
       7 AS ORD
       ,'LUM' AS NM
       , TARGET_YEAR 
       , DATA_YM
       , BU_NAME
       , LUM  TARGET
       , AMT ACTUAL
       , AMT/LUM as RATIO
from DSPBM.BU_TARGET_TW@anadbp01_dwdbp01 a 
left join 
      (select substr(YYYYMMDD,1,6) YYYYMM,組織,sum(餘額) AMT
      from 放款餘額_私銀
      group by substr(YYYYMMDD,1,6),組織) b 
 on a.DATA_YM=b.YYYYMM and TRIM(a.BU_NAME)=TRIM(b.組織);    
   
 --
drop table PB_TAR_TMP_09;
create table PB_TAR_TMP_09
as
select ord,nm,target_year, target_year || 'YTM' as DATA_YM,bu_name,sum(target) target,sum(actual) actual,sum(actual)/sum(target) ratio  
from  PB_TAR_TMP_04 --總收入
group by ord,nm,target_year, target_year || 'YTM' ,bu_name 
union 
select ord,nm,target_year, target_year || 'YTM' as DATA_YM,bu_name,sum(target) target,sum(actual) actual,sum(actual)/sum(target) ratio  
from  PB_TAR_TMP_05 --手收
group by ord,nm,target_year, target_year || 'YTM' ,bu_name 
union 
select ord,nm,target_year, target_year || 'YTM' as DATA_YM,bu_name,sum(target) target,sum(actual) actual,sum(actual)/sum(target) ratio  
from  PB_TAR_TMP_06 --利收
group by ord,nm,target_year, target_year || 'YTM' ,bu_name ;

drop table PB_TAR_TMP_10;
create table PB_TAR_TMP_10
as
select a.ord,nm,a.target_year, a.target_year || 'YTM' as DATA_YM,a.bu_name,target ,actual , ratio  
from 
(
    select * from  PB_TAR_TMP_01 --投資AUM
    union 
    select * from  PB_TAR_TMP_02 --存款AUM
    union 
    select * from  PB_TAR_TMP_03--總AUM
    union 
    select * from  PB_TAR_TMP_07 --PB客戶數
    union 
    select * from  PB_TAR_TMP_08 --LUM
) a 
inner join ( select max(DATA_YM) DATA_YM from PB_TAR_TMP_03  ) b 
on a.DATA_YM=b.DATA_YM;

 /* 暫時製作2024資料
 create table TMP_2024
as 
select ord,nm,'2024' as target_year
       ,'2024'||substr(data_ym,5,2) data_ym,bu_name
from  PB_TAR;
 */
drop table PB_TAR_01 ;
create table  PB_TAR_01
as 
select * from  PB_TAR_TMP_01 --投資AUM
union 
select * from  PB_TAR_TMP_02 --存款AUM
union 
select * from  PB_TAR_TMP_03--總AUM
union 
select * from  PB_TAR_TMP_04 --總收入
union 
select * from  PB_TAR_TMP_05 --手收
union 
select * from  PB_TAR_TMP_06 --利收
union 
select * from  PB_TAR_TMP_07 --PB客戶數
union 
select * from  PB_TAR_TMP_08 --LUM
union 
select * from PB_TAR_TMP_09  --手收、利收、總收入總計
union 
select * from PB_TAR_TMP_10
--union 
--select * from PB_TAR_01_2024
;

drop table PB_TAR_02 ;
create table  PB_TAR_02
as 
select      ord,
            nm,
            target_year,
            data_ym,bu_name,
            target,
            actual,
            ratio,
            lag(actual) over (PARTITION BY bu_name,NM order by data_ym) as LSAT_ACTUAL,
            actual - lag(actual) over (PARTITION BY bu_name,NM order by data_ym) as INCREMENTAL
from PB_TAR_01;

drop table PB_TAR_03 ;
create table  PB_TAR_03
as 
select      ord,
            nm,
            target_year,
            data_ym,bu_name,
            target,
            actual,
            ratio,
            lag(actual) over (PARTITION BY bu_name,NM order by data_ym) as LAST_ACTUAL,
            actual - lag(actual) over (PARTITION BY bu_name,NM order by data_ym) as INCREMENTAL,
            case 
               when nm like '%AUM%'  then target/1000000 
               when nm ='LUM'  then target/1000000
               when nm ='手收' then target/1000 
               when nm ='利收' then target/1000  
               when nm ='總收入' then target/1000  
            else target end as target_rpt,
            case 
               when nm like '%AUM%'  then actual/1000000 
               when nm ='LUM'  then actual/1000000
               when nm ='手收' then actual/1000 
               when nm ='利收' then actual/1000  
               when nm ='總收入' then actual/1000  
            else actual end as actual_rpt             
from PB_TAR_02;


drop table PB_TAR_04 ;
create table  PB_TAR_04
as 
select ord,nm,bu_name,avg(actual) actual
from PB_TAR_03
where target_year='2024' and nm in ('手收','利收','總收入') --收入看2024年平均
group by ord,nm,bu_name
union 
select ord,nm,bu_name,actual
from PB_TAR_03 --非收入看202412後淨增
where data_ym='202412' and nm not in ('手收','利收','總收入'); 

drop table PB_TAR;
create table  PB_TAR
as 
select a.ord,a.nm,a.target_year,a.data_ym ,a.bu_name,a.target,a.actual,a.ratio,a.last_actual,a.incremental,a.target_rpt,a.actual_rpt,
        case 
               when a.nm like '%AUM%'  then b.actual/1000000 
               when a.nm ='LUM'  then b.actual/1000000
               when a.nm ='手收' then b.actual/1000 
               when a.nm ='利收' then b.actual/1000  
               when a.nm ='總收入' then b.actual/1000  
            else b.actual end as actual_2024,  
        case 
               when a.nm like '%AUM%'  then  (a.actual-b.actual)/1000000 
               when a.nm ='LUM'  then (a.actual-b.actual)/1000000
               when a.nm ='手收' then (a.actual-b.actual)/1000 
               when a.nm ='利收' then (a.actual-b.actual)/1000  
               when a.nm ='總收入' then (a.actual-b.actual)/1000  
            else a.actual-b.actual end as ins_20205
from PB_TAR_03 a 
left join PB_TAR_04 b  ---2025年淨增
on a.ord=b.ord and a.nm=b.nm and a.bu_name=b.bu_name ;

/*
insert into PB_TAR (ord,nm,target_year,data_ym,bu_name,target,actual,ratio,last_actual,incremental,target_rpt,actual_rpt)
select * from PB_TAR_2024;
commit;
*/

grant select on INCOME_REPORT to dsvsr;
grant select on AUM_REPORT to dsvsr;
grant select on PB_TAR to dsvsr;
grant select on 放款額度_私銀 to dsvsr;
grant select on 放款餘額_私銀  to dsvsr;
grant select on PB_CUST to dsvsr;
grant select on ROA_TMP to dsvsr;



EXIT;

