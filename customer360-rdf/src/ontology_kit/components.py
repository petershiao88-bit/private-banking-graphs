"""類別組成元件：從模組 TTL 抽出每個類別與屬性的組成，依 config 規則驗證。"""

from collections import deque

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .config import MATURITY_ORDER

# 元件名稱 → RDF 表示。順序即文件中的呈現順序。
COMPONENTS = [
    ("uri", "類別 URI（命名空間決定所屬層）", "必要"),
    ("label", "rdfs:label（config: components.label_lang）", "必要"),
    ("definition", "skos:definition", "必要"),
    ("governance_level", "fh:governanceLevel，須等於所屬層設定", "必要"),
    ("subsidiary", "fh:subsidiary，子公司層必填、金控層不得有", "依層"),
    ("parents", "具名 rdfs:subClassOf；子公司類別須能接到金控類別", "子公司層必要"),
    ("properties", "以本類別為 rdfs:domain 的 Object／Data Property", "選用"),
    ("module / maturity", "宣告所在模組及其 FIBO 成熟度", "由 config 決定"),
    ("deprecated / replaced_by", "owl:deprecated true＋dcterms:isReplacedBy", "下架時必要"),
]


def load_modules(entries):
    """entries: [(name, path, maturity)] → (merged graph, {uri: (module, maturity)})."""
    merged = Graph()
    owner = {}
    for name, path, maturity in entries:
        graph = Graph().parse(path, format="turtle")
        for prefix, namespace in graph.namespaces():
            merged.bind(prefix, namespace, override=False)
        for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
            for subject in graph.subjects(RDF.type, kind):
                if isinstance(subject, URIRef):
                    owner.setdefault(str(subject), (name, maturity))
        merged += graph
    return merged, owner


def config_entries(cfg, modules=None):
    return [(m.file, m.path, m.maturity) for m in (modules or cfg.modules)]


def _texts(graph, subject, predicate):
    return [o for o in graph.objects(subject, predicate) if isinstance(o, Literal)]


def _pick(values, lang):
    preferred = sorted(str(v) for v in values if v.language == lang)
    return preferred[0] if preferred else (sorted(str(v) for v in values)[0] if values else None)


def _deprecated(graph, subject):
    return any(isinstance(o, Literal) and o.toPython() is True for o in graph.objects(subject, OWL.deprecated))


def extract(graph, owner, cfg):
    lang = cfg.components["label_lang"]
    governance = URIRef(cfg.annotations["governance_level"])
    subsidiary = URIRef(cfg.annotations["subsidiary"])
    replaced = URIRef(cfg.annotations["replaced_by"])

    def common(uri):
        subject = URIRef(uri)
        layer = cfg.layer_of(uri)
        module, maturity = owner.get(uri, (None, None))
        labels = _texts(graph, subject, RDFS.label)
        return {
            "id": cfg.curie(uri), "uri": uri, "layer": layer.key if layer else None,
            "module": module, "maturity": maturity,
            "label": _pick(labels, lang), "label_has_lang": any(v.language == lang for v in labels),
            "definition": _pick(_texts(graph, subject, SKOS.definition), lang),
            "governance_level": _pick(_texts(graph, subject, governance), None),
            "subsidiary": _pick(_texts(graph, subject, subsidiary), None),
            "deprecated": _deprecated(graph, subject),
            "replaced_by": sorted(str(o) for o in graph.objects(subject, replaced)),
        }

    properties = []
    for kind, tag in ((OWL.ObjectProperty, "object"), (OWL.DatatypeProperty, "datatype")):
        for subject in sorted(s for s in graph.subjects(RDF.type, kind) if isinstance(s, URIRef)):
            record = common(str(subject))
            record.update(kind=tag,
                          domain=sorted(str(o) for o in graph.objects(subject, RDFS.domain)),
                          range=sorted(str(o) for o in graph.objects(subject, RDFS.range)))
            properties.append(record)

    classes = []
    for subject in sorted(s for s in graph.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)):
        uri = str(subject)
        record = common(uri)
        parents = list(graph.objects(subject, RDFS.subClassOf))
        record.update(
            parents=sorted(str(p) for p in parents if isinstance(p, URIRef)),
            anonymous_parents=sum(1 for p in parents if not isinstance(p, URIRef)),
            properties=sorted(p["uri"] for p in properties if uri in p["domain"]),
        )
        classes.append(record)
    return classes, properties


def asserted_ancestors(classes):
    parents = {c["uri"]: c["parents"] for c in classes}
    result = {}
    for start in parents:
        seen, queue = {}, deque([(p, 1) for p in parents[start]])
        while queue:
            node, distance = queue.popleft()
            if node in seen:
                continue
            seen[node] = distance
            queue.extend((p, distance + 1) for p in parents.get(node, []))
        result[start] = seen
    return result


def validate(classes, properties, cfg):
    issues = []

    def add(level, record, rule, message):
        issues.append({"level": level, "id": record["id"], "rule": rule, "message": message})

    declared = {c["uri"]: c for c in classes}
    ancestors = asserted_ancestors(classes)
    required = set(cfg.components["required"])
    must_reach = cfg.components.get("must_reach_layer")
    rank = {level: i for i, level in enumerate(MATURITY_ORDER)}

    for record in [*classes, *properties]:
        layer = cfg.layers.get(record["layer"]) if record["layer"] else None
        if layer is None:
            add("error", record, "namespace", "命名空間不屬於 config.layers 任何一層")
            continue
        if "label" in required and not record["label_has_lang"]:
            add("error", record, "label", f"缺少 {cfg.components['label_lang']} 的 rdfs:label")
        if "definition" in required and not record["definition"]:
            add("error", record, "definition", "缺少 skos:definition")
        if "governance_level" in required and record["governance_level"] != layer.governance_level:
            add("error", record, "governance_level",
                f"治理層級應為「{layer.governance_level}」，實際為「{record['governance_level']}」")
        if layer.subsidiary and record["subsidiary"] != layer.subsidiary:
            add("error", record, "subsidiary", f"子公司應為「{layer.subsidiary}」，實際為「{record['subsidiary']}」")
        if not layer.subsidiary and record["subsidiary"]:
            add("error", record, "subsidiary", "金控層不得標示子公司")
        for target in record["replaced_by"]:
            if target not in declared and target not in {p["uri"] for p in properties}:
                add("error", record, "replaced_by", f"取代者未宣告：{target}")
        if record["deprecated"] and not record["replaced_by"]:
            add("warning", record, "deprecated", "已 deprecated 但沒有標取代者（dcterms:isReplacedBy）")

    for record in classes:
        if record["layer"] is None:
            continue
        if record["anonymous_parents"]:
            add("error", record, "parents", "含匿名 rdfs:subClassOf（restriction 等），不在組成元件模型內")
        for parent in record["parents"]:
            if parent not in declared:
                add("error", record, "parents", f"上層類別未宣告：{parent}")
                continue
            if declared[parent]["deprecated"] and not record["deprecated"]:
                add("error", record, "parents", f"上層 {declared[parent]['id']} 已 deprecated")
            mine, theirs = record["maturity"], declared[parent]["maturity"]
            if mine in rank and theirs in rank and rank[theirs] > rank[mine]:
                add("error", record, "maturity",
                    f"{mine} 類別不可依賴成熟度較低（{theirs}）的上層 {declared[parent]['id']}")
        if record["uri"] in ancestors[record["uri"]]:
            add("error", record, "cycle", "rdfs:subClassOf 形成循環")
        layer = cfg.layers[record["layer"]]
        if layer.subsidiary and must_reach and not any(
                declared.get(a, {}).get("layer") == must_reach for a in ancestors[record["uri"]]):
            add("error", record, "must_reach_layer", f"子公司類別必須經 subClassOf 接到 {must_reach} 層類別")

    for record in properties:
        if record["layer"] is None:
            continue
        if not record["domain"]:
            add("error", record, "domain", "屬性缺少 rdfs:domain")
        for uri in record["domain"] + (record["range"] if record["kind"] == "object" else []):
            if uri not in declared:
                add("error", record, "domain_range", f"domain／range 類別未宣告：{uri}")
    return sorted(issues, key=lambda i: (i["level"], i["id"], i["rule"]))


def build(cfg, modules=None):
    graph, owner = load_modules(config_entries(cfg, modules))
    classes, properties = extract(graph, owner, cfg)
    return graph, classes, properties, validate(classes, properties, cfg)


def render_markdown(cfg, classes, properties, issues, version):
    by_uri = {c["uri"]: c for c in classes}
    props = {p["uri"]: p for p in properties}
    errors = sum(i["level"] == "error" for i in issues)
    warnings = sum(i["level"] == "warning" for i in issues)
    lines = [f"# 類別組成元件（v{version}）", "",
             f"類別 {len(classes)}、Object Property {sum(p['kind'] == 'object' for p in properties)}、"
             f"Data Property {sum(p['kind'] == 'datatype' for p in properties)}。"
             f"驗證：{errors} 個錯誤、{warnings} 個警告。", "",
             "## 一個類別由哪些元件組成", "", "| 元件 | RDF 表示 | 要求 |", "|---|---|---|"]
    lines += [f"| {name} | {rdf} | {need} |" for name, rdf, need in COMPONENTS]
    if issues:
        lines += ["", "## 驗證問題", "", "| 等級 | ID | 規則 | 說明 |", "|---|---|---|---|"]
        lines += [f"| {i['level']} | `{i['id']}` | {i['rule']} | {i['message']} |" for i in issues]
    for key, layer in cfg.layers.items():
        members = [c for c in classes if c["layer"] == key]
        if not members:
            continue
        lines += ["", f"## {layer.title}（`{layer.prefix}:`，{len(members)} 類）", "",
                  "| 類別 | ID | 直接上層 | 模組／成熟度 | 以此為 domain 的屬性 | 定義 |", "|---|---|---|---|---|---|"]
        for c in members:
            parents = "、".join(by_uri[p]["label"] if p in by_uri else cfg.curie(p) for p in c["parents"]) or "—"
            owned = "、".join(props[p]["label"] or cfg.curie(p) for p in c["properties"]) or "—"
            name = c["label"] + ("（deprecated）" if c["deprecated"] else "")
            definition = (c["definition"] or "").replace("|", "／").replace("\n", " ")
            lines.append(f"| {name} | `{c['id']}` | {parents} | {c['module']}／{c['maturity']} | {owned} | {definition} |")
    lines += ["", "## 屬性", "", "| 屬性 | ID | 種類 | domain | range |", "|---|---|---|---|---|"]
    for p in properties:
        domain = "、".join(by_uri[d]["label"] if d in by_uri else cfg.curie(d) for d in p["domain"])
        rng = "、".join(by_uri[r]["label"] if r in by_uri else cfg.curie(r) for r in p["range"])
        lines.append(f"| {p['label']} | `{p['id']}` | {p['kind']} | {domain} | {rng} |")
    return "\n".join(lines) + "\n"
