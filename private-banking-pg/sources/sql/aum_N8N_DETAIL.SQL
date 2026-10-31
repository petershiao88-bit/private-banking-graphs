/*
Author : 1121329
create date :20250626
memo : AUM細項指標
*/
/*  
--9.8.7.5.實際: 存款 AUM總量
--歷史存款資料執行較久，將歷史資料一次性CREATE 後(執行時間為2025/5)，後續再與現況UNION，可減少重新執行時間，
drop table AUM_005_007_008_009_TMP01;
create table AUM_005_007_008_009_TMP01
as  
    SELECT  cust_id,LST_MTN_DT,'存款' as TYP,'台幣' AS TYP_DTL,
            case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
             TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, sum(BAL_AMT) as 存款AUM 
    FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
    WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400')   
        AND LST_MTN_DT>='20231201'
    group by cust_id,LST_MTN_DT,TRIM(PRFT_CNTR_CD), ACT_CD,
          case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end;

drop table AUM_005_007_008_009_TMP02;
create table AUM_005_007_008_009_TMP02
as              
    SELECT  cust_Id,LST_MTN_DT,'存款' as TYP,'台幣' AS TYP_DTL, 
            case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
            TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACC_CD, sum(AVAIL_BAL) as 存款AUM --  '台幣'  AS TYP,TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
    FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
    WHERE TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400')   AND LST_MTN_DT>='20231201'
    group by cust_id,lst_MTN_DT,TRIM(PRFT_CNTR_CD), ACC_CD,
          case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end ;
             
drop table AUM_005_007_008_009_TMP03;
create table AUM_005_007_008_009_TMP03
as     
    SELECT cust_Id,LST_MTN_DT,'存款' as TYP,'外幣' AS TYP_DTL,
            case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
             TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, sum(BAL_AMT) as 存款AUM --, GROSS_INCM 
    FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
    WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND LST_MTN_DT>='20231201'
    group by cust_Id,LST_MTN_DT,TRIM(PRFT_CNTR_CD), ACT_CD
;
*/
--current
drop table AUM_005_007_008_009_TMP04;
create table AUM_005_007_008_009_TMP04
as  
    SELECT  cust_id,DATA_DT,'存款' as TYP,'台幣' AS TYP_DTL,
             case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
            TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, sum(BAL_AMT) as AMT 
    FROM DSDEP.DEP_NT_ACCT@anadbp01_dwdbp01 
    group by cust_id,DATA_DT,TRIM(PRFT_CNTR_CD), ACT_CD,
             case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end   
;
drop table AUM_005_007_008_009_TMP05;
create table AUM_005_007_008_009_TMP05
as 
    SELECT  cust_Id,LST_MTN_DT,'存款' as TYP,'台幣' AS TYP_DTL,
            case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
            TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACC_CD, sum(AVAIL_BAL) as 存款AUM--  '台幣'  AS TYP,TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
    FROM DSDEP.DEP_FN_ACCT@anadbp01_dwdbp01
    group by cust_Id,LST_MTN_DT,TRIM(PRFT_CNTR_CD), ACC_CD,
          case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end;
--更新區間　2025/6後
drop table AUM_005_007_008_009_TMP06;
create table AUM_005_007_008_009_TMP06
as  
    SELECT  cust_id,LST_MTN_DT,'存款' as TYP,'台幣' AS TYP_DTL,
            case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
             TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, sum(BAL_AMT) as 存款AUM 
    FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
    WHERE   YYYYMM>='202506'
    group by cust_id,LST_MTN_DT,TRIM(PRFT_CNTR_CD), ACT_CD,
          case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end;

drop table AUM_005_007_008_009_TMP07;
create table AUM_005_007_008_009_TMP07
as              
    SELECT  cust_Id,LST_MTN_DT,'存款' as TYP,'台幣' AS TYP_DTL, 
            case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
            TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACC_CD, sum(AVAIL_BAL) as 存款AUM --  '台幣'  AS TYP,TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
    FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
    WHERE  YYYYMM>='202506'
    group by cust_id,lst_MTN_DT,TRIM(PRFT_CNTR_CD), ACC_CD,
          case 
              when trim(ACC_CD) IN ('2317','2327') then '外幣存款'
              when trim(ACC_CD) IN ('2545') then '結構型存款'
             end ;
             
drop table AUM_005_007_008_009_TMP08;
create table AUM_005_007_008_009_TMP08
as     
    SELECT cust_Id,LST_MTN_DT,'存款' as TYP,'外幣' AS TYP_DTL,
            case 
              when trim(ACT_CD) IN ('2311','2321','2322','2331','2332','2333','2335','2336') then '台幣存款'
              when trim(ACT_CD) IN ('2545') then '結構型存款'
             end as DETAIL,
             TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, sum(BAL_AMT) as 存款AUM --, GROSS_INCM 
    FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
    WHERE   YYYYMM>='202506'
    group by cust_Id,LST_MTN_DT,TRIM(PRFT_CNTR_CD), ACT_CD
;


drop table AUM_005_007_008_009;
create table AUM_005_007_008_009
as
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP01 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP02 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP03 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP04 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP05 a 
union
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP06 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP07 a 
union 
select  a.*,
        case when detail in ('台幣存款','外幣存款') then '台外幣存款' 
        else detail end as TYP_SUB_DTL
from AUM_005_007_008_009_TMP08 a 
;

---12.銀行_保險_AUM總量
--AUM資料為月批(至上個月)，當月資料須抓取最後一個月的資料值
drop table AUM_012_TMP01;
create table AUM_012_TMP01
as  
select orgcust_key as cust_id ,date_key as YYYYMMDD ,sum(AMT_INVEST) AMT
from DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT@anadbp01_dwdbp01
group by orgcust_key,date_key;

drop table AUM_012_TMP02;
create table AUM_012_TMP02
as  
select orgcust_key as cust_id ,to_char(sysdate-1,'yyyymmdd') as YYYYMMDD ,sum(AMT_INVEST) AMT
from DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT@anadbp01_dwdbp01
where date_key =
       (select  max(date_key) date_key from DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT@anadbp01_dwdbp01 ) 
group by orgcust_key,to_char(sysdate,'yyyymmdd');

drop table AUM_012;
create table AUM_012
as
select * from AUM_012_TMP01
union 
select * from AUM_012_TMP02;


/*以下皆為投資AUM*/
-- 13-18.投資AUM各細項產品
drop table AUM_013_015_015_016_017_018;
create table AUM_013_015_015_016_017_018
as 
select 
    idno cust_id,to_char(exedate,'yyyymmdd') yyyymmdd,PCCCODE,idno,
    case 
       when trustprd in ('其他-國外有價證券','其他-國外股票','股票') then '海外股票'
       when trustprd ='集合' then '集合管理帳戶'
       when trustprd ='海外債券' then '海外債券(信託)'
       when trustprd ='結構型商品' then '境外結構型商品'
    else trustprd end as trustprd,
    sum(CurrentTWDValue) CurrentTWDValue    
from DSFND.PB_FUND_MONTH@anadbp01_dwdbp01
group by  idno,to_char(exedate,'yyyymmdd') ,PCCCODE,idno,case 
       when trustprd in ('其他-國外有價證券','其他-國外股票','股票') then '海外股票'
       when trustprd ='集合' then '集合管理帳戶'
       when trustprd ='海外債券' then '海外債券(信託)'
       when trustprd ='結構型商品' then '境外結構型商品'
    else trustprd end;
    
--19.銀行_外國債券(自營平台)_AUM總量
drop table AUM_019_TMP_01;
create table AUM_019_TMP_01
as 
select CIF_ID AS CUST_ID,Data_dt as YYYYMMDD,sum(STO_AMT * MKT_PRI /100 * EXC_RATE) AMT
from DSWTR.BOND_POS_DAY@anadbp01_dwdbp01
where pcc_code like '2E%'
group by CIF_ID,Data_dt;

drop table AUM_019;
create table AUM_019
as 
select a.*
from AUM_019_TMP_01 a 
inner join 
(
  select substr(yyyymmdd,1,6) yyyymm ,max(yyyymmdd) yyyymmdd 
  from AUM_019_TMP_01
  group by substr(yyyymmdd,1,6)
 ) b on a.yyyymmdd=b.yyyymmdd;


--20.【銀行】員工福利信託_市值
drop table AUM_020_TMP01;
create table AUM_020_TMP01
as
select to_char(baldate,'yyyymmdd') yyyymmdd,idno as cust_id ,sum(PresentAmt) AMT
from DSEBS.EBTS_ACT_CntAUMBal_PB@anadbp01_dwdbp01
group by to_char(baldate,'yyyymmdd'),idno;

drop table AUM_020;
create table AUM_020
as
select a.yyyymmdd,a.cust_id,a.AMT
from AUM_020_TMP01 a
inner join 
  (
  select   substr(yyyymmdd,1,6) yyyymm,max(yyyymmdd) yyyymmdd
  from AUM_020_TMP01
  group by substr(yyyymmdd,1,6)
  ) b
on a.yyyymmdd=b.yyyymmdd;

--21.【銀行】股票及金錢信託_市值
drop table AUM_021_TMP01;
create table AUM_021_TMP01
as
select substr(postdate,1,8) yyyymmdd,id as cust_Id ,sum( MarketValueTWD)  AMT
from  DSTAM.TRUCONTRACT_PB@anadbp01_dwdbp01
group by substr(postdate,1,8),id;

drop table AUM_021;
create table AUM_021
as
select a.yyyymmdd,a.cust_id,a.AMT
from AUM_021_TMP01 a
inner join 
  (
  select   substr(yyyymmdd,1,6) yyyymm,max(yyyymmdd) yyyymmdd
  from AUM_021_TMP01
  group by substr(yyyymmdd,1,6)
  ) b
on a.yyyymmdd=b.yyyymmdd;
--22.銀行_信託保管_AUM總量
drop table AUM_022_TMP01;
create table AUM_022_TMP01
as
select cust_Id,"DATE" as YYYYMMDD,sum(AUM) as AMT
from DSPMS.PB_PMS_AUM@anadbp01_dwdbp01
group by cust_id,"DATE";

drop table AUM_022;
create table AUM_022
as
select a.yyyymmdd,a.cust_id,a.AMT
from AUM_022_TMP01 a
inner join 
  (
  select   substr(yyyymmdd,1,6) yyyymm,max(yyyymmdd) yyyymmdd
  from AUM_022_TMP01
  group by substr(yyyymmdd,1,6)
  ) b
on a.yyyymmdd=b.yyyymmdd;

--23.24.【證券】複委託-債券_市值
--23.證券_複委託債券_AUM總量 1. BOND 開頭非「TSSN」 2.取值 NETQTY/100 *CPRICE * 折台清算匯率
--24.證券_複委託結構型商品_AUM總量 1. BOND 開頭為「TSSN」 2.取值 NETQTY/100 *CPRICE * 折台清算匯率 
--證券資料要抓取上個月月底匯率
drop table AUM_023_024_TMP0;
create table AUM_023_024_TMP0
as 
select idno as cust_id,prcs_dt as yyyymmdd,nm,sum(NETQTY/100 *CPRICE * exch_rt) AMT
from 
      (select a.*,
              case when  bond like 'TSSN%' then '複委託結構型商品'
              else '複委託債券' end as NM
      from  DSPBM.PB_BONDPOS_SEC_M@anadbp01_dwdbp01 a ) a
left join 
     ( select A.*
     from dsdep.fn_exch_rt@anadbp01_dwdbp01 a
     inner join 
     ( 
         select substr(prcs_dt,1,6) yyyyymm,max(prcs_dt) prcs_dt 
         from dsdep.fn_exch_rt@anadbp01_dwdbp01 
         group by substr(prcs_dt,1,6)
     ) b on a.prcs_dt=b.prcs_dt
     )b  on a.currency=b.curr_cd and a.yyyymm=substr(b.prcs_dt,1,6)
group by idno,prcs_dt,nm
;
drop table AUM_023_024_TMP1;
create table AUM_023_024_TMP1
as 
select  idno as cust_id,clrdate as yyyymmdd,nm,sum(NETQTY/100 *CPRICE * exch_rt) AMT
from 
(
 select a.*,b.*,
         case when  bond like 'TSSN%' then '複委託結構型商品'
       else '複委託債券' end as NM
from  DSPBM.PB_BONDPOS_SEC@anadbp01_dwdbp01 a 
left join  dsdep.fn_exch_rt@anadbp01_dwdbp01  b 
on a.clrdate=b.prcs_dt and  a.currency=b.curr_cd
) a 
group by idno,clrdate,nm;

drop table AUM_023_024;
create table AUM_023_024
as 
select * from AUM_023_024_TMP0
union 
select * from AUM_023_024_TMP1;

--current現況 select * from DSPBM.PB_BONDPOS_SEC@anadbp01_dwdbp01
  --25.證券_基金_AUM總量
drop table AUM_025;
create table AUM_025
  as 
  select wkb02 as cust_id,yyyymmdd ,sum(WKB28 * WKB23 * WKB31) as amt
  from DSPBM.PB_FUNDPOSIT_SEC_M@anadbp01_dwdbp01
  group by wkb02,yyyymmdd
  union 
  select wkb02 as cust_id,yyyymmdd ,sum(WKB28* WKB23 * WKB31) as amt
  from DSPBM.PB_FUNDPOSIT_SEC@anadbp01_dwdbp01
  group by wkb02,yyyymmdd
  ;
    --26.證券_外國股票_AUM總量
drop table AUM_026_TMP0;
create table AUM_026_TMP0
as 
select   idno as cust_id,b.prcs_dt yyyymmdd,sum(NETQTY * CPRICE* exch_rt) as amt 
from  (select *
      from  DSPBM.PB_STOCKPOS_SEC_M@anadbp01_dwdbp01 a ) a
left join 
     ( select A.*
     from dsdep.fn_exch_rt@anadbp01_dwdbp01 a
     inner join 
     ( 
         select substr(prcs_dt,1,6) yyyyymm,max(prcs_dt) prcs_dt 
         from dsdep.fn_exch_rt@anadbp01_dwdbp01 
         group by substr(prcs_dt,1,6)
     ) b on a.prcs_dt=b.prcs_dt
     )b  on a.currency=b.curr_cd and a.yyyymm=substr(b.prcs_dt,1,6)
group by idno,b.prcs_dt
;    

drop table AUM_026_TMP1;
create table AUM_026_TMP1
as 
select  idno as cust_id,yyyymmdd,sum(NETQTY * CPRICE* exch_rt) as amt 
  from 
 (
  select idno, CLRDATE  YYYYMMDD,NETQTY ,CPRICE,currency --
  from DSPBM.PB_STOCKPOS_SEC@anadbp01_dwdbp01
  ) a
  left join 
  (
  select * from dsdep.fn_exch_rt@anadbp01_dwdbp01 --where prcs_dt='20240401'
  )b  on a.currency=b.curr_cd and yyyymmdd=prcs_dt
  group by idno,yyyymmdd;
 
drop table AUM_026;
create table AUM_026
as 
select * from AUM_026_TMP0
union 
select * from AUM_026_TMP1;

--27.證券_台股_AUM總量
drop table AUM_027;
create table AUM_027
as 
select cust_id,yyyymmdd,sum(amt) amt
from 
(
select YTRMRB025 as cust_id,yyyymmdd,YTRMRB110 * YTRMRB150  as amt
from dspbm.pb_ytrmrbp_sec_m@anadbp01_dwdbp01
union 
select YTRMRB025 as cust_id,yyyymmdd,YTRMRB110 * YTRMRB150  as amt
from dspbm.pb_ytrmrbp_sec@anadbp01_dwdbp01
) a
group by cust_id,yyyymmdd;
--28.股票設質
drop table AUM_028;
create table AUM_028
as 
select to_char(to_date(applydate,'yyyy/mm/dd'),'YYYYMMDD') YYYYMMDD ,lendinguserid as cust_id,sum(Qty * Product_Price) amt
from DSCSD.PBCMS_REPORTA03@anadbp01_dwdbp01
group by to_char(to_date(applydate,'yyyy/mm/dd'),'YYYYMMDD') ,lendinguserid;

EXIT;

