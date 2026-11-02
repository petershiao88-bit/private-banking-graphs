# 已由 active 存款模組取代的歷史草稿

`employee-deposit.json` 保留舊格式與查核脈絡，已標記 `superseded_not_build_input`，**不供建置器載入**。目前正式人工編輯來源為上層 `deposits.json`；格式、schema 選擇、來源限制及建置指令詳見 `../README.md`。

目前 active 模組已支援台幣存款、外幣存款、結構型存款各四個資料欄位定義，以及行員存款五個資料欄位定義。這些不是資料實例，也不是 RDF 商品類別的 datatype properties。

## 已解決的定義

行員存款指 **存款人本人為銀行行員的存款**，不是管理該客戶的 AO，亦不限於員工優惠方案。這個定義不再是 open question；是否已找到涵蓋所有行員本人存款的來源仍未知。

存款商品可參照核准的 `https://example.org/ontology/bank#DepositProduct`；Employee 類別／員工語意關聯 URI 仍未核准，active 模組使用 URI 全為 null 的 PendingSemanticReference，不捏造類別。

## 仍保留的缺口

- employeeId 的來源、欄位及 JOIN 均未確認；`AUM_TMP02.EMP_NO` 是客戶管理 AO 員編，明確排除。
- 員工底表僅觀察到 DSDEP.EMP_DEP_NT_ACCT_HS，未驗證來源完整性。
- currency 不能由 SQL 顯示文字推定；snapshotDate 的 DATA_DT／YYYYMM／LST_MTN_DT 語意未核定。
- AUM metadata 的 EMP_NT_ACCT_HS 命名差異不代表另一張已確認來源表。
- 舊 SQL 的分類、SUM／group by、歷史時間門檻與 UNION 僅為證據，不是新版執行規則；未建立帳戶模型、鍵或分行／數位分類。

草稿中的舊欄位格式及 legacyTransformation 只供追溯。使用 active 模組時以 `deposits.json` 與 `deposit_model.py` 為準，不以此草稿宣稱仍未支援建置，也不把保留的 SQL 片段當成取數指令。
