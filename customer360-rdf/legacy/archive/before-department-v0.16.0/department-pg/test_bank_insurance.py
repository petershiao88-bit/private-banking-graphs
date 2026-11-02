"""Bank insurance source meanings, common references and pending-only mappings."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

from test_product_fees import source_path, workbook_cells

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("insurance_metric_tests", HERE / "build_cypher.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BankInsuranceTests(unittest.TestCase):
    def setUp(self):
        self.model = builder.investment_metrics.load_model()
        self.concepts = {c["id"]: c for c in self.model["concepts"]}

    def test_insurance_metrics_use_common_product_with_separate_metric_relations_and_no_columns(self):
        graph = builder.investment_metrics.build_graph(self.model)
        edges = {(e["source"], e["type"], e["target"]) for e in graph["relationships"]}
        for aum, count, table, prop in (
            (True, 8, "DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT", "measuresProduct"),
            (False, 11, "DSINS.INSU_RPT_Q01", "feeIncomeFromProduct"),
        ):
            cid = "bank.insurance_" + ("aum" if aum else "fee_income")
            c = self.concepts[cid]
            self.assertEqual(c["product_class_uris"], [builder.investment_metrics.BANK + "InsuranceProduct"])
            self.assertEqual(len(c["fields"]), count)
            self.assertIn((cid, "HAS_SOURCE_TABLE", "source:" + table), edges)
            self.assertIn((cid + ".product", "REFERS_TO_OBJECT_PROPERTY", builder.FH + prop), edges)
            for field in c["fields"]:
                self.assertEqual(field["status"], "pending")
                self.assertIsNone(field["table"])
                self.assertIsNone(field["column"])
                self.assertEqual(field["candidates"], [])
                self.assertFalse(any(e[0] == cid + "." + field["field"] and e[1] == "CANDIDATE_SOURCE" for e in edges))
        self.assertTrue(all(v is None for v in self.model["execution"].values()))

    def test_original_investment_amount_and_monthly_contribution_evidence_keep_distinct_meanings(self):
        evidence = self.model["evidence"]
        record = evidence["insurance_aum_summary_sql"]
        start, end = record["lines"]
        text = "\n".join(source_path(record).read_text(encoding=record["encoding"]).splitlines()[start-1:end])
        self.assertIn("原始投資金額", text)
        self.assertIn("原始投資金額", self.concepts["bank.insurance_aum"]["observations"]["valuation_observation"])
        for eid, address, expected in (("insurance_fee_metadata", "E13", "手收"),
                                       ("insurance_contribution_iu_metadata", "E18", "客戶貢獻度"),
                                       ("insurance_contribution_ofi_metadata", "E8", "客戶貢獻度")):
            record = evidence[eid]
            self.assertEqual(workbook_cells(source_path(record), record["sheet"])[address], expected)
        fee = self.concepts["bank.insurance_fee_income"]["table_sources"]
        self.assertEqual(fee["status"], "observed_in_files")
        self.assertEqual({row["table"] for row in fee["tables"]}, {
            "DSINS.INSU_RPT_Q01", "DSKPI.KPI_DET_IU_002_NEW", "DSKPI.KPI_DET_OFI_001"})
        catalog = {s["table"] for s in self.model["sources"]}
        self.assertIn("DSKPI.KPI_DET_IU_002_NEW", catalog)
        self.assertIn("DSKPI.KPI_DET_OFI_001", catalog)
        generic = builder.advisory_income.load_model()["concepts"][1]["table_sources"]
        self.assertEqual(generic["status"], "partial_scope")
        self.assertIn("DSINS.INSU_RPT_Q01", {row["table"] for row in generic["tables"]})

    def test_missing_daily_source_column_mapping_and_cross_metric_domains_are_rejected(self):
        for change in ("contribution_source", "column", "candidate", "aum_domain", "market_value_rule"):
            altered = copy.deepcopy(self.model)
            fee = next(c for c in altered["concepts"] if c["id"] == "bank.insurance_fee_income")
            if change == "contribution_source":
                fee["table_sources"]["tables"][0]["table"] = "DSKPI.KPI_DET_IU_002_NEW"
            elif change == "column":
                fee["fields"][0]["column"] = "UNAPPROVED"
            elif change == "candidate":
                fee["fields"][0]["candidates"] = [{"table": "DSINS.INSU_RPT_Q01", "column": "UNAPPROVED"}]
            elif change == "aum_domain":
                next(r for r in altered["relation_definitions"] if r["id"] == fee["id"] + ".product")["domain_uri"] = builder.FH + "AUM"
            else:
                altered["execution"]["valuation_rules"] = "unapproved market valuation"
            with self.subTest(change=change), self.assertRaises(ValueError):
                builder.investment_metrics.build_graph(altered)


if __name__ == "__main__":
    unittest.main()
