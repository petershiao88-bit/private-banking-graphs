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
    "amount": ("decimal", FH + "metricAmount", None),
    "currency": ("string", None, None),
    "incomePeriod": (None, None, None),
    "snapshotDate": (None, None, None),
}
# These are optional business elements, not required data values or physical mappings.
AUM_ELEMENTS = {
    "aumAsOfDate": ("date", FH + "aumAsOfDate", None),
    "valuationQuantity": ("decimal", FH + "valuationQuantity", None),
    "valuationUnitPrice": ("decimal", FH + "valuationUnitPrice", None),
}
FEE_ELEMENTS = {
    "incomePeriodStart": ("date", FH + "incomePeriodStart", None),
    "incomePeriodEnd": ("date", FH + "incomePeriodEnd", None),
    "feeBaseAmount": ("decimal", FH + "feeBaseAmount", None),
    "feeDeductionAmount": ("decimal", FH + "feeDeductionAmount", None),
}
BASE_FIELDS = dict(FIELDS)
FEE_FIELDS = BASE_FIELDS | FEE_ELEMENTS
FIELDS = FEE_FIELDS | AUM_ELEMENTS
PROPERTY_SEMANTICS = {
    FH + "metricAmount": (FH + "Metric", "decimal"),
    **{uri: (FH + "AUM", hint) for hint, uri, _ in AUM_ELEMENTS.values()},
    **{uri: (FH + "FeeIncome", hint) for hint, uri, _ in FEE_ELEMENTS.values()},
    BANK + "employeeId": (BANK + "BankEmployee", "string"),
}
CONCEPTS = {
    "bank.financial_advisor": ("理專", BANK + "FinancialAdvisor", {"employeeId"}),
    "bank.product_fee_income": (
        "商品手收", BANK + "BankFeeIncome",
        {"employeeId", "customerId", "amount", "currency", "incomePeriod", "snapshotDate"} | set(FEE_ELEMENTS),
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
    "OntologyClassReference", "OntologyPropertyReference", "OntologyObjectPropertyReference", "SourceTable",
})
TABLE_ROLES = {
    "primary": "HAS_SOURCE_TABLE",
    "valuation_support": "USES_VALUATION_SOURCE",
    "date_lookup_only": "USES_DATE_LOOKUP_SOURCE",
}
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
    **{kind: ("BusinessConcept", "SourceTable") for kind in TABLE_ROLES.values()},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, context):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"{context}: unexpected or missing keys")


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_table_sources(mapping, evidence, sources, expected, partial=False):
    """Metric-to-table observations only; no physical field or execution mapping."""
    keys(mapping, {"status", "coverage", "tables", "unresolved_supporting_relations"}, "metric table sources")
    require(mapping["status"] == ("partial_scope" if partial else "observed_in_files"),
            "Incorrect source coverage status")
    require(isinstance(mapping["coverage"], str) and mapping["coverage"].strip(), "Missing table coverage")
    catalog = {s["table"]: s for s in sources}
    rows = mapping["tables"]
    require(isinstance(rows, list) and bool(rows), "Missing metric source tables")
    seen = set()

    def refs(values):
        require(isinstance(values, list) and bool(values) and len(values) == len(set(values))
                and all(isinstance(v, str) and v in evidence for v in values), "Invalid table evidence")

    for row in rows:
        keys(row, {"table", "role", "evidence"}, "table reference")
        table, role = row["table"], row["role"]
        require(isinstance(table, str) and table in catalog and role in TABLE_ROLES
                and table not in seen, "Unknown or duplicate metric table")
        seen.add(table)
        require(catalog[table]["database_verified"] is False
                and catalog[table]["status"] == "observed_in_files", "Table is file-observed metadata only")
        refs(row["evidence"])
    require({(r["table"], r["role"]) for r in rows} == set(expected), "Incorrect metric table roles or coverage")
    pending = mapping["unresolved_supporting_relations"]
    require(isinstance(pending, list), "Invalid unresolved supporting relations")
    names = set()
    for item in pending:
        keys(item, {"name", "role", "note", "evidence"}, "unresolved supporting relation")
        require(item["name"] == "T_LAST_TWO_WORKDAYS" and item["name"] not in names
                and item["role"] == "period_support"
                and isinstance(item["note"], str) and item["note"].strip(), "Unknown supporting relation")
        names.add(item["name"])
        refs(item["evidence"])


def normalized_table_sources(mapping):
    value = json.loads(canonical_json(mapping))
    value["tables"].sort(key=lambda row: (row["role"], row["table"]))
    value["unresolved_supporting_relations"].sort(key=lambda row: row["name"])
    for row in value["tables"] + value["unresolved_supporting_relations"]:
        row["evidence"].sort()
    return value


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
                 "concepts", "relation_definitions", "evidence", "sources"}, "advisor/income module")
    require(model["schema_version"] == "1.0.0" and model["ontology_version"] == "0.11.0",
            "Expected advisor/income schema 1.0.0 / ontology 0.11.0")
    require(model["status"] == "active" and model["scope"] == "metadata_only"
            and model["inference"] is False and model["instance_mapping"] is False,
            "Only active metadata without inference/instance mapping is supported")
    require(model["access_policy_status"] == "deferred_by_user", "Access design is deferred")
    keys(model["execution"], EXECUTION_KEYS, "execution")
    require(all(value is None for value in model["execution"].values()),
            "Sources, advisor recognition, income rules, attribution and grain are not approved")
    source_tables = {"DSDEP.SI_PERFO_RPT", "DSDEP.SI_PERFO_RPT_HS", "DSFND.PB_FUND_SPREAD_DAILY", "DSINS.INSU_RPT_Q01"} | {
        "DSDEP." + code + "_PERFO_RPT" + suffix for code in ("ELI", "FCI", "DCI") for suffix in ("", "_HS")}
    require(isinstance(model["sources"], list) and len(model["sources"]) == len(source_tables)
            and {s["table"] for s in model["sources"]} == source_tables,
            "Generic fee sources cover the reviewed bank fee subset only")
    require(isinstance(model["evidence"], dict) and bool(model["evidence"]), "Missing fee table evidence")
    keys(model["field_definitions"], FEE_FIELDS, "field definitions")
    for field, (hint, prop, entity) in FEE_FIELDS.items():
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
        cid = concept["id"]
        keys(concept, {"id", "name", "definition", "subsidiary", "department_owner", "class_uri",
                       "specific_product_class_uri", "fields"} | ({"table_sources"} if cid == "bank.product_fee_income" else set()),
             "business concept")
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
        if cid == "bank.product_fee_income":
            validate_table_sources(concept["table_sources"], model["evidence"], model["sources"],
                                   {(table, "primary") for table in source_tables}, partial=True)
            require(not concept["table_sources"]["unresolved_supporting_relations"], "No generic fee helper inferred")
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
    graph = project_graph(model)
    module = next(n for n in graph["nodes"] if n["id"] == "department-pg.advisory-income")
    module["properties"]["evidence_json"] = canonical_json(model["evidence"])
    return graph


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
                domain, datatype = PROPERTY_SEMANTICS[prop]
                node(prop, "OntologyPropertyReference", uri=prop,
                     range_uri="http://www.w3.org/2001/XMLSchema#" + datatype)
                class_ref(domain)
                edge(fid, "FIELD_REFERS_TO_PROPERTY", prop)
                edge(prop, "HAS_DOMAIN_REFERENCE", domain)

    mid = module_id
    node(mid, "MetadataModule", ontology_version=model["ontology_version"],
         schema_version=model["schema_version"], status="active",
         access_policy_status=model["access_policy_status"], execution_json=canonical_json(model["execution"]))
    for concept in model["concepts"]:
        cid = concept["id"]
        node(cid, "BusinessConcept", name=concept["name"], definition=concept["definition"],
             subsidiary=concept["subsidiary"], department_owner_json="null",
             specific_product_class_uri_json=canonical_json(concept["specific_product_class_uri"]))
        edge(mid, "HAS_CONCEPT", cid)
        class_ref(concept["class_uri"])
        edge(cid, "REFERS_TO_CLASS", concept["class_uri"])
        fields(cid, concept["fields"])
        if "table_sources" in concept:
            mapping = normalized_table_sources(concept["table_sources"])
            nodes[cid]["properties"]["table_sources_json"] = canonical_json(mapping)
            for row in mapping["tables"]:
                edge(cid, TABLE_ROLES[row["role"]], "source:" + row["table"])
    for source in model.get("sources", []):
        node("source:" + source["table"], "SourceTable", table=source["table"],
             status=source["status"], database_verified_json=canonical_json(source["database_verified"]),
             evidence_json=canonical_json(sorted(source["evidence"])))
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
