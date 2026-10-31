# 客戶360 RDF／OWL：Zed 接續開發交接

日期：2026-10-21  
目前本體版本：v0.2.0，設計草案  
目的：讓 Zed 接續編寫 RDF／OWL；ChatGPT Desktop 另負責簡報。

## 1. 先讀這一段

我們正在用客戶360需求清單萃取金控、子公司、部門的共通語意。目前只收斂客戶、金融商品、通聯資訊，以及子公司手機與地址的資料屬性，尚未建立完整客戶360本體。

接手時以本交接文件、目前本體檔案及使用者後續指示為準。早期規則檔中的「只有部門可映射實體資料」已經被本輪共識取代。不要把舊規則恢復回來，也不要把尚未核定的設計補成既定需求。

這個交接是編輯器／工作階段間的交接，不是 A2A 技術協定。

## 2. 工作分工與檔案位置

- **Zed**：接續編寫、整理與驗證 RDF／OWL；依使用者指示逐步擴充模型。
- **ChatGPT Desktop**：使用目前已確認的概念與架構製作簡報。這次交接本身不要求 Zed 製作簡報。
- 兩邊描述同一套模型；後續修改時需分清楚「已確認決議」「提議」「已實作」三種狀態。

### 建議在 Zed 開啟的本體工作資料夾

```text
C:\Users\petershiao\.codex\.chatgpt-projects\g-p-6a7c4e83c574819196c8491d29b0a6cd\outputs\customer360-ontology-20261021
```

### 專案工作根目錄

```text
C:\Users\petershiao\.codex\.chatgpt-projects\g-p-6a7c4e83c574819196c8491d29b0a6cd
```

根目錄的 `AGENTS.md` 仍須遵守。`sources/` 是唯讀的同步參考資料，不得編輯、改名、移動或刪除；不得修改其他同步專案檔案。

### 客戶360需求清單原檔

```text
C:\Users\petershiao\Desktop\Ontology\客戶360\金控自然人客戶360.xlsx
```

這是需求／欄位盤點清單，不是客戶實例資料。已讀取，含一張工作表、186個資料項目；分成客戶識別、通聯資訊、資產財力、接觸歷程、關係鏈、風險註記、維運管理七大項。Excel的大項不應自動各自轉成OWL類別；「資料來源」也不能直接視為概念治理層級。僅作參考，不在此交接中改動。

先前企業知識庫PoC位於 `C:\Users\petershiao\Desktop\Ontology\enterprise_kb_poc`，目前這批本體檔案尚未整合回該PoC，也未修改其HTML或程式。

## 3. 目前交付檔案

以下相對路徑均以本交接文件所在資料夾為基準。

| 檔案 | 用途 |
| --- | --- |
| `holding-core.ttl` | 金控核心：3個Class、2個Object Property、5個Annotation Property |
| `bank-contact.ttl` | 銀行手機與地址類別，7個Data Property |
| `securities-contact.ttl` | 證券手機與地址類別，7個Data Property |
| `life-contact.ttl` | 人壽手機與地址類別，7個Data Property |
| `customer360-ontology.ttl` | 自含的整合Turtle版，含上述四個模組的模型內容 |
| `customer360-ontology.owl` | 與整合Turtle表達同一張圖的RDF/XML版 |
| `catalog-v001.xml` | 分層模組本體URI對應到本機檔案的catalog |
| `README.txt` | 使用方式、模型範圍及驗證限制 |
| `HANDOFF-ZED-RDF-20261021.md` | 本交接文件 |

### 來源與匯出維護

目前分層TTL及整合版都已產生。後續建議以四份分層TTL作為編輯來源，再透過一致的建置流程產生整合TTL與RDF/XML，不要分別手改多份版本。

上一階段使用的暫存工具位於專案根目錄：

```text
.tmp-ontology-authoring-20261021\build_ontology.py
.tmp-ontology-authoring-20261021\verify_ontology.py
.tmp-ontology-authoring-20261021\reference-graph.json
.tmp-ontology-authoring-20261021\validation.json
```

**重要：目前的 `build_ontology.py` 將v0.2.0定義寫在程式中，重跑會覆寫本體檔案。修改TTL後，不要直接重跑舊建置器。** 建議接手後先讓建置流程改為讀取四份分層TTL；若仍採程式產生方式，則需同步更新程式內的模型定義。不要同時維護兩套互相矛盾的權威來源。

舊驗證腳本會與v0.2.0參考圖比對。合法變更模型時需同步更新測試基準；232個三元組只是當時版本的數量，不是後續必須維持的目標。

## 4. 已確認的三層分工

| 層級 | 語意及資料責任 |
| --- | --- |
| 金控 | 制定穩定的共同核心概念、關係及治理標記；不直接映射底表 |
| 子公司 | 定義公司共用的客戶基本資料，建立及維護映射，提供部門使用 |
| 部門 | 承接共用客戶資料；定義情境專屬概念，映射業務資料 |

客戶基本資料與通聯資訊由子公司統一處理，無須為接底表刻意增加部門子類別。其他業務資料由對應部門承接；個別資料歸屬仍須依業務用途確認。

子公司核心類別以 `rdfs:subClassOf` 承接金控核心。不要用 `owl:equivalentClass`、`owl:sameAs` 或 `partOf` 取代這個跨層繼承關係。這項約定針對類別繼承，不是把所有業務關係都改成subclass。

## 5. 目前實作的金控核心

| URI縮寫 | 類型 | 意義 |
| --- | --- | --- |
| `fh:Customer` | Class | 客戶；本次使用情境聚焦自然人，未形式化等同NaturalPerson |
| `fh:FinancialProduct` | Class | 金融商品共同上位概念 |
| `fh:ContactInformation` | Class | 來源單位所記錄、與客戶相關的通聯資訊 |

### Object Property

| 屬性 | domain | range | 定義／邊界 |
| --- | --- | --- | --- |
| `fh:holds` | `fh:Customer` | `fh:FinancialProduct` | 客戶持有金融商品；具體持有認定、基數與時間範圍待確認 |
| `fh:hasContactPoint` | `fh:Customer` | `fh:ContactInformation` | 客戶具有通聯資訊；容許來源不同的多筆紀錄，不指定唯一或優先使用的一筆 |

目前採用客戶直接連接金融商品及通聯紀錄。沒有必要的CustomerRelationship或FinancialPosition中介類別，也不額外替每位客戶建立「通聯資訊總包」節點。

### 金控Data Property

目前沒有核定必備清單。這是本階段範圍，不代表理論上金控不能定義Data Property。

### Annotation Property

| 屬性 | 用途 |
| --- | --- |
| `rdfs:label` | 名稱 |
| `skos:definition` | 業務定義 |
| `fh:governanceLevel` | 金控／子公司／部門 |
| `fh:subsidiary` | 銀行／證券／人壽等治理歸屬 |
| `fh:department` | 部門治理歸屬 |

金控定義填治理層級，子公司及部門不適用時不填。子公司定義填治理層級與子公司；部門定義再加所屬部門。目前沒有部門類別實例，因此尚無實際部門值。

治理Annotation描述的是模型定義的歸屬，不是實例紀錄來源。Annotation不會自動繼承成每筆資料的來源欄位，也不會建立資料存取權限。

## 6. 通聯資訊分類：採用的最終方案

每家子公司直接建立手機與地址類別，全部繼承金控的 `fh:ContactInformation`：

| 子公司 | Class | 父類別 |
| --- | --- | --- |
| 銀行 | `bank:MobileContactInformation` | `fh:ContactInformation` |
| 銀行 | `bank:AddressContactInformation` | `fh:ContactInformation` |
| 證券 | `sec:MobileContactInformation` | `fh:ContactInformation` |
| 證券 | `sec:AddressContactInformation` | `fh:ContactInformation` |
| 人壽 | `life:MobileContactInformation` | `fh:ContactInformation` |
| 人壽 | `life:AddressContactInformation` | `fh:ContactInformation` |

先前討論過但未採用的方案：

- 金控另設手機／地址子類別，並讓實例同時具備公司與通聯種類兩個型別。
- 子公司先增加「銀行通聯資訊／人壽通聯資訊」中間類別，再往下分手機、地址。

目前不要恢復這兩個方案。使用者選擇現在這個簡單、直接的subclass架構。

銀行與人壽同一客戶留下不同內容是正常要容納的情況。繼承只能把它們歸入共同上位概念，不會選出正確值、合併紀錄或產生唯一集團通聯資料。相同的字面值也不能直接當成同一筆來源紀錄。

未來若需跨公司統一查「手機」，需要另訂明確分類或查詢條件；不能僅憑類別名稱自動獲得正式OWL推論。

## 7. 已確認的子公司Data Property

三家公司各自在自己的命名空間定義相同的一組欄位，總計21個Data Property。不能直接視為同一個URI，也未宣告equivalentProperty。

### 手機：每家公司1個

| 本地名稱 | 中文名稱 | domain | range |
| --- | --- | --- | --- |
| `mobileNumber` | 手機號碼 | 該公司的 `MobileContactInformation` | `xsd:string` |

保留國碼、前導零與必要字元。本次沒有指定E.164、號碼長度、正規表示式或其他標準化規則。

### 地址：每家公司6個

| 本地名稱 | 中文名稱 | domain | range |
| --- | --- | --- | --- |
| `countryCode` | 國家／地區代碼 | 該公司的 `AddressContactInformation` | `xsd:string` |
| `city` | 縣市 | 同上 | `xsd:string` |
| `district` | 鄉鎮市區 | 同上 | `xsd:string` |
| `addressLine` | 街道門牌地址，含路街段、巷弄、號、樓層等 | 同上 | `xsd:string` |
| `postalCode` | 郵遞區號 | 同上 | `xsd:string` |
| `fullAddress` | 完整地址文字 | 同上 | `xsd:string` |

國家代碼標準、國際地址行政層級對應、各欄位必填與否尚未核定。不要自行加成強制規範。完整地址與拆分欄位之間尚未定義同步或組合函數。村里、門牌、樓層等是否拆成更多欄位仍是後續候選。

### 使用者明確排除的內容

- 不加入手機／地址Hash或其他代碼化欄位。
- 目前不加入客戶層或紀錄層有效註記，包括 `isValid`、`hasValidMobileContact` 等。
- 有效性判斷、去重、來源衝突取捨與golden record整理交由子公司原系統處理。
- golden record不自動等於每人只有一筆地址／手機；不同用途是否保留多筆由子公司定義，本體尚未強制唯一性。

## 8. RDF／OWL／Turtle的技術共識

- RDF是圖資料模型；Turtle（`.ttl`）是文字表示方式。
- 本體已在TTL中使用 `owl:Class`、`owl:ObjectProperty`、`owl:DatatypeProperty`、`owl:AnnotationProperty` 等宣告。
- `rdfs:subClassOf`、`rdfs:domain`、`rdfs:range` 是目前使用的RDFS語意。
- `.ttl` 與 `.owl` 是相同整合模型的不同表示格式；目前 `.owl` 採RDF/XML，沒有另一套獨立的業務邏輯。
- `fh:`、`bank:`、`sec:`、`life:` 是本案自訂前綴，不是RDF公版；完整URI才是識別資訊。
- 目前所有 `https://example.org/ontology/...` 命名空間是示意URI，尚未核定正式網址。
- 前綴不自動產生治理、繼承、映射或權限效果。
- Data Property在模型定義中獨立宣告，透過domain描述主體類別；在實例資料中，屬性直接連到實例與字面值。
- domain/range可用於推得型別，不是排他使用白名單，也不會自動強制必填。
- OWL開放世界下，缺值不自動等於false或違規。
- 目前TTL按宣告種類分區排列。使用者問過為何Data Property未緊接Class；已說明檔案位置不影響語意。可依閱讀需求改成每個類別後面緊接其屬性，但使用者尚未明確要求重排。

## 9. 驗證狀態：請精確描述

目前模型：9個Class、2個Object Property、21個Data Property、5個Annotation Property；整合版232個三元組。

已做：

1. 5份TTL經獨立解析程式檢查；該程式僅支援本次實際輸出的Turtle語法子集。
2. RDF/XML經標準XML解析，再還原為三元組，與整合TTL及建構參考圖完全一致。
3. 檢查類別數、Property類型、domain/range、治理標記與跨層繼承。
4. 檢查沒有帶入代碼化、有效註記或未核定公理。
5. 確認catalog對應的本機檔案存在。
6. 以暫存虛構資料驗證RDFS的subclass、domain及range推導；六種子公司通聯紀錄都能推得金控通聯類型。

尚未做：

- 通用標準RDF解析器的完整語法驗證。
- 專用OWL推論器的一致性／可滿足性檢查。
- Protégé或其他GUI編輯器實測。
- SHACL驗證、真實資料映射、跨公司身分對齊、API／SQL／Skill執行測試。

上一階段環境無可用rdflib／owlrl，安裝嘗試也未成功。自訂解析及推論測試不可描述成「完整OWL驗證通過」。虛構測試資料未寫入交付本體。

## 10. 接手後建議順序

1. 閱讀本交接、四份分層TTL及README，確認現有模型與上述決議一致。
2. 整理單一來源的建置流程，防止重跑舊腳本覆蓋人工編輯。
3. 若Zed環境有可用的通用RDF解析器，先驗證TTL，並核對整合TTL與RDF/XML圖內容一致。需要推論檢查時，再採適合的推論工具，清楚說明驗證範圍。
4. 依使用者下一項指示漸進擴充。每次先確認業務定義、類別／Property種類及治理層級，再寫入模型。
5. 模型變更後同步更新整合匯出、說明與驗證基準。先以圖語意比對，避免僅比對文字順序。

尚未核定、不要自行加入：

- Party完整分類、子公司客戶分類、完整商品分類及業務指標。
- 持有的精確業務條件、反向關係、基數限制、互斥、等價、sameAs、keys、property chain。
- 任何SHACL必填、唯一性、格式、碼表或封閉形狀。
- 新的金控Data Property清單。
- 映射底表、真實客戶資料、golden record程式、Skill與A2A調度機制。

對科技長的呈報主軸仍是：以金控共通語意支援跨子公司、跨部門的Agent協作。具體Skill檢查及映射屬支撐內容。不得宣稱目前本體已自動驗證所有Skill業務邏輯或已接上實際資料。

## 11. 交付與儲存狀態

本體檔案已在上述本機路徑產生。先前批次雲端保存因DNS連線問題失敗，沒有可確認的成功Library寫入身分；請不要假設已完成雲端備份。延續本機檔案即可。

原有v0.1規則／交接檔案位於 `outputs\ontology-governance-20261021`。本輪沒有覆寫它們；其中映射責任與核心範圍已有更新，請以本文件反映的後續共識為準。

## 12. 可貼給Zed的接續指令

> 請先閱讀本資料夾的 HANDOFF-ZED-RDF-20261021.md、README.txt，以及holding-core.ttl、bank-contact.ttl、securities-contact.ttl、life-contact.ttl。接續維護客戶360 RDF／OWL v0.2.0。金控定義共通語意，子公司映射共用客戶基本資料，部門映射業務資料。通聯類別採子公司手機／地址直接繼承金控通聯資訊，手機1個、地址6個Data Property；不加入Hash與有效註記，golden record由子公司系統處理。先確認編輯來源與匯出流程，避免舊建置器覆寫手動修改；後續依我的指示逐項擴充。變更時明確區分Class、Object Property、Data Property、Annotation Property與類別繼承，保留未定案邊界。ChatGPT Desktop將另外負責簡報。
