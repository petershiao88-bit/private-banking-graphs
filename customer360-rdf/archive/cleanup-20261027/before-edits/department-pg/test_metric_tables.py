"""Table-level metric lineage, source evidence, scope and field preservation."""
import copy
import importlib.util
import json
import re
import unittest
from collections import Counter
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from review_contract_v015 import normalize_reviewed_text
from review_contract_pg_income import historical_income_model

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BEFORE = ROOT / "archive/before-v0.13.0"
SPEC = importlib.util.spec_from_file_location("table_metric_builder", HERE / "build_cypher.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class MetricTableTests(unittest.TestCase):
    def modules(self):
        return (builder.advisory_income, builder.product_fees, builder.product_aum, builder.investment_metrics, builder.bank_business)

    def test_table_edges_start_at_metrics_and_keep_primary_and_support_separate(self):
        graph = builder.build_combined_graph()
        nodes = {n["id"]: n for n in graph["nodes"]}
        edges = {(e["source"], e["type"], e["target"]) for e in graph["relationships"]}
        rdf = Graph().parse(ROOT / "customer360-ontology.ttl", format="turtle")
        fh = Namespace(builder.FH)
        count = Counter()
        expected_edges = set()
        for module in self.modules():
            model = module.load_model()
            for concept in model["concepts"]:
                mapping = concept.get("table_sources")
                if mapping is None:
                    self.assertEqual(concept["id"], "bank.financial_advisor")
                    continue
                ancestors = set(rdf.transitive_objects(URIRef(concept["class_uri"]), RDFS.subClassOf))
                self.assertIn(fh.Metric, ancestors)
                self.assertNotIn(fh.FinancialProduct, ancestors)
                count["aum" if fh.AUM in ancestors else "fee" if fh.FeeIncome in ancestors else "lum" if fh.LUM in ancestors else "interest"] += 1
                self.assertEqual(json.loads(nodes[concept["id"]]["properties"]["table_sources_json"]),
                                 builder.advisory_income.normalized_table_sources(mapping))
                for row in mapping["tables"]:
                    target = "source:" + row["table"]
                    self.assertEqual(nodes[target]["label"], "SourceTable")
                    expected_edges.add((concept["id"], builder.advisory_income.TABLE_ROLES[row["role"]], target))
        self.assertEqual(count, {"aum": 18, "fee": 21, "lum": 1, "interest": 2})
        actual = {edge for edge in edges if edge[1] in builder.advisory_income.TABLE_ROLES.values()}
        self.assertEqual(actual, expected_edges)
        self.assertEqual(Counter(edge[1] for edge in actual),
                         {"HAS_SOURCE_TABLE": 88, "USES_VALUATION_SOURCE": 3, "USES_DATE_LOOKUP_SOURCE": 2})

    def test_every_table_mapping_is_supported_by_original_sql_or_table_metadata(self):
        for module in self.modules():
            model = module.load_model()
            for concept in model["concepts"]:
                mapping = concept.get("table_sources")
                if mapping is None:
                    continue
                for row in mapping["tables"]:
                    supported = False
                    for eid in row["evidence"]:
                        record = model["evidence"][eid]
                        path = ROOT.parents[1].joinpath(*Path(record["file"]).parts[1:])
                        self.assertTrue(path.is_file())
                        if "lines" in record:
                            lines = path.read_text(encoding=record.get("encoding", "cp950")).splitlines()
                            start, end = record["lines"]
                            text = "\n".join(lines[start-1:end]).upper()
                            supported |= re.search(r"\b" + re.escape(row["table"].upper()) + r"\b", text) is not None
                        else:
                            supported |= record.get("sheet") == row["table"]
                    self.assertTrue(supported, (concept["id"], row))
                amount = next(f for f in concept["fields"] if f["field"] == "amount")
                for candidate in amount.get("candidates", []):
                    row = next(row for row in mapping["tables"] if row["table"] == candidate["table"])
                    self.assertTrue(set(candidate["evidence"]) <= set(row["evidence"]),
                                    "Retain metric-specific evidence as well as shared table catalogs")

    def test_partial_generic_fee_and_source_anomalies_are_not_promoted_to_full_primary_sources(self):
        generic = builder.advisory_income.load_model()["concepts"][1]["table_sources"]
        self.assertEqual(generic["status"], "partial_scope")
        model = builder.investment_metrics.load_model()
        concepts = {c["id"]: c for c in model["concepts"]}
        for cid, lookup in (("securities.fund_fee_income", "DSPBM.PB_BONDTRADM_SEC"),
                            ("securities.foreign_stock_fee_income", "DSPBM.PB_STOCKTRADM_AM_SEC")):
            mapping = concepts[cid]["table_sources"]
            self.assertIn({"table": lookup, "role": "date_lookup_only"},
                          [{k: row[k] for k in ("table", "role")} for row in mapping["tables"]])
            self.assertEqual(mapping["unresolved_supporting_relations"][0]["name"], "T_LAST_TWO_WORKDAYS")
        for c in concepts.values():
            self.assertNotIn("T_LAST_TWO_WORKDAYS", {row["table"] for row in c["table_sources"]["tables"]})

    def test_existing_field_mappings_and_rdf_semantics_survive_collective_management_extension(self):
        for name in ("model.json", "deposits.json", "advisory-income.json", "product-fees.json",
                     "product-aum.json", "investment-metrics.json"):
            before = json.loads((BEFORE / "department-pg" / name).read_text(encoding="utf-8"))
            after = json.loads((HERE / name).read_text(encoding="utf-8"))
            after = historical_income_model(after)
            after["ontology_version"] = before["ontology_version"]
            old_concepts = {c["id"]: c for c in before["concepts"]}
            after["concepts"] = [c for c in after["concepts"] if c["id"] in old_concepts]
            for concept in after["concepts"]:
                original = old_concepts[concept["id"]]
                if "product_class_uris" not in original:
                    concept.pop("product_class_uris", None)
                if "table_sources" in original:
                    # Existing source roles/evidence survive; generic coverage can grow.
                    for row in original["table_sources"]["tables"]:
                        current = next(r for r in concept["table_sources"]["tables"] if r["table"] == row["table"])
                        self.assertEqual(row["role"], current["role"])
                        self.assertTrue(set(row["evidence"]) <= set(current["evidence"]))
                    concept["table_sources"] = copy.deepcopy(original["table_sources"])
            if "sources" in before:
                old_tables = {s["table"] for s in before["sources"]}
                after["sources"] = [s for s in after["sources"] if s["table"] in old_tables]
                after["evidence"] = {key: after["evidence"][key] for key in before["evidence"]}
            if "relation_definitions" in before:
                old_relations = {rel["id"] for rel in before["relation_definitions"]}
                after["relation_definitions"] = [rel for rel in after["relation_definitions"] if rel["id"] in old_relations]
            if name == "investment-metrics.json":
                # Source requirements and summary SQL resolve the old pledged-stock deferral.
                before["pending_scope"] = [p for p in before["pending_scope"] if p["id"] != "securities.stock_pledge"]
                # Collective-management fees remain a new deferral relative to this baseline.
                old_pending = {p["id"] for p in before["pending_scope"]}
                after["pending_scope"] = [p for p in after["pending_scope"] if p["id"] in old_pending]
            self.assertEqual(before, after, name)
        for name in ("holding-core.ttl", "bank-common.ttl", "bank-deposit.ttl", "bank-investment-products.ttl",
                     "securities-common.ttl", "customer360-ontology.ttl", "customer360-ontology.owl"):
            fmt = "xml" if name.endswith(".owl") else "turtle"
            before_rdf = Graph().parse(BEFORE / name, format=fmt)
            after_rdf = Graph().parse(ROOT / name, format=fmt)
            for graph in (before_rdf, after_rdf):
                for ontology in list(graph.subjects(RDF.type, OWL.Ontology)):
                    graph.remove((ontology, None, None))
            amount = URIRef("https://example.org/ontology/holding#metricAmount")
            before_rdf.remove((amount, SKOS.definition, None))
            after_rdf.remove((amount, SKOS.definition, None))
            normalize_reviewed_text(before_rdf)
            normalize_reviewed_text(after_rdf)
            self.assertTrue(set(before_rdf) <= set(after_rdf), name)
            collective = URIRef("https://example.org/ontology/bank#CollectiveManagementProduct")
            allowed = {collective} | {URIRef("https://example.org/ontology/holding#" + term) for term in
                       ("Department", "usesMetric", "LUM", "InterestIncome", "lumMeasuresProduct", "interestIncomeFromProduct",
                        "lumAsOfDate", "interestPeriodStart", "interestPeriodEnd")} | {
                       URIRef("https://example.org/ontology/bank#" + term) for term in
                       ("PrivateBankingDepartment", "PlannedTrustProduct", "TrustCustodyProduct", "ForeignExchangeProduct",
                        "LetterOfCreditProduct", "GoldProduct", "LoanProduct", "BankLUM", "BankInterestIncome")}
            self.assertTrue(all(triple[0] in allowed for triple in set(after_rdf) - set(before_rdf)), name)

    def test_mapping_order_is_deterministic_and_wrong_table_roles_or_column_assignments_are_rejected(self):
        for module, arg in ((builder.advisory_income, "income_model"), (builder.product_fees, "fee_model"),
                            (builder.product_aum, "aum_model"), (builder.investment_metrics, "investment_model"),
                            (builder.bank_business, "business_model")):
            model = module.load_model()
            changed = copy.deepcopy(model)
            for c in changed["concepts"]:
                if "table_sources" not in c:
                    continue
                mapping = c["table_sources"]
                mapping["tables"].reverse()
                for row in mapping["tables"] + mapping["unresolved_supporting_relations"]:
                    row["evidence"].reverse()
            self.assertEqual(builder.render_combined_cypher(), builder.render_combined_cypher(**{arg: changed}))
            metric_index = next(i for i, c in enumerate(model["concepts"]) if "table_sources" in c)
            for key, wrong in (("column", "UNAPPROVED"), ("table", "DSDEP.MADE_UP"),
                               ("role", "date_lookup_only")):
                invalid = copy.deepcopy(model)
                invalid["concepts"][metric_index]["table_sources"]["tables"][0][key] = wrong
                with self.subTest(module=module.__name__, key=key), self.assertRaises(ValueError):
                    module.build_graph(invalid)


if __name__ == "__main__":
    unittest.main()
