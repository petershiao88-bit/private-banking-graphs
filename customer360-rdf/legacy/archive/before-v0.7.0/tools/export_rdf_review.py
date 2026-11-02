"""Export the current RDF schema as a reviewable property-graph-style view."""

import json
from pathlib import Path

from rdflib.namespace import OWL, RDF, RDFS, SKOS

from build_ontology import expected_graph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "rdf-review-v0.6.0"


def main():
    config, graph = expected_graph()

    def label(uri):
        return str(graph.value(uri, RDFS.label) or uri)

    classes = set(graph.subjects(RDF.type, OWL.Class))
    fields = set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    objects = set(graph.subjects(RDF.type, OWL.ObjectProperty))
    annotations = set(graph.subjects(RDF.type, OWL.AnnotationProperty))
    nodes = []
    for uri in sorted(classes):
        nodes.append({
            "id": str(uri), "label": label(uri),
            "owner": "bank" if "/bank#" in str(uri) else "holding",
            "definition": str(graph.value(uri, SKOS.definition)),
            "properties": [{"id": str(prop), "label": label(prop),
                            "range": str(graph.value(prop, RDFS.range))}
                           for prop in sorted(fields) if (prop, RDFS.domain, uri) in graph],
        })
    edges = [{"source": str(child), "target": str(parent), "kind": "subclass", "label": "繼承",
              "predicate": str(RDFS.subClassOf)} for child, parent in graph.subject_objects(RDFS.subClassOf)]
    for prop in sorted(objects):
        domains, ranges = list(graph.objects(prop, RDFS.domain)), list(graph.objects(prop, RDFS.range))
        if len(domains) != 1 or len(ranges) != 1:
            raise ValueError("Review view requires a single explicit domain and range")
        edges.append({"source": str(domains[0]), "target": str(ranges[0]), "kind": "relationship",
                      "label": label(prop), "predicate": str(prop)})
    payload = {"version": config["version"], "nodes": nodes,
               "edges": sorted(edges, key=lambda e: (e["source"], e["predicate"], e["target"])),
               "annotations": [{"id": str(uri), "label": label(uri)} for uri in sorted(annotations)],
               "scope": "rdf_schema_only", "projection": "class nodes, domain/range edges, datatype fields in nodes"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rdf-graph.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(nodes)} classes, {len(edges)} schema edges and {len(fields)} data properties")


if __name__ == "__main__":
    main()
