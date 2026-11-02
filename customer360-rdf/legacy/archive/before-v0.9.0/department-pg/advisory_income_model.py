"""Bounded advisor/income metadata contract and offline projection; no data access."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FH = "https://example.org/ontology/holding#"
BANK = "https://example.org/ontology/bank#"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
FIELDS = {
    "employeeId": ("string", BANK + "employeeId", BANK + "BankEmployee"),
    "customerId": ("string", None, FH + "Customer"),
    "productId": ("string", None, FH + "FinancialProduct"),
    "amount": ("decimal", None, None),
    "currency": ("string", None, None),
    "incomePeriod": (None, None, None),
    "snapshotDate": (None, None, None),
}
CONCEPTS = {
    "bank.financial_advisor": ("理專", BANK + "FinancialAdvisor", {"employeeId"}),
    "bank.product_fee_income": (
        "商品手收", BANK + "BankFeeIncome",
        {"employeeId", "customerId", "amount", "currency", "incomePeriod", "snapshotDate"},
    ),
}
RELATIONS = {
    "bank.advisor_serves_customer": (
        "bank.financial_advisor", FH + "serves", FH + "Employee", FH + "Customer",
        {"employeeId", "customerId"},
    ),
    "bank.product_fee_income.product": (
        "bank.product_fee_income", FH + "feeIncomeFromProduct", FH + "FeeIncome",
        FH + "FinancialProduct", {"productId"},
    ),
    "bank.product_fee_income.advisor": (
        "bank.product_fee_income", BANK + "attributedToAdvisor", BANK + "BankFeeIncome",
        BANK + "FinancialAdvisor", set(),
    ),
}
EXECUTION_KEYS = {
    "sql", "join_rules", "filter_rules", "aggregation_rules", "row_grain",
    "advisor_recognition_rules", "fee_recognition_rules", "attribution_rules", "period_basis",
}
LABELS = frozenset({
    "MetadataModule", "BusinessConcept", "BusinessRelationDefinition", "DataFieldDefinition",
    "OntologyClassReference", "OntologyPropertyReference", "OntologyObjectPropertyReference",
})
RELATIONSHIPS = {
    "HAS_CONCEPT": ("MetadataModule", "BusinessConcept"),
    "REFERS_TO_CLASS": ("BusinessConcept", "OntologyClassReference"),
    "HAS_FIELD_DEFINITION": ("BusinessConcept", "DataFieldDefinition"),
    "HAS_RELATION_DEFINITION": ("BusinessConcept", "BusinessRelationDefinition"),
    "HAS_RELATION_FIELD": ("BusinessRelationDefinition", "DataFieldDefinition"),
    "REFERS_TO_OBJECT_PROPERTY": ("BusinessRelationDefinition", "OntologyObjectPropertyReference"),
    "HAS_TARGET_CLASS": ("BusinessRelationDefinition", "OntologyClassReference"),
    "FIELD_REFERS_TO_PROPERTY": ("DataFieldDefinition", "OntologyPropertyReference"),
    "FIELD_IDENTIFIES_CLASS": ("DataFieldDefinition", "OntologyClassReference"),
    "HAS_DOMAIN_REFERENCE": ("OntologyPropertyReference", "OntologyClassReference"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, context):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"{context}: unexpected or missing keys")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_fields(fields, expected):
    require(isinstance(fields, list) and len(fields) == len(expected), "Incorrect field coverage")
    seen = set()
    for item in fields:
        keys(item, {"field", "status", "table", "column"}, "field mapping")
        require(isinstance(item["field"], str) and item["field"] in expected
                and item["field"] not in seen, "Unknown or duplicate field")
        seen.add(item["field"])
        require(item["status"] == "pending" and item["table"] is None and item["column"] is None,
                "Advisor/income source mappings remain pending")


def validate_model(model):
    keys(model, {"schema_version", "ontology_version", "status", "scope", "inference",
                 "instance_mapping", "access_policy_status", "execution", "field_definitions",
                 "concepts", "relation_definitions"}, "advisor/income module")
    require(model["schema_version"] == "1.0.0" and model["ontology_version"] == "0.8.0",
            "Expected advisor/income schema 1.0.0 / ontology 0.8.0")
    require(model["status"] == "active" and model["scope"] == "metadata_only"
            and model["inference"] is False and model["instance_mapping"] is False,
            "Only active metadata without inference/instance mapping is supported")
    require(model["access_policy_status"] == "deferred_by_user", "Access design is deferred")
    keys(model["execution"], EXECUTION_KEYS, "execution")
    require(all(value is None for value in model["execution"].values()),
            "Sources, advisor recognition, income rules, attribution and grain are not approved")
    keys(model["field_definitions"], FIELDS, "field definitions")
    for field, (hint, prop, entity) in FIELDS.items():
        definition = model["field_definitions"][field]
        keys(definition, {"name", "definition", "data_type_hint", "property_uri", "entity_class_uri"},
             "field definition")
        require(all(isinstance(definition[key], str) and definition[key].strip()
                    for key in ("name", "definition")), "Missing field name/definition")
        require((definition["data_type_hint"], definition["property_uri"],
                 definition["entity_class_uri"]) == (hint, prop, entity),
                "Incorrect common semantic reference or type hint")
    concepts = model["concepts"]
    require(isinstance(concepts, list) and len(concepts) == len(CONCEPTS), "Expected two concepts")
    seen = set()
    for concept in concepts:
        keys(concept, {"id", "name", "definition", "subsidiary", "department_owner", "class_uri",
                       "specific_product_class_uri", "fields"}, "business concept")
        cid = concept["id"]
        require(isinstance(cid, str) and cid in CONCEPTS and cid not in seen,
                "Unknown or duplicate concept")
        seen.add(cid)
        name, class_uri, fields = CONCEPTS[cid]
        require(concept["name"] == name and concept["class_uri"] == class_uri,
                "Incorrect advisor/income common semantic reference")
        require(isinstance(concept["definition"], str) and bool(concept["definition"].strip()),
                "Missing concept definition")
        require(concept["subsidiary"] == "bank" and concept["department_owner"] is None
                and concept["specific_product_class_uri"] is None,
                "Department owner and specific product semantics remain pending")
        validate_fields(concept["fields"], fields)
    relations = model["relation_definitions"]
    require(isinstance(relations, list) and len(relations) == len(RELATIONS), "Incorrect relation coverage")
    seen = set()
    for relation in relations:
        keys(relation, {"id", "name", "source_concept", "property_uri", "domain_uri",
                        "target_class_uri", "fields"}, "business relation definition")
        rid = relation["id"]
        require(isinstance(rid, str) and rid in RELATIONS and rid not in seen,
                "Unknown or duplicate relation")
        seen.add(rid)
        source, prop, domain, target, fields = RELATIONS[rid]
        require(tuple(relation[key] for key in ("source_concept", "property_uri", "domain_uri",
                                               "target_class_uri")) == (source, prop, domain, target),
                "Incorrect service/product relation semantics")
        require(isinstance(relation["name"], str) and bool(relation["name"].strip()),
                "Missing relation name")
        validate_fields(relation["fields"], fields)


def load_model(path=None):
    model = json.loads((HERE / "advisory-income.json" if path is None else Path(path)).read_text(
        encoding="utf-8"))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    return project_graph(model)


def project_graph(model, module_id="department-pg.advisory-income"):
    """Project a model already validated by its owning module's contract."""
    nodes, edges = {}, {}

    def node(node_id, label, **properties):
        value = {"id": node_id, "label": label, "properties": {"scope": "metadata_only", **properties}}
        require(node_id not in nodes or nodes[node_id] == value, "Conflicting advisor/income node ID")
        nodes[node_id] = value

    def edge(source, kind, target):
        eid = source + "|" + kind + "|" + target
        edges[eid] = {"id": eid, "type": kind, "source": source, "target": target}

    def class_ref(uri):
        node(uri, "OntologyClassReference", uri=uri)

    def fields(parent, items, relation=False):
        for mapping in items:
            name = mapping["field"]
            fid = parent + "." + name
            definition = model["field_definitions"][name]
            node(fid, "DataFieldDefinition", field_name=name, name=definition["name"],
                 definition=definition["definition"], status=mapping["status"],
                 data_type_hint_json=canonical_json(definition["data_type_hint"]),
                 mapping_json=canonical_json(mapping))
            edge(parent, "HAS_RELATION_FIELD" if relation else "HAS_FIELD_DEFINITION", fid)
            entity, prop = definition["entity_class_uri"], definition["property_uri"]
            if entity:
                class_ref(entity)
                edge(fid, "FIELD_IDENTIFIES_CLASS", entity)
            if prop:
                node(prop, "OntologyPropertyReference", uri=prop, range_uri=XSD_STRING)
                edge(fid, "FIELD_REFERS_TO_PROPERTY", prop)
                edge(prop, "HAS_DOMAIN_REFERENCE", entity)

    mid = module_id
    node(mid, "MetadataModule", ontology_version=model["ontology_version"],
         schema_version=model["schema_version"], status="active",
         access_policy_status=model["access_policy_status"], execution_json=canonical_json(model["execution"]))
    for concept in model["concepts"]:
        cid = concept["id"]
        node(cid, "BusinessConcept", name=concept["name"], definition=concept["definition"],
             subsidiary="bank", department_owner_json="null",
             specific_product_class_uri_json=canonical_json(concept["specific_product_class_uri"]))
        edge(mid, "HAS_CONCEPT", cid)
        class_ref(concept["class_uri"])
        edge(cid, "REFERS_TO_CLASS", concept["class_uri"])
        fields(cid, concept["fields"])
    for relation in model["relation_definitions"]:
        rid, prop = relation["id"], relation["property_uri"]
        node(rid, "BusinessRelationDefinition", name=relation["name"], status="pending_mapping")
        node(prop, "OntologyObjectPropertyReference", uri=prop, domain_uri=relation["domain_uri"],
             range_uri=relation.get("range_uri", relation["target_class_uri"]))
        class_ref(relation["target_class_uri"])
        edge(relation["source_concept"], "HAS_RELATION_DEFINITION", rid)
        edge(rid, "REFERS_TO_OBJECT_PROPERTY", prop)
        edge(rid, "HAS_TARGET_CLASS", relation["target_class_uri"])
        fields(rid, relation["fields"], relation=True)
    return {"nodes": sorted(nodes.values(), key=lambda item: item["id"]),
            "relationships": sorted(edges.values(), key=lambda item: item["id"])}
