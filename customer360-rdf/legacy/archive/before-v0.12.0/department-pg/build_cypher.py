"""Build Neo4j 5 metadata DDL/DML offline using only the Python standard library."""

import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPOSIT_SPEC = importlib.util.spec_from_file_location("department_pg_deposits", HERE / "deposit_model.py")
assert DEPOSIT_SPEC is not None and DEPOSIT_SPEC.loader is not None
deposits = importlib.util.module_from_spec(DEPOSIT_SPEC)
DEPOSIT_SPEC.loader.exec_module(deposits)
INCOME_SPEC = importlib.util.spec_from_file_location("department_pg_advisory_income", HERE / "advisory_income_model.py")
assert INCOME_SPEC is not None and INCOME_SPEC.loader is not None
advisory_income = importlib.util.module_from_spec(INCOME_SPEC)
INCOME_SPEC.loader.exec_module(advisory_income)
FEE_SPEC = importlib.util.spec_from_file_location("department_pg_product_fees", HERE / "product_fees_model.py")
assert FEE_SPEC is not None and FEE_SPEC.loader is not None
product_fees = importlib.util.module_from_spec(FEE_SPEC)
FEE_SPEC.loader.exec_module(product_fees)
AUM_SPEC = importlib.util.spec_from_file_location("department_pg_product_aum", HERE / "product_aum_model.py")
assert AUM_SPEC is not None and AUM_SPEC.loader is not None
product_aum = importlib.util.module_from_spec(AUM_SPEC)
AUM_SPEC.loader.exec_module(product_aum)
INV_SPEC = importlib.util.spec_from_file_location("department_pg_investment_metrics", HERE / "investment_metrics_model.py")
assert INV_SPEC is not None and INV_SPEC.loader is not None
investment_metrics = importlib.util.module_from_spec(INV_SPEC)
INV_SPEC.loader.exec_module(investment_metrics)

FH = "https://example.org/ontology/holding#"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
CONTRACT = {
    "bank.loan_verification_mobile": (
        "貸款照會手機", "MobileContactInformation", ("mobileNumber",)
    ),
    "bank.customer_visit_address": (
        "客戶訪問地址", "AddressContactInformation",
        ("countryCode", "city", "district", "addressLine", "postalCode", "fullAddress"),
    ),
}
LABELS = frozenset({
    "BusinessConcept", "OntologyClassReference", "OntologyPropertyReference", "MappingSlot"
})
RELATIONSHIPS = {
    "REFERS_TO_CLASS": ("BusinessConcept", "OntologyClassReference"),
    "HAS_MAPPING": ("BusinessConcept", "MappingSlot"),
    "REFERS_TO_PROPERTY": ("MappingSlot", "OntologyPropertyReference"),
    "HAS_DOMAIN_REFERENCE": ("OntologyPropertyReference", "OntologyClassReference"),
}
SOURCE_KEYS = {"status", "table", "field", "sql", "join_rules", "filter_rules"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, context):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"{context}: unexpected or missing keys")


def validate_model(model):
    """Validate the preserved contact contract under v0.11.0, without loading RDF.

    JSON Schema describes the structure; these additional checks enforce unique
    IDs, exact concept/property coverage, domains, and pending-only source safety.
    """
    keys(model, {"schema_version", "ontology_version", "scope", "inference",
                 "instance_mapping", "concepts"}, "model")
    require(model["schema_version"] == "1.0.0", "Unsupported schema version")
    require(model["ontology_version"] == "0.11.0", "Expected ontology v0.11.0")
    require(model["scope"] == "metadata_only" and model["inference"] is False
            and model["instance_mapping"] is False, "Only metadata without inference is allowed")
    concepts = model["concepts"]
    require(isinstance(concepts, list) and len(concepts) == len(CONTRACT),
            "Expected exactly two concepts")
    seen = set()
    for concept in concepts:
        keys(concept, {"id", "name", "subsidiary", "department_owner", "class_uri", "mappings"},
             "concept")
        concept_id = concept["id"]
        require(isinstance(concept_id, str) and concept_id in CONTRACT and concept_id not in seen,
                "Unknown or duplicate concept ID")
        seen.add(concept_id)
        name, class_name, fields = CONTRACT[concept_id]
        require(concept["name"] == name, f"{concept_id}: unexpected business name")
        require(concept["subsidiary"] == "bank" and concept["department_owner"] is None,
                f"{concept_id}: owner must remain unknown; subsidiary must be bank")
        require(concept["class_uri"] == FH + class_name, f"{concept_id}: incorrect class URI")
        mappings = concept["mappings"]
        require(isinstance(mappings, list) and len(mappings) == len(fields),
                f"{concept_id}: incorrect mapping count")
        seen_fields = set()
        for mapping in mappings:
            keys(mapping, {"id", "property_uri", "domain_uri", "range_uri", "source"}, "mapping")
            prop = mapping["property_uri"]
            require(isinstance(prop, str) and prop in {FH + field for field in fields}
                    and prop not in seen_fields, f"{concept_id}: unknown or duplicate property")
            seen_fields.add(prop)
            field = prop[len(FH):]
            require(mapping["id"] == concept_id + "." + field, "Unstable mapping ID")
            require(mapping["domain_uri"] == concept["class_uri"], "Incorrect property domain")
            require(mapping["range_uri"] == XSD_STRING, "Expected xsd:string range")
            source = mapping["source"]
            keys(source, SOURCE_KEYS, "source")
            require(source["status"] == "pending"
                    and all(source[key] is None for key in SOURCE_KEYS - {"status"}),
                    "Physical sources must remain pending with null table/field/SQL/rules")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_model(path=None):
    with (HERE / "model.json" if path is None else Path(path)).open(encoding="utf-8") as stream:
        model = json.load(stream)
    validate_model(model)
    return model


def build_graph(model):
    """Return deterministically sorted metadata nodes and relationships."""
    validate_model(model)
    nodes = {}
    edges = {}

    def node(node_id, label, **properties):
        value = {"id": node_id, "label": label,
                 "properties": {"scope": "metadata_only", **properties}}
        require(node_id not in nodes or nodes[node_id] == value, "Conflicting node ID")
        nodes[node_id] = value

    def edge(source, kind, target):
        edge_id = source + "|" + kind + "|" + target
        edges[edge_id] = {"id": edge_id, "type": kind, "source": source, "target": target}

    for concept in model["concepts"]:
        concept_id, class_uri = concept["id"], concept["class_uri"]
        node(concept_id, "BusinessConcept", name=concept["name"], subsidiary=concept["subsidiary"],
             department_owner_json=canonical_json(concept["department_owner"]))
        node(class_uri, "OntologyClassReference", uri=class_uri)
        edge(concept_id, "REFERS_TO_CLASS", class_uri)
        for mapping in concept["mappings"]:
            slot_id, prop_uri = mapping["id"], mapping["property_uri"]
            node(slot_id, "MappingSlot", status="pending", source_json=canonical_json(mapping["source"]))
            node(prop_uri, "OntologyPropertyReference", uri=prop_uri, range_uri=mapping["range_uri"])
            edge(concept_id, "HAS_MAPPING", slot_id)
            edge(slot_id, "REFERS_TO_PROPERTY", prop_uri)
            edge(prop_uri, "HAS_DOMAIN_REFERENCE", mapping["domain_uri"])
    return {"nodes": sorted(nodes.values(), key=lambda item: item["id"]),
            "relationships": sorted(edges.values(), key=lambda item: item["id"])}


def cypher_string(value):
    """Use JSON string escaping (double quotes) for Cypher string literals."""
    require(isinstance(value, str), "Expected a string property")
    return json.dumps(value, ensure_ascii=False)


def cypher_properties(properties):
    for key in properties:
        require(re.fullmatch(r"[a-z_]+", key) is not None, "Unsafe property key")
    return "{" + ", ".join(key + ": " + cypher_string(properties[key])
                            for key in sorted(properties)) + "}"


def build_combined_graph(model=None, deposit_model=None, income_model=None, fee_model=None, aum_model=None, investment_model=None):
    """Load all active modules by default; merge without changing contact APIs."""
    contact_graph = build_graph(load_model() if model is None else model)
    deposit_graph = deposits.build_graph(deposits.load_model() if deposit_model is None else deposit_model)
    income_graph = advisory_income.build_graph(
        advisory_income.load_model() if income_model is None else income_model)
    fee_graph = product_fees.build_graph(product_fees.load_model() if fee_model is None else fee_model)
    aum_graph = product_aum.build_graph(product_aum.load_model() if aum_model is None else aum_model)
    investment_graph = investment_metrics.build_graph(
        investment_metrics.load_model() if investment_model is None else investment_model)
    combined = {}
    for collection in ("nodes", "relationships"):
        items = {}
        for graph in (contact_graph, deposit_graph, income_graph, fee_graph, aum_graph, investment_graph):
            for item in graph[collection]:
                require(item["id"] not in items or items[item["id"]] == item,
                        "Conflicting stable ID between active modules")
                items[item["id"]] = item
        combined[collection] = sorted(items.values(), key=lambda item: item["id"])
    return combined


def render_cypher(model):
    """Render contacts only; retained for existing callers and contact tests."""
    return render_graph_cypher(build_graph(model))


def render_combined_cypher(model=None, deposit_model=None, income_model=None, fee_model=None, aum_model=None, investment_model=None):
    return render_graph_cypher(build_combined_graph(model, deposit_model, income_model, fee_model, aum_model, investment_model))


def render_graph_cypher(graph):
    allowed_labels = LABELS | deposits.LABELS | advisory_income.LABELS | product_fees.LABELS | product_aum.LABELS | investment_metrics.LABELS
    allowed_relationships = {**RELATIONSHIPS, **deposits.RELATIONSHIPS, **advisory_income.RELATIONSHIPS,
                             **product_fees.RELATIONSHIPS, **product_aum.RELATIONSHIPS, **investment_metrics.RELATIONSHIPS}
    nodes = {node["id"]: node for node in graph["nodes"]}
    lines = [
        "// Generated by build_cypher.py; do not edit. Neo4j 5 metadata only.",
        "// URI references are not RDF type/equivalence assertions or instance mappings.",
        "// SourceTable nodes are file-observed metadata, not database verification.",
        "// Pending mappings stay JSON nulls; no source SQL is executed.",
        "CREATE CONSTRAINT department_pg_metadata_id IF NOT EXISTS",
        "FOR (n:MetadataNode) REQUIRE n.id IS UNIQUE;",
        "",
    ]
    for node in graph["nodes"]:
        require(node["label"] in allowed_labels, "Unknown node label")
        lines.append("MERGE (n:MetadataNode:" + node["label"]
                     + " {id: " + cypher_string(node["id"]) + "})")
        lines.append("SET n += " + cypher_properties(node["properties"]) + ";")
    lines.append("")
    for edge in graph["relationships"]:
        require(edge["type"] in allowed_relationships, "Unknown relationship type")
        source, target = edge["source"], edge["target"]
        require(source in nodes and target in nodes, "Missing relationship endpoint")
        require((nodes[source]["label"], nodes[target]["label"]) == allowed_relationships[edge["type"]],
                "Incorrect relationship endpoint labels")
        lines.append("MATCH (s:MetadataNode {id: " + cypher_string(source)
                     + "}), (t:MetadataNode {id: " + cypher_string(target) + "})")
        lines.append("MERGE (s)-[r:" + edge["type"] + " {id: "
                     + cypher_string(edge["id"]) + "}]->(t);")
    return "\n".join(lines) + "\n"


def main():
    output = render_combined_cypher()
    (HERE / "model.cypher").write_bytes(output.encode("utf-8"))
    print("Generated department-pg/model.cypher (metadata only; no database connection)")


if __name__ == "__main__":
    main()
