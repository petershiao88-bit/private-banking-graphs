客戶360 RDF／OWL v0.2.0
日期：2026-10-21
狀態：依目前共識撰寫的設計草案。正式URI與部署方式尚未核定。

一、建議開啟方式
直接開啟 customer360-ontology.owl（RDF/XML），或閱讀 customer360-ontology.ttl（Turtle）。
兩份檔案表示同一張OWL本體RDF圖；不是兩套模型，也不是先寫RDF再另外複製一套OWL。
這兩份是自含整合版，不需要從示意網址下載其他本體。

二、分層來源檔
holding-core.ttl：金控3個核心類別、2個Object Property與5個Annotation Property。
bank-contact.ttl：銀行手機、地址兩個類別，以及7個Data Property。
securities-contact.ttl：證券手機、地址兩個類別，以及7個Data Property。
life-contact.ttl：人壽手機、地址兩個類別，以及7個Data Property。
分層檔透過owl:imports引用金控核心；catalog-v001.xml將示意本體URI對應到同目錄檔案。
支援OASIS catalog的本體編輯器可使用此對應；本次未進行特定GUI編輯器的載入測試。

三、模型清單
金控Class：Customer（客戶）、FinancialProduct（金融商品）、ContactInformation（通聯資訊）。
Object Property：holds、hasContactPoint；domain為Customer，range分別是FinancialProduct及ContactInformation。
Annotation Property：rdfs:label、skos:definition、fh:governanceLevel、fh:subsidiary、fh:department。
金控層目前沒有必備Data Property。
子公司直接定義MobileContactInformation及AddressContactInformation；六個子類別都直接subClassOf金控ContactInformation。
不另外建立公司通聯資訊中間類別，也不另建金控手機／地址類別。
每家子公司分別定義下列7個Data Property，range皆為xsd:string：
mobileNumber：手機號碼。
countryCode：國家／地區代碼，代碼標準待定。
city：縣市。
district：鄉鎮市區。
addressLine：路街段、巷弄、門牌、樓層等詳細地址。
postalCode：郵遞區號。
fullAddress：完整地址。
mobileNumber的domain是該公司MobileContactInformation；其餘六個屬性的domain是該公司AddressContactInformation。

四、治理與資料邊界
金控定義共通語意；子公司負責共用客戶基本資料及其映射，部門負責業務資料與情境延伸。
此分工取代舊交接文件「只有部門才能直接映射底表」的限制；本次不改動舊版交接檔案。
子公司先依自己系統建立golden record，本體承接其權威通聯資料。
golden record不強制等於每人僅一筆地址或手機；不同用途可以有不同紀錄。
本版不加入Hash／代碼化欄位、有效註記、優先順序或golden record計算規則。
Annotation標示模型定義的治理歸屬，不會自動變成實例層來源屬性；映射與資料服務仍需保留紀錄來源。
公司別類型及命名空間不等於授權或存取控制。
跨公司號碼或地址相同不代表自動合併紀錄；不同來源內容差異繼續保留。

五、本次未擴充
未新增Party完整分類、子公司客戶類別、商品分類示例、部門類別或業務指標。
未建立CustomerRelationship或FinancialPosition必要中介。
未指定最小／最大基數、FunctionalProperty、反向關係、互斥、等價或sameAs。
未強制所有字串欄位必填、countryCode碼表、手機國碼格式或國際地址拆分規則。
domain/range用於型別語意與推論，不是輸入拒絕規則。
完整地址與拆分欄位未定義同步或組合函數。
沒有SHACL、實際資料、資料庫SQL/API連線、資料映射或Skill執行邏輯。
目前僅在使用情境上聚焦自然人，未形式化Customer等同NaturalPerson。
本體名稱、英文技術名稱與example.org命名空間是本次實作使用的暫定識別資訊。

六、參考標準
Turtle：https://www.w3.org/TR/turtle/
OWL 2 Primer：https://www.w3.org/TR/owl2-primer/
OWL 2 Mapping to RDF Graphs：https://www.w3.org/TR/owl2-mapping-to-rdf/
XSD Datatypes：https://www.w3.org/TR/xmlschema11-2/

七、實際驗證結果
5份Turtle檔經獨立解析檢查；解析器僅覆蓋本次輸出的語法子集，不是通用Turtle實作。
RDF/XML經標準XML解析；還原後與整合Turtle及建構參考圖逐三元組完全一致，共232個三元組。
類別數、三種Property宣告、domain/range、各子公司直接繼承與治理註記檢查通過。
檢查未包含代碼化、有效註記、未核定基數、互斥、反向或等價公理。
本機catalog所對應的引用檔案均存在。
以暫存虛構資料驗證RDFS的subclass、domain與range推導：6筆銀證壽手機／地址紀錄皆可推得通聯資訊類型。
虛構測試資料未寫入交付本體。
目前環境未提供可用的完整RDF／OWL套件，未執行專用OWL推論器的一致性檢查，亦未進行GUI編輯器測試。
