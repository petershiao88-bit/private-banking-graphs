"""Deposit field-definition contracts, evidence safety and combined graph tests."""

import copy
import importlib
import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("department_pg_extended_builder", HERE / "build_cypher.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
deposits = builder.deposits


class DepositTests(unittest.TestCase):
    def setUp(self):
        self.model = deposits.load_model()
        self.graph = builder.build_combined_graph(deposit_model=self.model)
        self.concepts = {item["id"]: item for item in self.model["concepts"]}

    def test_four_and_five_field_contracts(self):
        expected = {"customerId", "currency", "balance", "snapshotDate"}
        self.assertEqual(len(self.concepts), 4)
        self.assertEqual(self.model["ontology_version"], "0.8.0")
        for concept_id, concept in self.concepts.items():
            fields = expected | ({"employeeId"} if concept_id == "bank.employee_deposit" else set())
            self.assertEqual({item["field"] for item in concept["fields"]}, fields)
            self.assertEqual(concept["subsidiary"], "bank")
            self.assertIsNone(concept["department_owner"])
        self.assertEqual(len(self.model["field_definitions"]), 5)
        for definition in self.model["field_definitions"].values():
            self.assertEqual(set(definition), {"name", "definition", "data_type_hint"})
            self.assertNotIn("value", definition)

    def test_combinations_only_in_pg_with_multiple_common_references(self):
        expected = {
            "bank.twd_deposit": {"DepositProduct", "TWDFinancialProduct"},
            "bank.foreign_currency_deposit": {"DepositProduct", "ForeignCurrencyFinancialProduct"},
            "bank.structured_deposit": {"DepositProduct", "StructuredFinancialProduct"},
            "bank.employee_deposit": {"DepositProduct"},
        }
        for concept_id, class_names in expected.items():
            targets = {deposits.BANK + name for name in class_names}
            self.assertEqual(set(self.concepts[concept_id]["class_uris"]), targets)
            self.assertEqual({edge["target"] for edge in self.graph["relationships"]
                              if edge["source"] == concept_id and edge["type"] == "REFERS_TO_CLASS"},
                             targets)
        pending = self.concepts["bank.employee_deposit"]["pending_semantic_reference"]
        self.assertEqual(pending["status"], "pending_depositor_identity_mapping")
        self.assertEqual(pending["class_uri"], deposits.BANK + "BankEmployee")
        for key in ("relation_uri", "source_table", "source_column", "join_rules"):
            self.assertIsNone(pending[key])

    def test_employee_is_depositor_not_advisor_or_preferential_scheme(self):
        concept = self.concepts["bank.employee_deposit"]
        self.assertIn("存款人本人", concept["definition"])
        self.assertIn("不將行員存款限縮為優惠方案",
                      self.model["observations"]["employee_source"]["note"])
        self.assertEqual(concept["source_candidates"], ["DSDEP.EMP_DEP_NT_ACCT_HS"])
        employee = next(item for item in concept["fields"] if item["field"] == "employeeId")
        self.assertEqual(employee["candidates"], [])
        self.assertIsNone(employee["table"])
        self.assertIsNone(employee["column"])
        self.assertIsNone(self.model["execution"]["join_rules"])
        distinction = self.model["observations"]["advisor_distinction"]
        self.assertEqual(distinction["rejected_source"], "AUM_TMP02.EMP_NO")
        self.assertEqual(distinction["status"], "excluded_mapping")
        tables = {item["table"] for item in self.model["sources"]}
        self.assertNotIn("AUM_TMP02", tables)
        self.assertNotIn("DSDEP.EMP_NT_ACCT_HS", tables)
        self.assertEqual(self.model["observations"]["employee_source"]["status"], "coverage_pending")

    def test_raw_balance_and_customer_columns(self):
        for concept in self.concepts.values():
            for mapping in concept["fields"]:
                if mapping["field"] not in {"customerId", "balance"}:
                    continue
                self.assertEqual(mapping["status"], "observed_raw_candidate")
                self.assertEqual({item["table"] for item in mapping["candidates"]},
                                 set(concept["source_candidates"]))
                for candidate in mapping["candidates"]:
                    expected = "CUST_ID" if mapping["field"] == "customerId" else (
                        "AVAIL_BAL" if ".DEP_FN_" in candidate["table"] else "BAL_AMT")
                    self.assertEqual(candidate["column"], expected)
                self.assertIsNone(mapping["table"])
                self.assertIsNone(mapping["column"])
        self.assertIsNone(self.model["execution"]["aggregation_rules"])
        self.assertIsNone(self.model["execution"]["row_grain"])

    def test_currency_and_snapshot_remain_pending(self):
        for concept in self.concepts.values():
            fields = {item["field"]: item for item in concept["fields"]}
            currency, date = fields["currency"], fields["snapshotDate"]
            self.assertEqual(currency["status"], "pending_currency")
            self.assertEqual(currency["candidates"], [])
            self.assertIsNone(currency["constant"])
            self.assertEqual(date["status"], "pending_time_semantics")
            self.assertIsNone(date["table"])
            self.assertIsNone(date["column"])
        self.assertIsNone(self.model["field_definitions"]["snapshotDate"]["data_type_hint"])
        structured = self.concepts["bank.structured_deposit"]
        date = next(item for item in structured["fields"] if item["field"] == "snapshotDate")
        by_table = {}
        for candidate in date["candidates"]:
            by_table.setdefault(candidate["table"], set()).add(candidate["column"])
        self.assertEqual(by_table["DSDEP.DEP_NT_ACCT"], {"DATA_DT"})
        for table in ("DSDEP.DEP_NT_ACCT_HS", "DSDEP.EMP_DEP_NT_ACCT_HS"):
            self.assertEqual(by_table[table], {"DATA_DT", "YYYYMM", "LST_MTN_DT"})
        for table in ("DSDEP.DEP_FN_ACCT", "DSDEP.DEP_FN_ACCT_HS"):
            self.assertEqual(by_table[table], {"LST_MTN_DT"})

    def test_classifications_are_evidence_not_execution(self):
        nt = {"2311", "2321", "2322", "2331", "2332", "2333", "2335", "2336"}
        for concept_id, concept in self.concepts.items():
            for classification in concept["classification_evidence"]:
                expected = {"2545"} if concept_id == "bank.structured_deposit" else (
                    {"2317", "2327"} if concept_id == "bank.foreign_currency_deposit" else (
                        nt | {"2545"} if concept_id == "bank.employee_deposit" else nt))
                self.assertEqual(set(classification["codes"]), expected)
                self.assertEqual(classification["status"], "evidence_only")
                self.assertEqual(classification["column"],
                                 "ACC_CD" if ".DEP_FN_" in classification["table"] else "ACT_CD")
        self.assertEqual(set(self.concepts["bank.structured_deposit"]["source_candidates"]),
                         {item["table"] for item in self.model["sources"]})
        self.assertTrue(all(value is None for value in self.model["execution"].values()))
        history = self.model["observations"]["historical_filter"]
        self.assertEqual((history["column"], history["operator"], history["value"]),
                         ("YYYYMM", ">=", "202506"))
        self.assertEqual(history["status"], "evidence_only_not_operational_default")

    def test_graph_counts_endpoints_and_preserved_contacts(self):
        expected = {
            "BusinessConcept": 17, "OntologyClassReference": 15, "OntologyPropertyReference": 8,
            "MappingSlot": 7, "MetadataModule": 4, "DataFieldDefinition": 76,
            "SourceTable": 10, "PendingSemanticReference": 1,
            "BusinessRelationDefinition": 14, "OntologyObjectPropertyReference": 4,
        }
        nodes = {item["id"]: item for item in self.graph["nodes"]}
        edges = self.graph["relationships"]
        self.assertEqual(Counter(item["label"] for item in nodes.values()), expected)
        self.assertEqual(len(nodes), 156)
        self.assertEqual(len(edges), 299)
        self.assertEqual(sum(edge["type"] == "REFERS_TO_CLASS" for edge in edges), 20)
        self.assertEqual(len({item["id"] for item in edges}), len(edges))
        endpoint_types = {**builder.RELATIONSHIPS, **deposits.RELATIONSHIPS,
                          **builder.advisory_income.RELATIONSHIPS}
        for edge in edges:
            self.assertIn(edge["source"], nodes)
            self.assertIn(edge["target"], nodes)
            self.assertEqual((nodes[edge["source"]]["label"], nodes[edge["target"]]["label"]),
                             endpoint_types[edge["type"]])
        contact_graph = builder.build_graph(builder.load_model())
        self.assertTrue(all(item in self.graph["nodes"] for item in contact_graph["nodes"]))
        self.assertTrue(all(item in edges for item in contact_graph["relationships"]))
        for item in nodes.values():
            self.assertEqual(item["properties"]["scope"], "metadata_only")
        self.assertEqual(sum(edge["type"] == "CANDIDATE_SOURCE" for edge in edges), 78)

    def test_graph_carries_all_evidence_and_unresolved_metadata(self):
        nodes = {item["id"]: item for item in self.graph["nodes"]}
        module = nodes["department-pg.deposits"]["properties"]
        self.assertEqual(json.loads(module["evidence_json"]), self.model["evidence"])
        self.assertEqual(json.loads(module["execution_json"]), self.model["execution"])
        for source in self.model["sources"]:
            properties = nodes["source:" + source["table"]]["properties"]
            self.assertIs(json.loads(properties["database_verified_json"]), False)
            self.assertEqual(properties["status"], "observed_in_files")
        for concept in self.concepts.values():
            for mapping in concept["fields"]:
                node = nodes[concept["id"] + "." + mapping["field"]]
                stored = json.loads(node["properties"]["mapping_json"])
                self.assertEqual(stored["field"], mapping["field"])
                self.assertIsNone(stored["table"])
                self.assertIsNone(stored["column"])
                expected = [{**item, "evidence": sorted(item["evidence"])}
                            for item in mapping["candidates"]]
                self.assertEqual(sorted(stored["candidates"], key=deposits.canonical_json),
                                 sorted(expected, key=deposits.canonical_json))

    def test_no_product_dataproperties_accounts_branches_or_instance_claims(self):
        graph = deposits.build_graph(self.model)
        self.assertNotIn("OntologyPropertyReference", {item["label"] for item in graph["nodes"]})
        for item in graph["nodes"]:
            if item["label"] == "DataFieldDefinition":
                for forbidden in ("uri", "property_uri", "domain_uri", "range_uri", "value"):
                    self.assertNotIn(forbidden, item["properties"])
        for item in graph["relationships"]:
            self.assertNotIn(item["type"], {"REFERS_TO_PROPERTY", "HAS_DOMAIN_REFERENCE", "IS_A"})
        output = builder.render_graph_cypher(graph)
        for forbidden in ("#TWDDepositProduct", "#ForeignCurrencyDepositProduct", "#StructuredDepositProduct",
                          "#Employee", "#customerId", "#currency", "#balance", "#snapshotDate",
                          "#employeeId", ":Account", ":Customer", ":Employee", "rdf:type",
                          "owl:sameAs", "owl:equivalentClass", "rdfs:subClassOf", "CALL ",
                          "LOAD CSV", "CREATE TABLE", "SELECT ", "branch", "digital"):
            self.assertNotIn(forbidden, output)
        self.assertIs(self.model["inference"], False)
        self.assertIs(self.model["instance_mapping"], False)

    def test_rejects_unapproved_sources_rules_and_field_claims(self):
        changes = []
        for key in self.model["execution"]:
            changed = copy.deepcopy(self.model)
            changed["execution"][key] = "not approved"
            changes.append(changed)
        for key, value in (("constant", "TWD"), ("table", "DSDEP.DEP_NT_ACCT"),
                           ("column", "CURRENCY"), ("property_uri", deposits.BANK + "currency")):
            changed = copy.deepcopy(self.model)
            changed["concepts"][0]["fields"][1][key] = value
            changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][-1]["fields"][-1]["candidates"] = [{
            "table": "AUM_TMP02", "column": "EMP_NO", "meaning": "not depositor",
            "evidence": ["sql_advisor"],
        }]
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][-1]["pending_semantic_reference"]["class_uri"] = deposits.BANK + "Employee"
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][0]["class_uris"] = [deposits.BANK + "TWDDepositProduct"]
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["sources"][-1]["table"] = "DSDEP.EMP_NT_ACCT_HS"
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][0]["fields"][0]["candidates"][0]["evidence"] = []
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["sources"][0]["database_verified"] = True
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][0]["fields"].pop()
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][0]["fields"].append(changed["concepts"][0]["fields"][0])
        changes.append(changed)
        for key, value in (("records", []), ("inference", True), ("instance_mapping", True)):
            changed = copy.deepcopy(self.model)
            changed[key] = value
            changes.append(changed)
        for index, changed in enumerate(changes):
            with self.subTest(change=index), self.assertRaises(ValueError):
                builder.render_combined_cypher(deposit_model=changed)

    def test_combined_output_deterministic_with_reordered_modules(self):
        contacts = builder.load_model()
        contacts["concepts"].reverse()
        for concept in contacts["concepts"]:
            concept["mappings"].reverse()
        reordered = copy.deepcopy(self.model)
        reordered["concepts"].reverse()
        reordered["sources"].reverse()
        for source in reordered["sources"]:
            source["evidence"].reverse()
        for item in reordered["evidence"].values():
            if "rows" in item:
                item["rows"].reverse()
        for item in reordered["observations"].values():
            item["evidence"].reverse()
        for concept in reordered["concepts"]:
            concept["class_uris"].reverse()
            concept["fields"].reverse()
            concept["source_candidates"].reverse()
            concept["classification_evidence"].reverse()
            for item in concept["classification_evidence"]:
                item["codes"].reverse()
                item["evidence"].reverse()
            for mapping in concept["fields"]:
                mapping["candidates"].reverse()
                for candidate in mapping["candidates"]:
                    candidate["evidence"].reverse()
        output = builder.render_combined_cypher()
        self.assertEqual(output, builder.render_combined_cypher(contacts, reordered))
        self.assertEqual(output.encode("utf-8"), (HERE / "model.cypher").read_bytes())
        self.assertEqual(output.count("MERGE (n:MetadataNode:"), 156)
        self.assertEqual(output.count("MERGE (s)-[r:"), 299)
        self.assertIn("REQUIRE n.id IS UNIQUE", output)

    def test_historical_draft_is_superseded(self):
        draft = json.loads((HERE / "drafts" / "employee-deposit.json").read_text(encoding="utf-8"))
        self.assertEqual(draft["status"], "superseded_not_build_input")
        self.assertEqual(draft["activeSource"], "department-pg/deposits.json")
        self.assertIn("存款人本人", draft["concept"]["definition"])
        self.assertNotIn("行員存款指行員持有的存款，或適用員工方案的存款？", draft["openQuestions"])
        product = next(item for item in draft["relatedConcepts"] if item["name"] == "存款商品")
        self.assertEqual(product["rdfClassUri"], deposits.BANK + "DepositProduct")

    def test_all_uri_references_are_full_absolute_uris(self):
        for node in self.graph["nodes"]:
            for key in ("uri", "range_uri"):
                if key in node["properties"]:
                    uri = urlsplit(node["properties"][key])
                    self.assertIn(uri.scheme, {"http", "https"})
                    self.assertTrue(uri.netloc)
                    self.assertTrue(uri.fragment)

    def test_optional_all_rdf_references_resolve_in_local_ontologies(self):
        try:
            rdf = importlib.import_module("rdflib")
            ns = importlib.import_module("rdflib.namespace")
        except ImportError:
            self.skipTest("Optional rdflib is not installed")
        files = [HERE.parent / name for name in ("holding-core.ttl", "bank-deposit.ttl", "bank-common.ttl", "bank-investment-products.ttl")]
        if not all(path.is_file() for path in files):
            self.skipTest("Parent bank-deposit.ttl / v0.8.0 ontology is not yet available")
        graph = rdf.Graph()
        for path in files:
            graph.parse(path, format="turtle")
        for node in self.graph["nodes"]:
            if node["label"] in {"OntologyClassReference", "OntologyPropertyReference"}:
                target = rdf.URIRef(node["properties"]["uri"])
                expected = ns.OWL.Class if node["label"] == "OntologyClassReference" else ns.OWL.DatatypeProperty
                self.assertIn((target, ns.RDF.type, expected), graph)
        for class_name in ("DepositProduct", "TWDFinancialProduct", "ForeignCurrencyFinancialProduct",
                           "StructuredFinancialProduct"):
            self.assertIn((rdf.URIRef(deposits.BANK + class_name), ns.RDFS.subClassOf,
                           rdf.URIRef(builder.FH + "FinancialProduct")), graph)
        for class_name in ("TWDDepositProduct", "ForeignCurrencyDepositProduct", "StructuredDepositProduct"):
            target = rdf.URIRef(deposits.BANK + class_name)
            self.assertFalse(list(graph.triples((target, None, None))))
            self.assertFalse(list(graph.triples((None, None, target))))
        self.assertNotIn((rdf.URIRef(deposits.BANK + "Employee"), ns.RDF.type, ns.OWL.Class), graph)

    def test_read_only_sql_evidence_ranges_match_columns_and_sources(self):
        root = HERE.parents[2]
        for source in self.model["sources"]:
            sql_ref = deposits.SOURCES[source["table"]][2]
            evidence = self.model["evidence"][sql_ref]
            path = root.joinpath(*Path(evidence["file"]).parts[1:])
            if not path.is_file():
                self.skipTest("Read-only SQL evidence is not present in this checkout")
            # Match ASCII identifiers without assuming the legacy SQL comment encoding.
            lines = path.read_bytes().split(b"\n")
            start, end = evidence["lines"]
            text = b"\n".join(lines[start - 1:end]).upper()
            identifiers = (source["table"], "CUST_ID", deposits.SOURCES[source["table"]][0],
                           deposits.SOURCES[source["table"]][1], deposits.SOURCES[source["table"]][3][0])
            for identifier in identifiers:
                self.assertIn(identifier.encode("ascii"), text)

    def test_read_only_workbook_date_and_naming_evidence(self):
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        relationship_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        root = HERE.parents[2]
        for evidence_id, snapshot_row in (("income_nt", 78), ("income_employee", 77),
                                          ("aum_employee_naming", 77)):
            evidence = self.model["evidence"][evidence_id]
            path = root.joinpath(*Path(evidence["file"]).parts[1:])
            if not path.is_file():
                self.skipTest("Read-only workbook evidence is not present in this checkout")
            with zipfile.ZipFile(path) as archive:
                strings = []
                if "xl/sharedStrings.xml" in archive.namelist():
                    strings = ["".join(item.itertext()) for item in ET.fromstring(
                        archive.read("xl/sharedStrings.xml")).findall("m:si", ns)]
                rels = {item.attrib["Id"]: item.attrib["Target"] for item in ET.fromstring(
                    archive.read("xl/_rels/workbook.xml.rels"))}
                sheets = ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", ns)
                sheet = next(item for item in sheets if item.attrib["name"] == evidence["sheet"])
                target = rels[sheet.attrib["{" + relationship_ns + "}id"]]
                member = target.lstrip("/") if target.startswith("/") else "xl/" + target
                rows = {}
                for row in ET.fromstring(archive.read(member)).findall("m:sheetData/m:row", ns):
                    cells = []
                    for cell in row.findall("m:c", ns):
                        value = cell.findtext("m:v", default="", namespaces=ns)
                        if cell.attrib.get("t") == "s":
                            value = strings[int(value)]
                        elif cell.attrib.get("t") == "inlineStr":
                            inline = cell.find("m:is", ns)
                            value = "" if inline is None else "".join(inline.itertext())
                        cells.append(value)
                    rows[int(row.attrib["r"])] = cells
                self.assertIn("DATA_DT", rows[22])
                self.assertIn("資料日期", rows[22])
                self.assertIn("LST_MTN_DT", rows[39])
                self.assertEqual(rows[39][4], "")
                self.assertIn("YYYYMM", rows[snapshot_row])
                self.assertIn("Snapshot 年月", rows[snapshot_row])
                self.assertIn("BAL_AMT", rows[12])
                self.assertIn("CUST_ID", rows[20])


if __name__ == "__main__":
    unittest.main()
