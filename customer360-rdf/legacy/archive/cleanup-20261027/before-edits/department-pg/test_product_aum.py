"""AUM semantics, reused source candidates and fee/AUM separation checks."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pg_aum_tests", HERE / "build_cypher.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
aum = builder.product_aum


class ProductAUMTests(unittest.TestCase):
    def setUp(self):
        self.model = aum.load_model()

    def test_only_aum_uses_measurement_while_income_retains_separate_product_relation(self):
        for module in (builder.advisory_income.load_model(), builder.product_fees.load_model()):
            for relation in module["relation_definitions"]:
                self.assertNotEqual(relation["property_uri"], aum.FH + "measuresProduct")
                if relation["id"].endswith(".product"):
                    self.assertEqual(relation["property_uri"], aum.FH + "feeIncomeFromProduct")
                    self.assertEqual(relation["domain_uri"], aum.FH + "FeeIncome")
        rdf = Graph()
        config = json.loads((HERE.parent / "build-config.json").read_text(encoding="utf-8"))
        for source in config["sources"]:
            rdf.parse(HERE.parent / source, format="turtle")
        for concept in self.model["concepts"]:
            self.assertIn(URIRef(aum.FH + "AUM"), set(rdf.transitive_objects(URIRef(concept["class_uri"]), RDFS.subClassOf)))
            for uri in concept["product_class_uris"]:
                self.assertIn((URIRef(uri), RDF.type, OWL.Class), rdf)
        for relation in self.model["relation_definitions"]:
            self.assertEqual(relation["domain_uri"], aum.FH + "AUM")
            self.assertEqual(relation["property_uri"], aum.FH + "measuresProduct")

    def test_deposit_aum_reuses_raw_evidence_without_approving_recognition_or_snapshot(self):
        base = builder.deposits.load_model()
        for concept in self.model["concepts"]:
            fields = {f["field"]: f for f in concept["fields"]}
            self.assertEqual(set(fields), {"customerId", "productId", "amount", "currency", "snapshotDate",
                                           "aumAsOfDate", "valuationQuantity", "valuationUnitPrice"})
            self.assertEqual(fields["amount"]["status"], "pending_aum_recognition")
            self.assertEqual(fields["currency"]["candidates"], [])
            self.assertEqual(fields["productId"]["candidates"], [])
            self.assertTrue(all(f["table"] is None and f["column"] is None for f in fields.values()))
            if concept["basis_concept"]:
                source = next(c for c in base["concepts"] if c["id"] == concept["basis_concept"])
                for name, original in (("customerId", "customerId"), ("amount", "balance"), ("snapshotDate", "snapshotDate")):
                    self.assertEqual(fields[name]["candidates"], next(f["candidates"] for f in source["fields"] if f["field"] == original))
        self.assertTrue(all(v is None for v in self.model["execution"].values()))
        self.assertEqual(self.model["access_policy_status"], "deferred_by_user")

    def test_investment_sql_supports_raw_inputs_and_keeps_date_selection_as_observation(self):
        for eid, identifiers in {
            "sql_bank_investment_aum": ("DSFND.PB_FUND_MONTH", "IDNO", "EXEDATE", "CURRENTTWDVALUE", "TRUSTPRD", "海外股票", "海外債券(信託)", "境外結構型商品"),
            "sql_bank_bond_proprietary_aum": ("DSWTR.BOND_POS_DAY", "CIF_ID", "DATA_DT", "STO_AMT * MKT_PRI /100 * EXC_RATE", "MAX(YYYYMMDD)", "GROUP BY SUBSTR(YYYYMMDD,1,6)"),
        }.items():
            record = self.model["evidence"][eid]
            path = HERE.parents[2].joinpath(*Path(record["file"]).parts[1:])
            lines = path.read_bytes().decode(record["encoding"]).splitlines()
            start, end = record["lines"]
            text = "\n".join(lines[start - 1:end]).upper()
            for identifier in identifiers:
                self.assertIn(identifier.upper(), text)
        proprietary = next(c for c in self.model["concepts"] if c["id"].endswith("proprietary_aum"))
        amount = next(f for f in proprietary["fields"] if f["field"] == "amount")
        self.assertEqual({c["column"] for c in amount["candidates"]}, {"STO_AMT", "MKT_PRI", "EXC_RATE"})
        self.assertIn("全體", proprietary["observations"]["date_observation"])
        self.assertIsNone(self.model["execution"]["snapshot_selection"])

    def test_rejects_premature_rules_cross_metric_domains_and_fake_product_ids(self):
        changes = []
        for key in self.model["execution"]:
            model = copy.deepcopy(self.model)
            model["execution"][key] = "not approved"
            changes.append(model)
        model = copy.deepcopy(self.model)
        model["concepts"][0]["fields"][0]["table"] = "DSDEP.DEP_NT_ACCT"
        changes.append(model)
        model = copy.deepcopy(self.model)
        model["concepts"][0]["class_uri"] = aum.BANK + "BankFeeIncome"
        changes.append(model)
        model = copy.deepcopy(self.model)
        model["relation_definitions"][0]["domain_uri"] = aum.FH + "Metric"
        changes.append(model)
        model = copy.deepcopy(self.model)
        field = next(f for f in model["concepts"][3]["fields"] if f["field"] == "productId")
        field["candidates"] = [{"table": aum.FUND, "column": "TRUSTPRD"}]
        changes.append(model)
        for key, value in (("access_policy_status", "customer_visible"), ("instance_mapping", True), ("records", [])):
            model = copy.deepcopy(self.model)
            model[key] = value
            changes.append(model)
        for i, model in enumerate(changes):
            with self.subTest(change=i), self.assertRaises(ValueError):
                builder.render_combined_cypher(aum_model=model)

    def test_projection_preserves_evidence_qualifiers_and_deterministic_reordering(self):
        graph = aum.build_graph(self.model)
        nodes = {n["id"]: n for n in graph["nodes"]}
        for concept in self.model["concepts"]:
            stored = json.loads(nodes[concept["id"]]["properties"]["observations_json"])
            self.assertEqual(stored["valuation_observation"], concept["observations"]["valuation_observation"])
            targets = {e["target"] for e in graph["relationships"] if e["source"] == concept["id"] + ".product" and e["type"] == "HAS_TARGET_CLASS"}
            self.assertEqual(targets, {aum.FH + "FinancialProduct", *concept["product_class_uris"]})
        reordered = copy.deepcopy(self.model)
        for key in ("concepts", "sources", "relation_definitions"):
            reordered[key].reverse()
        for evidence in reordered["evidence"].values():
            if "rows" in evidence:
                evidence["rows"].reverse()
        for concept in reordered["concepts"]:
            concept["fields"].reverse()
            concept["product_class_uris"].reverse()
            concept["observations"]["classification_evidence"].reverse()
            for field in concept["fields"]:
                field["candidates"].reverse()
                for candidate in field["candidates"]:
                    candidate["evidence"].reverse()
        output = builder.render_combined_cypher()
        self.assertEqual(output, builder.render_combined_cypher(aum_model=reordered))
        self.assertEqual(output.encode("utf-8"), (HERE / "model.cypher").read_bytes())


if __name__ == "__main__":
    unittest.main()
