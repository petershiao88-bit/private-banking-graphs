from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs' / 'customer360-ontology-20261021'
OUT.mkdir(parents=True, exist_ok=True)
VERSION = '0.2.0'
NS = {
    'fh': 'https://example.org/ontology/holding#',
    'bank': 'https://example.org/ontology/bank#',
    'sec': 'https://example.org/ontology/securities#',
    'life': 'https://example.org/ontology/life#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
}


def uri(name):
    if name.startswith(('http://', 'https://')):
        return name
    prefix, local = name.split(':', 1)
    return NS[prefix] + local


def U(name):
    return ('uri', uri(name), '', '')


def L(value, lang=''):
    return ('literal', value, lang, '')


def add(g, subject, predicate, obj):
    g.add((uri(subject), uri(predicate), obj))


def describe(g, name, kind, label, definition, level, company=None):
    add(g, name, 'rdf:type', U(kind))
    add(g, name, 'rdfs:label', L(label, 'zh-TW'))
    add(g, name, 'skos:definition', L(definition, 'zh-TW'))
    add(g, name, 'fh:governanceLevel', L(level))
    if company:
        add(g, name, 'fh:subsidiary', L(company))


def ontology_header(g, iri, title, description, parent=None):
    add(g, iri, 'rdf:type', U('owl:Ontology'))
    add(g, iri, 'owl:versionIRI', U(iri + '/' + VERSION))
    add(g, iri, 'owl:versionInfo', L(VERSION + ' / design draft / 2026-10-21'))
    add(g, iri, 'rdfs:label', L(title, 'zh-TW'))
    add(g, iri, 'rdfs:comment', L(description, 'zh-TW'))
    if parent:
        add(g, iri, 'owl:imports', U(parent))


core_iri = NS['fh'][:-1]
core = set()
ontology_header(core, core_iri, '客戶360金控核心本體',
                 '依本次討論整理的設計草案。命名空間為示意URI；實際資料映射與golden record整理由子公司或部門系統負責。')

annotations = [
    ('rdfs:label', '名稱', '提供類別或屬性的顯示名稱。'),
    ('skos:definition', '定義', '提供類別或屬性的業務意義描述。'),
    ('fh:governanceLevel', '治理層級', '標示定義所屬層級；本案約定使用金控、子公司或部門。'),
    ('fh:subsidiary', '所屬子公司', '標示類別或屬性定義的子公司治理歸屬；不適用時省略。'),
    ('fh:department', '所屬部門', '標示類別或屬性定義的部門治理歸屬；不適用時省略。'),
]
for name, label, definition in annotations:
    describe(core, name, 'owl:AnnotationProperty', label, definition, '金控')

classes = [
    ('fh:Customer', '客戶', '集團業務中所服務的客戶；本次以自然人客戶為使用情境，尚未形式化自然人範圍限制。'),
    ('fh:FinancialProduct', '金融商品', '供各子公司延伸具體商品分類的共同上位概念。'),
    ('fh:ContactInformation', '通聯資訊', '由來源單位記錄、與客戶相關的通聯資訊。'),
]
for name, label, definition in classes:
    describe(core, name, 'owl:Class', label, definition, '金控')

object_properties = [
    ('fh:holds', '持有金融商品', '表達客戶持有金融商品的關係；具體持有認定、基數與時間範圍尚待後續確認。', 'fh:FinancialProduct'),
    ('fh:hasContactPoint', '具有通聯資訊', '連接客戶與來源單位所記錄、與該客戶相關的通聯紀錄；實際使用由下層系統提供的權威通聯資料承接。', 'fh:ContactInformation'),
]
for name, label, definition, target in object_properties:
    describe(core, name, 'owl:ObjectProperty', label, definition, '金控')
    add(core, name, 'rdfs:domain', U('fh:Customer'))
    add(core, name, 'rdfs:range', U(target))

data_specs = [
    ('mobileNumber', '手機號碼', 'MobileContactInformation', '該筆手機通聯紀錄的號碼字串，依來源保留國碼、前導零與其他必要字元；標準化格式尚未核定。'),
    ('countryCode', '國家／地區代碼', 'AddressContactInformation', '該筆地址所屬國家或地區的代碼；代碼標準尚待確認。'),
    ('city', '縣市', 'AddressContactInformation', '該筆地址的縣市，例如臺北市或新竹縣；國際地址的行政層級對應尚待確認。'),
    ('district', '鄉鎮市區', 'AddressContactInformation', '該筆地址的鄉鎮市區，例如大安區或竹北市。'),
    ('addressLine', '街道門牌地址', 'AddressContactInformation', '縣市與鄉鎮市區以外的詳細地址內容，可包含路、街、段、巷、弄、號、樓層與室等。'),
    ('postalCode', '郵遞區號', 'AddressContactInformation', '該筆地址的郵遞區號字串，保留前導零及必要字元；格式尚未限制。'),
    ('fullAddress', '完整地址', 'AddressContactInformation', '子公司提供的完整地址文字；本版未規定其由拆分欄位自動組合或互相同步。'),
]

modules = {'holding-core.ttl': core}
module_iris = {core_iri}
for prefix, company, filename in [
    ('bank', '銀行', 'bank-contact.ttl'),
    ('sec', '證券', 'securities-contact.ttl'),
    ('life', '人壽', 'life-contact.ttl'),
]:
    g = set()
    module_iri = NS[prefix][:-1]
    module_iris.add(module_iri)
    ontology_header(g, module_iri, company + '通聯資訊本體',
                     company + '負責共用客戶通聯資料的定義、golden record整理與實體資料映射；本檔僅定義語意模型，未連接實際系統。', core_iri)
    for local, label in [('MobileContactInformation', '手機通聯資訊'),
                         ('AddressContactInformation', '地址通聯資訊')]:
        name = prefix + ':' + local
        describe(g, name, 'owl:Class', company + label,
                 '由' + company + '整理及提供、與客戶相關的' + label + '，承接該公司系統建立的權威通聯資料。',
                 '子公司', company)
        add(g, name, 'rdfs:subClassOf', U('fh:ContactInformation'))
    for local, label, domain, definition in data_specs:
        name = prefix + ':' + local
        describe(g, name, 'owl:DatatypeProperty', label, definition, '子公司', company)
        add(g, name, 'rdfs:domain', U(prefix + ':' + domain))
        add(g, name, 'rdfs:range', U('xsd:string'))
    modules[filename] = g


def compact(iri):
    for prefix, base in NS.items():
        if iri.startswith(base) and iri[len(base):]:
            return prefix + ':' + iri[len(base):]
    return '<' + iri + '>'


def turtle_object(term):
    kind, value, lang, datatype = term
    if kind == 'uri':
        return compact(value)
    text = json.dumps(value, ensure_ascii=False)
    if lang:
        text += '@' + lang
    if datatype:
        text += '^^' + compact(datatype)
    return text


predicate_order = {uri(p): i for i, p in enumerate([
    'rdf:type', 'rdfs:subClassOf', 'rdfs:label', 'skos:definition',
    'rdfs:domain', 'rdfs:range', 'fh:governanceLevel', 'fh:subsidiary',
    'fh:department', 'owl:imports', 'owl:versionIRI', 'owl:versionInfo', 'rdfs:comment'])}


def turtle(g):
    lines = ['# 客戶360語意模型 v' + VERSION + '，2026-10-21，設計草案。',
             '# example.org 為示意命名空間；不是實際服務位址。',
             '# 本檔以 RDF/Turtle 表示 OWL 本體。', '']
    lines += [f'@prefix {p}: <{base}> .' for p, base in NS.items()]
    lines.append('')
    by_subject = defaultdict(list)
    for s, p, o in g:
        by_subject[s].append((p, o))
    for kind, heading in [
        ('owl:Ontology', '本體資訊'), ('owl:AnnotationProperty', 'Annotation Property：名稱、定義與治理歸屬'),
        ('owl:Class', 'Class：概念類別與繼承'), ('owl:ObjectProperty', 'Object Property：業務關係'),
        ('owl:DatatypeProperty', 'Data Property：字面資料值'),
    ]:
        subjects = sorted(s for s in by_subject if (s, uri('rdf:type'), U(kind)) in g)
        if not subjects:
            continue
        lines += ['', '# ' + '=' * 58, '# ' + heading, '# ' + '=' * 58, '']
        for s in subjects:
            lines.append(compact(s))
            pairs = sorted(by_subject[s], key=lambda pair: (predicate_order.get(pair[0], 99), pair[0], pair[1]))
            for index, (p, o) in enumerate(pairs):
                predicate = 'a' if p == uri('rdf:type') else compact(p)
                ending = ' .' if index == len(pairs) - 1 else ' ;'
                lines.append('    ' + predicate + ' ' + turtle_object(o) + ending)
            lines.append('')
    return '\n'.join(lines) + '\n'


def write_xml(g, path):
    for prefix, base in NS.items():
        ET.register_namespace(prefix, base)
    root = ET.Element('{' + NS['rdf'] + '}RDF')
    by_subject = defaultdict(list)
    for s, p, o in g:
        by_subject[s].append((p, o))
    for s in sorted(by_subject):
        el = ET.SubElement(root, '{' + NS['rdf'] + '}Description', {'{' + NS['rdf'] + '}about': s})
        for p, o in sorted(by_subject[s]):
            tag_prefix = next(base for base in NS.values() if p.startswith(base))
            prop = ET.SubElement(el, '{' + tag_prefix + '}' + p[len(tag_prefix):])
            kind, value, lang, datatype = o
            if kind == 'uri':
                prop.set('{' + NS['rdf'] + '}resource', value)
            else:
                prop.text = value
                if lang:
                    prop.set('{http://www.w3.org/XML/1998/namespace}lang', lang)
                if datatype:
                    prop.set('{' + NS['rdf'] + '}datatype', datatype)
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


for filename, g in modules.items():
    (OUT / filename).write_text(turtle(g), encoding='utf-8')

# Consolidated exports contain one ontology header and no network imports.
combined = {t for g in modules.values() for t in g if t[0] not in module_iris}
bundle_iri = 'https://example.org/ontology/customer360'
ontology_header(combined, bundle_iri, '客戶360核心與通聯資訊整合本體',
                 '金控核心與銀行、證券、人壽通聯模型的自含整合版。子公司先完成golden record整理，再映射共用基本資料；部門承接並映射業務資料。')
(OUT / 'customer360-ontology.ttl').write_text(turtle(combined), encoding='utf-8')
write_xml(combined, OUT / 'customer360-ontology.owl')

catalog_ns = 'urn:oasis:names:tc:entity:xmlns:xml:catalog'
ET.register_namespace('', catalog_ns)
catalog = ET.Element('{' + catalog_ns + '}catalog', {'prefer': 'public'})
for filename, g in modules.items():
    iri = next(s for s, p, o in g if p == uri('rdf:type') and o == U('owl:Ontology'))
    for name in (iri, iri + '/' + VERSION):
        ET.SubElement(catalog, '{' + catalog_ns + '}uri', {'name': name, 'uri': filename})
ET.indent(catalog, space='  ')
ET.ElementTree(catalog).write(OUT / 'catalog-v001.xml', encoding='utf-8', xml_declaration=True)

readme = '''客戶360 RDF／OWL v0.2.0
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
'''
(OUT / 'README.txt').write_text(readme, encoding='utf-8')

# Persist a scratch-only reference graph for independent parsers and verification.
reference = {'namespaces': NS, 'graphs': {name: sorted(g) for name, g in modules.items()},
             'combined': sorted(combined)}
(Path(__file__).parent / 'reference-graph.json').write_text(json.dumps(reference, ensure_ascii=False), encoding='utf-8')
files = [str(OUT / name) for name in ['customer360-ontology.ttl', 'customer360-ontology.owl',
         'holding-core.ttl', 'bank-contact.ttl', 'securities-contact.ttl', 'life-contact.ttl',
         'catalog-v001.xml', 'README.txt']]
(Path(__file__).parent / 'upload-request.json').write_text(json.dumps({'uploads': [
    {'local_path': path, 'purpose': 'create_library_file', 'library_artifact_type': 'other'} for path in files
]}, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'files': files, 'class_count': 9, 'object_property_count': 2,
                  'data_property_count': 21, 'annotation_property_count': 5,
                  'combined_triples': len(combined)}, ensure_ascii=True))
