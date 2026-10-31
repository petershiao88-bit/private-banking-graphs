"""Validate initial product-fee evidence, source ambiguity and offline projection."""

import copy
import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pg_product_fee_tests", HERE / "build_cypher.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
fees = builder.product_fees


def source_path(evidence):
    return HERE.parents[2].joinpath(*Path(evidence["file"]).parts[1:])


def workbook_cells(path, sheet_name):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as archive:
        strings = ["".join(e.itertext()) for e in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", ns)]
        rels = {e.attrib["Id"]: e.attrib["Target"] for e in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheet = next(e for e in ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", ns)
                     if e.attrib["name"] == sheet_name)
        target = rels[sheet.attrib[rid]]
        member = target.lstrip("/") if target.startswith("/") else "xl/" + target
        cells = {}
        for cell in ET.fromstring(archive.read(member)).findall(".//m:c", ns):
            value = cell.findtext("m:v", "", ns)
            if cell.attrib.get("t") == "s":
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(cell.find("m:is", ns).itertext())
            cells[cell.attrib["r"]] = value
        return cells


class ProductFeeTests(unittest.TestCase):
    def setUp(self):
        self.model = fees.load_model()

    def test_sql_ranges_and_private_products_support_only_initial_scope(self):
        evidence = self.model["evidence"]
        for eid, identifiers in {
            "sql_si": ("INCOME_039", "CUSTOMER_ID", "TRADE_DATE", "S_PCC_CODE", "FEE_AMOUNT_TWD", "UNION"),
            "sql_offshore": ("INCOME_042", "FEEDATE", "IDNO", "BRHREBATEAMT", "FHID='SN'", "BAOPCCCODE"),
            "sql_si_summary": ("INCOME_039", "結構型_境內"),
            "sql_offshore_summary": ("INCOME_042", "結構型_境外"),
        }.items():
            record = evidence[eid]
            lines = source_path(record).read_bytes().decode(record["encoding"]).splitlines()
            start, end = record["lines"]
            text = "\n".join(lines[start - 1:end]).upper()
            for identifier in identifiers:
                self.assertIn(identifier.upper(), text)
        for eid in ("private_product_domestic", "private_product_offshore"):
            record = evidence[eid]
            private = json.loads(source_path(record).read_text(encoding="utf-8"))
            product = next(n["properties"] for n in private["nodes"]
                           if n["kind"] == "product" and n["properties"]["productCode"] == record["product_code"])
            self.assertEqual(product["productCategory"], "結構型商品")
        domestic = next(c for c in self.model["concepts"] if c["private_product_code"] == "bank_structured_domestic")
        self.assertIn("尚未納入", domestic["observations"]["coverage"])
        self.assertEqual({s["table"] for s in self.model["sources"]}, {*fees.SI, fees.OFFSHORE} | {
            "DSDEP." + kind + "_PERFO_RPT" + suffix for kind in ("ELI", "FCI", "DCI") for suffix in ("", "_HS")} | {"DSTAS.FO108_W"})

    def test_metadata_cells_support_candidates_and_distinguish_event_dates_and_ids(self):
        checks = {
            "metadata_si": {"B2": "CUSTOMER_ID", "E3": "交易單號", "B13": "FEE_AMOUNT_TWD", "E13": "手續費換算台幣",
                            "B21": "RM_ID", "B23": "TRADE_DATE", "E23": "交易日", "B29": "USER_ID"},
            "metadata_offshore": {"B7": "BAOEMPID", "B9": "BRHREBATEAMT", "E9": "分行手續費",
                                  "B13": "FEEDATE", "E13": "手續費發生日", "B18": "FUNDID",
                                  "E18": "基金代碼", "B20": "IDNO", "B31": "SAOEMPID"},
        }
        for eid, expected in checks.items():
            record = self.model["evidence"][eid]
            cells = workbook_cells(source_path(record), record["sheet"])
            for cell, value in expected.items():
                self.assertEqual(cells[cell], value)
        for concept in self.model["concepts"]:
            fields = {f["field"]: f for f in concept["fields"]}
            for field in ("snapshotDate", "incomePeriod", "currency"):
                self.assertEqual(fields[field]["candidates"], [])
            for candidate in fields["employeeId"]["candidates"]:
                self.assertEqual(candidate["applicability"], "pending_advisor_attribution")
                self.assertNotIn("PCC", candidate["column"])
            self.assertTrue(all(f["table"] is None and f["column"] is None for f in fields.values()))
            expected_product = "StockProduct" if concept["id"] == "bank.overseas_stock_fee_income" else "StructuredFinancialProduct"
            self.assertEqual(concept["specific_product_class_uri"], fees.BANK + expected_product)

    def test_rejects_selected_sources_unproven_dates_role_ids_and_permissions(self):
        changes = []
        for key in self.model["execution"]:
            model = copy.deepcopy(self.model)
            model["execution"][key] = "not approved"
            changes.append(model)
        model = copy.deepcopy(self.model)
        model["concepts"][0]["fields"][0]["table"] = fees.SI[0]
        changes.append(model)
        model = copy.deepcopy(self.model)
        employee = next(f for f in model["concepts"][0]["fields"] if f["field"] == "employeeId")
        employee["candidates"][0]["column"] = "S_PCC_CODE"
        changes.append(model)
        model = copy.deepcopy(self.model)
        date = next(f for f in model["concepts"][0]["fields"] if f["field"] == "snapshotDate")
        date["candidates"] = [{"table": fees.SI[0], "column": "TRADE_DATE"}]
        changes.append(model)
        for key, value in (("access_policy_status", "all_advisors_allowed"), ("instance_mapping", True), ("records", [])):
            model = copy.deepcopy(self.model)
            model[key] = value
            changes.append(model)
        model = copy.deepcopy(self.model)
        model["concepts"][0]["specific_product_class_uri"] = fees.BANK + "StructuredDepositProduct"
        changes.append(model)
        for i, model in enumerate(changes):
            with self.subTest(change=i), self.assertRaises(ValueError):
                builder.render_combined_cypher(fee_model=model)

    def test_evidence_and_candidates_survive_combined_projection_and_reordering(self):
        graph = fees.build_graph(self.model)
        nodes = {n["id"]: n for n in graph["nodes"]}
        for concept in self.model["concepts"]:
            observed = json.loads(nodes[concept["id"]]["properties"]["observations_json"])
            if "event_date" in concept["observations"]:
                self.assertEqual(observed["event_date"], concept["observations"]["event_date"])
            else:
                expected_observations = copy.deepcopy(concept["observations"])
                expected_observations["evidence"].sort()
                self.assertEqual(observed, expected_observations)
            for field in concept["fields"]:
                mapping = json.loads(nodes[concept["id"] + "." + field["field"]]["properties"]["mapping_json"])
                self.assertEqual({(c["table"], c["column"]) for c in mapping["candidates"]},
                                 {(c["table"], c["column"]) for c in field["candidates"]})
        reordered = copy.deepcopy(self.model)
        for key in ("concepts", "relation_definitions", "sources"):
            reordered[key].reverse()
        for source in reordered["sources"]:
            source["evidence"].reverse()
        for concept in reordered["concepts"]:
            concept["fields"].reverse()
            concept["observations"]["evidence"].reverse()
            for field in concept["fields"]:
                field["candidates"].reverse()
                for candidate in field["candidates"]:
                    candidate["evidence"].reverse()
        output = builder.render_combined_cypher()
        self.assertEqual(output, builder.render_combined_cypher(fee_model=reordered))
        self.assertEqual(output.encode("utf-8"), (HERE / "model.cypher").read_bytes())
        for table in self.model["sources"]:
            self.assertEqual(nodes["source:" + table["table"]]["properties"]["database_verified_json"], "false")

    def test_four_new_fees_reuse_common_semantics_and_leave_all_column_candidates_empty(self):
        expected = {
            "bank.overseas_stock_fee_income": {"StockProduct", "OverseasFinancialProduct"},
            "bank.domestic_structured_eli_fee_income": {"StructuredFinancialProduct"},
            "bank.domestic_structured_fci_fee_income": {"StructuredFinancialProduct"},
            "bank.dci_fee_income": {"StructuredFinancialProduct"},
        }
        graph = fees.build_graph(self.model)
        edges = {(e["source"], e["type"], e["target"]) for e in graph["relationships"]}
        for cid, products in expected.items():
            concept = next(c for c in self.model["concepts"] if c["id"] == cid)
            self.assertEqual(concept["class_uri"], fees.BANK + "BankFeeIncome")
            self.assertEqual(set(concept["product_class_uris"]), {fees.BANK + p for p in products})
            for uri in concept["product_class_uris"]:
                self.assertIn((cid + ".product", "HAS_TARGET_CLASS", uri), edges)
            self.assertIn((cid + ".product", "REFERS_TO_OBJECT_PROPERTY", fees.FH + "feeIncomeFromProduct"), edges)
            for mapping in concept["fields"]:
                self.assertEqual(mapping["status"], "pending")
                self.assertIsNone(mapping["table"])
                self.assertIsNone(mapping["column"])
                self.assertEqual(mapping["candidates"], [])
                self.assertFalse(any(e[0] == cid + "." + mapping["field"] and e[1] == "CANDIDATE_SOURCE" for e in edges))

    def test_fee_table_evidence_keeps_original_dci_fee_and_new_tmu_components_separate(self):
        expected = {
            "bank.overseas_stock_fee_income": ("sql_overseas_stock", {fees.OFFSHORE}),
            "bank.domestic_structured_eli_fee_income": ("sql_eli", {"DSDEP.ELI_PERFO_RPT", "DSDEP.ELI_PERFO_RPT_HS"}),
            "bank.domestic_structured_fci_fee_income": ("sql_fci", {"DSDEP.FCI_PERFO_RPT", "DSDEP.FCI_PERFO_RPT_HS"}),
            "bank.dci_fee_income": ("sql_dci", {"DSDEP.DCI_PERFO_RPT", "DSDEP.DCI_PERFO_RPT_HS"}),
        }
        for cid, (eid, tables) in expected.items():
            concept = next(c for c in self.model["concepts"] if c["id"] == cid)
            rows = concept["table_sources"]["tables"]
            self.assertEqual({row["table"] for row in rows}, tables | ({"DSTAS.FO108_W"} if cid == "bank.dci_fee_income" else set()))
            record = self.model["evidence"][eid]
            start, end = record["lines"]
            text = "\n".join(source_path(record).read_text(encoding=record["encoding"]).splitlines()[start-1:end]).upper()
            for table in tables:
                self.assertIn(table.upper() + "@", text)
            if cid == "bank.dci_fee_income":
                self.assertIn("INCOME_037", text)
                self.assertNotIn("INCOME_038", text)
                self.assertNotIn("TMUPROFIT", text)
                self.assertTrue(any("非 DCD" in s for s in concept["observations"]["excluded_scope"]))
            elif cid == "bank.overseas_stock_fee_income":
                self.assertIn("'PS'", text)
            else:
                self.assertNotIn("DSDEP.SI_PERFO_RPT@", text)
        for kind in ("eli", "fci", "dci"):
            record = self.model["evidence"]["metadata_" + kind]
            cells = workbook_cells(source_path(record), record["sheet"])
            self.assertEqual(cells["B1"], "欄位名稱")
        self.assertIn("DSTAS.FO108_W", {s["table"] for s in self.model["sources"]})

    def test_rejects_new_fee_column_mapping_product_scope_changes_and_replacing_fee_with_tmu_source(self):
        cid = "bank.dci_fee_income"
        variants = []
        for key, value in (("table", "DSDEP.DCI_PERFO_RPT"), ("column", "UNAPPROVED"),
                           ("candidates", [{"table": "DSDEP.DCI_PERFO_RPT", "column": "UNAPPROVED"}])):
            changed = copy.deepcopy(self.model)
            c = next(c for c in changed["concepts"] if c["id"] == cid)
            c["fields"][0][key] = value
            variants.append(changed)
        changed = copy.deepcopy(self.model)
        next(c for c in changed["concepts"] if c["id"] == cid)["table_sources"]["tables"][0]["table"] = "DSTAS.FO108_W"
        variants.append(changed)
        changed = copy.deepcopy(self.model)
        next(c for c in changed["concepts"] if c["id"] == "bank.overseas_stock_fee_income")["product_class_uris"] = [fees.BANK + "StockProduct"]
        variants.append(changed)
        for changed in variants:
            with self.assertRaises(ValueError):
                fees.build_graph(changed)


if __name__ == "__main__":
    unittest.main()
