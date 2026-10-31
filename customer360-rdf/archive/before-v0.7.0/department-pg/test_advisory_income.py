"""Cross-layer reference, unresolved source and deterministic integration checks."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pg_income_test_builder", HERE / "build_cypher.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
income = builder.advisory_income


class AdvisoryIncomeTests(unittest.TestCase):
    def setUp(self):
        self.model = income.load_model()

    def test_references_resolve_and_inherited_domains_apply_without_pg_inference(self):
        rdf = Graph()
        config = json.loads((HERE.parent / "build-config.json").read_text(encoding="utf-8"))
        for source in config["sources"]:
            rdf.parse(HERE.parent / source, format="turtle")
        graph = builder.build_combined_graph(income_model=self.model)
        kinds = {"OntologyClassReference": OWL.Class,
                 "OntologyPropertyReference": OWL.DatatypeProperty,
                 "OntologyObjectPropertyReference": OWL.ObjectProperty}
        for node in graph["nodes"]:
            if node["label"] in kinds:
                props = node["properties"]
                target = URIRef(props["uri"])
                self.assertIn((target, RDF.type, kinds[node["label"]]), rdf)
                for key, predicate in (("domain_uri", RDFS.domain), ("range_uri", RDFS.range)):
                    if key in props:
                        self.assertEqual(set(rdf.objects(target, predicate)), {URIRef(props[key])})
        concepts = {c["id"]: c for c in self.model["concepts"]}
        for relation in self.model["relation_definitions"]:
            source = URIRef(concepts[relation["source_concept"]]["class_uri"])
            self.assertIn(URIRef(relation["domain_uri"]),
                          set(rdf.transitive_objects(source, RDFS.subClassOf)))
        self.assertFalse(self.model["inference"])
        self.assertFalse(self.model["instance_mapping"])
        self.assertNotIn("IS_A", {edge["type"] for edge in graph["relationships"]})

    def test_approved_semantics_do_not_resolve_sources_or_role_and_income_rules(self):
        self.assertEqual(self.model["access_policy_status"], "deferred_by_user")
        self.assertTrue(all(value is None for value in self.model["execution"].values()))
        definitions = self.model["field_definitions"]
        self.assertNotEqual(definitions["incomePeriod"]["definition"],
                            definitions["snapshotDate"]["definition"])
        self.assertNotIn("advisorId", definitions)
        graph = income.build_graph(self.model)
        for node in graph["nodes"]:
            if node["label"] == "DataFieldDefinition":
                mapping = json.loads(node["properties"]["mapping_json"])
                self.assertIsNone(mapping["table"])
                self.assertIsNone(mapping["column"])
                self.assertNotIn("value", node["properties"])
        combined = builder.build_combined_graph()
        # Adding roles and income must not invent source tables or customer instances.
        observed_sources = {s["table"] for module in (builder.deposits.load_model(), builder.product_fees.load_model())
                            for s in module["sources"]}
        self.assertEqual({n["properties"]["table"] for n in combined["nodes"] if n["label"] == "SourceTable"},
                         observed_sources)
        self.assertTrue(all(n["properties"]["scope"] == "metadata_only" for n in combined["nodes"]))
        for concept in self.model["concepts"]:
            self.assertIsNone(concept["specific_product_class_uri"])

    def test_rejects_premature_mappings_permissions_and_wrong_semantics(self):
        changes = []
        for key in self.model["execution"]:
            changed = copy.deepcopy(self.model)
            changed["execution"][key] = "unapproved"
            changes.append(changed)
        for key, value in (("table", "invented_table"), ("column", "invented_column"),
                           ("status", "resolved")):
            changed = copy.deepcopy(self.model)
            changed["concepts"][0]["fields"][0][key] = value
            changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][0]["class_uri"] = income.BANK + "FinancialAdvisor"
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["relation_definitions"][0]["target_class_uri"] = income.BANK + "BankEmployee"
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["field_definitions"]["amount"]["property_uri"] = income.BANK + "productAmount"
        changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["access_policy_status"] = "all_advisors_allowed"
        changes.append(changed)
        for key, value in (("records", []), ("inference", True), ("instance_mapping", True)):
            changed = copy.deepcopy(self.model)
            changed[key] = value
            changes.append(changed)
        changed = copy.deepcopy(self.model)
        changed["concepts"][1]["fields"].append(changed["concepts"][1]["fields"][0])
        changes.append(changed)
        for index, changed in enumerate(changes):
            with self.subTest(change=index), self.assertRaises(ValueError):
                builder.render_combined_cypher(income_model=changed)

    def test_new_metadata_survives_projection_reordering_and_safe_rendering(self):
        graph = income.build_graph(self.model)
        nodes = {n["id"]: n for n in graph["nodes"]}
        for concept in self.model["concepts"]:
            self.assertEqual(nodes[concept["id"]]["properties"]["definition"], concept["definition"])
        for relation in self.model["relation_definitions"]:
            edges = {(e["source"], e["type"], e["target"]) for e in graph["relationships"]}
            self.assertIn((relation["id"], "REFERS_TO_OBJECT_PROPERTY", relation["property_uri"]), edges)
            self.assertIn((relation["id"], "HAS_TARGET_CLASS", relation["target_class_uri"]), edges)
        reordered = copy.deepcopy(self.model)
        for key in ("concepts", "relation_definitions"):
            reordered[key].reverse()
            for item in reordered[key]:
                item["fields"].reverse()
        output = builder.render_combined_cypher()
        self.assertEqual(output, builder.render_combined_cypher(income_model=reordered))
        self.assertEqual(output.encode("utf-8"), (HERE / "model.cypher").read_bytes())
        escaped = copy.deepcopy(self.model)
        text = '引號 " 與換行\n保留在定義中'
        escaped["concepts"][0]["definition"] = text
        rendered = builder.render_combined_cypher(income_model=escaped)
        self.assertIn(builder.cypher_string(text), rendered)


if __name__ == "__main__":
    unittest.main()
