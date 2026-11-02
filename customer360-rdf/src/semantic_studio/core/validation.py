"""SHACL：載入 shapes、在 OWL 推理後的圖上驗證，並把結果與 shape 整理成前端可讀的格式。"""

import re

from pyshacl import validate as shacl_validate
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .common import SH


class Validator:
    def __init__(self, cfg, dict_ns):
        self.cfg, self.dict_ns = cfg, dict_ns
        self.shapes = Graph()
        for path in sorted(cfg.path_of("shapes_dir").glob("*.ttl")):
            self.shapes.parse(path, format="turtle")

    # ---------- 顯示用 ----------

    def display(self, uri):
        text = str(uri)
        if text.startswith(str(self.dict_ns)):
            return "dict:" + text[len(self.dict_ns):]
        for namespace, prefix in ((str(SH), "sh:"), (str(RDFS), "rdfs:"), (str(SKOS), "skos:"), (str(OWL), "owl:")):
            if text.startswith(namespace):
                return prefix + text[len(namespace):]
        return self.cfg.curie(uri)

    def node_id(self, focus):
        text = str(focus)
        if text.startswith(str(self.dict_ns)):
            return "term:" + text[len(self.dict_ns):].split("__m")[0]
        return text

    def _path_text(self, path):
        if isinstance(path, URIRef):
            return self.display(path)
        if isinstance(path, BNode) and (path, RDF.first, None) in self.shapes:  # 序列路徑 ( a b )
            return " / ".join(self.display(p) for p in self.shapes.items(path))
        return str(path)

    def _owner(self, source):
        if isinstance(source, BNode):
            parent = next(self.shapes.subjects(SH.property, source), None)
            return parent if parent is not None else source
        return source

    # ---------- 驗證 ----------

    def validate(self, inferred_ontology, dictionary_graph):
        data = Graph()
        for triple in inferred_ontology:
            data.add(triple)
        for triple in dictionary_graph:
            data.add(triple)
        conforms, results_graph, _ = shacl_validate(data, shacl_graph=self.shapes, inference="none",
                                                    allow_warnings=True, advanced=True)
        results = []
        for result in results_graph.subjects(RDF.type, SH.ValidationResult):
            focus = results_graph.value(result, SH.focusNode)
            shape = self._owner(results_graph.value(result, SH.sourceShape))
            value = results_graph.value(result, SH.value)
            path = results_graph.value(result, SH.resultPath)
            mapping = re.search(r"__m(\d+)$", str(focus))
            results.append({
                "node": self.node_id(focus), "focus": self.display(focus),
                "mapping_index": int(mapping.group(1)) if mapping else None,
                "severity": str(results_graph.value(result, SH.resultSeverity)).rsplit("#", 1)[-1],
                "shape": str(shape) if isinstance(shape, URIRef) else "（匿名 shape）",
                "message": str(results_graph.value(result, SH.resultMessage) or ""),
                "path": self.display(path) if isinstance(path, URIRef) else None,
                "value": (self.display(value) if isinstance(value, URIRef) else str(value)) if value is not None else None,
            })
        results.sort(key=lambda r: (r["severity"] != "Violation", r["node"], r["message"]))
        return {"conforms": conforms, "results": results}

    def shape_list(self):
        shapes = []
        for shape in sorted(set(self.shapes.subjects(RDF.type, SH.NodeShape)), key=str):
            if not isinstance(shape, URIRef):
                continue
            constraints = []
            for prop in self.shapes.objects(shape, SH.property):
                parts = []
                for key in ("minCount", "maxCount", "class", "in", "languageIn", "datatype", "hasValue"):
                    value = self.shapes.value(prop, SH[key])
                    if value is None:
                        continue
                    if key in ("in", "languageIn"):
                        parts.append(f"{key} ({', '.join(str(i) for i in self.shapes.items(value))})")
                    else:
                        parts.append(f"{key} {self.display(value) if isinstance(value, URIRef) else value}")
                constraints.append({"kind": "property", "path": self._path_text(self.shapes.value(prop, SH.path)),
                                    "rule": "；".join(parts), "message": str(self.shapes.value(prop, SH.message) or "")})
            for sparql in self.shapes.objects(shape, SH.sparql):
                constraints.append({"kind": "sparql", "path": None,
                                    "rule": str(self.shapes.value(sparql, SH.select) or "").strip(),
                                    "message": str(self.shapes.value(sparql, SH.message) or "")})
            if self.shapes.value(shape, SH["or"]) is not None:
                constraints.append({"kind": "or", "path": None, "rule": "sh:or（條件式規則）",
                                    "message": str(self.shapes.value(shape, SH.message) or "")})
            shapes.append({"id": str(shape), "label": str(self.shapes.value(shape, RDFS.label) or shape.split("#")[-1]),
                           "severity": str(self.shapes.value(shape, SH.severity) or SH.Violation).rsplit("#", 1)[-1],
                           "comment": str(self.shapes.value(shape, RDFS.comment) or ""),
                           "targets": [self.display(t) for t in self.shapes.objects(shape, SH.targetClass)],
                           "constraints": constraints})
        return shapes
