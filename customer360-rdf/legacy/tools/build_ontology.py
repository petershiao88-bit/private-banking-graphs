"""Build self-contained RDF exports from the explicitly listed local Turtle sources."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]


def local_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path outside project: {name}")
    return path


def expected_graph(root=ROOT):
    config = json.loads((root / "build-config.json").read_text(encoding="utf-8"))
    sources = config["sources"]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError("Sources must be nonempty and unique")
    source_paths = {local_file(root, name) for name in sources}
    outputs = {local_file(root, name) for name in config["outputs"].values()}
    if source_paths & outputs or len(outputs) != 2:
        raise ValueError("Outputs must be distinct and cannot overwrite sources")
    catalog = {entry.attrib["name"]: entry.attrib["uri"]
               for entry in ET.parse(root / "catalog-v001.xml").getroot()}
    graph = Graph()
    for name in sources:
        source = Graph().parse(local_file(root, name), format="turtle")
        for prefix, uri in source.namespaces():
            graph.bind(prefix, uri)
        graph += source
    ontologies = set(graph.subjects(RDF.type, OWL.Ontology))
    if not ontologies:
        raise ValueError("No ontology declaration in source modules")
    # Never resolve placeholder ontology IRIs over the network.
    for target in graph.objects(None, OWL.imports):
        mapped = catalog.get(str(target))
        if (target not in ontologies or mapped is None
                or local_file(root, mapped) not in source_paths):
            raise ValueError(f"Import must be explicitly included as a local source: {target}")
    for ontology in ontologies:
        graph.remove((ontology, None, None))
    ontology = URIRef(config["ontology_uri"])
    graph.add((ontology, RDF.type, OWL.Ontology))
    graph.add((ontology, RDFS.label, Literal(config["label"], lang="zh-TW")))
    graph.add((ontology, OWL.versionIRI, URIRef(str(ontology) + "/" + config["version"])))
    graph.add((ontology, OWL.versionInfo, Literal(
            config["version"] + " / design draft / " + config.get("date", "2026-10-21"))))
    return config, graph


def check_outputs(root=ROOT):
    config, expected = expected_graph(root)
    graphs = {kind: Graph().parse(local_file(root, path), format=kind)
              for kind, path in config["outputs"].items()}
    for kind, graph in graphs.items():
        if not isomorphic(graph, expected):
            raise ValueError(f"Stale or mismatched {kind} export; run tools/build_ontology.py")
    return {
        "result": "PASS", "version": config["version"], "parser": "rdflib",
        "source_modules": len(config["sources"]), "combined_triples": len(expected),
        "classes": len(set(expected.subjects(RDF.type, OWL.Class))),
        "object_properties": len(set(expected.subjects(RDF.type, OWL.ObjectProperty))),
        "data_properties": len(set(expected.subjects(RDF.type, OWL.DatatypeProperty))),
        "annotation_properties": len(set(expected.subjects(RDF.type, OWL.AnnotationProperty))),
        "source_export_graph_equality": True, "full_owl_reasoner": "not run",
    }


def build(root=ROOT):
    config, graph = expected_graph(root)
    # Serialize and round-trip both formats before replacing either export.
    payloads = {}
    for kind, name in config["outputs"].items():
        payload = graph.serialize(format=kind, encoding="utf-8")
        if not isomorphic(graph, Graph().parse(data=payload, format=kind)):
            raise ValueError(f"Round-trip graph mismatch: {kind}")
        payloads[local_file(root, name)] = payload
    for path, payload in payloads.items():
        path.write_bytes(payload)
    return check_outputs(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify exports without writing files")
    args = parser.parse_args()
    report = check_outputs() if args.check else build()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
