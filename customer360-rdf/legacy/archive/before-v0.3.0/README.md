# 客戶 360 RDF／OWL

基礎及整合輸出版本：v0.2.0（設計草案，2026-10-21）。另已新增尚未併入整合輸出的銀行業務通聯模組。本目錄是從 ChatGPT 專案輸出複製出的 Zed 接續開發工作副本；原始外部同步專案維持唯讀。

## 權威來源

後續編輯以下列分層 Turtle 檔為模型來源：

- `holding-core.ttl`
- `bank-contact.ttl`
- `securities-contact.ttl`
- `life-contact.ttl`
- `bank-business-contact.ttl`（新增業務延伸；尚未併入整合輸出）

`customer360-ontology.ttl` 與 `customer360-ontology.owl` 是整合輸出，不應與分層 TTL 分別手動維護。業務決議與未定案邊界以 `HANDOFF-ZED-RDF-20261021.md` 為準；原始版本說明保留在 `README.txt`。

## 目前結構

| 位置 | 用途 |
|---|---|
| 原有四份分層 TTL | v0.2.0 基礎模型編輯來源 |
| `bank-business-contact.ttl` | 銀行業務通聯延伸，匯入銀行共用通聯本體 |
| `customer360-ontology.ttl` | 自含的整合 Turtle 輸出 |
| `customer360-ontology.owl` | 與整合 Turtle 同圖的 RDF/XML 輸出 |
| `catalog-v001.xml` | 分層本體 URI 至本機檔案的 catalog |
| `tools/legacy-v0.2.0/` | 上一階段建置器、驗證器與 v0.2.0 基準，僅供追溯 |

## 2026-10-21 已確認並實作的業務延伸

依使用者指示，本次只新增獨立模組及 catalog 對應，不修改原有四份分層 TTL 或整合 TTL／OWL。整合檔仍為原 v0.2.0，不包含以下兩個新類別；`README.txt` 與舊交接文件保留為原版本紀錄，本節記載後續決議。

| 新類別 | 父類別 | 沿用欄位 |
|---|---|---|
| `bank:LoanVerificationMobileContactInformation` 貸款照會手機通聯資訊 | `bank:MobileContactInformation` | `bank:mobileNumber` |
| `bank:CustomerVisitAddressContactInformation` 客戶訪問地址通聯資訊 | `bank:AddressContactInformation` | 銀行既有六個地址 Data Property |

- 業務用途以 subclass 表達，治理層級為部門、子公司為銀行；實際權責部門尚未確認，暫不填 `fh:department`。英文 URI 為本次草案技術識別名稱。
- 客戶訪問地址表示供業務人員前往訪問客戶的地址，不預設等於居住地址；用途分類不代表照會通過或訪問完成。
- 不同業務可以指向同一筆銀行 golden record，不強制每個業務複製通聯紀錄，也不按相同字面值自動合併。實例 URI 及來源映射仍由銀行系統決定。
- 尚未新增貸款申請、訪問事件、業務使用關係或真實資料；未新增 Data Property、有效註記、互斥、等價或唯一性公理。
- 欲閱讀新增模型，請開啟 `bank-business-contact.ttl` 並透過 catalog 解析銀行及金控匯入；單獨讀取舊整合檔不會看到新類別。GUI 載入尚未實測。
- 後續需要整合輸出時，須先建立以分層 TTL 為輸入的建置流程，勿重跑舊建置器。

### 本次驗證範圍

已使用舊驗證器的純解析函式（未執行其寫檔流程）檢查新模組，結果通過：16 個三元組、2 個 Class，直接父類別與治理標記符合上述設計，本機 catalog 匯入對應檔案存在。原有四份分層 TTL 及兩份整合輸出與外部 v0.2.0 來源的 SHA-256 仍一致。

解析器僅支援既有輸出語法子集；未執行通用 RDF parser、專用 OWL reasoner 或 GUI 測試。舊 `validation.json` 仍是 v0.2.0 紀錄，不涵蓋新增模組。

## 維護規則

1. 不要直接執行 `tools/legacy-v0.2.0/build_ontology.py`；模型定義寫死在程式中，會覆寫目前檔案。
2. 先將建置流程改為讀取分層 TTL（含新增業務模組），再用它產生整合 TTL 與 RDF/XML。
3. 合法模型變更需同步更新文件、整合輸出與驗證基準；232 個三元組不是固定目標。
4. 不自行加入未核定的類別、公理、SHACL、格式限制、唯一性或真實資料映射。
5. 每次變更明確區分已確認決議、提議與已實作內容。
