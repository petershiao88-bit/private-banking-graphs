"""Check actual Semantica round trips, parallel edges, provenance and Explorer APIs."""

import json
import tempfile
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote

from export_graph import HERE, build_graph, source_hashes, views, dump, PG_PRIVATE_BANKING, RDF_PRIVATE_BANKING


def main():
    from semantica.context import ContextGraph
    from semantica.explorer.session import GraphSession
    from fastapi.testclient import TestClient
    from rdflib.namespace import OWL, RDF
    from build_ontology import expected_graph
    from serve import create_explorer

    graph, triples, hashes = build_graph()
    disk = json.loads((HERE / "data/full.json").read_text(encoding="utf-8"))
    assert disk == views(graph)["full"], "Export is stale"
    manifest = json.loads((HERE / "data/manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_sha256"] == hashes, "Source differs from exported baseline"
    _, source_rdf = expected_graph()
    declared_classes = {str(uri) for uri in source_rdf.subjects(RDF.type, OWL.Class)}
    full_rdf_nodes = {n["id"] for n in disk["nodes"] if n["type"] == "OntologyClass"}
    assert full_rdf_nodes == declared_classes, "Declared RDF classes missing from combined view"
    assert {e["id"] for e in disk["edges"] if e["type"] == "RDF_SUBCLASS_OF" or e["type"].startswith("RDF_DECLARED_")} == {e["id"] for e in views(graph)["ontology"]["edges"]}, "RDF relationships missing from combined view"
    business_ids = {n["id"] for n in disk["nodes"] if n["type"] in {"Department", "Metric", "BusinessConcept", "SourceTable"}}
    expected_bridges = {e["id"] for e in graph["edges"] if e["type"] == "REFERS_TO_CLASS" and e["source"] in business_ids and e["target"] in declared_classes}
    bridges = [e for e in disk["edges"] if e["type"] == "REFERS_TO_CLASS"]
    assert {e["id"] for e in bridges} == expected_bridges, "PG-to-RDF correspondences missing or invented"
    assert all(e["source"] in business_ids and e["target"] in declared_classes for e in bridges), "Correspondence must connect directly to a declared RDF class"
    assert any(e["source"] == "securities.total_aum" and e["target"] == "https://example.org/ontology/securities#SecuritiesAUM" for e in bridges)
    results = {}
    for name, variant in views(graph).items():
        ids = {n["id"] for n in variant["nodes"]}
        assert PG_PRIVATE_BANKING not in ids, "Duplicate PG private department still displayed"
        assert RDF_PRIVATE_BANKING in ids, "RDF private department missing"
        assert all(e["source"] in ids and e["target"] in ids for e in variant["edges"]), "Dangling display endpoint"
        assert all(e["source"] != PG_PRIVATE_BANKING and e["target"] != PG_PRIVATE_BANKING for e in variant["edges"])
        if name != "ontology":
            expected_metrics = {e["target"] for e in graph["edges"] if e["source"] == PG_PRIVATE_BANKING and e["type"] == "USES_METRIC" and e["target"] in ids}
            adoption = [e for e in variant["edges"] if e["type"] == "USES_METRIC"]
            assert {e["target"] for e in adoption} == expected_metrics, "Metric adoption scope changed"
            assert all(e["source"] == RDF_PRIVATE_BANKING and e["metadata"]["visual_projection"]["original_source"] == PG_PRIVATE_BANKING for e in adoption)
            if name == "full":
                assert len(adoption) == 44
        if name == "ontology":
            assert all(n["type"] == "OntologyClass" for n in variant["nodes"])
            assert all(e["type"] == "RDF_SUBCLASS_OF" or e["type"].startswith("RDF_DECLARED_") for e in variant["edges"])
        else:
            allowed_nodes = {"Metric", "BusinessConcept", "SourceTable"}
            allowed_edges = {"USES_METRIC", "HAS_COMPONENT_METRIC", "HAS_SOURCE_TABLE", "USES_VALUATION_SOURCE", "USES_DATE_LOOKUP_SOURCE"}
            if name == "full":
                allowed_nodes.add("OntologyClass")
                allowed_edges.add("RDF_SUBCLASS_OF")
                allowed_edges.add("REFERS_TO_CLASS")
            assert all(n["type"] in allowed_nodes or n["id"] == RDF_PRIVATE_BANKING for n in variant["nodes"]), "Technical node leaked into business view"
            assert all(e["type"] in allowed_edges or (name == "full" and e["type"].startswith("RDF_DECLARED_")) for e in variant["edges"]), "Reference or mapping edge leaked into business view"
    with tempfile.TemporaryDirectory() as tmp:
        for name, expected in views(graph).items():
            loaded = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
            loaded.load_from_file(HERE / "data" / (name + ".json"))
            assert set(loaded.nodes) == {n["id"] for n in expected["nodes"]}
            session = GraphSession(loaded)
            actual_edges = {e["id"]: e for e in session.iter_edges()}
            assert len(actual_edges) == len(expected["edges"]), "Parallel edge lost"
            for edge in expected["edges"]:
                actual = actual_edges[edge["id"]]
                assert (actual["source"], actual["target"], actual["type"]) == (edge["source"], edge["target"], edge["type"])
                assert actual["properties"] == edge["metadata"], "Edge provenance changed"
            for node in expected["nodes"]:
                actual = session.get_node(node["id"])
                assert actual["properties"]["original_pg_properties"] == node["properties"]["original_pg_properties"]
                assert actual["properties"]["projection"] == node["properties"]["projection"]
            saved = Path(tmp) / (name + ".json")
            loaded.save_to_file(saved)
            reloaded = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
            reloaded.load_from_file(saved)
            assert len(reloaded.nodes) == len(loaded.nodes) and len(reloaded.edges) == len(loaded.edges)
            with TestClient(create_explorer(name)) as client:
                assert client.get("/").status_code == 200
                assert 'id="root"' in client.get("/").text, "Packaged frontend missing"
                nodes_response = client.get("/api/graph/nodes", params={"limit": 5000})
                edges_response = client.get("/api/graph/edges", params={"limit": 5000})
                assert nodes_response.status_code == edges_response.status_code == 200
                assert nodes_response.json()["total"] == len(expected["nodes"])
                assert edges_response.json()["total"] == len(expected["edges"])
                if name in ("full", "securities", "business"):
                    response = client.get("/api/graph/nodes", params={"search": "證券總 AUM"})
                    assert any(n["id"] == "securities.total_aum" for n in response.json()["nodes"]), "Chinese search failed"
                    response = client.get("/api/graph/edges", params={"source": "securities.total_aum", "type": "HAS_COMPONENT_METRIC"})
                    assert response.json()["total"] == 5, "Total AUM coverage changed"
                if name in ("ontology", "full"):
                    response = client.get("/api/graph/node", params={"node_id": "https://example.org/ontology/holding#Metric"})
                    assert response.status_code == 200, "RDF URI lookup failed"
                if name == "full":
                    response = client.get("/api/graph/edges", params={"source": RDF_PRIVATE_BANKING, "type": "USES_METRIC", "limit": 5000})
                    assert response.status_code == 200 and response.json()["total"] == 44
                    response = client.get("/api/graph/node", params={"node_id": PG_PRIVATE_BANKING})
                    assert response.status_code == 404, "Duplicate department still available through API"
                registry = client.get("/api/ontology/registry")
                assert registry.status_code == 200 and len(registry.json()) == 1
                ontology = registry.json()[0]
                assert ontology["uri"] == "https://example.org/ontology/customer360"
                assert ontology["class_count"] == 43 and ontology["property_count"] == 33, "Incomplete ontology loaded in Hub"
                response = client.get("/api/ontology/graph", params={"uri": ontology["uri"]})
                assert response.status_code == 200 and response.json()["nodes"], "Ontology editor graph unavailable"
                hub_nodes = response.json()["nodes"]
                assert {n["id"] for n in hub_nodes if n.get("entity_type") == "class"} == declared_classes
                response = client.get("/api/ontology/entity/" + quote(RDF_PRIVATE_BANKING, safe=""))
                assert response.status_code == 200 and response.json()["definition"]
                assert "https://example.org/ontology/holding#Department" in response.json()["superclasses"]
                response = client.get("/api/ontology/entity/" + quote("https://example.org/ontology/holding#usesMetric", safe=""))
                assert response.status_code == 200
                assert response.json()["domain"] == ["https://example.org/ontology/holding#Department"]
                assert response.json()["range"] == ["https://example.org/ontology/holding#Metric"]
                # Hub properties must never reappear on the simplified main canvas.
                assert client.get("/api/graph/nodes", params={"limit": 5000}).json()["total"] == len(expected["nodes"])
                results[name] = {"nodes": len(expected["nodes"]), "edges": len(expected["edges"]), "api": "passed"}
    assert source_hashes() == hashes, "Original sources changed"
    report = {"status": "passed", "semantica": "0.7.0", "views": results,
              "pg_to_rdf_correspondences": len(bridges),
              "ontology_hub": {"classes": 43, "properties": 33, "rdf_triples": len(triples), "main_canvas_unchanged": True},
              "runtime_versions": {name: version(name) for name in
                                   ["semantica", "rdflib", "fastapi", "starlette", "pydantic", "networkx", "numpy", "scipy", "pandas"]},
              "rdf_triples_audited": len(triples), "original_sources_unchanged": True,
              "checks": ["stable node and edge IDs", "all parallel edges", "original PG properties and pending states",
                         "edge provenance", "save/load round trip", "frontend assets", "Chinese search", "RDF URI lookup", "five AUM components", "all declared RDF classes and relationships in combined view", "all remaining direct PG-to-RDF class correspondences", "one RDF private department with all 44 metric adoption edges", "complete ontology loaded in isolated Hub session", "Hub definitions, inheritance, domain and range", "no property, field, mapping or reference nodes on business canvas"]}
    dump(HERE / "data/verification.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
