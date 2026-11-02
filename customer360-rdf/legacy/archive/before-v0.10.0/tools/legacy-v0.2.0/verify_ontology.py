"""Verify the emitted Turtle subset, RDF/XML graph and agreed schema.

This is deliberately not a general-purpose Turtle parser or OWL reasoner.
It independently parses exactly the syntax used by these no-blank-node files.
"""
import json
import re
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'outputs' / 'customer360-ontology-20261021'
reference = json.loads((HERE / 'reference-graph.json').read_text(encoding='utf-8'))
NS = reference['namespaces']


def term_uri(value):
    return ('uri', value, '', '')


def expand(value, prefixes):
    if value.startswith('<'):
        return value[1:-1]
    prefix, local = value.split(':', 1)
    return prefixes[prefix] + local


def parse_turtle(path):
    source = path.read_text(encoding='utf-8')
    token_re = re.compile(
        r'\s+|\#[^\n]*|@prefix\b|<[^<>\s]*>|'
        r'"(?:[^"\\\r\n]|\\["\\/bfnrt]|\\u[0-9A-Fa-f]{4})*"|'
        r'@[A-Za-z]+(?:-[A-Za-z0-9]+)*|\^\^|'
        r'[A-Za-z_][A-Za-z0-9_-]*:[A-Za-z0-9_-]*|\ba\b|[;,.]')
    tokens = []
    pos = 0
    while pos < len(source):
        m = token_re.match(source, pos)
        assert m, f'Unsupported/invalid Turtle token at {path.name}:{pos}'
        token = m.group()
        pos = m.end()
        if not token.isspace() and not token.startswith('#'):
            tokens.append(token)
    cursor = 0
    prefixes = {}

    def take():
        nonlocal cursor
        assert cursor < len(tokens), 'Unexpected Turtle EOF'
        token = tokens[cursor]
        cursor += 1
        return token

    while cursor < len(tokens) and tokens[cursor] == '@prefix':
        take()
        key, value, end = take(), take(), take()
        assert key.endswith(':') and value.startswith('<') and end == '.'
        assert key[:-1] not in prefixes
        prefixes[key[:-1]] = value[1:-1]
    graph = set()
    while cursor < len(tokens):
        subject = expand(take(), prefixes)
        more_predicates = True
        while more_predicates:
            predicate_token = take()
            predicate = NS['rdf'] + 'type' if predicate_token == 'a' else expand(predicate_token, prefixes)
            more_objects = True
            while more_objects:
                token = take()
                if token.startswith('"'):
                    value = json.loads(token)
                    lang, datatype = '', ''
                    if cursor < len(tokens) and tokens[cursor].startswith('@'):
                        lang = take()[1:]
                    elif cursor < len(tokens) and tokens[cursor] == '^^':
                        take()
                        datatype = expand(take(), prefixes)
                    obj = ('literal', value, lang, datatype)
                else:
                    obj = term_uri(expand(token, prefixes))
                graph.add((subject, predicate, obj))
                end = take()
                assert end in (',', ';', '.'), f'Invalid Turtle delimiter: {end}'
                more_objects = end == ','
            more_predicates = end == ';'
    return graph


def parse_xml(path):
    root = ET.parse(path).getroot()
    assert root.tag == '{' + NS['rdf'] + '}RDF'
    graph = set()
    for desc in root:
        assert desc.tag == '{' + NS['rdf'] + '}Description'
        subject = desc.attrib['{' + NS['rdf'] + '}about']
        for prop in desc:
            base, local = prop.tag[1:].split('}', 1)
            predicate = base + local
            target = prop.get('{' + NS['rdf'] + '}resource')
            if target is not None:
                obj = term_uri(target)
            else:
                obj = ('literal', prop.text or '',
                       prop.get('{http://www.w3.org/XML/1998/namespace}lang', ''),
                       prop.get('{' + NS['rdf'] + '}datatype', ''))
            graph.add((subject, predicate, obj))
    return graph


def reference_graph(rows):
    return {(s, p, tuple(o)) for s, p, o in rows}


graphs = {}
for name, rows in reference['graphs'].items():
    graphs[name] = parse_turtle(OUT / name)
    assert graphs[name] == reference_graph(rows), name + ' graph mismatch'
combined = parse_turtle(OUT / 'customer360-ontology.ttl')
xml_graph = parse_xml(OUT / 'customer360-ontology.owl')
assert combined == xml_graph == reference_graph(reference['combined'])

TYPE = NS['rdf'] + 'type'
SUBCLASS = NS['rdfs'] + 'subClassOf'
DOMAIN = NS['rdfs'] + 'domain'
RANGE = NS['rdfs'] + 'range'
OW = NS['owl']
FH = NS['fh']


def subjects_of(kind):
    return {s for s, p, o in combined if p == TYPE and o == term_uri(OW + kind)}


classes = subjects_of('Class')
objects = subjects_of('ObjectProperty')
data = subjects_of('DatatypeProperty')
annotations = subjects_of('AnnotationProperty')
assert (len(classes), len(objects), len(data), len(annotations)) == (9, 2, 21, 5)
assert not (objects & data or objects & annotations or data & annotations)
assert objects == {FH + 'holds', FH + 'hasContactPoint'}
assert not any(s.startswith(FH) for s in data)
assert annotations == {NS['rdfs'] + 'label', NS['skos'] + 'definition',
                       FH + 'governanceLevel', FH + 'subsidiary', FH + 'department'}
assert {s for s in classes if s.startswith(FH)} == {
    FH + 'Customer', FH + 'FinancialProduct', FH + 'ContactInformation'}
assert not any(p == OW + 'imports' for s, p, o in combined)
for prefix in ['bank', 'sec', 'life']:
    base = NS[prefix]
    for class_local in ['MobileContactInformation', 'AddressContactInformation']:
        parents = {o[1] for s, p, o in combined if s == base + class_local and p == SUBCLASS}
        assert parents == {FH + 'ContactInformation'}
    props = {s for s in data if s.startswith(base)}
    assert len(props) == 7
    assert {s[len(base):] for s in props} == {
        'mobileNumber', 'countryCode', 'city', 'district', 'addressLine', 'postalCode', 'fullAddress'}
    for prop in props:
        local = prop[len(base):]
        domain = base + ('MobileContactInformation' if local == 'mobileNumber' else 'AddressContactInformation')
        assert {o for s, p, o in combined if s == prop and p == DOMAIN} == {term_uri(domain)}
        assert {o for s, p, o in combined if s == prop and p == RANGE} == {term_uri(NS['xsd'] + 'string')}

for prop in objects:
    assert (prop, DOMAIN, term_uri(FH + 'Customer')) in combined
    target = 'FinancialProduct' if prop.endswith('holds') else 'ContactInformation'
    assert (prop, RANGE, term_uri(FH + target)) in combined

for entity in classes | objects | data | annotations:
    for predicate in ['rdfs:label', 'skos:definition', 'fh:governanceLevel']:
        prefix, local = predicate.split(':')
        assert any(s == entity and p == NS[prefix] + local for s, p, o in combined)

for s, p, o in combined:
    assert not any(banned.lower() in s.lower() for banned in [
        'Hash', 'isValid', 'hasValid', 'FinancialPosition', 'CustomerRelationship', 'BusinessMetric'])
    assert p not in {OW + name for name in ['sameAs', 'equivalentClass', 'disjointWith',
        'inverseOf', 'cardinality', 'minCardinality', 'maxCardinality']}
    assert not (p == TYPE and o[1] in {OW + 'FunctionalProperty', OW + 'InverseFunctionalProperty'})
    if p == SUBCLASS:
        assert s in classes and o[1] in classes

# Check import/catalog resolution without fetching placeholder IRIs.
catalog = ET.parse(OUT / 'catalog-v001.xml').getroot()
catalog_map = {node.attrib['name']: node.attrib['uri'] for node in catalog}
assert catalog_map[FH[:-1]] == 'holding-core.ttl'
for name, graph in graphs.items():
    for s, p, o in graph:
        if p == OW + 'imports':
            assert o[1] in catalog_map and (OUT / catalog_map[o[1]]).is_file()

# RDFS subclass/domain/range smoke test over scratch-only fictional records.
closure = set(combined)
customer = 'urn:test:customer:A'
records = []
for prefix in ['bank', 'sec', 'life']:
    for local in ['MobileContactInformation', 'AddressContactInformation']:
        record = 'urn:test:' + prefix + ':' + local
        records.append(record)
        closure.add((customer, FH + 'hasContactPoint', term_uri(record)))
        closure.add((record, TYPE, term_uri(NS[prefix] + local)))
product = 'urn:test:product:A'
closure.add((customer, FH + 'holds', term_uri(product)))
changed = True
while changed:
    additions = set()
    parents = [(s, o[1]) for s, p, o in closure if p == SUBCLASS]
    domains = [(s, o[1]) for s, p, o in closure if p == DOMAIN]
    ranges = [(s, o[1]) for s, p, o in closure if p == RANGE]
    types = [(s, o[1]) for s, p, o in closure if p == TYPE]
    for instance, cls in types:
        for child, parent in parents:
            if cls == child:
                additions.add((instance, TYPE, term_uri(parent)))
    for s, p, o in list(closure):
        for prop, cls in domains:
            if p == prop:
                additions.add((s, TYPE, term_uri(cls)))
        for prop, cls in ranges:
            if p == prop and o[0] == 'uri':
                additions.add((o[1], TYPE, term_uri(cls)))
    additions -= closure
    changed = bool(additions)
    closure.update(additions)
assert all((record, TYPE, term_uri(FH + 'ContactInformation')) in closure for record in records)
assert (customer, TYPE, term_uri(FH + 'Customer')) in closure
assert (product, TYPE, term_uri(FH + 'FinancialProduct')) in closure
assert len(set(records)) == 6

report = {
    'result': 'PASS', 'turtle_files_parsed': 5, 'rdf_xml_files_parsed': 1,
    'turtle_parser_scope': 'independent parser limited to the emitted Turtle syntax',
    'rdf_xml_turtle_graph_equality': True, 'combined_triples': len(combined),
    'classes': len(classes), 'object_properties': len(objects), 'data_properties': len(data),
    'annotation_properties': len(annotations), 'local_catalog_imports_resolve': True,
    'rdfs_smoke_test_records': 6, 'full_owl_reasoner': 'not run',
    'source_records_in_exports': False,
}
(HERE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
readme = OUT / 'README.txt'
text = readme.read_text(encoding='utf-8').split('\n七、實際驗證結果')[0]
text += '''
七、實際驗證結果
5份Turtle檔經獨立解析檢查；解析器僅覆蓋本次輸出的語法子集，不是通用Turtle實作。
RDF/XML經標準XML解析；還原後與整合Turtle及建構參考圖逐三元組完全一致，共232個三元組。
類別數、三種Property宣告、domain/range、各子公司直接繼承與治理註記檢查通過。
檢查未包含代碼化、有效註記、未核定基數、互斥、反向或等價公理。
本機catalog所對應的引用檔案均存在。
以暫存虛構資料驗證RDFS的subclass、domain與range推導：6筆銀證壽手機／地址紀錄皆可推得通聯資訊類型。
虛構測試資料未寫入交付本體。
目前環境未提供可用的完整RDF／OWL套件，未執行專用OWL推論器的一致性檢查，亦未進行GUI編輯器測試。
'''
readme.write_text(text, encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
