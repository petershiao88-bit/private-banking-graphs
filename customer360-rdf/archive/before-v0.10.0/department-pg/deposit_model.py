"""Active deposit metadata contract and offline graph projection (stdlib only).

Fields describe data definitions, not RDF product properties or instance values.
This deliberately bounded validator is the deposit module's executable schema.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = "https://example.org/ontology/bank#"
NT_CODES = ("2311", "2321", "2322", "2331", "2332", "2333", "2335", "2336")
FN_CODES = ("2317", "2327")
SOURCES = {
    "DSDEP.DEP_NT_ACCT": ("BAL_AMT", "ACT_CD", "sql_nt_current", ("DATA_DT",)),
    "DSDEP.DEP_NT_ACCT_HS": (
        "BAL_AMT", "ACT_CD", "sql_nt_history", ("LST_MTN_DT", "DATA_DT", "YYYYMM")
    ),
    "DSDEP.DEP_FN_ACCT": ("AVAIL_BAL", "ACC_CD", "sql_fn_current", ("LST_MTN_DT",)),
    "DSDEP.DEP_FN_ACCT_HS": ("AVAIL_BAL", "ACC_CD", "sql_fn_history", ("LST_MTN_DT",)),
    "DSDEP.EMP_DEP_NT_ACCT_HS": (
        "BAL_AMT", "ACT_CD", "sql_employee", ("LST_MTN_DT", "DATA_DT", "YYYYMM")
    ),
}
CONCEPTS = {
    "bank.twd_deposit": (
        "台幣存款", ("DepositProduct", "TWDFinancialProduct"), tuple(SOURCES)[:2]
    ),
    "bank.foreign_currency_deposit": (
        "外幣存款", ("DepositProduct", "ForeignCurrencyFinancialProduct"), tuple(SOURCES)[2:4]
    ),
    "bank.structured_deposit": (
        "結構型存款", ("DepositProduct", "StructuredFinancialProduct"), tuple(SOURCES)
    ),
    "bank.employee_deposit": ("行員存款", ("DepositProduct",), ("DSDEP.EMP_DEP_NT_ACCT_HS",)),
}
FIELDS = {
    "customerId": ("客戶識別", "string", "observed_raw_candidate"),
    "currency": ("幣別", "string", "pending_currency"),
    "balance": ("餘額", "decimal", "observed_raw_candidate"),
    "snapshotDate": ("快照日期", None, "pending_time_semantics"),
    "employeeId": ("行員識別", "string", "pending_employee_identity"),
}
LABELS = frozenset({
    "MetadataModule", "BusinessConcept", "OntologyClassReference", "DataFieldDefinition",
    "SourceTable", "PendingSemanticReference",
})
RELATIONSHIPS = {
    "HAS_CONCEPT": ("MetadataModule", "BusinessConcept"),
    "REFERS_TO_CLASS": ("BusinessConcept", "OntologyClassReference"),
    "HAS_FIELD_DEFINITION": ("BusinessConcept", "DataFieldDefinition"),
    "CANDIDATE_SOURCE": ("DataFieldDefinition", "SourceTable"),
    "HAS_PENDING_REFERENCE": ("BusinessConcept", "PendingSemanticReference"),
}
EXECUTION_KEYS = {
    "sql", "join_rules", "filter_rules", "union_rules", "aggregation_rules", "row_grain",
    "partition_windows",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, context):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"{context}: unexpected or missing keys")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sorted_objects(values):
    return sorted(values, key=canonical_json)


def validate_model(model):
    keys(model, {"schema_version", "ontology_version", "status", "scope", "inference",
                 "instance_mapping", "field_definitions", "execution", "evidence", "sources",
                 "observations", "concepts"}, "deposit module")
    require(model["schema_version"] == "1.0.0" and model["ontology_version"] == "0.9.0",
            "Expected deposit schema 1.0.0 / ontology 0.9.0")
    require(model["status"] == "active" and model["scope"] == "metadata_only"
            and model["inference"] is False and model["instance_mapping"] is False,
            "Only active metadata without inference/instance mapping is supported")
    keys(model["execution"], EXECUTION_KEYS, "execution")
    require(all(value is None for value in model["execution"].values()),
            "No operational SQL, joins, filters, union, aggregation, grain or windows approved")
    keys(model["field_definitions"], FIELDS, "field definitions")
    for field, (name, hint, _) in FIELDS.items():
        definition = model["field_definitions"][field]
        keys(definition, {"name", "definition", "data_type_hint"}, "field definition")
        require(definition["name"] == name and definition["data_type_hint"] == hint
                and nonempty(definition["definition"]), "Incorrect field definition")
    evidence = model["evidence"]
    require(isinstance(evidence, dict) and bool(evidence), "Missing evidence catalog")
    allowed_files = {
        "Ontology/私銀智能問答/sources/sql/1.AUM_DETAIL.sql",
        "Ontology/私銀智能問答/sources/sql/2._AUM_SUMY.~sql",
        "Ontology/私銀智能問答/sources/sql/0_PB_CUST_DEATAIL.sql",
        "Ontology/私銀智能問答/sources/metadata/收入_metadata.xlsx",
        "Ontology/私銀智能問答/sources/metadata/AUM_metadata.xlsx",
    }
    for item in evidence.values():
        require(isinstance(item, dict), "Invalid evidence record")
        if "lines" in item:
            keys(item, {"file", "lines"}, "SQL evidence")
            lines = item["lines"]
            require(isinstance(lines, list) and len(lines) == 2
                    and all(type(line) is int and line > 0 for line in lines)
                    and lines[0] <= lines[1], "Invalid evidence line range")
        else:
            keys(item, {"file", "sheet", "rows"}, "workbook evidence")
            require(nonempty(item["sheet"]) and isinstance(item["rows"], list)
                    and bool(item["rows"])
                    and all(type(row) is int and row > 0 for row in item["rows"]),
                    "Invalid sheet/row evidence")
        require(item["file"] in allowed_files, "Unknown evidence file")

    def evidence_refs(refs):
        require(isinstance(refs, list) and bool(refs)
                and all(isinstance(ref, str) and ref in evidence for ref in refs)
                and len(set(refs)) == len(refs), "Missing/unknown/duplicate evidence reference")

    sources = model["sources"]
    require(isinstance(sources, list) and len(sources) == len(SOURCES), "Expected five sources")
    seen = set()
    for source in sources:
        keys(source, {"table", "status", "database_verified", "evidence"}, "source table")
        table = source["table"]
        require(isinstance(table, str) and table in SOURCES and table not in seen,
                "Unknown or duplicate source table")
        seen.add(table)
        require(source["status"] == "observed_in_files" and source["database_verified"] is False,
                "Source observations are not database verification")
        evidence_refs(source["evidence"])
        require(SOURCES[table][2] in source["evidence"], "Source lacks SQL evidence")
    observations = model["observations"]
    keys(observations, {"historical_filter", "currency", "union", "employee_source",
                        "advisor_distinction", "grain_and_identity"}, "observations")
    for observation in observations.values():
        require(isinstance(observation, dict), "Invalid observation")
        evidence_refs(observation.get("evidence"))
    require(observations["historical_filter"] == {
        "column": "YYYYMM", "operator": ">=", "value": "202506",
        "status": "evidence_only_not_operational_default",
        "evidence": observations["historical_filter"]["evidence"],
    }, "Historical filter must remain evidence only")
    require(observations["advisor_distinction"].get("rejected_source") == "AUM_TMP02.EMP_NO"
            and observations["advisor_distinction"].get("status") == "excluded_mapping",
            "Advisor EMP_NO must not become depositor employee identity")
    concepts = model["concepts"]
    require(isinstance(concepts, list) and len(concepts) == len(CONCEPTS), "Expected four concepts")
    seen = set()
    for concept in concepts:
        keys(concept, {"id", "name", "definition", "subsidiary", "department_owner", "class_uris",
                       "source_candidates", "classification_evidence", "pending_semantic_reference",
                       "fields"}, "deposit concept")
        concept_id = concept["id"]
        require(isinstance(concept_id, str) and concept_id in CONCEPTS and concept_id not in seen,
                "Unknown or duplicate deposit concept")
        seen.add(concept_id)
        name, class_names, tables = CONCEPTS[concept_id]
        require(concept["name"] == name and nonempty(concept["definition"])
                and isinstance(concept["class_uris"], list)
                and sorted(concept["class_uris"]) == sorted(BANK + name for name in class_names),
                "Incorrect deposit semantic references")
        require(concept["subsidiary"] == "bank" and concept["department_owner"] is None,
                "Department owner remains unknown")
        require(isinstance(concept["source_candidates"], list)
                and sorted(concept["source_candidates"]) == sorted(tables),
                "Incorrect deposit source candidates")
        classifications = concept["classification_evidence"]
        require(isinstance(classifications, list) and len(classifications) == len(tables),
                "Incomplete classification evidence")
        classified = set()
        for item in classifications:
            keys(item, {"table", "column", "codes", "status", "evidence"}, "classification")
            table = item["table"]
            require(table in tables and table not in classified, "Invalid classification source")
            classified.add(table)
            codes = ("2545",) if concept_id == "bank.structured_deposit" else (
                NT_CODES + ("2545",) if concept_id == "bank.employee_deposit" else (
                    FN_CODES if concept_id == "bank.foreign_currency_deposit" else NT_CODES))
            require(item["column"] == SOURCES[table][1] and item["status"] == "evidence_only"
                    and sorted(item["codes"]) == sorted(codes), "Incorrect observed classification")
            evidence_refs(item["evidence"])
            require(SOURCES[table][2] in item["evidence"], "Classification lacks source SQL evidence")
        pending = concept["pending_semantic_reference"]
        if concept_id == "bank.employee_deposit":
            keys(pending, {"id", "name", "status", "class_uri", "relation_uri", "source_table",
                           "source_column", "join_rules"}, "pending employee reference")
            require(pending["id"] == concept_id + ".depositor_employee_reference"
                    and pending["name"] == "存款人本人為行員"
                    and pending["status"] == "pending_depositor_identity_mapping"
                    and pending["class_uri"] == BANK + "BankEmployee"
                    and all(pending[key] is None for key in (
                        "relation_uri", "source_table", "source_column", "join_rules")),
                    "Approved employee class must not resolve the unknown depositor identity join")
        else:
            require(pending is None, "Unexpected pending semantic reference")
        fields = concept["fields"]
        expected_fields = set(FIELDS) - (set() if concept_id == "bank.employee_deposit" else {"employeeId"})
        require(isinstance(fields, list) and len(fields) == len(expected_fields), "Incorrect field count")
        seen_fields = set()
        for mapping in fields:
            keys(mapping, {"field", "status", "table", "column", "constant", "candidates"}, "mapping")
            field = mapping["field"]
            require(isinstance(field, str) and field in expected_fields and field not in seen_fields,
                    "Unknown or duplicate field")
            seen_fields.add(field)
            require(mapping["status"] == FIELDS[field][2]
                    and all(mapping[key] is None for key in ("table", "column", "constant")),
                    "Mappings are candidates, not selected physical mappings or constants")
            expected = set()
            for table in tables:
                if field == "customerId":
                    expected.add((table, "CUST_ID"))
                elif field == "balance":
                    expected.add((table, SOURCES[table][0]))
                elif field == "snapshotDate":
                    expected.update((table, column) for column in SOURCES[table][3])
            candidates = mapping["candidates"]
            require(isinstance(candidates, list), "Expected candidate list")
            actual = set()
            for candidate in candidates:
                keys(candidate, {"table", "column", "meaning", "evidence"}, "field candidate")
                pair = (candidate["table"], candidate["column"])
                require(pair in expected and pair not in actual and nonempty(candidate["meaning"]),
                        "Unknown/duplicate field candidate; currency and employeeId have none")
                actual.add(pair)
                evidence_refs(candidate["evidence"])
                table, column = pair
                required_ref = SOURCES[table][2]
                if column in {"DATA_DT", "YYYYMM"} and table.endswith("_HS"):
                    required_ref = "income_employee" if "EMP_" in table else "income_nt"
                require(required_ref in candidate["evidence"], "Candidate lacks source-specific evidence")
            require(actual == expected, "Incomplete field candidate coverage")


def load_model(path=None):
    model = json.loads((HERE / "deposits.json" if path is None else Path(path)).read_text(encoding="utf-8"))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    nodes, edges = {}, {}

    def node(node_id, label, **properties):
        value = {"id": node_id, "label": label,
                 "properties": {"scope": "metadata_only", **properties}}
        require(node_id not in nodes or nodes[node_id] == value, "Conflicting deposit node ID")
        nodes[node_id] = value

    def edge(source, kind, target):
        edge_id = f"{source}|{kind}|{target}"
        edges[edge_id] = {"id": edge_id, "type": kind, "source": source, "target": target}

    module_id = "department-pg.deposits"
    # Catalog and module-wide limitations remain available in the generated graph.
    observations = dict(model["observations"])
    for key, item in observations.items():
        observations[key] = {**item, "evidence": sorted(item["evidence"])}
    evidence = {key: {**item, **({"rows": sorted(item["rows"])} if "rows" in item else {})}
                for key, item in model["evidence"].items()}
    node(module_id, "MetadataModule", ontology_version=model["ontology_version"],
         schema_version=model["schema_version"], status="active",
         execution_json=canonical_json(model["execution"]), evidence_json=canonical_json(evidence),
         observations_json=canonical_json(observations))
    for source in model["sources"]:
        node("source:" + source["table"], "SourceTable", table=source["table"],
             status=source["status"], database_verified_json="false",
             evidence_json=canonical_json(sorted(source["evidence"])))
    for concept in model["concepts"]:
        concept_id = concept["id"]
        classifications = [{**item, "codes": sorted(item["codes"]),
                            "evidence": sorted(item["evidence"])}
                           for item in concept["classification_evidence"]]
        node(concept_id, "BusinessConcept", name=concept["name"], definition=concept["definition"],
             subsidiary="bank", department_owner_json="null",
             source_candidates_json=canonical_json(sorted(concept["source_candidates"])),
             classification_evidence_json=canonical_json(sorted_objects(classifications)))
        edge(module_id, "HAS_CONCEPT", concept_id)
        for class_uri in concept["class_uris"]:
            node(class_uri, "OntologyClassReference", uri=class_uri)
            edge(concept_id, "REFERS_TO_CLASS", class_uri)
        for mapping in concept["fields"]:
            field = mapping["field"]
            field_id = concept_id + "." + field
            definition = model["field_definitions"][field]
            candidates = [{**item, "evidence": sorted(item["evidence"])} for item in mapping["candidates"]]
            normalized = {**mapping, "candidates": sorted_objects(candidates)}
            node(field_id, "DataFieldDefinition", field_name=field, name=definition["name"],
                 definition=definition["definition"], status=mapping["status"],
                 data_type_hint_json=canonical_json(definition["data_type_hint"]),
                 mapping_json=canonical_json(normalized))
            edge(concept_id, "HAS_FIELD_DEFINITION", field_id)
            for candidate in candidates:
                edge(field_id, "CANDIDATE_SOURCE", "source:" + candidate["table"])
        pending = concept["pending_semantic_reference"]
        if pending is not None:
            node(pending["id"], "PendingSemanticReference", name=pending["name"],
                 status=pending["status"], reference_json=canonical_json(pending))
            edge(concept_id, "HAS_PENDING_REFERENCE", pending["id"])
    return {"nodes": sorted(nodes.values(), key=lambda item: item["id"]),
            "relationships": sorted(edges.values(), key=lambda item: item["id"])}
