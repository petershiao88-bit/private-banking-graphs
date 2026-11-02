"""載入本體：類別組成元件＋OWL 推理（推理失敗時仍可瀏覽，並回報原因）。"""

from dataclasses import dataclass, field

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDFS

from ontology_kit import components, reasoning


@dataclass
class OntologyView:
    graph: Graph
    classes: dict
    properties: dict
    component_issues: list
    ancestors: dict
    report: dict | None
    reasoning_error: str | None
    _inferred: Graph | None = field(default=None, repr=False)

    def inferred_graph(self):
        """本體＋OWL 推理出的 rdfs:subClassOf 閉包（含自反），SHACL 在這張圖上驗證。"""
        if self._inferred is None:
            data = Graph()
            for triple in self.graph:
                data.add(triple)
            for uri in self.classes:
                data.add((URIRef(uri), RDFS.subClassOf, URIRef(uri)))
                for ancestor in self.ancestors.get(uri, []):
                    data.add((URIRef(uri), RDFS.subClassOf, URIRef(ancestor)))
            self._inferred = data
        return self._inferred

    def is_a(self, uri, target):
        return uri == target or target in self.ancestors.get(uri, [])

    def chains(self, uri):
        if not self.report:
            return []
        labels = {u: c["label"] for u, c in self.classes.items()}
        tops = [a for a in self.ancestors.get(uri, []) if not self.ancestors.get(a)]
        return [" ⊑ ".join(labels.get(u, u) for u in e["path"]) for e in self.report["entailments"]
                if e["class"] == uri and e["ancestor"] in tops]


def load(cfg):
    graph, classes, properties, issues = components.build(cfg)
    asserted = components.asserted_ancestors(classes)
    ancestors = {uri: sorted(a, key=lambda x: (a[x], x)) for uri, a in asserted.items()}
    reasoning_input = Graph()
    for triple in graph:
        if triple[1] != OWL.imports:  # 模組已合併，import 不參與推理
            reasoning_input.add(triple)
    try:
        report, error = reasoning.reason(reasoning_input, cfg), None
        ancestors = {uri: [a["uri"] for a in items] for uri, items in report["ancestors"].items()}
    except (reasoning.UnsupportedAxioms, reasoning.ReasoningMismatch) as exc:
        report, error = None, str(exc)
    return OntologyView(graph, {c["uri"]: c for c in classes}, {p["uri"]: p for p in properties},
                        issues, ancestors, report, error)
