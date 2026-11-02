"""Load the complete local Turtle ontology for the native Ontology Hub only."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path


def attach_local_ontology(app):
    from fastapi import Request
    from semantica.context import ContextGraph
    from semantica.explorer.dependencies import get_session
    from semantica.explorer.session import GraphSession
    from semantica.explorer.routes.ontology import OntologyEntry, _parse_rdf_sync, _classify_node_type

    source = Path(__file__).resolve().parent.parent / "customer360-ontology.ttl"
    content = source.read_bytes()
    # The native basic RDF parser preserves annotation properties and literal
    # definitions that the OntologyIngestor conversion omits in version 0.7.0.
    nodes, edges, metadata = _parse_rdf_sync(content, "turtle")
    uri = metadata["uri"]
    for node in nodes:
        node["properties"]["scheme_uri"] = uri
    graph = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
    session = GraphSession(graph)
    session.add_nodes_and_edges(nodes, edges)
    entry = OntologyEntry(
        uri=uri, name=metadata["name"], description=metadata.get("description"),
        version=metadata.get("version"), format="turtle", status="external",
        class_count=sum(_classify_node_type(n["type"]) == "class" for n in nodes),
        property_count=sum(_classify_node_type(n["type"]) == "property" for n in nodes),
        loaded_at=datetime.now(timezone.utc).isoformat(),
        tags=["customer360", "local", "v0.16.0"])
    app.state.ontology_registry = {uri: entry}
    app.state.ontology_hub_session = session
    app.state.ontology_hub_source = {
        "path": source.name, "sha256": hashlib.sha256(content).hexdigest(),
        "rdf_triples": metadata["triple_count"], "uri": uri}

    def scoped_session(request: Request):
        if request.url.path.startswith("/api/ontology/"):
            return request.app.state.ontology_hub_session
        return request.app.state.session

    app.dependency_overrides[get_session] = scoped_session

