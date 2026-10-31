"""Bank fee metrics and table observations; never execute the observed SQL."""

import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("product_fee_common_projection", HERE / "advisory_income_model.py")
assert SPEC is not None and SPEC.loader is not None
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
require, keys, canonical_json = common.require, common.keys, common.canonical_json
FH, BANK = common.FH, common.BANK
SI = ("DSDEP.SI_PERFO_RPT", "DSDEP.SI_PERFO_RPT_HS")
OFFSHORE = "DSFND.PB_FUND_SPREAD_DAILY"
CONCEPTS = {
    "bank.domestic_structured_si_fee_income": ("境內結構型商品手收（SI）", "bank_structured_domestic", SI),
    "bank.offshore_structured_fee_income": ("境外結構型商品手收", "bank_structured_offshore", (OFFSHORE,)),
    "bank.overseas_stock_fee_income": ("銀行海外股票手收", "bank_overseas_stock", (OFFSHORE,)),
    "bank.domestic_structured_eli_fee_income": ("境內結構型商品手收（ELI）", "bank_structured_domestic",
                                                ("DSDEP.ELI_PERFO_RPT", "DSDEP.ELI_PERFO_RPT_HS")),
    "bank.domestic_structured_fci_fee_income": ("境內結構型商品手收（FCI）", "bank_structured_domestic",
                                                ("DSDEP.FCI_PERFO_RPT", "DSDEP.FCI_PERFO_RPT_HS")),
    "bank.dci_fee_income": ("銀行 DCI 手續費收入", "bank_dci",
                             ("DSDEP.DCI_PERFO_RPT", "DSDEP.DCI_PERFO_RPT_HS")),
}
ADDED_CONCEPTS = set(CONCEPTS) - {"bank.domestic_structured_si_fee_income", "bank.offshore_structured_fee_income"}
PRODUCT_CLASSES = {cid: (("StockProduct", "OverseasFinancialProduct") if cid == "bank.overseas_stock_fee_income"
                         else ("StructuredFinancialProduct",)) for cid in CONCEPTS}
LABELS = common.LABELS | {"SourceTable"}
RELATIONSHIPS = {**common.RELATIONSHIPS, "CANDIDATE_SOURCE": ("DataFieldDefinition", "SourceTable")}


def candidate_pairs(cid, field):
    if cid in ADDED_CONCEPTS:
        return set()  # The current extension is table-only; do not assign columns.
    if cid == "bank.domestic_structured_si_fee_income":
        if field in {"customerId", "amount"}:
            return {(table, "CUSTOMER_ID" if field == "customerId" else "FEE_AMOUNT_TWD") for table in SI}
        return {(SI[0], col) for col in ("RM_ID", "USER_ID")} if field == "employeeId" else set()
    cols = {"customerId": ("IDNO",), "amount": ("BRHREBATEAMT",),
            "employeeId": ("BAOEMPID", "SAOEMPID"), "productId": ("FUNDID",)}
    return {(OFFSHORE, col) for col in cols.get(field, ())}


def validate_model(model):
    keys(model, {"schema_version", "ontology_version", "status", "scope", "inference",
                 "instance_mapping", "access_policy_status", "execution", "field_definitions",
                 "evidence", "sources", "concepts", "relation_definitions"}, "product fee module")
    require(model["schema_version"] == "1.0.0" and model["ontology_version"] == "0.15.0"
            and model["status"] == "active" and model["scope"] == "metadata_only"
            and model["inference"] is False and model["instance_mapping"] is False,
            "Expected active v0.15.0 metadata without instances or inference")
    require(model["access_policy_status"] == "deferred_by_user", "Access design is deferred")
    keys(model["execution"], common.EXECUTION_KEYS, "execution")
    require(all(v is None for v in model["execution"].values()), "No source execution or grain approved")
    keys(model["field_definitions"], common.FEE_FIELDS, "field definitions")
    for field, (hint, prop, entity) in common.FEE_FIELDS.items():
        definition = model["field_definitions"][field]
        keys(definition, {"name", "definition", "data_type_hint", "property_uri", "entity_class_uri"},
             "field definition")
        require((definition["data_type_hint"], definition["property_uri"], definition["entity_class_uri"])
                == (hint, prop, entity), "Incorrect field semantics")
        require(all(isinstance(definition[k], str) and definition[k].strip() for k in ("name", "definition")),
                "Missing field definition")
    evidence = model["evidence"]
    expected_ids = {"sql_si", "sql_offshore", "sql_si_summary", "sql_offshore_summary",
                    "metadata_si", "metadata_offshore", "private_product_domestic", "private_product_offshore",
                    "sql_overseas_stock", "sql_eli", "sql_fci", "sql_dci", "metadata_eli", "metadata_fci", "metadata_dci",
                    "private_product_stock", "private_product_dci"}
    keys(evidence, expected_ids, "evidence")
    for eid, item in evidence.items():
        if eid.startswith("sql_"):
            keys(item, {"file", "lines", "encoding"}, "SQL evidence")
            require(item["file"] == "Ontology/私銀智能問答/sources/sql/" + (
                "9.INCOME_SMY.sql" if eid.endswith("summary") else "8.INCOME_DETAIL.sql")
                and item["encoding"] == "cp950", "Incorrect SQL evidence location")
            lines = item["lines"]
            require(isinstance(lines, list) and len(lines) == 2
                    and all(type(n) is int and n > 0 for n in lines) and lines[0] <= lines[1],
                    "Invalid evidence line range")
        elif eid.startswith("metadata_"):
            keys(item, {"file", "sheet", "rows"}, "workbook evidence")
            sheet = {"metadata_si": SI[0], "metadata_offshore": OFFSHORE,
                     **{"metadata_" + kind: "DSDEP." + kind.upper() + "_PERFO_RPT" for kind in ("eli", "fci", "dci")}}[eid]
            require(item["file"] == "Ontology/私銀智能問答/sources/metadata/收入_metadata.xlsx"
                    and item["sheet"] == sheet,
                    "Incorrect workbook evidence location")
            require(isinstance(item["rows"], list) and bool(item["rows"])
                    and all(type(n) is int and n > 0 for n in item["rows"]), "Invalid workbook rows")
        else:
            keys(item, {"file", "product_code"}, "private product evidence")
            require(item["file"] == "Ontology/私銀智能問答/ontology/independent_concepts/concept_graph.json"
                    and item["product_code"] == {"private_product_domestic": "bank_structured_domestic",
                        "private_product_offshore": "bank_structured_offshore", "private_product_stock": "bank_overseas_stock",
                        "private_product_dci": "bank_dci"}[eid], "Incorrect product evidence")

    def refs(values):
        require(isinstance(values, list) and bool(values) and len(values) == len(set(values))
                and all(isinstance(v, str) and v in evidence for v in values), "Missing or invalid evidence")

    sources = model["sources"]
    expected_tables = {table for _, _, tables in CONCEPTS.values() for table in tables}
    require(isinstance(sources, list) and len(sources) == len(expected_tables), "Incorrect bank fee table coverage")
    seen = set()
    for source in sources:
        keys(source, {"table", "status", "database_verified", "evidence"}, "source")
        table = source["table"]
        require(table in expected_tables and table not in seen and source["status"] == "observed_in_files"
                and source["database_verified"] is False, "Source observation is not database verification")
        seen.add(table)
        refs(source["evidence"])
    concepts = model["concepts"]
    require(isinstance(concepts, list) and len(concepts) == len(CONCEPTS), "Incorrect bank fee concept coverage")
    seen = set()
    for concept in concepts:
        keys(concept, {"id", "name", "definition", "subsidiary", "department_owner", "class_uri",
                       "specific_product_class_uri", "private_product_code", "product_class_uris", "fields", "observations", "table_sources"},
             "product fee concept")
        cid = concept["id"]
        require(isinstance(cid, str) and cid in CONCEPTS and cid not in seen, "Unknown/duplicate concept")
        seen.add(cid)
        name, product_code, _ = CONCEPTS[cid]
        common.validate_table_sources(concept["table_sources"], evidence, sources,
                                      {(table, "primary") for table in CONCEPTS[cid][2]})
        require(not concept["table_sources"]["unresolved_supporting_relations"], "No bank fee helper inferred")
        require(concept["name"] == name and concept["private_product_code"] == product_code
                and concept["class_uri"] == BANK + "BankFeeIncome"
                and concept["specific_product_class_uri"] == BANK + PRODUCT_CLASSES[cid][0]
                and isinstance(concept["product_class_uris"], list)
                and sorted(concept["product_class_uris"]) == sorted(BANK + p for p in PRODUCT_CLASSES[cid])
                and concept["subsidiary"] == "bank" and concept["department_owner"] is None,
                "Incorrect product/income common semantic references")
        require(isinstance(concept["definition"], str) and bool(concept["definition"].strip()),
                "Missing concept definition")
        observations = concept["observations"]
        required_observations = ("coverage", "classification_observation", "excluded_scope", "gaps", "evidence") if cid in ADDED_CONCEPTS else (
            "coverage", "sql_output", "sql_group_by", "sql_aggregation", "sql_combination", "sql_filters",
            "event_date", "fee_currency", "gaps", "evidence")
        require(isinstance(observations, dict) and all(key in observations for key in required_observations), "Incomplete source observations")
        if cid in ADDED_CONCEPTS:
            keys(observations, required_observations, "table-only observations")
            require(all(isinstance(observations[k], str) and observations[k].strip()
                        for k in ("coverage", "classification_observation")), "Missing bank fee scope")
            require(isinstance(observations["excluded_scope"], list) and bool(observations["excluded_scope"])
                    and isinstance(observations["gaps"], list) and bool(observations["gaps"]), "Missing unresolved bank fee scope")
        refs(observations["evidence"])
        fields = concept["fields"]
        require(isinstance(fields, list) and len(fields) == len(common.FEE_FIELDS), "Incorrect fee field coverage")
        seen_fields = set()
        for mapping in fields:
            keys(mapping, {"field", "status", "table", "column", "candidates"}, "field mapping")
            field = mapping["field"]
            require(isinstance(field, str) and field in common.FEE_FIELDS and field not in seen_fields,
                    "Unknown or duplicate field")
            seen_fields.add(field)
            expected = candidate_pairs(cid, field)
            status = "pending" if cid in ADDED_CONCEPTS else ("observed_raw_candidate" if field in {"amount", "customerId"} else
                      "pending_attribution" if field == "employeeId" else
                      "pending_product_identity" if field == "productId" and expected else "pending")
            require(mapping["status"] == status and mapping["table"] is None and mapping["column"] is None,
                    "Observed candidates do not select an operational mapping")
            candidates = mapping["candidates"]
            require(isinstance(candidates, list) and len(candidates) == len(expected), "Candidate coverage mismatch")
            actual = set()
            for candidate in candidates:
                keys(candidate, {"table", "column", "meaning", "evidence", "applicability"}, "candidate")
                pair = (candidate["table"], candidate["column"])
                require(pair in expected and pair not in actual, "Unknown/duplicate source candidate")
                actual.add(pair)
                refs(candidate["evidence"])
                require(isinstance(candidate["meaning"], str) and bool(candidate["meaning"].strip()), "Missing candidate meaning")
                applicability = ("pending_advisor_attribution" if field == "employeeId" else
                                 "pending_sn_product_identifier" if field == "productId" else "observed_in_sql")
                require(candidate["applicability"] == applicability, "Incorrect applicability status")
                required = ("metadata_si" if cid.endswith("si_fee_income") else "metadata_offshore") if field in {
                    "employeeId", "productId"} else ("sql_si" if cid.endswith("si_fee_income") else "sql_offshore")
                require(required in candidate["evidence"], "Missing source-specific evidence")
    relations = model["relation_definitions"]
    require(isinstance(relations, list) and len(relations) == 2 * len(CONCEPTS), "Expected product and advisor relations for each fee concept")
    seen = set()
    for relation in relations:
        keys(relation, {"id", "name", "source_concept", "property_uri", "domain_uri", "range_uri",
                        "target_class_uri", "fields"}, "product relation")
        cid = relation["source_concept"]
        rid = relation["id"]
        require(isinstance(cid, str) and cid in CONCEPTS and isinstance(rid, str) and rid not in seen,
                "Unknown/duplicate relation")
        seen.add(rid)
        expected = {
            cid + ".product": (FH + "feeIncomeFromProduct", FH + "FeeIncome", FH + "FinancialProduct",
                               BANK + PRODUCT_CLASSES[cid][0]),
            cid + ".advisor": (BANK + "attributedToAdvisor", BANK + "BankFeeIncome",
                               BANK + "FinancialAdvisor", BANK + "FinancialAdvisor"),
        }
        require(rid in expected and tuple(relation[k] for k in (
            "property_uri", "domain_uri", "range_uri", "target_class_uri")) == expected[rid]
            and relation["fields"] == [], "Incorrect product/advisor relation semantics")
    require(seen == {cid + suffix for cid in CONCEPTS for suffix in (".product", ".advisor")},
            "Incomplete product/advisor relation coverage")


def load_model(path=None):
    model = json.loads((HERE / "product-fees.json" if path is None else Path(path)).read_text(encoding="utf-8"))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    normalized = copy.deepcopy(model)
    for evidence in normalized["evidence"].values():
        if "rows" in evidence:
            evidence["rows"].sort()
    for concept in normalized["concepts"]:
        concept["observations"]["evidence"].sort()
        for mapping in concept["fields"]:
            for candidate in mapping["candidates"]:
                candidate["evidence"].sort()
            mapping["candidates"].sort(key=canonical_json)
    graph = common.project_graph(normalized, "department-pg.product-fees")
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {e["id"]: e for e in graph["relationships"]}
    nodes["department-pg.product-fees"]["properties"]["evidence_json"] = canonical_json(normalized["evidence"])
    for source in normalized["sources"]:
        sid = "source:" + source["table"]
        nodes[sid] = {"id": sid, "label": "SourceTable", "properties": {
            "scope": "metadata_only", "table": source["table"], "status": source["status"],
            "database_verified_json": "false", "evidence_json": canonical_json(sorted(source["evidence"]))}}
    for concept in normalized["concepts"]:
        cid = concept["id"]
        nodes[cid]["properties"].update(observations_json=canonical_json(concept["observations"]),
                                       private_product_code=concept["private_product_code"])
        if cid in ADDED_CONCEPTS:
            nodes[cid]["properties"]["product_class_uris_json"] = canonical_json(sorted(concept["product_class_uris"]))
        for uri in concept["product_class_uris"]:
            nodes[uri] = {"id": uri, "label": "OntologyClassReference", "properties": {"scope": "metadata_only", "uri": uri}}
            source, target = cid + ".product", uri
            eid = source + "|HAS_TARGET_CLASS|" + target
            edges[eid] = {"id": eid, "type": "HAS_TARGET_CLASS", "source": source, "target": target}
        for mapping in concept["fields"]:
            for table in sorted({candidate["table"] for candidate in mapping["candidates"]}):
                source, target = cid + "." + mapping["field"], "source:" + table
                eid = source + "|CANDIDATE_SOURCE|" + target
                edges[eid] = {"id": eid, "type": "CANDIDATE_SOURCE", "source": source, "target": target}
    graph["nodes"] = sorted(nodes.values(), key=lambda n: n["id"])
    graph["relationships"] = sorted(edges.values(), key=lambda n: n["id"])
    return graph
