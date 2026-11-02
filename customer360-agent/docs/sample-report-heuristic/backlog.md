# 本體維護待辦（由本體檢查的質疑紀錄產生）

來源：heuristic｜本體 v0.17.0｜2026-11-01 01:12:47

## 1. 誤質疑（答案其實正確）→ 可能要補本體

（無）
## 2. 促成修正的質疑（中途被質疑，模型之後改對）

| 觸發 | 次數 | 例子 |
|---|---|---|
| ambiguous_subsidiary | 8 | a01／plan：基金手收怎麼算？ |

## 3. 有效的質疑與硬擋（答案最後仍有錯）

| 觸發 | 次數 | 例子 |
|---|---|---|
| ambiguous_subsidiary | 16 | a01／baseline：基金手收怎麼算？ |
| anchor_conflict | 7 | g03／baseline：集合管理帳戶的手收是哪個指標？ |
| anchor_missing | 6 | s02／workflow：把證券總 AUM 和複委託債券 AUM 加起來，就是客戶在證券的全部資產嗎？ |
| anchor_conflict｜外匯 | 4 | g02／baseline：銀行外匯的 AUM 怎麼查？ |
| anchor_conflict｜海外 | 4 | h01／baseline：不屬於證券的海外商品 AUM 有哪些？ |
| anchor_conflict｜股票 | 4 | g04／baseline：股票設質的 LUM 在哪裡看？ |
| anchor_conflict｜黃金 | 4 | g05／baseline：黃金 AUM 是哪個指標？ |
| anchor_missing｜基金 | 4 | h06／baseline：銀行的 ETF 算不算基金商品？ |
| anchor_missing｜外匯 | 4 | g02／baseline：銀行外匯的 AUM 怎麼查？ |
| anchor_missing｜海外 | 4 | h01／baseline：不屬於證券的海外商品 AUM 有哪些？ |
| anchor_missing｜股票 | 4 | g04／baseline：股票設質的 LUM 在哪裡看？ |
| anchor_missing｜黃金 | 4 | g05／baseline：黃金 AUM 是哪個指標？ |
| missing_subsidiary | 4 | p05／baseline：要看銀行和證券兩邊的基金 AUM，要用哪些指標？ |
| cue_conflict | 3 | p01／context：我在銀行的 AUM 有哪些項目？ |
| not_permitted | 3 | p01／baseline：我在銀行的 AUM 有哪些項目？ |
