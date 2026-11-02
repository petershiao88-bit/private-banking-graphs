# 實驗 3：預先定義 workflow vs LLM 組計畫

三份題庫共 73 題。workflow 範本：metric_lookup、concept_is_a、concept_relation，欄位型別都是本體類別。全部計算 97.2 秒（含 oracle 窮舉）。

## 結果

| 做法 | 正確 | 默默答錯 | 保守未答 |
|---|---|---|---|
| workflow＋程式填欄位（完全不用 LLM） | 59/73（81%） | 4 | 10 |
| workflow 的表達上限（欄位一定填對，oracle） | 67/73（92%） | — | — |
| 允許組合兩個範本呼叫（LLM 拆解問題＋填欄位） | 71/73（97%） | — | — |

組合兩個範本後仍表達不了：s02 把證券總 AUM 和複委託債券 AUM 加起來，就是客戶在證券的全部資產嗎？；x12 台股 AUM 是哪個指標？

| 題庫 | 程式填欄位 | 表達上限 |
|---|---|---|
| questions.yaml | 28/33（85%） | 32/33（97%） |
| holdout.yaml | 19/24（79%） | 21/24（88%） |
| holdout2.yaml | 12/16（75%） | 14/16（88%） |

| 題型 | 題數 | 程式填欄位答對 | 表達上限 |
|---|---|---|---|
| 多種類 | 2 | 1 | 1 |
| 子公司歧義 | 8 | 7 | 7 |
| 子公司線索 | 5 | 5 | 5 |
| 待定或不存在 | 6 | 6 | 6 |
| 數值請求 | 1 | 1 | 1 |
| 概念 | 2 | 0 | 2 |
| 權限 | 7 | 6 | 7 |
| 直接對應 | 22 | 18 | 20 |
| 縮寫 | 1 | 1 | 0 |
| 總指標 | 3 | 2 | 2 |
| 錨點陷阱 | 10 | 8 | 10 |
| 階層與否定 | 6 | 4 | 6 |

workflow 的 4 個默默答錯，本體檢查硬擋攔下 0 個、質疑攔下 3 個。

## workflow 答錯或答不了的題目

- d02｜直接對應｜放款餘額要看哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'lum'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
- h05｜階層與否定｜銀行手收指標是不是一種指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'fee', 'subsidiary': 'bank'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
- h06｜階層與否定｜銀行的 ETF 算不算基金商品？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'products': ['ETF', '基金'], 'subsidiary': 'bank', 'token': 'ETF'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
- s02｜總指標｜把證券總 AUM 和複委託債券 AUM 加起來，就是客戶在證券的全部資產嗎？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['債券'], 'subsidiary': 'securities', 'summary': True}]} → answer ['securities.bond_aum']｜silent_wrong；指標不符；缺 securities.total_aum｜上限不可表達｜檢查：硬擋 —、質疑 ['anchor_missing']
- p03｜權限｜證券總手收是哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'fee', 'subsidiary': 'securities', 'summary': True}]} → answer ['securities.bond_fee_income', 'securities.foreign_stock_fee_income', 'securities.structured_fee_income']｜silent_wrong；決策 answer，期望 out_of_scope｜上限可表達｜檢查：硬擋 —、質疑 ['anchor_missing']
- x10｜直接對應｜境外結構型商品 AUM 是哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['結構型']}]} → answer ['bank.offshore_structured_aum', 'bank.structured_deposit_aum', 'securities.structured_aum']｜silent_wrong；指標不符；多 bank.structured_deposit_aum、securities.structured_aum｜上限可表達｜檢查：硬擋 —、質疑 —
- x12｜直接對應｜台股 AUM 是哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限不可表達｜檢查：硬擋 —、質疑 —
- x14｜概念｜私銀部門跟指標之間是什麼關係？ → concept_relation {'calls': [{'template': 'concept_relation', 'a': 'bank:PrivateBankingDepartment', 'b': 'fh:Department'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
- x16｜子公司歧義｜基金和 ETF 的 AUM 各用哪些指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['ETF', '基金'], 'token': 'ETF'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer／clarify｜上限不可表達｜檢查：硬擋 —、質疑 —
- x23｜錨點陷阱｜客戶買海外債券型基金的 AUM 要看哪個？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['基金', '海外']}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 clarify／answer｜上限可表達｜檢查：硬擋 —、質疑 —
- y08｜直接對應｜外幣存款的 AUM 跟存款利收各是哪個？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['存款', '外幣']}, {'template': 'metric_lookup', 'kind': 'interest', 'products': ['存款', '外幣']}]} → answer ['bank.foreign_currency_deposit_aum']｜silent_wrong；指標不符；缺 bank.deposit_interest_income｜上限不可表達｜檢查：硬擋 —、質疑 ['anchor_missing']
- y10｜概念｜手收指標可以歸屬給誰？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'fee'}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
- y14｜多種類｜銀行黃金的手收跟證券的債券手收，各是哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'fee', 'products': ['債券', '黃金']}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限不可表達｜檢查：硬擋 —、質疑 —
- y15｜錨點陷阱｜客戶的外幣保單 AUM 看哪個指標？ → metric_lookup {'calls': [{'template': 'metric_lookup', 'kind': 'aum', 'products': ['外幣', '保險']}]} → out_of_scope []｜safe_miss；決策 out_of_scope，期望 answer｜上限可表達｜檢查：硬擋 —、質疑 —
