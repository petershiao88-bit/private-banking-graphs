# v0.3.0 模型遷移說明

本次為草案模型的破壞性 URI 調整，尚未接入真實資料或正式部署。此表是人工遷移指引，不是 OWL 等價公理，也不自動合併任何紀錄。

## 公司別通聯定義統一為金控

以下 `company:` 分別指原 `bank:`、`sec:`、`life:` 命名空間，每一套都遷移到同一個金控定義。

| 原 URI 簡寫 | 新 URI 簡寫 |
|---|---|
| `company:MobileContactInformation` | `fh:MobileContactInformation` |
| `company:AddressContactInformation` | `fh:AddressContactInformation` |
| `company:mobileNumber` | `fh:mobileNumber` |
| `company:countryCode` | `fh:countryCode` |
| `company:city` | `fh:city` |
| `company:district` | `fh:district` |
| `company:addressLine` | `fh:addressLine` |
| `company:postalCode` | `fh:postalCode` |
| `company:fullAddress` | `fh:fullAddress` |

`fh:` 的完整前綴為 `https://example.org/ontology/holding#`。原銀行／證券／人壽完整前綴分別為 `https://example.org/ontology/bank#`、`https://example.org/ontology/securities#`、`https://example.org/ontology/life#`。

遷移的是概念與欄位識別，不是把三家公司的實際值合併成一筆。公司、來源系統、來源主鍵、有效性與取數規則應在資料來源映射／服務中保留。碼表或格式差異仍需逐項確認，不能只改 URI 就宣稱資料語意及格式已統一。

## 部門 OWL 類別改為 PG 業務概念

| 原草案 OWL 類別 | 新 PG 業務概念 ID | 參照金控類別 |
|---|---|---|
| `bank:LoanVerificationMobileContactInformation` | `bank.loan_verification_mobile` | `fh:MobileContactInformation` |
| `bank:CustomerVisitAddressContactInformation` | `bank.customer_visit_address` | `fh:AddressContactInformation` |

沒有建立 `owl:equivalentClass`、`owl:sameAs` 或 subclass 對應。PG 保存的是業務概念與來源映射 metadata，不是每位客戶或每筆通聯實例。

## 來源與舊檔

- 原有三份公司通聯 TTL 及 bank-business-contact.ttl 已退出有效來源。
- 修改前的 11 份模型、catalog、說明與交接均保存在 `archive/before-v0.3.0/`。
- 有效來源清單在 `build-config.json`，不遞迴掃描 archive 或 legacy 目錄。
- 整合 TTL／OWL 由新版 `tools/build_ontology.py` 產生，兩者都已更新至 v0.3.0。
- 未核定金融商品細分類、職員、帳戶或業務案件模型，不因整理檔案而補入。
