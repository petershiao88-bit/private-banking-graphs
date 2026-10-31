/*
Author : 1121329
create date :20250610
memo : 
     收入各指標細項開發
*/

--28.銀行保險手收(日更新)  --COMM_AMT 僅有2025/5月Current檔案
--from dxdmb.aum_acct_ft@anadbp01_dwdbp01 
--select * from DSINS.INSU_RPT_Q01@anadbp01_dwdbp01 
drop table INCOME_028;
create table INCOME_028
as 
select dept_easy_nm,dept_easy_nm2,applicant_id as cust_id,apply_dt as yyyymmdd,sum(COMM_AMT) AMT--dept_easy_nm,dept_easy_nm2,
from DSINS.INSU_RPT_Q01@anadbp01_dwdbp01
group by dept_easy_nm,dept_easy_nm2,applicant_id,apply_dt;
--29.【銀行】保險手收 總量(月更新) --取值PS  
--20251124 調整抓取LST_MTN_DT的下一個月為收入
drop table INCOME_029;
create table INCOME_029
as 
select  cust_id ,
        to_char(add_months(to_date(lst_mtn_dt,'yyyymmdd'),1),'yyyymmdd')as  yyyymmdd,
        sum(ps) amt --,* --lst_mtn_dt,category,sum(ps) --AO_ID,CUST_ID,PS
from DSKPI.KPI_DET_IU_002_NEW@anadbp01_dwdbp01
where ps is not null
group by cust_id ,lst_mtn_dt; 

--where insure_START_DATE = '01140221'
--30.【銀行】保險手收 總量(月更新)   --取值PS
--20251124 調整抓取LST_MTN_DT的下一個月為收入
drop table INCOME_030;
create table INCOME_030
as 
select cust_id ,to_char(add_months(to_date(lst_mtn_dt,'yyyymmdd'),1),'yyyymmdd') as yyyymmdd,sum(ps) amt  -- source_name,lst_mtn_dt,sum(ps) ps,count(*) 人數 --distinct lst_mtn_dt 
from DSKPI.KPI_DET_OFI_001@anadbp01_dwdbp01
where open_account='Y'
group by cust_id ,lst_mtn_dt;
--31.【銀行】海外債券手收 總量

drop table INCOME_031;
create table INCOME_031
as 
select baopcccode as PCCODE,
       idno as cust_id ,
       to_char(to_date(feedate+19110000,'yyyymmdd'),'yyyymmdd') as yyyymmdd, 
       sum(BRHREBATEAMT+(WKR028/100)) amt--baopcccode,sum(BRHREBATEAMT+(WKR028/100)) --feedate,sum(BRHREBATEAMT+(WKR028/100))
from DSFND.PB_FUND_SPREAD_DAILY@anadbp01_dwdbp01
where FHID='CB' --and substr(feedate,1,6)='011403'--01121227    
and baopcccode like '%2E%'    --私銀處
group by baopcccode,idno,feedate;

--and BRHREBATEAMT+(WKR028/100)=416
--32.【銀行】外國債券(自營平台)手收 總量  -- INC_AMT_NT
drop table INCOME_032;
create table INCOME_032
as 
select cif_id as cust_id ,txn_dt as yyyymmdd,PCC_CODE pccode,sum(ABS(INC_AMT_NT)) amt
from DSWTR.BOND_TXN@anadbp01_dwdbp01
WHERE pcc_code LIKE '2E%'
group by cif_id,txn_dt,PCC_CODE;
--33.34.35.36【銀行】基金手收 總量
--20251124 調整新增判斷saopcccode like '2E%'
drop table INCOME_033_034_035_036;
create table INCOME_033_034_035_036
as 
select  to_char(to_date(feedate+19110000,'yyyymmdd') ,'yyyymmdd' ) as yyyymmdd --substr(FEEDATE,1,6)  -- FHID,IDNO as cust_id,      
        ,idno as cust_id       
        ,case 
              when FHID not in ('PS','CB','YB','SN') then '基金' 
              when TRIM(FHID) ='YB' then 'ETF'
              when FHID ='PS' then '海外股票'
              when FHID like 'TA%' or FHID  like 'TB%' or FHID  like 'TD%' or FHID  like 'TE%'  then '集合管理帳戶'
        end as   FH_TYP 
        ,baopcccode PCCODE
        ,sum(BrhRebateAmt) as AMT
from DSFND.PB_FUND_SPREAD_DAILY@anadbp01_dwdbp01 
where  (baopcccode like '2E%' or saopcccode like '2E%') and feedate>='011212'  --and feedate='011403' 
group by  
      to_char(to_date(feedate+19110000,'yyyymmdd') ,'yyyymmdd' )   --substr(FEEDATE,1,6),
      ,idno
      ,case 
              when FHID not in ('PS','CB','YB','SN') then '基金' 
              when TRIM(FHID) ='YB' then 'ETF'
              when FHID ='PS' then '海外股票'
              when FHID like 'TA%' or FHID  like 'TB%' or FHID  like 'TD%' or FHID  like 'TE%'  then '集合管理帳戶'
       end
       ,baopcccode;
        
--37.【銀行】DCI 手收 總量  --DSDEP.DCI_PERFO_RPT CURRENT
drop table INCOME_037;
create table INCOME_037
as 
select 
       trade_date as yyyymmdd,
       customer_id as cust_id,
       RM_PCCODE PCCODE,
       sum(FEE_AMOUNT_TWD) AMT --customer_id as cust_Id
from DSDEP.DCI_PERFO_RPT_HS@anadbp01_dwdbp01
group  by  
       trade_date,
       customer_id,
       RM_PCCODE
union 
select 
       trade_date,
       customer_id,
       RM_PCCODE RM_PCCODE,
       sum(FEE_AMOUNT_TWD) AMT --customer_id as cust_Id
from DSDEP.DCI_PERFO_RPT@anadbp01_dwdbp01
group  by  
       trade_date,
       customer_id,
       RM_PCCODE    
  ;
--38.【銀行】DCI 手收 總量 --TMU損益
drop table INCOME_038;
create table INCOME_038
as
select to_char(to_date(TRIM(postdate), 'YYYY/MM/DD'),'yyyymmdd') yyyymmdd,
       entitynumber as cust_id,
       CONFCLASSCODE PCCODE,
       sum(TmuProfit) AMT
from DSTAS.FO108_W@anadbp01_dwdbp01
where TRIM(Product)='DCD'
group by to_char(to_date(TRIM(postdate), 'YYYY/MM/DD'),'yyyymmdd'),
      entitynumber,
      CONFCLASSCODE
      ;

--39.【銀行】境內結構型商品手收 總量
--PB SI 交易明細
drop table INCOME_039;
create table INCOME_039
as 
select customer_id cust_id ,
       trade_date yyyymmdd,
       S_PCC_CODE PCCODE,
       sum(FEE_AMOUNT_TWD) AMT
from DSDEP.SI_PERFO_RPT_HS@anadbp01_dwdbp01   --CURRENT檔案  DSDEP.SI_PERFO_RPT 
group by customer_id,trade_date,S_PCC_CODE
union 
select customer_id cust_id ,
       trade_date yyyymmdd,
       S_PCC_CODE PCCODE,
       sum(FEE_AMOUNT_TWD) AMT
from DSDEP.SI_PERFO_RPT@anadbp01_dwdbp01   --CURRENT檔案  DSDEP.SI_PERFO_RPT 
group by customer_id,trade_date,S_PCC_CODE;

--40.ELI戰報   DSDEP.ELI_PERFO_RPT
drop table INCOME_040;
create table INCOME_040
as 
select trade_date yyyymmdd,
       customer_id cust_id, 
       RM_PCCODE PCCODE,
       sum(FEE_AMOUNT) AMT
from DSDEP.ELI_PERFO_RPT_HS@anadbp01_dwdbp01  --CURRENT 檔案 DSDEP.ELI_PERFO_RPT
group by trade_date,customer_id,RM_PCCODE
union
select trade_date yyyymmdd,
       customer_id cust_id,
       RM_PCCODE PCCODE, 
       sum(FEE_AMOUNT) AMT
from DSDEP.ELI_PERFO_RPT@anadbp01_dwdbp01  --CURRENT 檔案 DSDEP.ELI_PERFO_RPT
group by trade_date,customer_id,RM_PCCODE
 ;

-- FEE_AMOUNT_TWD-->PB FCI 交易明細
--41.FCI戰報
drop table INCOME_041;
create table INCOME_041
as 
select customer_id cust_id
       ,trade_date yyyymmdd
       ,O_PCC_CODE PCCODE
       ,sum(fee_amount_twd) AMT
from DSDEP.FCI_PERFO_RPT_HS@anadbp01_dwdbp01
where status_ch='新增'
group by customer_id,trade_date,O_PCC_CODE
union 
select customer_id cust_id
       ,trade_date yyyymmdd
      ,O_PCC_CODE PCCODE
       ,sum(fee_amount_twd) AMT
from DSDEP.FCI_PERFO_RPT@anadbp01_dwdbp01
where status_ch='新增'
group by customer_id,trade_date,O_PCC_CODE;
  

--42.【銀行】境外結構型商品手收 總量 PB ELI 交易明細
--DSDEP.ELI_PERFO_RPT
drop table INCOME_042;
create table INCOME_042
as 
select to_char(to_date(feedate+19110000,'yyyymmdd'),'yyyymmdd') as yyyymmdd,
       idno as cust_id,
       BAOPCCCODE PCCODE,
       sum(BrhRebateAmt) AMT --BrhRebateAmt
from DSFND.PB_FUND_SPREAD_DAILY@anadbp01_dwdbp01
where FHID='SN' and baopcccode like '2E%'
group by feedate,idno,baopcccode;

--43.【銀行】FX手收 總量
--銀行 FX(WBS) 手收 
--20251124 移除 PCC_CODE 為2E條件
drop table INCOME_043_TMP01;
create table INCOME_043_TMP01
as 
select to_char(to_date(PROC_DATE,'yyyymmdd'),'yyyymmdd') yyyymmdd,
       cust_id,
       pcc_code PCCODE,
       sum(BAL_AMT_TWD) AMT  -- BAL_AMT_TWD
from DSWBS.PB_SPOT_Daily@anadbp01_dwdbp01
group by to_char(to_date(PROC_DATE,'yyyymmdd'),'yyyymmdd')
,cust_id,pcc_code;

drop table INCOME_043_TMP02;
create table INCOME_043_TMP02
as 
select to_char(to_date(PROC_DATE,'yyyymmdd'),'yyyymmdd') yyyymmdd,
       cust_id,
       pcc_code PCCODE,
       sum(BAL_AMT_TWD) AMT  -- BAL_AMT_TWD
from DSWBS.PB_SPOT_Daily_HS@anadbp01_dwdbp01
where pcc_code like '2E%'
group by to_char(to_date(PROC_DATE,'yyyymmdd'),'yyyymmdd')
,cust_id,pcc_code;

drop table INCOME_043;
create table INCOME_043
as 
select * from INCOME_043_TMP01
union 
select * from INCOME_043_TMP02;
--select * from DSWBS.PB_SPOT_Daily@anadbp01_dwdbp01
--44.【銀行】FX手收 總量--銀行 FX(TMU) 手收 
--20251124 調整 不排除2E條件
drop table INCOME_044;
create table INCOME_044
as 
select to_char(to_date(TRIM(usertradedate), 'YYYY/MM/DD'),'yyyymmdd')  yyyymmdd --TmuProfit
       ,entitynumber as cust_id 
       ,sum(TmuProfit) as AMT  
from DSTAS.FO108_W@anadbp01_dwdbp01
where TRIM(Product) not in  ('DCD','Cash Bond')
group by to_char(to_date(TRIM(usertradedate), 'YYYY/MM/DD'),'yyyymmdd') ,entitynumber;

--45.【銀行】開狀手收 總量
drop table INCOME_045;
create table INCOME_045
as 
select 
        proc_date yyyymmdd,
        cust_id,
        PCC_CODE PCCODE,
        sum(FEE_AMT) AMT   
from DSWBS.IMPM007_HS@anadbp01_dwdbp01
where to_char(to_date(FEE_END_DATE,'YYYY/MM/DD'),'YYYYMMDD') >= to_char(sysdate,'YYYYMMDD')
group by proc_date,cust_id,PCC_CODE
union 
select 
        proc_date ,
        cust_id,
        PCC_CODE PCCODE,
        sum(FEE_AMT)  AMT    
from DSWBS.IMPM007@anadbp01_dwdbp01
where to_char(to_date(FEE_END_DATE,'YYYY/MM/DD'),'YYYYMMDD') >= to_char(sysdate,'YYYYMMDD')
group by proc_date ,
        cust_id,
        PCC_CODE 
        ;
--
--46.【銀行】信託保管費手收 總量
--規劃型信託(股票信託、金錢信託)
drop table INCOME_046;
create table INCOME_046
as 
select postdate yyyymmdd,
       id as cust_id, 
       sum(SecuritiesBrwFee+SecuritiesMngFee+SecuritiesCrgFee+PecuniaryMngFee+PecuniaryCrgFee) as AMT
from DSTAM.TRUCONTRACT_PB@anadbp01_dwdbp01
group by postdate,id;

--47.規劃型信託(員工持股信託)  --累計
drop table INCOME_047;
create table INCOME_047
as
select to_char(baldate,'yyyymmdd') yyyymmdd,
       idno as cust_id,
       sum(fee+createfee)  as AMT
from  DSEBS.EBTS_ACT_CntAUMBal_PB@anadbp01_dwdbp01
group by baldate,idno;

--48.私人銀行事業處業績檔(保管)
drop table INCOME_048;
create table INCOME_048
as
select to_char("DATE",'yyyymmdd') as YYYYMMDD,cust_id,sum(FEE) as AMT 
from  DSPMS.PB_PMS_AUM@anadbp01_dwdbp01
group by "DATE",cust_id;
--select * from DSPMS.PB_PMS_AUM@anadbp01_dwdbp01
--49.【銀行】黃金手收 總量
drop table INCOME_049_TMP01;
create table INCOME_049_TMP01
as
select customer_id cust_id,
       idate yyyymmdd,
       sum(plamt_twd) AMT
from DSDEP.GD_PERFO_RPT@anadbp01_dwdbp01
group by customer_id,idate;

drop table INCOME_049_TMP02;
create table INCOME_049_TMP02
as
select customer_id cust_id,
       idate yyyymmdd,
       sum(plamt_twd) AMT
from DSDEP.GD_PERFO_RPT_HS@anadbp01_dwdbp01
group by customer_id,idate;

drop table INCOME_049;
create table INCOME_049
as
select * from INCOME_049_TMP01
union 
select * from INCOME_049_TMP02;

--51.【證券】複委託-債券手收 總量  bond not like 'TSSN%' 
--54.【證券】複委託-結構型商品手收 總量  bond  like 'TSSN%' 
--證券月底資料最後兩個工作天計算至下個月
drop table INCOME_051_054_TMP01;
create table INCOME_051_054_TMP01
as
select 
     idno cust_id,
     clrdate,
      case 
           when bond  like 'TSSN%'  then   '結構型商品'
            else '債券' end as  FLG,   
      CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END AS yyyymmdd,
     sum( CFEE * FXRATE)  as amt
 from DSPBM.PB_BONDTRADM_SEC_M@anadbp01_dwdbp01 t
 LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM
 group by idno, clrdate,
          case 
           when bond  like 'TSSN%'  then   '結構型商品'
            else '債券' end,clrdate,CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM')||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)||'01'
       END ;
            
drop table INCOME_051_054_TMP02;
create table INCOME_051_054_TMP02
as
select 
     idno cust_id,clrdate,
      case 
           when bond  like 'TSSN%'  then   '結構型商品'
            else '債券' end as  FLG,   
      CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END AS yyyymmdd,
     sum( CFEE * FXRATE)  as amt
 from DSPBM.PB_BONDTRADM_SEC@anadbp01_dwdbp01 t
 LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM 
 where yyyymmdd = (select max(yyyymmdd) from DSPBM.PB_BONDTRADM_SEC@anadbp01_dwdbp01)
 group by idno,
       case 
           when bond  like 'TSSN%'  then   '結構型商品'
            else '債券' end,clrdate, 
        CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END;
            
drop table INCOME_051_054;
create table INCOME_051_054
as
select *  from INCOME_051_054_TMP01
union 
select *  from INCOME_051_054_TMP02;
--52.【證券】複委託-基金手收 總量
--20251124 證券月底資料最後兩個工作天計算至下個月
drop table INCOME_052_TMP01;
create table INCOME_052_TMP01
as
select wka28 as cust_id,
        CASE WHEN t.wka02 >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.wka02,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.wka02,1,6)  ||'01'
       END as yyyymmdd,
       sum(wka31) as amt
from DSPBM.PB_FUNDTRADM_SEC_M@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.wka02,1,6) = l.YM
group by wka28, CASE WHEN t.wka02 >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.wka02,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.wka02,1,6)  ||'01'
       END  ;
--select YYYYMM ||'01'  from DSPBM.PB_FUNDTRADM_SEC_M@anadbp01_dwdbp01
drop table INCOME_052_TMP02;
create table INCOME_052_TMP02
as
select  wka28 as cust_id,
        CASE WHEN t.wka02 >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.wka02,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.wka02,1,6)  ||'01'
       END as yyyymmdd,
       sum(wka31) as amt
from DSPBM.PB_FUNDTRADM_SEC@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.wka02,1,6) = l.YM
where yyyymmdd = (select max(yyyymmdd) from DSPBM.PB_BONDTRADM_SEC@anadbp01_dwdbp01)
group by wka28, CASE WHEN t.wka02 >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.wka02,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.wka02,1,6)  ||'01'
       END;
--select * from INCOME_052_TMP02
drop table INCOME_052;
create table INCOME_052
as
select * from INCOME_052_TMP01
union 
select * from INCOME_052_TMP02;

--53.【證券】複委託-外國股票手收 總量
--20251124 證券月底資料最後兩個工作天計算至下個月
drop table INCOME_053_TMP01;
create table INCOME_053_TMP01
as
select 'PM' AP ,idno as cust_id,
        CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END as yyyymmdd,
       sum((CFEE-ABFEE)*FXRATE) as amt
from DSPBM.PB_STOCKTRADM_PM_SEC_M@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM
group by idno,CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END
union
select  'AM' AP ,idno as cust_id,
         CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
         END as yyyymmdd,
        sum((CFEE-ABFEE)*FXRATE) as amt
from DSPBM.PB_STOCKTRADM_AM_SEC_M@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM
group by idno,CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END;

drop table INCOME_053_TMP02;
create table INCOME_053_TMP02
as
select 'PM' AP ,idno as cust_id,
        CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END as yyyymmdd,
       sum((CFEE-ABFEE)*FXRATE) as amt
from DSPBM.PB_STOCKTRADM_PM_SEC@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM
where yyyymmdd = (select max(yyyymmdd) from DSPBM.PB_STOCKTRADM_PM_SEC@anadbp01_dwdbp01)
group by idno,CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
       END
union
select  'AM' AP ,idno as cust_id,
        CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
         END as yyyymmdd,
        sum((CFEE-ABFEE)*FXRATE) as amt
from DSPBM.PB_STOCKTRADM_AM_SEC_M@anadbp01_dwdbp01 t
LEFT JOIN T_LAST_TWO_WORKDAYS l ON SUBSTR(t.CLRDATE,1,6) = l.YM
where yyyymmdd =(select max(yyyymmdd) from DSPBM.PB_STOCKTRADM_AM_SEC@anadbp01_dwdbp01)
group by idno,CASE WHEN t.CLRDATE >= l.LAST2_WD 
            THEN TO_CHAR(ADD_MONTHS(TO_DATE(t.CLRDATE,'YYYYMMDD'),1),'YYYYMM') ||'01'
            ELSE SUBSTR(t.CLRDATE,1,6)  ||'01'
         END;

drop table INCOME_053;
create table INCOME_053
as
select * from INCOME_053_TMP01
union 
select * from INCOME_053_TMP02;

--66、67 存款利收總量
--66 存款利收總量
/*
drop table INCOME_066_TMP01;
create table INCOME_066_TMP01
as
     SELECT cust_id,yyyymmdd,sum(AMT) AMT
     FROM (
        SELECT cust_id,yyyymm || '01'  yyyymmdd, sum(GROSS_INCM)  AMT --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 利息 
        FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
        where TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>='202312' and YYYYMM<='202505'
        group by cust_id,yyyymm
        UNION ALL
        SELECT cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT --* --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
        FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
        WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>='202312' and YYYYMM<='202505'
        group by cust_id,yyyymm
        UNION ALL
        SELECT  cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT-- TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 
        FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
        WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>='202312' and YYYYMM<='202505'
        group by cust_id,yyyymm
        ) 
GROUP BY cust_id,yyyymmdd;
*/
/*
drop table INCOME_066_TMP02;
create table INCOME_066_TMP02
as
     SELECT cust_id,yyyymmdd,sum(AMT) AMT
     FROM (
        SELECT cust_id,yyyymm || '01'  yyyymmdd, sum(GROSS_INCM)  AMT --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 利息 
        FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
        where TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505' 
        group by cust_id,yyyymm
        UNION ALL
        SELECT cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT --* --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
        FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
        WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505'
        group by cust_id,yyyymm
        UNION ALL
        SELECT  cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT-- TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 
        FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
        WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505'
        group by cust_id,yyyymm
        ) 
GROUP BY cust_id,yyyymmdd;
*/
drop table INCOME_066_TMP021;
create table INCOME_066_TMP021
as
SELECT cust_id,yyyymm || '01'  yyyymmdd, sum(GROSS_INCM)  AMT --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 利息 
FROM DSDEP.DEP_NT_ACCT_HS@anadbp01_dwdbp01
where TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505'
group by cust_id,yyyymm ;

drop table INCOME_066_TMP022;
create table INCOME_066_TMP022
as
SELECT cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT --* --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
FROM DSDEP.DEP_FN_ACCT_HS@anadbp01_dwdbp01
WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505'
group by cust_id,yyyymm ;

drop table INCOME_066_TMP023;
create table INCOME_066_TMP023
as
SELECT  cust_id, yyyymm || '01' yyyymmdd,sum(GROSS_INCM)  AMT-- TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, BAL_AMT, GROSS_INCM 
FROM DSDEP.EMP_DEP_NT_ACCT_HS@anadbp01_dwdbp01
WHERE  TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400') AND YYYYMM>'202505'
group by cust_id,yyyymm;
--歷史資料5月後
drop table INCOME_066_TMP02;
create table INCOME_066_TMP02
as 
SELECT cust_id,yyyymmdd,sum(AMT) AMT
     FROM (
     select * from INCOME_066_TMP021
     union all 
     select * from INCOME_066_TMP022
     union all
     select * from INCOME_066_TMP023
        )  a
GROUP BY cust_id,yyyymmdd;

--DSDEP.DEP_NT_ACCT 資料表 無 GROSS_INCM欄位
drop table INCOME_066_TMP03;
create table INCOME_066_TMP03
as
SELECT cust_id, data_dt yyyymmdd,sum(GROSS_INCM)  AMT --* --TRIM(PRFT_CNTR_CD) PRFT_CNTR_CD, ACT_CD, AVAIL_BAL, GROSS_INCM 
FROM DSDEP.DEP_FN_ACCT@anadbp01_dwdbp01
WHERE  TRIM(PRFT_CNTR_CD) like  '2E%' --AND YYYYMM>'202505'
group by cust_id,data_dt;
        
drop table INCOME_066;
create table INCOME_066
as
select * from INCOME_066_TMP01
union 
select * from INCOME_066_TMP02
union 
select * from INCOME_066_TMP03
;
--TMP02執行太久 拆開執行，僅更新一個月資料
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
/* --此段執行時間較久，歷史檔與現況分開執行
drop table INCOME_067_TMP01;
create table INCOME_067_TMP01
as
select cust_id,yyyymmdd,sum(AMT) AMT
from 
(
    SELECT cust_id, yyyymm ||'01'  as yyyymmdd,sum(GROSS_INCM) AMT  -- ACC_CD, SUM(LN_BAL), SUM(GROSS_INCM) FROM (
    FROM DSLON.LN_NT_ACCT_HS@anadbp01_dwdbp01 A
    WHERE  PRFT_CNTR_CD IN ('2E3000', '2E3200', '2E3300', '2E3400')
    AND yyyymm>='202312' and  YYYYMM<='202505'
    group by cust_id,yyyymm
    UNION ALL
    SELECT cust_id, yyyymm || '01' as yyyymmdd, sum(INT_INCM - CB_INT_AMT) AMT --ACC_CD, BAL_AMT, 
    FROM DSLON.LN_FN_ACCT_HS@anadbp01_dwdbp01 A
    WHERE TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400')
    AND yyyymm>='202312' and  YYYYMM<='202505'
    group by cust_id,yyyymm
)  a 
GROUP BY cust_id,yyyymmdd;
*/
/*
drop table INCOME_067_TMP02;
create table INCOME_067_TMP02
as
select cust_id,yyyymmdd,sum(AMT) AMT
from 
(
    SELECT cust_id, yyyymm ||'01'  as yyyymmdd,sum(GROSS_INCM) AMT  -- ACC_CD, SUM(LN_BAL), SUM(GROSS_INCM) FROM (
    FROM DSLON.LN_NT_ACCT_HS@anadbp01_dwdbp01 A
    WHERE  PRFT_CNTR_CD IN ('2E3000', '2E3200', '2E3300', '2E3400')
    AND  YYYYMM>'202505'
    group by cust_id,yyyymm
    UNION ALL
    SELECT cust_id, yyyymm || '01' as yyyymmdd, sum(INT_INCM - CB_INT_AMT) AMT --ACC_CD, BAL_AMT, 
    FROM DSLON.LN_FN_ACCT_HS@anadbp01_dwdbp01 A
    WHERE TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400')
    AND YYYYMM>'202505'
    group by cust_id,yyyymm
)  a 
GROUP BY cust_id,yyyymmdd;
*/

drop table INCOME_067_TMP021;
create table INCOME_067_TMP021
as
  SELECT cust_id, yyyymm ||'01'  as yyyymmdd,sum(GROSS_INCM) AMT  -- ACC_CD, SUM(LN_BAL), SUM(GROSS_INCM) FROM (
    FROM DSLON.LN_NT_ACCT_HS@anadbp01_dwdbp01 A
    WHERE  PRFT_CNTR_CD IN ('2E3000', '2E3200', '2E3300', '2E3400')
    AND  YYYYMM>'202505'
    group by cust_id,yyyymm;

drop table INCOME_067_TMP022;
create table INCOME_067_TMP022
as
SELECT cust_id, yyyymm || '01' as yyyymmdd, sum(INT_INCM - CB_INT_AMT) AMT --ACC_CD, BAL_AMT, 
FROM DSLON.LN_FN_ACCT_HS@anadbp01_dwdbp01 A
WHERE TRIM(PRFT_CNTR_CD) IN ('2E3000', '2E3200', '2E3300', '2E3400')
AND YYYYMM>'202505'
group by cust_id,yyyymm;

drop table INCOME_067_TMP02;
create table INCOME_067_TMP02
as
select cust_id,yyyymmdd,sum(AMT) AMT
from 
( select * from INCOME_067_TMP021
  union all
  select * from INCOME_067_TMP022
 ) a
GROUP BY cust_id,yyyymmdd;

--DSLON.LN_NT_ACCT 無 GROSS_INCM 欄位
drop table INCOME_067_TMP03;
create table INCOME_067_TMP03
as
SELECT cust_id, data_dt as yyyymmdd, sum(INT_INCM - CB_INT_AMT) AMT --ACC_CD, BAL_AMT, 
FROM DSLON.LN_FN_ACCT@anadbp01_dwdbp01 A
WHERE TRIM(PRFT_CNTR_CD)  like '2E%'
group by cust_id, data_dt;


/*
drop table INCOME_067_TMP03;
create table INCOME_067_TMP03
as
SELECT * --cust_id, data_dt  as yyyymmdd,sum(GROSS_INCM) AMT  -- ACC_CD, SUM(LN_BAL), SUM(GROSS_INCM) FROM (
FROM DSLON.LN_NT_ACCT@anadbp01_dwdbp01 A
WHERE  PRFT_CNTR_CD IN ('2E3000', '2E3200', '2E3300', '2E3400')
group by cust_id,data_dt;
*/
drop table INCOME_067;
create table INCOME_067
as
select * from INCOME_067_TMP01
union 
select * from INCOME_067_TMP02
union 
select * from INCOME_067_TMP03;

--TMP02 執行太久，歷史資料僅更新一個月資料，並分段執行
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
EXIT;
