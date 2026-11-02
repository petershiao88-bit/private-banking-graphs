"""Semantic Studio：權限沿類別繼承、詞條對應組合、SHACL、存檔與 HTTP API。"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import yaml

from ontology_kit.config import Config
from semantic_studio.core import Studio, StudioError
from semantic_studio.server import ThreadingHTTPServer, make_handler

ROOT = Path(__file__).resolve().parents[2]

BANK = "https://example.org/ontology/bank#"
FH = "https://example.org/ontology/holding#"


def sandbox(test):
    tmp = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, tmp)
    shutil.copy2(ROOT / "config.yaml", tmp / "config.yaml")
    for folder in ("ontology", "dictionary", "policy", "shapes", "release"):
        shutil.copytree(ROOT / folder, tmp / folder)
    (tmp / "pg").mkdir()
    for path in (ROOT / "pg").glob("*.json"):
        shutil.copy2(path, tmp / "pg" / path.name)
    return tmp


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for key in [k for k in os.environ if k.startswith("C360_")]:
            os.environ.pop(key)
        cls.studio = Studio(Config(ROOT / "config.yaml"))
        cls.state = cls.studio.state()

    def term(self, term_id):
        return next(t for t in self.state["terms"] if t["id"] == term_id)

    def test_state_has_full_graph_reasoning_and_dictionary(self):
        s = self.state
        pg = [t for t in s["terms"] if t["origin"] == "pg"]
        self.assertEqual((len(s["classes"]), len(s["inferred"]), len(pg)), (43, 7, 52))
        self.assertEqual(len(s["properties"]), 28)
        self.assertIsNone(s["reasoning_error"])
        self.assertTrue(all(t["mappings"] for t in pg), "PG 五種類別欄位都要轉成對應")

    def test_class_rules_are_inherited_by_subclasses_only(self):
        perms = {c["id"]: c["permissions"] for c in self.state["classes"]}
        self.assertEqual(perms["bank:BankAUM"]["customer"]["effect"], "deny")
        self.assertEqual(perms["fh:AUM"]["customer"]["effect"], "allow")
        self.assertEqual(perms["bank:BankAUM"]["rm"]["effect"], "allow")

    def test_terms_inherit_permissions_from_their_class_combination(self):
        fee = self.term("demo.fund_subscription_fee")["permissions"]["customer"]
        self.assertEqual(fee["effect"], "deny")
        self.assertEqual({m["rule"] for m in fee["matches"]}, {"customer-no-bank-fee", "customer-no-bank-fund-fee"})
        combo = next(m for m in fee["matches"] if m["rule"] == "customer-no-bank-fund-fee")
        self.assertTrue(combo["combination"])
        self.assertEqual({(v["rule_class"], v["mapped_class"], v["inherited"]) for v in combo["via"]},
                         {("fh:FeeIncome", "bank:BankFeeIncome", True), ("bank:FundProduct", "bank:FundProduct", False)})
        sec = self.term("securities.fund_fee_income")["permissions"]["customer"]
        self.assertEqual([m["rule"] for m in sec["matches"]], ["customer-no-securities-fund-fee"])
        self.assertEqual(self.term("demo.fund_holding_value")["permissions"]["customer"]["effect"], "allow")
        self.assertEqual(self.term("demo.overseas_bond_coupon")["permissions"]["customer"]["effect"], "unmapped")

    def test_shacl_runs_on_inferred_graph_and_flags_only_unmapped_demo(self):
        results = self.state["validation"]["results"]
        self.assertEqual([(r["node"], r["severity"]) for r in results], [("term:demo.overseas_bond_coupon", "Violation")])
        self.assertGreaterEqual(len(self.state["shapes"]), 6)

    def test_preview_reports_bad_combinations(self):
        preview = self.studio.preview_term({"id": "x.bad", "name": "壞例子", "mappings": [
            {"class": "bank:BankFeeIncome", "role": "primary"}, {"class": "bank:BankAUM", "role": "primary"},
            {"class": "fh:Customer", "role": "product"}, {"class": "fh:FeeIncome", "role": "other"}]})
        messages = {(r["severity"], r["message"]) for r in preview["validation"]}
        self.assertIn(("Violation", "一個詞條只能有一個屬於「指標」的主類別"), messages)
        self.assertIn(("Violation", "角色為「商品」時，類別必須屬於金融商品"), messages)
        self.assertIn(("Warning", "對應的類別之間有上下位關係，上層那個是多餘的"), messages)
        self.assertEqual(preview["permissions"]["customer"]["effect"], "deny")
        with self.assertRaises(StudioError):
            self.studio.preview_term({"id": "x.unknown", "name": "x", "mappings": [{"class": "bank:Nope", "role": "primary"}]})

    def test_suggestions_prefer_name_over_definition(self):
        names = [s["class"] for s in self.studio.suggest("基金申購手續費", "客戶申購基金時銀行收取的手續費")]
        self.assertIn("bank:FundProduct", names[:3])
        self.assertIn("fh:FeeIncome", names[:4])  # 同義詞：手續費 → 手收
        self.assertNotIn("fh:Customer", names[:3])  # 只出現在定義裡的詞排在後面


class StudioWriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = sandbox(self)
        self.studio = Studio(Config(self.tmp / "config.yaml"))

    def test_save_import_delete_only_touch_dictionary_file(self):
        before = {p: p.read_bytes() for p in self.tmp.glob("ontology/**/*.ttl")}
        self.studio.save_term({"id": "wm.insurance_fee", "name": "保險佣金收入", "mappings": [
            {"class": "bank:BankFeeIncome", "role": "primary"}, {"class": "bank:InsuranceProduct", "role": "product"}]})
        saved = yaml.safe_load((self.tmp / "dictionary/terms.yaml").read_text(encoding="utf-8"))
        self.assertIn({"class": "bank:InsuranceProduct", "role": "product"},
                      next(t for t in saved["terms"] if t["id"] == "wm.insurance_fee")["mappings"])
        term = next(t for t in self.studio.state()["terms"] if t["id"] == "wm.insurance_fee")
        self.assertEqual(term["permissions"]["customer"]["effect"], "deny")
        added = self.studio.import_terms("id,name,definition,mappings\nwm.a,甲,,fh:AUM@primary;bank:GoldProduct@product\nwm.b,乙,,\n",
                                         "csv", "測試匯入")
        self.assertEqual(added, ["wm.a", "wm.b"])
        with self.assertRaises(StudioError):
            self.studio.import_terms("id,name\nwm.a,重複\n", "csv", "x")
        with self.assertRaises(StudioError):
            self.studio.save_term({"id": "bank.fund_aum", "name": "撞 PG ID", "mappings": []})
        self.studio.delete_term("wm.b")
        with self.assertRaises(StudioError):
            self.studio.delete_term("bank.fund_aum")
        self.assertEqual(before, {p: p.read_bytes() for p in self.tmp.glob("ontology/**/*.ttl")})

    def test_policy_change_recomputes_terms_and_rejects_unknown_class(self):
        policy = yaml.safe_load((self.tmp / "policy/access-policy.yaml").read_text(encoding="utf-8"))
        policy["rules"].append({"id": "customer-no-aum", "role": "customer", "effect": "deny", "classes": ["fh:AUM"], "note": ""})
        self.studio.save_policy(policy)
        term = next(t for t in self.studio.state()["terms"] if t["id"] == "demo.fund_holding_value")
        self.assertEqual(term["permissions"]["customer"]["effect"], "deny")
        policy["rules"].append({"id": "bad", "role": "customer", "effect": "deny", "classes": ["fh:Nope"]})
        with self.assertRaises(StudioError):
            self.studio.save_policy(policy)
        policy["rules"].pop()
        policy["rules"].append({"id": "bad", "role": "ghost", "effect": "deny", "classes": ["fh:AUM"]})
        with self.assertRaises(StudioError):
            self.studio.save_policy(policy)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Studio(Config(ROOT / "config.yaml"))))
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None, header=True):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json", **({"X-Studio": "1"} if header else {})})
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.read()

    def test_pages_state_and_write_protection(self):
        self.assertEqual(self.request("/")[0], 200)
        status, js = self.request("/static/lib/cytoscape.min.js")
        self.assertEqual(status, 200)
        self.assertGreater(len(js), 100000)
        self.assertIn(b"export function setState", self.request("/static/js/store.js")[1])
        state = json.loads(self.request("/api/state")[1])
        self.assertEqual(len(state["classes"]), 43)
        self.assertIn(b"owl:Class", self.request("/api/turtle?what=ontology")[1])
        status, body = self.request("/api/term/preview", {"term": {"id": "x.y", "name": "x", "mappings": []}})
        self.assertEqual(json.loads(body)["permissions"]["customer"]["effect"], "unmapped")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/term/save", {"term": {"id": "x.y", "name": "x"}}, header=False)
        self.assertEqual(caught.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/static/../config.yaml")
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
