"""Run with python -m unittest discover -s department-pg from the parent directory."""

import copy
import importlib
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("department_pg_builder", HERE / "build_cypher.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.model = builder.load_model()
        self.graph = builder.build_graph(self.model)

    def test_exact_business_concepts_and_semantic_targets(self):
        expected = {
            "bank.loan_verification_mobile": (
                "貸款照會手機", "MobileContactInformation", {"mobileNumber"}
            ),
            "bank.customer_visit_address": (
                "客戶訪問地址", "AddressContactInformation",
                {"countryCode", "city", "district", "addressLine", "postalCode", "fullAddress"},
            ),
        }
        self.assertEqual({item["id"] for item in self.model["concepts"]}, set(expected))
        for concept in self.model["concepts"]:
            name, class_name, fields = expected[concept["id"]]
            self.assertEqual(concept["name"], name)
            self.assertEqual(concept["subsidiary"], "bank")
            self.assertIsNone(concept["department_owner"])
            self.assertEqual(concept["class_uri"], builder.FH + class_name)
            self.assertEqual({item["property_uri"] for item in concept["mappings"]},
                             {builder.FH + field for field in fields})
            for mapping in concept["mappings"]:
                self.assertEqual(mapping["domain_uri"], concept["class_uri"])
                self.assertEqual(mapping["range_uri"], builder.XSD_STRING)

    def test_graph_endpoints_and_stable_unique_ids(self):
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        edges = self.graph["relationships"]
        self.assertEqual(len(nodes), 18)
        self.assertEqual(len(nodes), len(self.graph["nodes"]))
        self.assertEqual(len(edges), 23)
        self.assertEqual(len({edge["id"] for edge in edges}), len(edges))
        for edge in edges:
            self.assertIn(edge["source"], nodes)
            self.assertIn(edge["target"], nodes)
            self.assertEqual((nodes[edge["source"]]["label"], nodes[edge["target"]]["label"]),
                             builder.RELATIONSHIPS[edge["type"]])
            self.assertEqual(edge["id"], "|".join((edge["source"], edge["type"], edge["target"])))
        for node in nodes.values():
            if node["label"].startswith("Ontology"):
                self.assertEqual(node["id"], node["properties"]["uri"])
                self.assertTrue(node["id"].startswith(builder.FH))

    def test_pending_sources_are_slots_not_tables_or_data(self):
        self.assertEqual({node["label"] for node in self.graph["nodes"]}, builder.LABELS)
        slots = [node for node in self.graph["nodes"] if node["label"] == "MappingSlot"]
        self.assertEqual(len(slots), 7)
        for slot in slots:
            source = json.loads(slot["properties"]["source_json"])
            self.assertEqual(slot["properties"]["status"], "pending")
            self.assertEqual(source, {
                "status": "pending", "table": None, "field": None, "sql": None,
                "join_rules": None, "filter_rules": None,
            })
        for node in self.graph["nodes"]:
            if node["label"] == "BusinessConcept":
                self.assertIsNone(json.loads(node["properties"]["department_owner_json"]))

    def test_no_instance_or_inference_claims(self):
        self.assertEqual(self.model["scope"], "metadata_only")
        self.assertIs(self.model["inference"], False)
        self.assertIs(self.model["instance_mapping"], False)
        for node in self.graph["nodes"]:
            self.assertEqual(node["properties"]["scope"], "metadata_only")
        self.assertEqual({edge["type"] for edge in self.graph["relationships"]},
                         set(builder.RELATIONSHIPS))
        output = builder.render_cypher(self.model)
        for forbidden in (":Customer", ":SourceTable", ":SourceField", "rdf:type", "owl:sameAs",
                          "owl:equivalentClass", "rdfs:subClassOf", "CALL ", "LOAD CSV"):
            self.assertNotIn(forbidden, output)

    def test_rejects_physical_sources_and_executable_sql(self):
        for key, value in {
            "status": "resolved", "table": "unapproved_table", "field": "unapproved_field",
            "sql": "SELECT 1", "join_rules": [], "filter_rules": {},
        }.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(self.model)
                changed["concepts"][0]["mappings"][0]["source"][key] = value
                with self.assertRaises(ValueError):
                    builder.render_cypher(changed)

    def test_rejects_wrong_domains_ranges_properties_and_ids(self):
        for key, value in {
            "id": "random-instance-id", "domain_uri": builder.FH + "ContactInformation",
            "range_uri": "http://www.w3.org/2001/XMLSchema#integer",
            "property_uri": builder.FH + "city",
        }.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(self.model)
                changed["concepts"][0]["mappings"][0][key] = value
                with self.assertRaises(ValueError):
                    builder.validate_model(changed)

    def test_rejects_duplicates_missing_fields_and_instance_extensions(self):
        changes = []
        duplicate = copy.deepcopy(self.model)
        duplicate["concepts"][1] = duplicate["concepts"][0]
        changes.append(duplicate)
        duplicate_field = copy.deepcopy(self.model)
        duplicate_field["concepts"][1]["mappings"][1] = duplicate_field["concepts"][1]["mappings"][0]
        changes.append(duplicate_field)
        missing_field = copy.deepcopy(self.model)
        missing_field["concepts"][1]["mappings"].pop()
        changes.append(missing_field)
        instances = copy.deepcopy(self.model)
        instances["records"] = [{"customer": "not-allowed"}]
        changes.append(instances)
        inferred = copy.deepcopy(self.model)
        inferred["inference"] = True
        changes.append(inferred)
        typed = copy.deepcopy(self.model)
        typed["instance_mapping"] = True
        changes.append(typed)
        for index, changed in enumerate(changes):
            with self.subTest(change=index), self.assertRaises(ValueError):
                builder.validate_model(changed)

    def test_schema_documents_pending_only_metadata(self):
        schema = json.loads((HERE / "model.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(self.model))
        for key in ("schema_version", "ontology_version", "scope", "inference", "instance_mapping"):
            self.assertEqual(schema["properties"][key]["const"], self.model[key])
        source_schema = schema["$defs"]["mapping"]["properties"]["source"]
        self.assertFalse(source_schema["additionalProperties"])
        self.assertEqual(set(source_schema["required"]), builder.SOURCE_KEYS)
        self.assertEqual(source_schema["properties"]["status"], {"const": "pending"})
        for key in builder.SOURCE_KEYS - {"status"}:
            self.assertEqual(source_schema["properties"][key], {"type": "null"})

    def test_deterministic_even_when_input_arrays_are_reordered(self):
        reordered = copy.deepcopy(self.model)
        reordered["concepts"].reverse()
        for concept in reordered["concepts"]:
            concept["mappings"].reverse()
        self.assertEqual(builder.build_graph(self.model), builder.build_graph(reordered))
        self.assertEqual(builder.render_cypher(self.model), builder.render_cypher(reordered))
        self.assertEqual(builder.render_cypher(self.model), builder.render_cypher(self.model))

    def test_checked_in_cypher_matches_builder_byte_for_byte(self):
        self.assertEqual((HERE / "model.cypher").read_bytes(),
                         builder.render_combined_cypher(self.model).encode("utf-8"))

    def test_cypher_fixed_labels_constraint_and_stable_merges(self):
        output = builder.render_cypher(self.model)
        self.assertIn("CREATE CONSTRAINT department_pg_metadata_id IF NOT EXISTS", output)
        self.assertIn("FOR (n:MetadataNode) REQUIRE n.id IS UNIQUE;", output)
        self.assertEqual(output.count("MERGE (n:MetadataNode:"), 18)
        self.assertEqual(output.count("MERGE (s)-[r:"), 23)
        for node in self.graph["nodes"]:
            self.assertIn("MERGE (n:MetadataNode:" + node["label"]
                          + " {id: " + builder.cypher_string(node["id"]) + "})", output)
        self.assertNotIn("CREATE (", output)
        self.assertNotIn("DELETE ", output)

    def test_string_and_nested_json_escaping(self):
        text = '引號 "、單引號 \'、反斜線 \\、換行\n、tab\t、控制\x01、emoji 😀'
        literal = builder.cypher_string(text)
        self.assertEqual(json.loads(literal), text)
        self.assertNotIn("\n", literal)
        self.assertIn('\\"', literal)
        self.assertIn("\\\\", literal)
        nested = builder.canonical_json({"text": text, "missing": None})
        properties = builder.cypher_properties({"source_json": nested})
        embedded_literal = properties[len("{source_json: "):-1]
        self.assertEqual(json.loads(json.loads(embedded_literal)), {"text": text, "missing": None})
        with self.assertRaises(ValueError):
            builder.cypher_properties({"unsafe`key": "value"})

    def test_optional_current_core_rdf_contract(self):
        try:
            rdflib = importlib.import_module("rdflib")
            namespace = importlib.import_module("rdflib.namespace")
        except ImportError:
            self.skipTest("Optional rdflib is not installed; stdlib contract tests still run")
        Graph, URIRef = rdflib.Graph, rdflib.URIRef
        OWL, RDF, RDFS = namespace.OWL, namespace.RDF, namespace.RDFS
        core = HERE.parent / "holding-core.ttl"
        if not core.is_file():
            self.skipTest("Parent holding-core.ttl is not available")
        graph = Graph().parse(core, format="turtle")
        ontology = URIRef("https://example.org/ontology/holding")
        versions = [str(value) for predicate in (OWL.versionIRI, OWL.versionInfo)
                    for value in graph.objects(ontology, predicate)]
        if not any(value.endswith(("/0.3.0", "/0.4.0", "/0.5.0", "/0.6.0", "/0.7.0", "/0.8.0"))
                   or value.startswith(("0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0")) for value in versions):
            self.skipTest("Parent core is not a supported contact contract version")
        for concept in self.model["concepts"]:
            class_uri = URIRef(concept["class_uri"])
            self.assertIn((class_uri, RDF.type, OWL.Class), graph)
            for mapping in concept["mappings"]:
                prop = URIRef(mapping["property_uri"])
                self.assertIn((prop, RDF.type, OWL.DatatypeProperty), graph)
                self.assertEqual(set(graph.objects(prop, RDFS.domain)), {class_uri})
                self.assertEqual(set(graph.objects(prop, RDFS.range)), {URIRef(builder.XSD_STRING)})


if __name__ == "__main__":
    unittest.main()
