"""把 Studio 的內部狀態整理成前端需要的 JSON。"""

from rdflib import Graph, URIRef

from . import dictionary
from .common import StudioError

REASONING_FIELDS = ("engine", "input_triples", "closure_triples", "classes", "asserted_subclass_axioms",
                    "entailed_pairs", "inferred_only", "independent_check", "cycles", "unsatisfiable",
                    "consistency", "limitations")


def term_view(studio, term):
    classes = studio.onto.classes
    return {**term, "mappings": [{"class": studio.cfg.curie(m["class"]), "uri": m["class"], "role": m["role"],
                                  "label": classes.get(m["class"], {}).get("label") or studio.cfg.curie(m["class"])}
                                 for m in term["mappings"]]}


def state(studio):
    cfg, onto, ev = studio.cfg, studio.onto, studio.evaluator
    classes = [{"uri": uri, "id": c["id"], "label": c["label"], "definition": c["definition"],
                "layer": c["layer"], "module": c["module"], "maturity": c["maturity"],
                "deprecated": c["deprecated"], "parents": c["parents"],
                "ancestors": onto.ancestors.get(uri, []), "chain": onto.chains(uri),
                "permissions": ev.all_roles(ev.for_class, uri)}
               for uri, c in sorted(onto.classes.items())]
    inferred = [{"source": e["class"], "target": e["ancestor"], "path": e["path"]}
                for e in (onto.report or {}).get("entailments", []) if not e["asserted"]]
    terms = [{**term_view(studio, t), "permissions": ev.all_roles(ev.for_term, t)} for t in studio.all_terms()]
    policy = studio.policy
    return {
        "ontology": {"label": cfg.label, "version": cfg.version, "status": cfg.status, "date": cfg.date},
        "layers": [{"key": k, "title": l.title, "prefix": l.prefix} for k, l in cfg.layers.items()],
        "modules": [{"file": m.file, "layer": m.layer, "topic": m.topic, "maturity": m.maturity} for m in cfg.modules],
        "mapping_roles": studio.mapping_roles,
        "classes": classes,
        "properties": [{"uri": p["uri"], "id": p["id"], "label": p["label"], "kind": p["kind"], "module": p["module"],
                        "domain": p["domain"], "range": [r if r in onto.classes else cfg.curie(r) for r in p["range"]],
                        "definition": p["definition"]} for p in onto.properties.values()],
        "inferred": inferred,
        "terms": terms,
        "policy": {**policy, "rules": [{**r, "classes": [cfg.curie(c) for c in r["classes"]]} for r in policy["rules"]]},
        "shapes": studio.validator.shape_list(),
        "validation": studio.validation,
        "component_issues": onto.component_issues,
        "reasoning": {k: onto.report[k] for k in REASONING_FIELDS} if onto.report else None,
        "reasoning_error": onto.reasoning_error,
    }


def node_detail(studio, node_id):
    onto = studio.onto
    if node_id.startswith("term:"):
        term = studio.find_term(node_id[5:])
        if term is None:
            raise StudioError("找不到詞條")
        return {"kind": "term", "turtle": dictionary.to_graph(studio.dict_ns, [term]).serialize(format="turtle"),
                "validation": [v for v in studio.validation["results"] if v["node"] == node_id]}
    subject = URIRef(node_id)
    out = Graph()
    for prefix, namespace in onto.graph.namespaces():
        out.bind(prefix, namespace)
    for triple in onto.graph.triples((subject, None, None)):
        out.add(triple)
    names = onto.graph.namespace_manager
    incoming = [{"subject": s.n3(names), "predicate": p.n3(names)} for s, p, _ in onto.graph.triples((None, None, subject))]
    curie = studio.cfg.curie(node_id)
    applicable = [s["label"] for s in studio.validator.shape_list() if "owl:Class" in s["targets"] or curie in s["targets"]]
    kind = "class" if node_id in onto.classes else "property"
    record = onto.classes.get(node_id) or onto.properties.get(node_id) or {}
    return {"kind": kind, "module": record.get("module"), "turtle": out.serialize(format="turtle"),
            "incoming": incoming, "shapes": applicable,
            "validation": [v for v in studio.validation["results"] if v["node"] == node_id],
            "terms": [t["id"] for t in studio.all_terms() if any(m["class"] == node_id for m in t["mappings"])]}


def turtle(studio, what):
    if what == "ontology":
        return studio.onto.graph.serialize(format="turtle")
    if what == "dictionary":
        return dictionary.to_graph(studio.dict_ns, studio.all_terms()).serialize(format="turtle")
    if what == "shapes":
        return studio.validator.shapes.serialize(format="turtle")
    raise StudioError("what 只能是 ontology、dictionary、shapes")
