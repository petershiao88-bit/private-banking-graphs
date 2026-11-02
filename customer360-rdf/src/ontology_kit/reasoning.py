"""OWL 推理：以 owlrl（OWL 2 RL）對 release 包做 TBox 閉包，並以獨立的 subClassOf 走訪交叉驗證。"""

from collections import deque
from importlib.metadata import version as package_version

import owlrl
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

LIMITATIONS = [
    "只推理具名類別的 TBox（rdfs:subClassOf 閉包與 domain 繼承）；沒有個體資料。",
    "OWL 2 RL 規則集不是完整 OWL DL：未做一致性與可滿足性的完備檢查，只檢查是否有類別被推成 owl:Nothing。",
    "只接受 config.reasoner 白名單內的公理；出現其他公理時拒絕發佈，不會忽略後假稱完整。",
]


class UnsupportedAxioms(ValueError):
    def __init__(self, issues):
        super().__init__("本體含推理白名單以外的公理：" + "；".join(issues))
        self.issues = issues


class ReasoningMismatch(RuntimeError):
    pass


def guard(graph, cfg):
    rules = cfg.reasoner
    allowed_predicates = {OWL[name] for name in rules["allowed_owl_predicates"]}
    allowed_types = {OWL[name] for name in rules["allowed_owl_types"]}
    allowed_rdfs = {RDFS[name] for name in rules["allowed_rdfs_predicates"]}
    classes = set(graph.subjects(RDF.type, OWL.Class))
    issues = set()
    for subject, predicate, obj in graph:
        if str(predicate).startswith(str(OWL)) and predicate not in allowed_predicates:
            issues.add(f"謂詞 {predicate.n3(graph.namespace_manager)}")
        if str(predicate).startswith(str(RDFS)) and predicate not in allowed_rdfs:
            issues.add(f"謂詞 {predicate.n3(graph.namespace_manager)}")
        if predicate == RDF.type and str(obj).startswith(str(OWL)) and obj not in allowed_types:
            issues.add(f"型別 {obj.n3(graph.namespace_manager)}")
        if predicate == RDF.type and obj in classes:
            issues.add("個體資料（rdf:type 指向本體類別）不在發佈範圍")
        if predicate == RDFS.subClassOf and (isinstance(subject, BNode) or isinstance(obj, BNode)):
            issues.add("匿名類別的 rdfs:subClassOf（restriction 等）")
    return sorted(issues)


def _walk(parents, start):
    seen, queue = {}, deque((p, 1) for p in parents.get(start, []))
    while queue:
        node, distance = queue.popleft()
        if node in seen:
            continue
        seen[node] = distance
        queue.extend((p, distance + 1) for p in parents.get(node, []))
    return seen


def _path(parents, start, target):
    queue, seen = deque([[start]]), set()
    while queue:
        path = queue.popleft()
        if path[-1] == target:
            return path
        if path[-1] in seen:
            continue
        seen.add(path[-1])
        queue.extend(path + [p] for p in parents.get(path[-1], []))
    return []


def reason(graph, cfg):
    issues = guard(graph, cfg)
    if issues:
        raise UnsupportedAxioms(issues)
    classes = sorted(str(s) for s in graph.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef))
    names = set(classes)
    asserted = {c: sorted(str(o) for o in graph.objects(URIRef(c), RDFS.subClassOf) if str(o) in names)
                for c in classes}

    closure = Graph()
    for triple in graph:
        closure.add(triple)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(closure)

    entailed = {c: {str(o) for o in closure.objects(URIRef(c), RDFS.subClassOf) if str(o) in names and str(o) != c}
                for c in classes}
    independent = {c: _walk(asserted, c) for c in classes}
    mismatched = [c for c in classes if entailed[c] != set(independent[c]) - {c}]
    if mismatched:
        raise ReasoningMismatch("owlrl 結果與獨立走訪不一致：" + ", ".join(cfg.curie(c) for c in mismatched))
    cycles = sorted(c for c in classes if c in independent[c])
    unsatisfiable = sorted(c for c in classes if (URIRef(c), RDFS.subClassOf, OWL.Nothing) in closure)

    ancestors, entailments = {}, []
    for c in classes:
        ordered = sorted(entailed[c], key=lambda a: (independent[c][a], a))
        ancestors[c] = [{"uri": a, "distance": independent[c][a]} for a in ordered]
        for a in ordered:
            entailments.append({"class": c, "ancestor": a, "asserted": a in asserted[c],
                                "path": _path(asserted, c, a)})
    return {
        "engine": f"owlrl {package_version('owlrl')}（OWL 2 RL）",
        "rdflib": package_version("rdflib"),
        "scope": "tbox_named_classes",
        "input_triples": len(graph),
        "closure_triples": len(closure),
        "classes": len(classes),
        "asserted_subclass_axioms": sum(len(v) for v in asserted.values()),
        "entailed_pairs": len(entailments),
        "inferred_only": sum(not e["asserted"] for e in entailments),
        "independent_check": "passed",
        "cycles": cycles,
        "unsatisfiable": unsatisfiable,
        "consistency": "not_checked",
        "limitations": LIMITATIONS,
        "ancestors": ancestors,
        "entailments": entailments,
    }


def render_markdown(cfg, report, labels):
    def name(uri):
        return f"{labels.get(uri, cfg.curie(uri))}（`{cfg.curie(uri)}`）"
    lines = [f"# 推理報告（v{cfg.version}）", "",
             f"- 引擎：{report['engine']}；rdflib {report['rdflib']}",
             f"- 輸入 {report['input_triples']} triples → 閉包 {report['closure_triples']} triples",
             f"- 類別 {report['classes']}；宣告的 subClassOf {report['asserted_subclass_axioms']} 條；"
             f"蘊含的上下位關係 {report['entailed_pairs']} 組，其中推理新增 {report['inferred_only']} 組",
             f"- 與獨立 subClassOf 走訪交叉驗證：{report['independent_check']}",
             f"- 循環：{len(report['cycles'])}；不可滿足類別：{len(report['unsatisfiable'])}；一致性：{report['consistency']}",
             "", "## 推理新增的關係", "", "| 類別 | 推出的上層 | 推理路徑 |", "|---|---|---|"]
    for e in report["entailments"]:
        if not e["asserted"]:
            chain = " ⊑ ".join(labels.get(u, cfg.curie(u)) for u in e["path"])
            lines.append(f"| {name(e['class'])} | {name(e['ancestor'])} | {chain} |")
    lines += ["", "## 限制", ""] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"
