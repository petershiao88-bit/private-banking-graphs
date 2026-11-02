"""知識層與 context 包：指標目錄、權限（含總指標繼承分項拒絕）、角色過濾、release 對應。"""

import json
import unittest

from tests import shared_kb
from c360_agent import packs
from c360_agent.tools import ToolBox


class KnowledgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_catalog_matches_pg_inventory(self):
        kinds = {}
        for m in self.kb.metrics.values():
            kinds[m.kind] = kinds.get(m.kind, 0) + 1
        self.assertEqual(len(self.kb.metrics), 44)
        self.assertEqual(kinds, {"aum": 19, "lum": 1, "fee": 22, "interest": 2})  # 與 METRIC-TABLE-SOURCES.md 一致

    def test_every_metric_class_and_product_exists(self):
        for m in self.kb.metrics.values():
            self.assertIn(m.class_id, self.kb.classes, m.id)
            for p in m.product_ids:
                self.assertIn(p, self.kb.classes, m.id)
            self.assertTrue(m.tables, m.id)

    def test_summary_tables_come_from_components(self):
        total = self.kb.metrics["securities.total_aum"]
        self.assertEqual(total.table_status, "via_components")
        self.assertTrue(all(t.get("inherited_from") in total.components for t in total.tables))

    def test_policy_and_aggregate_deny(self):
        kb = self.kb
        self.assertEqual(kb.metric_access("bank.fund_aum", "customer")["effect"], "deny")
        self.assertEqual(kb.metric_access("securities.fund_fee_income", "customer")["effect"], "deny")  # 組合規則
        self.assertEqual(kb.metric_access("securities.bond_aum", "customer")["effect"], "allow")
        total = kb.metric_access("securities.total_fee_income", "customer")
        self.assertEqual(total["effect"], "deny")
        self.assertIn("分項", total["reasons"][-1])
        self.assertEqual(kb.metric_access("securities.total_aum", "customer")["effect"], "allow")
        self.assertEqual(len(kb.visible_metrics("rm")), 44)

    def test_is_a_uses_owl_closure(self):
        self.assertEqual(self.kb.is_a("bank:FinancialAdvisor", "fh:Employee"),
                         ["bank:FinancialAdvisor", "bank:BankEmployee", "fh:Employee"])
        self.assertTrue(self.kb.is_inferred("bank:FinancialAdvisor", "fh:Employee"))
        self.assertIsNone(self.kb.is_a("bank:ETFProduct", "bank:FundProduct"))

    def test_metrics_matching_by_product_subtree(self):
        ids = {m.id for m in self.kb.metrics_matching(kind="aum", product="bank:OverseasFinancialProduct")}
        self.assertEqual(ids, {"bank.overseas_stock_aum", "bank.overseas_bond_trust_aum",
                               "bank.overseas_bond_proprietary_aum", "bank.offshore_structured_aum"})
        all_aum = self.kb.metrics_matching(kind="aum", product="fh:FinancialProduct", include_summary=False)
        self.assertEqual(len(all_aum), 18)

    def test_search_uses_synonyms(self):
        metrics = lambda q: [h["id"] for h in self.kb.search(q) if h["type"] == "metric"]  # noqa: E731
        self.assertEqual(metrics("放款餘額")[0], "bank.loan_lum")
        self.assertEqual(metrics("保單手續費收入")[0], "bank.insurance_fee_income")
        self.assertIn("bank.lc_fee_income", metrics("開狀業務收了多少手續費，要用哪個指標？")[:3])  # 長問句（實驗 4）
        hidden = [h["id"] for h in self.kb.search("基金手收", role="customer")]
        self.assertNotIn("bank.fund_fee_income", hidden)

    def test_release_state(self):
        self.assertTrue(self.kb.release["released"])
        self.assertTrue(self.kb.release["matches_release"])
        self.assertEqual(len(self.kb.fingerprint()), 64)


class PackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_customer_pack_omits_denied_metrics(self):
        pack = packs.build(self.kb, "customer")
        for mid, m in self.kb.metrics.items():
            visible = self.kb.metric_access(mid, "customer")["effect"] != "deny"
            self.assertEqual(f"`{mid}`" in pack["markdown"], visible, mid)
        self.assertEqual(pack["data"]["hidden_metric_count"], 35)
        self.assertNotIn("基金申購手續費", pack["markdown"])  # 示範詞條已排除

    def test_rm_pack_has_everything_and_is_deterministic(self):
        a, b = packs.build(self.kb, "rm"), packs.build(self.kb, "rm")
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertEqual(len(a["data"]["metrics"]), 44)
        for section in ("## 使用規則", "## 類別階層", "## 關係屬性", "## 指標清單", "## 待定範圍"):
            self.assertIn(section, a["markdown"])
        self.assertIn("債券商品（銀行） `bank:BondProduct`", a["markdown"])
        self.assertIn("Σ 私銀－證券總 AUM", a["markdown"])
        self.assertLess(a["tokens_est"], 8000)

    def test_full_pack_adds_definitions(self):
        compact, full = packs.build(self.kb, "rm", "compact"), packs.build(self.kb, "rm", "full")
        self.assertGreater(full["chars"], compact["chars"])
        self.assertIn("（估值輔助）", full["markdown"])

    def test_skeleton_and_baseline(self):
        skeleton = packs.build(self.kb, "rm", skeleton=True)
        self.assertNotIn("## 指標清單", skeleton["markdown"])
        self.assertNotIn("bank.fund_aum", skeleton["markdown"])
        baseline = packs.build(self.kb, "baseline")
        self.assertNotIn("## 類別階層", baseline["markdown"])
        self.assertEqual(baseline["markdown"].count("| `"), 44)

    def test_write_all(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            out, manifest = packs.write_all(self.kb, Path(tmp))
            self.assertEqual(len(manifest["packs"]), 7)
            data = json.loads((out / "customer.compact.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["metrics"]), 9)


class ToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_denied_and_missing_look_the_same(self):
        box = ToolBox(self.kb, "customer")
        denied = box.call("get_metric", {"metric_id": "bank.fund_aum"})
        missing = box.call("get_metric", {"metric_id": "bank.nothing"})
        self.assertEqual(denied["error"].split("：")[0], missing["error"].split("：")[0])
        self.assertNotIn("bank.fund_aum", json.dumps(box.call("list_metrics", {}), ensure_ascii=False))

    def test_tool_errors_are_returned_not_raised(self):
        box = ToolBox(self.kb, "rm")
        self.assertIn("error", box.call("get_class", {"class_id": "fh:Nope"}))
        self.assertIn("error", box.call("list_metrics", {"kind": "xyz"}))
        self.assertIn("error", box.call("is_a", "{not json"))
        self.assertIn("error", box.call("unknown_tool", {}))
        self.assertIn("error", box.call("get_metric", {"wrong": 1}))
        self.assertEqual(len(box.calls), 5)

    def test_tool_results(self):
        box = ToolBox(self.kb, "rm")
        card = box.call("get_metric", {"metric_id": "securities.total_aum"})
        self.assertEqual(len(card["components"]), 5)
        self.assertIn("不可", card["warning"])
        self.assertTrue(box.call("is_a", {"class_id": "bank:BankAUM", "ancestor_id": "fh:Metric"})["result"])
        self.assertEqual(len(box.call("list_gaps")["gaps"]), 3)
        self.assertEqual(len(box.schemas()), 6)


if __name__ == "__main__":
    unittest.main()
