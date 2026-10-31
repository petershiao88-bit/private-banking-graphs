"""Read the current RDF/PG model and export Semantica views; never edit sources."""

import hashlib
import json
from copy import deepcopy
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PG_PRIVATE_BANKING = "bank.private_banking"
RDF_PRIVATE_BANKING = "https://example.org/ontology/bank#PrivateBankingDepartment"
sys.path.insert(0, str(ROOT / "tools"))
from build_ontology import check_outputs, expected_graph
from export_fabric_graph import load_pg, project


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_hashes():
    config = json.loads((ROOT / "build-config.json").read_text(encoding="utf-8"))
    paths = [ROOT / "build-config.json", ROOT / "catalog-v001.xml",
             *[ROOT / p for p in config["sources"]],
             *[ROOT / p for p in config["outputs"].values()],
             *sorted((ROOT / "department-pg").glob("*.json")),
             ROOT / "department-pg/model.cypher"]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def build_graph():
    before = source_hashes()
    check_outputs()
    config, rdf = expected_graph()
    pg = load_pg()
    projection = project(rdf, pg)
    raw_edges = {e["id"]: e for e in pg["relationships"]}
    nodes = []
    for node in projection["nodes"]:
        original = json.loads(node["properties_json"])
        properties = {**original, "name": node["display_name"], "definition": node["definition"],
                      "projection": {k: v for k, v in node.items()
                                     if k not in ("properties_json", "rdf_annotations_json")},
                      "original_pg_properties": original,
                      "rdf_annotations": json.loads(node["rdf_annotations_json"])}
        nodes.append({"id": node["id"], "type": node["kind"],
                      "content": node["display_name"], "properties": properties})
    edges = []
    for edge in projection["edges"]:
        original = raw_edges.get(edge["id"], {}).get("properties", {})
        edges.append({"id": edge["id"], "source": edge["source_id"], "target": edge["target_id"],
                      "type": edge["kind"], "weight": 1.0,
                      "metadata": {**original, "projection": edge,
                                   "original_pg_properties": original}})
    graph = {"graph_id": "customer360-v" + config["version"], "nodes": nodes, "edges": edges}
    assert len({n["id"] for n in nodes}) == len(nodes), "Duplicate node IDs"
    assert len({e["id"] for e in edges}) == len(edges), "Duplicate edge IDs"
    ids = {n["id"] for n in nodes}
    assert all(e["source"] in ids and e["target"] in ids for e in edges), "Dangling edges"
    assert source_hashes() == before, "Source changed while exporting"
    return graph, projection["rdf_triples"], before


def induced(graph, ids, name):
    return {"graph_id": graph["graph_id"] + ":" + name,
            "nodes": [n for n in graph["nodes"] if n["id"] in ids],
            "edges": [e for e in graph["edges"] if e["source"] in ids and e["target"] in ids]}


def single_private_department(view, graph):
    """Contract only the duplicate department for display, retaining RDF identity.

    Adoption remains PG metadata projected onto the RDF class on this canvas;
    this does not assert an RDF organization instance or rewrite the ontology.
    """
    if not any(n["id"] == PG_PRIVATE_BANKING for n in view["nodes"]):
        return view
    result = deepcopy(view)
    result["nodes"] = [n for n in result["nodes"] if n["id"] != PG_PRIVATE_BANKING]
    if not any(n["id"] == RDF_PRIVATE_BANKING for n in result["nodes"]):
        rdf_department = next(n for n in graph["nodes"] if n["id"] == RDF_PRIVATE_BANKING)
        assert rdf_department["type"] == "OntologyClass"
        result["nodes"].append(deepcopy(rdf_department))
    edges = []
    for edge in result["edges"]:
        source, target = edge["source"], edge["target"]
        edge["source"] = RDF_PRIVATE_BANKING if source == PG_PRIVATE_BANKING else source
        edge["target"] = RDF_PRIVATE_BANKING if target == PG_PRIVATE_BANKING else target
        if edge["source"] == edge["target"] and (source == PG_PRIVATE_BANKING or target == PG_PRIVATE_BANKING):
            continue  # Former department -> class correspondence is now redundant.
        if (source, target) != (edge["source"], edge["target"]):
            edge["metadata"]["visual_projection"] = {
                "kind": "department_display_contraction", "original_source": source,
                "original_target": target, "display_source": edge["source"],
                "display_target": edge["target"], "scope": "visualization_only_not_rdf_instance_assertion"}
        edges.append(edge)
    result["nodes"].sort(key=lambda n: n["id"])
    result["edges"] = edges
    return result


def views(graph):
    by_id = {n["id"]: n for n in graph["nodes"]}
    business_ids = {n["id"] for n in graph["nodes"] if n["type"] in ("Department", "Metric", "BusinessConcept", "SourceTable")}
    securities = {"bank.private_banking"} | {n["id"] for n in graph["nodes"]
        if n["type"] == "Metric" and n["id"].startswith("securities.")}
    for edge in graph["edges"]:
        if edge["source"] in securities and by_id[edge["target"]]["type"] in ("SourceTable", "BusinessConcept"):
            securities.add(edge["target"])
    # RDF classes are real ontology concepts, including URIs also present as
    # PG ClassReference metadata. Keep each class URI once, and allow direct
    # PG-to-class correspondence without property/intermediate reference nodes.
    rdf_ids = {n["id"] for n in graph["nodes"] if n["type"] == "OntologyClass"}
    ontology = induced(graph, rdf_ids, "ontology")
    ontology["edges"] = [e for e in ontology["edges"]
                         if e["type"] == "RDF_SUBCLASS_OF" or e["type"].startswith("RDF_DECLARED_")]
    full = induced(graph, business_ids | rdf_ids, "full")
    full["edges"] = [e for e in full["edges"]
                     if e["type"] in {"USES_METRIC", "HAS_COMPONENT_METRIC", "HAS_SOURCE_TABLE",
                                      "USES_VALUATION_SOURCE", "USES_DATE_LOOKUP_SOURCE", "RDF_SUBCLASS_OF"}
                     or e["type"].startswith("RDF_DECLARED_")
                     or (e["type"] == "REFERS_TO_CLASS" and e["source"] in business_ids and e["target"] in rdf_ids)]
    variants = {"full": full, "business": induced(graph, business_ids, "business"),
                "securities": induced(graph, securities, "securities"), "ontology": ontology}
    return {name: single_private_department(view, graph) for name, view in variants.items()}


def main():
    graph, triples, hashes = build_graph()
    out = HERE / "data"
    variants = views(graph)
    for name, variant in variants.items():
        dump(out / (name + ".json"), variant)
    dump(out / "rdf-triples-audit.json", triples)
    endpoint_counts = Counter((e["source"], e["target"]) for e in variants["full"]["edges"])
    manifest = {"scope": "rdf_classes_and_pg_business_nodes_with_direct_class_correspondence", "source_sha256": hashes,
                "display_contractions": {PG_PRIVATE_BANKING: RDF_PRIVATE_BANKING},
                "views": {k: {"nodes": len(g["nodes"]), "edges": len(g["edges"])} for k, g in variants.items()},
                "rdf_triples": len(triples), "parallel_endpoint_pairs": sum(v > 1 for v in endpoint_counts.values()),
                "notice": "HAS_COMPONENT_METRIC is coverage, not SUM. RDF declarations are not instance facts. Pending states are preserved. No LLM or business SQL is executed."}
    dump(out / "manifest.json", manifest)
    print(json.dumps({"views": manifest["views"], "rdf_triples": len(triples),
                      "sources_unchanged": source_hashes() == hashes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
