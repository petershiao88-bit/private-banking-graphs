/*
    Author  : 1121329
    memo    : 私銀資料表儀表盤資料
    用途    : 提供給應用二組與海外資料合併加值
*/

drop table INCOME_REPORT;
create table INCOME_REPORT
as 
select * from INCOME_REPORT@dwdbp01_anadbp01;

drop table AUM_REPORT;
create table AUM_REPORT
as 
select * from AUM_REPORT@dwdbp01_anadbp01;

drop table PB_TAR;
create table PB_TAR
as 
select * from PB_TAR@dwdbp01_anadbp01;

drop table 放款額度_私銀;
create table 放款額度_私銀
as 
select * from 放款額度_私銀@dwdbp01_anadbp01;

drop table 放款餘額_私銀;
create table 放款餘額_私銀
as 
select * from 放款餘額_私銀@dwdbp01_anadbp01;

drop table PB_CUST;
create table PB_CUST
as 
select * from PB_CUST@dwdbp01_anadbp01;

drop table ROA_TMP;
create table ROA_TMP
as 
select * from ROA_TMP@dwdbp01_anadbp01;

grant select on INCOME_REPORT to "1121619";
grant select on AUM_REPORT to "1121619";
grant select on PB_TAR to "1121619";
grant select on 放款額度_私銀 to "1121619";
grant select on 放款餘額_私銀  to "1121619";
grant select on PB_CUST to "1121619";
grant select on ROA_TMP to "1121619";

EXIT;