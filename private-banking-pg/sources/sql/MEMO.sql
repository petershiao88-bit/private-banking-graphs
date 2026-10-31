/*
Author : 1121329
date   : 20250627
*/

本專案為私銀儀表盤使用
報表路徑 : http://birpt01/reports/powerbi/數位科技處/數據策略部/應用一組/私銀高階管理儀表盤

檔案說明
"F:\Working_ABBB\1121329\私銀\autocmd\0_PB_CUST_DEATAIL.sql"
說明 : PB客戶數每月清單

"F:\Working_ABBB\1121329\私銀\autocmd\1.AUM_DETAIL.sql"
說明 : AUM　各明細指標計算


"F:\Working_ABBB\1121329\私銀\autocmd\2.AUM_SUMY.sql"
說明 : AUM　彙整資料計算
相依程式　：　1.AUM_DETAIL.sql

"F:\Working_ABBB\1121329\私銀\autocmd\3.LUM_by_day.sql"
說明 : LUM 每日各指標彙整計算

"F:\Working_ABBB\1121329\私銀\autocmd\4.LUM_BY_HS.sql"
說明 : LUM 歷史各指標彙整計算

"F:\Working_ABBB\1121329\私銀\autocmd\5.LUM_MERGE.sql"
說明 : LUM 每日以及歷史各指標彙整計算
相依程式　：3.LUM_by_day.sql、4.LUM_BY_HS

"F:\Working_ABBB\1121329\私銀\autocmd\6_PB_CUST_SMY.sql"
說明　: 客戶數狀態彙整，需將客戶數AUM級距貼標
相依程式　：1.AUM_DETAIL.sql

"F:\Working_ABBB\1121329\私銀\autocmd\7.PB_CUST_LUM.sql"
說明　: 客戶數狀態彙整，LUM客戶貸款人數
相依程式　：5.LUM_MERGE

"F:\Working_ABBB\1121329\私銀\autocmd\8.INCOME_DETAIL.sql"
說明　: 收入各明細指標計算

"F:\Working_ABBB\1121329\私銀\autocmd\9.INCOME_SMY.sql"
說明　: 收入彙整計算

"F:\Working_ABBB\1121329\私銀\autocmd\10._INCOME_ROA.sql"
說明　: ROA、ROBA 計算
相依程式　：2.AUM_SUMY、5.LUM_MERGE、9.INCOME_SMY

"F:\Working_ABBB\1121329\私銀\autocmd\11.TARGET.sql"
說明　: 各指標目標值
相依程式　：0_PB_CUST_DEATAIL、2.AUM_SUMY、5.LUM_MERGE、6_PB_CUST_SMY、9.INCOME_SMY

