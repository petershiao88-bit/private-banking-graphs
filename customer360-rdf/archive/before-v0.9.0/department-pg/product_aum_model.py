"""Bounded product AUM metadata contract; source observations are not executable rules."""

import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def local_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = local_module("aum_common_projection", "advisory_income_model.py")
deposits = local_module("aum_deposit_candidates", "deposit_model.py")
FH, BANK = common.FH, common.BANK
keys, require, canonical_json = common.keys, common.require, common.canonical_json
FIELDS = {key: common.FIELDS[key] for key in ("customerId", "productId", "amount", "currency", "snapshotDate")}
EXECUTION_KEYS = {"sql", "join_rules", "filter_rules", "aggregation_rules", "row_grain",
                  "valuation_rules", "deduplication_rules", "snapshot_selection", "currency_conversion"}
CONCEPTS = {
    "bank.twd_deposit_aum": ("台幣存款 AUM", ("DepositProduct", "TWDFinancialProduct"), "bank.twd_deposit"),
    "bank.foreign_currency_deposit_aum": ("外幣存款 AUM", ("DepositProduct", "ForeignCurrencyFinancialProduct"), "bank.foreign_currency_deposit"),
    "bank.structured_deposit_aum": ("結構型存款 AUM", ("DepositProduct", "StructuredFinancialProduct"), "bank.structured_deposit"),
    "bank.overseas_stock_aum": ("海外股票 AUM", ("StockProduct", "OverseasFinancialProduct"), None),
    "bank.overseas_bond_trust_aum": ("海外債券（信託）AUM", ("BondProduct", "OverseasFinancialProduct"), None),
    "bank.offshore_structured_aum": ("境外結構型商品 AUM", ("StructuredFinancialProduct", "OverseasFinancialProduct"), None),
    "bank.overseas_bond_proprietary_aum": ("海外債券（自營）AUM", ("BondProduct", "OverseasFinancialProduct"), None),
}
LABELS = common.LABELS | {"SourceTable"}
RELATIONSHIPS = {**common.RELATIONSHIPS, "CANDIDATE_SOURCE": ("DataFieldDefinition", "SourceTable")}
FUND = "DSFND.PB_FUND_MONTH"
BOND = "DSWTR.BOND_POS_DAY"


def normalized_evidence(item):
    return {**item, **({"rows": sorted(item["rows"])} if "rows" in item else {})}


def normalized_classifications(items):
    values = []
    for item in items:
        value = dict(item)
        for key in ("codes", "values", "evidence"):
            if key in value:
                value[key] = sorted(value[key])
        values.append(value)
    return sorted(values, key=canonical_json)


def expected_candidates(cid, field, deposit_model):
    basis = CONCEPTS[cid][2]
    if basis:
        if field not in {"customerId", "amount", "snapshotDate"}:
            return []
        source = next(c for c in deposit_model["concepts"] if c["id"] == basis)
        original = "balance" if field == "amount" else field
        return next(m["candidates"] for m in source["fields"] if m["field"] == original)
    proprietary = cid == "bank.overseas_bond_proprietary_aum"
    columns = {"customerId": ["CIF_ID"] if proprietary else ["IDNO"],
               "amount": ["STO_AMT", "MKT_PRI", "EXC_RATE"] if proprietary else ["CurrentTWDValue"],
               "snapshotDate": ["DATA_DT"] if proprietary else ["EXEDATE"]}.get(field, [])
    return [{"table": BOND if proprietary else FUND, "column": column} for column in columns]


def validate_model(model):
    keys(model, {"schema_version", "ontology_version", "status", "scope", "inference", "instance_mapping",
                 "access_policy_status", "field_definitions", "execution", "evidence", "sources", "concepts",
                 "relation_definitions"}, "product AUM module")
    require(model["schema_version"] == "1.0.0" and model["ontology_version"] == "0.8.0"
            and model["status"] == "active" and model["scope"] == "metadata_only"
            and model["inference"] is False and model["instance_mapping"] is False,
            "Expected active v0.8.0 AUM metadata without instances or inference")
    require(model["access_policy_status"] == "deferred_by_user", "Access design remains deferred")
    keys(model["execution"], EXECUTION_KEYS, "AUM execution")
    require(all(v is None for v in model["execution"].values()), "No AUM execution, valuation, sum or snapshot rules approved")
    keys(model["field_definitions"], FIELDS, "AUM field definitions")
    for field, semantics in FIELDS.items():
        definition = model["field_definitions"][field]
        keys(definition, {"name", "definition", "data_type_hint", "property_uri", "entity_class_uri"}, "field definition")
        require(tuple(definition[k] for k in ("data_type_hint", "property_uri", "entity_class_uri")) == semantics,
                "Incorrect AUM field semantics")
        require(all(isinstance(definition[k], str) and definition[k].strip() for k in ("name", "definition")),
                "Missing AUM field definition")
    base = deposits.load_model()
    evidence = model["evidence"]
    extra = {"sql_bank_investment_aum": [211, 230], "sql_bank_bond_proprietary_aum": [232, 251]}
    keys(evidence, set(base["evidence"]) | set(extra), "AUM evidence catalog")
    for eid, item in base["evidence"].items():
        require(normalized_evidence(evidence[eid]) == normalized_evidence(item),
                "Reused deposit evidence must remain unchanged")
    for eid, lines in extra.items():
        require(evidence[eid] == {"file": "Ontology/私銀智能問答/sources/sql/1.AUM_DETAIL.sql",
                                 "lines": lines, "encoding": "cp950"}, "Incorrect AUM SQL evidence")

    def refs(values):
        require(isinstance(values, list) and bool(values) and all(isinstance(v, str) and v in evidence for v in values)
                and len(set(values)) == len(values), "Missing/duplicate/unknown AUM evidence")

    expected_sources = {s["table"]: s for s in base["sources"]}
    for table, eid in ((FUND, "sql_bank_investment_aum"), (BOND, "sql_bank_bond_proprietary_aum")):
        expected_sources[table] = {"table": table, "status": "observed_in_files", "database_verified": False, "evidence": [eid]}
    sources = model["sources"]
    require(isinstance(sources, list) and len(sources) == len(expected_sources), "Incorrect AUM source coverage")
    seen = set()
    for source in sources:
        keys(source, {"table", "status", "database_verified", "evidence"}, "AUM source")
        table = source["table"]
        require(table in expected_sources and table not in seen, "Unknown/duplicate AUM source")
        seen.add(table)
        expected = expected_sources[table]
        require(source["status"] == expected["status"] and source["database_verified"] is False
                and sorted(source["evidence"]) == sorted(expected["evidence"]), "Source is a file observation only")
    concepts = model["concepts"]
    require(isinstance(concepts, list) and len(concepts) == len(CONCEPTS), "Expected seven product AUM concepts")
    seen = set()
    for concept in concepts:
        keys(concept, {"id", "name", "definition", "subsidiary", "department_owner", "class_uri",
                       "specific_product_class_uri", "product_class_uris", "basis_concept", "fields", "observations"}, "AUM concept")
        cid = concept["id"]
        require(isinstance(cid, str) and cid in CONCEPTS and cid not in seen, "Unknown/duplicate AUM concept")
        seen.add(cid)
        name, products, basis = CONCEPTS[cid]
        require(concept["name"] == name and concept["class_uri"] == BANK + "BankAUM"
                and concept["subsidiary"] == "bank" and concept["department_owner"] is None
                and concept["basis_concept"] == basis and concept["specific_product_class_uri"] is None
                and isinstance(concept["product_class_uris"], list)
                and sorted(concept["product_class_uris"]) == sorted(BANK + p for p in products),
                "Incorrect AUM common references or product qualifiers")
        require(isinstance(concept["definition"], str) and bool(concept["definition"].strip()), "Missing AUM definition")
        observations = concept["observations"]
        require(isinstance(observations, dict) and all(k in observations for k in (
            "coverage", "classification_evidence", "valuation_observation", "date_observation", "gaps", "evidence")),
            "Incomplete AUM observations")
        refs(observations["evidence"])
        if basis:
            source = next(c for c in base["concepts"] if c["id"] == basis)
            expected_classifications = source["classification_evidence"]
        elif cid.endswith("proprietary_aum"):
            expected_classifications = []
        else:
            values, label = {
                "bank.overseas_stock_aum": (["其他-國外有價證券", "其他-國外股票", "股票"], "海外股票"),
                "bank.overseas_bond_trust_aum": (["海外債券"], "海外債券(信託)"),
                "bank.offshore_structured_aum": (["結構型商品"], "境外結構型商品"),
            }[cid]
            expected_classifications = [{"table": FUND, "column": "TRUSTPRD", "values": values,
                                        "mapped_label": label, "status": "evidence_only",
                                        "evidence": ["sql_bank_investment_aum"]}]
        require(isinstance(observations["classification_evidence"], list)
                and normalized_classifications(observations["classification_evidence"])
                == normalized_classifications(expected_classifications), "Incorrect observed AUM product classification")
        fields = concept["fields"]
        require(isinstance(fields, list) and len(fields) == len(FIELDS), "Expected five AUM fields")
        seen_fields = set()
        for mapping in fields:
            keys(mapping, {"field", "status", "table", "column", "candidates"}, "AUM field")
            field = mapping["field"]
            require(isinstance(field, str) and field in FIELDS and field not in seen_fields, "Unknown/duplicate AUM field")
            seen_fields.add(field)
            status = {"amount": "pending_aum_recognition", "customerId": "observed_raw_candidate",
                      "currency": "pending_currency", "snapshotDate": "pending_time_semantics",
                      "productId": "pending_product_identity"}[field]
            require(mapping["status"] == status and mapping["table"] is None and mapping["column"] is None,
                    "AUM mappings remain candidates, not approved physical mappings")
            expected = expected_candidates(cid, field, base)
            candidates = mapping["candidates"]
            require(isinstance(candidates, list) and len(candidates) == len(expected), "Incorrect AUM candidate coverage")
            pairs = {(c["table"], c["column"]) for c in expected}
            actual = set()
            for candidate in candidates:
                keys(candidate, {"table", "column", "meaning", "evidence"}, "AUM candidate")
                pair = (candidate["table"], candidate["column"])
                require(pair in pairs and pair not in actual and isinstance(candidate["meaning"], str)
                        and candidate["meaning"].strip(), "Unknown/duplicate AUM input or missing meaning")
                actual.add(pair)
                refs(candidate["evidence"])
                required = (next(c["evidence"] for c in expected if (c["table"], c["column"]) == pair) if basis else
                            ["sql_bank_bond_proprietary_aum" if cid.endswith("proprietary_aum") else "sql_bank_investment_aum"])
                require(set(required) <= set(candidate["evidence"]), "Missing source-specific AUM evidence")
    relations = model["relation_definitions"]
    require(isinstance(relations, list) and len(relations) == len(CONCEPTS), "Incorrect AUM relation coverage")
    seen = set()
    for relation in relations:
        keys(relation, {"id", "name", "source_concept", "property_uri", "domain_uri", "target_class_uri", "fields"}, "AUM relation")
        cid = relation["source_concept"]
        require(isinstance(cid, str) and cid in CONCEPTS and cid not in seen and relation["id"] == cid + ".product"
                and relation["property_uri"] == FH + "measuresProduct" and relation["domain_uri"] == FH + "AUM"
                and relation["target_class_uri"] == FH + "FinancialProduct" and relation["fields"] == [],
                "AUM alone uses the AUM measurement relation")
        seen.add(cid)


def load_model(path=None):
    model = json.loads((HERE / "product-aum.json" if path is None else Path(path)).read_text(encoding="utf-8"))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    normalized = copy.deepcopy(model)
    for concept in normalized["concepts"]:
        concept["observations"]["evidence"].sort()
        concept["observations"]["classification_evidence"] = normalized_classifications(
            concept["observations"]["classification_evidence"])
        for mapping in concept["fields"]:
            for candidate in mapping["candidates"]:
                candidate["evidence"].sort()
            mapping["candidates"].sort(key=canonical_json)
    graph = common.project_graph(normalized, "department-pg.product-aum")
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {e["id"]: e for e in graph["relationships"]}
    evidence = copy.deepcopy(normalized["evidence"])
    for item in evidence.values():
        if "rows" in item:
            item["rows"].sort()
    nodes["department-pg.product-aum"]["properties"]["evidence_json"] = canonical_json(evidence)
    for source in normalized["sources"]:
        sid = "source:" + source["table"]
        nodes[sid] = {"id": sid, "label": "SourceTable", "properties": {
            "scope": "metadata_only", "table": source["table"], "status": source["status"],
            "database_verified_json": "false", "evidence_json": canonical_json(sorted(source["evidence"]))}}

    def edge(source, kind, target):
        eid = source + "|" + kind + "|" + target
        edges[eid] = {"id": eid, "type": kind, "source": source, "target": target}

    for concept in normalized["concepts"]:
        cid = concept["id"]
        nodes[cid]["properties"].update(observations_json=canonical_json(concept["observations"]),
            product_class_uris_json=canonical_json(sorted(concept["product_class_uris"])),
            basis_concept_json=canonical_json(concept["basis_concept"]))
        for uri in concept["product_class_uris"]:
            nodes[uri] = {"id": uri, "label": "OntologyClassReference", "properties": {"scope": "metadata_only", "uri": uri}}
            edge(cid + ".product", "HAS_TARGET_CLASS", uri)
        for mapping in concept["fields"]:
            for table in {c["table"] for c in mapping["candidates"]}:
                edge(cid + "." + mapping["field"], "CANDIDATE_SOURCE", "source:" + table)
    return {"nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "relationships": sorted(edges.values(), key=lambda e: e["id"])}
