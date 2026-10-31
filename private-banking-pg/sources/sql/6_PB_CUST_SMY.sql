/*
Author : 1121329
create date :20250626
memo : 私銀客戶數狀態
*/

--6.已開PB總客戶數
drop table PB_CUST_006_TMP;
create table PB_CUST_006_TMP
as 
select distinct yyyymm,customer_id
from (
     select yyyymm,cif_cust_info_seq  
     from  DSWBS.DEP_ACC_hs@anadbp01_dwdbp01 
     where  Case_status='01' and Sub_code='0002' 
     union 
     select to_number(to_char(sysdate,'YYYYMM'))  yyyymm,cif_cust_info_seq
     from  DSWBS.DEP_ACC@anadbp01_dwdbp01 
     where  Case_status='01' and Sub_code='0002' 
) a 
inner join DSWBS.CIF_CUST_INFO@anadbp01_dwdbp01 b
on a.cif_cust_info_seq=b.cif_cust_info_seq;


drop table PB_CUST_006;
create table PB_CUST_006
as 
select
       a.*,
       case when b.customer_id  is not null then '已開PB帳戶' else '未開PB帳戶' end as PB_FLG
from PB_CUST_005 a 
left join PB_CUST_006_TMP b
on a.cust_id=b.customer_id and a.yyyymm=b.yyyymm;

drop table PB_CUST_006;
create table PB_CUST_006
as 
select
       a.*,
       case when b.customer_id  is not null then '已開PB帳戶' else '未開PB帳戶' end as PB_FLG
from PB_CUST_005 a 
left join PB_CUST_006_TMP b
on a.cust_id=b.customer_id and a.yyyymm=b.yyyymm;

--7-10 客戶數 、Organic 客戶數、Migration 客戶數、轉介 客戶數

--12.OBU 總客戶數 、12.DBU 客戶數
--該程式執行較久，先建立起來後續UNION

/*
drop table PB_CUST_012_TMP01;
create table PB_CUST_012_TMP01
as 
select distinct 
yyyymm,acct_no,cust_id,
case 
         when  TRIM(DBU_OBU_FLG)=2 then 'OBU'
         else 'DBU'  end as FLG
from dsdep.dep_fn_acct_hs@anadbp01_dwdbp01 
where YYYYMM>='202312' and  YYYYMM<='202505';
*/
drop table PB_CUST_012_TMP02;
create table PB_CUST_012_TMP02
as 
select distinct 
yyyymm,acct_no,cust_id,
case 
         when  TRIM(DBU_OBU_FLG)=2 then 'OBU'
         else 'DBU'  end as FLG
from dsdep.dep_fn_acct_hs@anadbp01_dwdbp01 
where YYYYMM>='202505';

drop table PB_CUST_012_TMP03;
create table PB_CUST_012_TMP03
as 
select distinct 
to_number(to_char(sysdate,'YYYYMM')) YYYYMM,acct_no,cust_id,
case 
         when  TRIM(DBU_OBU_FLG)=2 then 'OBU'
         else 'DBU'  end as FLG
from dsdep.dep_fn_acct@anadbp01_dwdbp01 ;

drop table PB_CUST_012;
create table PB_CUST_012
as
select * from PB_CUST_012_TMP01
union
select * from PB_CUST_012_TMP02
union 
select * from PB_CUST_012_TMP03;

drop table PB_CUST_TMP01;
create table PB_CUST_TMP01
as 
select
     a.*,
     case when b.FLG='OBU' then 'OBU' else 'DBU' end as FLG 
from PB_CUST_006 a 
left join (select distinct  cust_id,yyyymm,FLG
            from PB_CUST_012) b
on a.cust_id=b.cust_id  and a.yyyymm=b.yyyymm;

--11.參考AUM大表
drop table PB_CUST_011;
create table PB_CUST_011
as 
select cust_id,substr(yyyymmdd,1,6) yyyymm,sum(AMT) AMT
from AUM_TMP02
group by cust_id,substr(yyyymmdd,1,6);


drop table PB_CUST_TMP02;
create table PB_CUST_TMP02
as 
select a.*,
       case when b.amt>=30000000 then '3千萬以上'
       else '3千萬以下' end as ASSET,
       case 
            when b.amt>=100000000 then '1億'
            when b.amt>=50000000 then '5千萬'
            when b.amt>=30000000 then '3千萬'
       else '3千萬以下' end as ASSET_SUB
from PB_CUST_TMP01 a
left join PB_CUST_011 b on a.cust_id=b.cust_id and a.yyyymm=b.yyyymm;

/*  
--PB Organic、Migration、轉介 狀態私銀會提供檔案人工上傳
drop table PB_CUST_STS;
create table PB_CUST_STS
as 
select YYYYMMDD,FLG,隱碼　as cust_id from PB_CUST_202505;
insert into PB_CUST_STS
select cust_id,yyyymm,STS_FLG 
from PB_CUST_202509;
commit;
select yyyymmdd,count(*) from PB_CUST_STS  group by yyyymmdd;
*/


drop table PB_CUST_TMP03;
create table PB_CUST_TMP03
as 
select a.*,
       b.flg as STS_FLG
from PB_CUST_TMP02 a
left join PB_CUST_STS b on a.cust_id=b.cust_id and a.yyyymm = substr(b.yyyymmdd,1,6) 
;

      -- select * from PB_CUST
EXIT;
