# 本體修改提案（2026-11-01）：台股、信託投資、自營

> 來源：架構實驗的質疑紀錄與 workflow 表達不了的題目（結論 C4、C7）。
> 已在沙盒（本體副本）驗證，正式的 `customer360-rdf` 尚未修改。採用時請照 HANDOFF 的升版流程：`bump 0.18.0` → `build` → PG 兩支腳本 → 測試 → `release`。

## 要改什麼

### 1. 新增 3 個類別

**`ontology/securities/products.ttl`**

```turtle
securities:TaiwanStockProduct a owl:Class ;
    rdfs:label "台股商品"@zh-TW ;
    rdfs:subClassOf fh:FinancialProduct , securities:StockProduct ;
    skos:definition "在台灣證券市場交易的股票商品。"@zh-TW ;
    fh:governanceLevel "子公司" ;
    fh:subsidiary "證券" .
```

**`ontology/bank/products.ttl`**

```turtle
bank:TrustInvestmentProduct a owl:Class ;
    rdfs:label "信託投資商品"@zh-TW ;
    rdfs:subClassOf fh:FinancialProduct ;
    skos:definition "客戶透過銀行特定金錢信託方式投資的商品。"@zh-TW ;
    fh:governanceLevel "子公司" ;
    fh:subsidiary "銀行" .

bank:ProprietaryTradingProduct a owl:Class ;
    rdfs:label "自營商品"@zh-TW ;
    rdfs:subClassOf fh:FinancialProduct ;
    skos:definition "銀行以自營部位與客戶交易的商品。"@zh-TW ;
    fh:governanceLevel "子公司" ;
    fh:subsidiary "銀行" .
```

「信託」「自營」其實是通路或交易方式的維度，不是商品種類。這裡先用商品子類別表達，是為了讓既有的權限與指標對應規則不用改。長期建議另外設計「通路」維度。

### 2. PG 指標加上商品對應

在 `product_class_uris` 加入：

| 指標 | 加入的類別 |
|---|---|
| `securities.taiwan_stock_aum` | `securities:TaiwanStockProduct` |
| `bank.overseas_bond_trust_aum`、`bank.overseas_bond_trust_fee_income` | `bank:TrustInvestmentProduct` |
| `bank.overseas_bond_proprietary_aum`、`bank.overseas_bond_proprietary_fee_income` | `bank:ProprietaryTradingProduct` |

### 3. 權限計算（結論 C5）

總指標要繼承分項的拒絕。目前客戶可以看「證券總手收」，但它的分項含有客戶不可看的「證券複委託基金手收」。實驗台用 `agent.aggregate_inherits_component_deny` 處理，建議放回 `semantic_studio/core/permissions.py`。

## 沙盒量測結果

用 `C360A_CONFIG=<沙盒設定> python experiments/run_all.py` 量測：

| 項目 | 目前 v0.17.0 | 套用提案後 |
|---|---|---|
| workflow 範本表達上限（只靠本體類別，不借指標名稱） | 89% | **93%** |
| 組合兩個範本後的上限 | 95% | **99%**（只剩「加總推理」1 題） |
| workflow 程式填欄位 | 77% | 79% |
| 硬擋誤擋正確答案（三份題庫） | 0 | 0 |
| 質疑誤擋 | 0／1／2 | 1／1／2 |

新增的那 1 題質疑誤擋是 s03「證券總手收有沒有包含台股手收？」：本體現在認得「台股」，所以質疑「選到的指標沒有涵蓋台股」。這個質疑其實就是正確答案的內容（不包含台股），作答時會轉成提醒。這也說明：**本體每加一個詞，都可能產生新的質疑，所以改版前一定要跑回歸關卡。**
