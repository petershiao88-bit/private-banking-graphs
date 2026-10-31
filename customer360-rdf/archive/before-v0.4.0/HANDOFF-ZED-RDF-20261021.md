# 客戶360 RDF／OWL 與部門 PG：Zed 接續交接

更新：2026-10-21；目前版本 v0.3.0，設計草案。

## 先讀

本文件、README.md、現有模型與使用者後續指示是目前依據。原 v0.2.0 交接及本體已完整保存在 `archive/before-v0.3.0/`。本次共識取代「公司別手機／地址類別」「子公司重複欄位」「部門繼續延伸 OWL 子類別」的舊設計，勿恢復。

工作目錄：`C:\Users\petershiao\Desktop\Ontology\客戶360\customer360-rdf-owl`。
上層 `客戶360/AGENTS.md` 適用；使用者已明確要求專案內相關程式、建置及測試直接執行，不逐項詢問。仍遵守工具核准與對外部署等範圍限制。

## 已確認決議

1. 金控與子公司層使用 RDF／OWL 定義共同語意；資料面現況不應決定概念分類。
2. 手機與地址均為金控 `fh:ContactInformation` 的直接子類別，不再按公司各建一份。
3. 手機號碼及六個地址 Data Property 也統一提升金控。
4. 客戶到通聯使用 `fh:hasContactPoint`；手機／地址到通聯才使用 `rdfs:subClassOf`。
5. 部門使用 Property Graph 描述業務概念及到底表、欄位、SQL、JOIN、篩選的映射；不是客戶資料實例圖。
6. 貸款照會手機、客戶訪問地址留在部門 PG，不是 OWL 子類別。PG 參照完整 RDF 概念／屬性 URI，但沒有自動等價、型別宣告或推論。
7. 真實紀錄可留在原資料庫；本階段不要求每筆紀錄有共用 RDF 實例 URI。不同業務可映射同一銀行 golden record 來源；識別鍵與 JOIN 仍待確認。
8. 業務定義保持精簡，只寫核心意義；設計邊界另寫文件。
9. 不加入 Hash、有效註記。有效性、去重、來源衝突與 golden record 整理由來源權責系統處理。

## 已實作

### RDF

- 唯一來源：`holding-core.ttl`。未新增經核定的子公司專屬概念，因此本輪沒有子公司來源模組。
- 5 Class：Customer、FinancialProduct、ContactInformation、MobileContactInformation、AddressContactInformation，均為 `fh:`。
- 2 Object Property：`fh:holds`、`fh:hasContactPoint`。
- 7 Data Property：`fh:mobileNumber`、countryCode、city、district、addressLine、postalCode、fullAddress。
- 手機號碼 domain 為 MobileContactInformation；其餘六欄為 AddressContactInformation；range 全為 xsd:string。
- 5 Annotation Property 保留，包括 `fh:department` 的詞彙宣告；沒有部門 OWL Class 或部門治理的實際定義。
- `build-config.json` 列出來源。`tools/build_ontology.py` 讀取來源後產生整合 TTL 及 RDF/XML，不再把模型寫死在 Python。
- `catalog-v001.xml` 只指向有效本體及 v0.3.0 版本。
- 原三家公司通聯 TTL 及 bank-business-contact.ttl 自有效根目錄移除，完整快照在 archive。未加 equivalentClass／equivalentProperty 相容公理。

### 部門 PG

- `department-pg/model.json` 為來源，`model.schema.json` 記載自訂交換格式。
- 兩個業務概念：貸款照會手機、客戶訪問地址，對應金控手機／地址類別與七個欄位。
- 模型共 18 metadata 節點、23 關係；有業務概念、RDF 類別／屬性參照、待確認來源映射槽。
- 部門名稱為 null；底表、欄位、SQL、JOIN、filter 均 pending/null，沒有假來源、客戶實例或可執行 SQL。
- `build_cypher.py` 離線產生 Neo4j 5 `model.cypher`，未匯入或修改任何 Neo4j。未建 A2A、Skill 或資料查詢服務。
- 此版建置契約刻意只允許上述兩個概念及 pending 來源；正式確認來源或新增概念後需同步擴充模型、schema、建置驗證與測試。

## 建置與驗證

本目錄 `.venv` 已安裝 `rdflib==7.6.0`，依賴在 requirements.txt，不修改系統 Python。

```powershell
.venv\Scripts\python.exe -B tools\build_ontology.py
.venv\Scripts\python.exe -B tools\build_ontology.py --check
.venv\Scripts\python.exe -B department-pg\build_cypher.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.venv\Scripts\python.exe -B -m unittest discover -s department-pg -v
```

RDF 9 項與 PG 13 項測試全部通過，無略過。已以通用 rdflib 解析來源 TTL、整合 TTL、RDF/XML，檢查圖同構及結構契約。整合圖目前 100 triples，非固定驗收目標。未執行完整 OWL reasoner、可滿足性／一致性檢查、SHACL、GUI、SQL、真實資料或 Neo4j 部署。

勿執行 `tools/legacy-v0.2.0/` 的舊建置／驗證流程；舊 232 triples 與舊 validation.json 不適用新版。

## 仍在討論，尚未實作

金融商品盤點已參考私銀 `ontology/independent_concepts/concept_graph.json` 的 25 個產品與服務，以及客戶360 Excel。尚未將它們全部核定為 Class。

- 已同意省略「銀行金融商品」中間層；由具體商品分類直接承接金控金融商品。討論了存款商品、台幣／外幣金融商品及存款商品的多重繼承，但尚未寫入 TTL。
- 商品結構與幣別是不同維度；結構型存款與 DCI 不直接等同，也未宣告互斥或保本條件。
- 討論集團職員、銀行行員，但尚未實作；行員是人員，不可與存款商品用多重繼承混成一類。
- 行員存款已確認指「行員以客戶身分持有的存款」，不是 AO 管理客戶的存款，也不限定員工優惠方案。部門 PG 可分別關聯行員與存款概念，不需將兩者做 OWL 多重繼承。
- 存款本輪範圍：台幣、外幣、結構型存款共用客戶識別、幣別、餘額、快照日期四項映射資料欄位；行員存款多保留行員識別。欄位設計已確認，來源映射仍有缺口；行員存款獨立 JSON 草稿見 `department-pg/drafts/employee-deposit.json`，不在正式 PG 建置輸入內。
- 分行／數位分類已明確移出本輪範圍，日後再討論；目前不新增其類別、Property 或映射。
- 先盤商品，再確認帳戶、契約、保單與持有部位；不強制所有商品經帳戶持有。
- 尚未核定反向關係、基數、互斥、等價、sameAs、keys、property chain、SHACL、格式、必填及碼表。
- 自然人情境不等於 Customer 已形式化等同 NaturalPerson。持有條件與時間範圍仍待確認。

## 安全與其他專案

需求清單：上層 `金控自然人客戶360.xlsx`，186 項，是需求參考，不是資料實例；未修改。
原 ChatGPT 同步專案及其 sources 保持唯讀。私銀、enterprise_kb_poc、既有 asset-financial-ontology 的程式、圖譜與資料都未修改。本次不製作簡報。
示意 URI 尚未核定；沒有可確認雲端備份，不宣稱已同步雲端。
