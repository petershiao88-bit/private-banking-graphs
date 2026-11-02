"""Verify actual rule inference, SHACL enforcement and the delivery boundary."""
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import handoff_demo as demo


class HandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = demo.run_suite()
        cls.results = {r["case_id"]: r for r in cls.report["results"]}

    def test_all_scenario_verdicts_and_delivery(self):
        self.assertEqual((self.report["passed"], self.report["total"]), (14, 14))
        for result in self.results.values():
            with self.subTest(case=result["case_id"]):
                allowed = result["verdict"] in {"allowed", "allowed_after_redaction"}
                self.assertEqual(result["delivered"], allowed)
                self.assertEqual(len(result["receiver_inbox"]), int(allowed))
                if allowed:
                    self.assertTrue(result["stages"][-1]["validation"]["conforms"])

    def test_fee_block_is_a_real_shacl_violation(self):
        result = self.results["fee_block"]
        stage = result["stages"][0]
        self.assertFalse(stage["validation"]["conforms"])
        self.assertTrue(stage["validation"]["violations"])
        self.assertTrue({"bank_view", "internal_performance"} <= set(stage["reasoning"]["labels"]))
        self.assertEqual(result["receiver_inbox"], [])

    def test_redaction_removes_value_and_sources_before_delivery(self):
        result = self.results["fee_mask"]
        self.assertEqual([s["validation"]["conforms"] for s in result["stages"]], [False, True])
        payload = result["receiver_inbox"][0]
        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("1.5%", "fee_staging", "bank_fee", "internal_performance", "bank_view"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(payload["items"], [demo.PUBLIC_ITEM])
        self.assertEqual(payload["labels"], ["public"])
        self.assertEqual(result["transformation"]["output_sha256"], demo.digest(payload["items"]))
        self.assertEqual(len(result["decision_ids"]), 2)
        self.assertTrue(result["decision_trace"])
        # Restricted original lineage remains visible to the audit, not Agent B.
        self.assertIn("fee_staging", {e["entity_id"] for e in result["lineage"]["entries"]})

    def test_multihop_lineage_inherits_both_subsidiaries(self):
        result = self.results["combined_no_consent"]
        reasoning = result["stages"][0]["reasoning"]
        self.assertEqual(set(reasoning["labels"]), {"personal_data", "bank_subsidiary", "securities_subsidiary"})
        self.assertIn("combined_position", reasoning["sources"])
        self.assertIn("bank_holdings", reasoning["sources"])
        self.assertIn("securities_holdings", reasoning["sources"])
        self.assertTrue(any(f.startswith("RequiresConsent(answer_") for f in reasoning["derived_facts"]))
        ids = {e["entity_id"] for e in result["lineage"]["entries"]}
        self.assertTrue({"combined_position", "bank_holdings", "securities_holdings"} <= ids)

    def test_registered_class_hierarchy_is_really_inferred(self):
        reasoning = self.results["fee_block"]["stages"][0]["reasoning"]
        metric_token = next(token for token, uri in reasoning["class_token_map"].items() if uri == demo.HOLDING + "Metric")
        self.assertIn(f"IsA(fee, {metric_token})", reasoning["derived_facts"])
        self.assertNotIn(f"IsA(fee, {metric_token})", reasoning["facts"])

    def test_consent_must_come_from_trusted_registry(self):
        self.assertTrue(self.results["combined_with_consent"]["delivered"])
        for case in ("fake_consent", "wrong_scope", "expired_consent", "fake_public"):
            with self.subTest(case=case):
                result = self.results[case]
                self.assertEqual(result["verdict"], "needs_consent")
                self.assertFalse(result["consent"]["verified"])
                self.assertEqual(result["receiver_inbox"], [])

    def test_masking_one_item_does_not_clear_other_obligations(self):
        result = self.results["mixed_mask"]
        self.assertEqual(len(result["stages"]), 2)
        final = result["stages"][-1]
        self.assertNotIn("internal_performance", final["reasoning"]["labels"])
        self.assertIn("personal_data", final["reasoning"]["labels"])
        self.assertFalse(final["validation"]["conforms"])
        self.assertEqual(result["receiver_inbox"], [])

    def test_unknown_or_unverified_inputs_never_reach_reasoner(self):
        for case in ("tampered_output", "missing_source", "unknown_term", "fake_downgrade"):
            with self.subTest(case=case):
                result = self.results[case]
                self.assertEqual(result["verdict"], "blocked")
                self.assertEqual(result["stages"], [])
                self.assertFalse(result["precheck"]["verified"])

    def test_dropped_sources_and_wrong_customer_fail_receipt_check(self):
        for mutate in ("drop_sources", "wrong_customer", "unregistered_agent"):
            claim, request = demo.make_scenario("combined_with_consent")
            if mutate == "drop_sources":
                claim["items"][0]["source_ids"] = ["product_catalog"]
            elif mutate == "wrong_customer":
                request["customer"] = "another_customer"
            else:
                request["sender"] = "unknown_agent"
            receiver = demo.DemoReceiver()
            result = demo.HandoffHarness().execute(claim, request, receiver)
            self.assertEqual(result["verdict"], "blocked")
            self.assertEqual(receiver.inbox, [])

    def test_engine_validation_and_audit_failure_cannot_send(self):
        for method in ("infer", "validate", "record_material", "decision"):
            claim, request = demo.make_scenario("public")
            receiver = demo.DemoReceiver()
            harness = demo.HandoffHarness()
            with self.subTest(method=method), patch.object(harness, method, side_effect=RuntimeError("fixture failure")):
                with self.assertRaises(RuntimeError):
                    harness.execute(claim, request, receiver)
                self.assertEqual(receiver.inbox, [])

    def test_unclassified_source_and_cycle_are_not_treated_as_public(self):
        for source in ({"labels": [], "upstream": [], "description": "missing labels"}, {"labels": ["public"], "upstream": ["combined_position"], "description": "cycle"}):
            with patch.dict(demo.SOURCES, {"combined_position": source}):
                claim, request = demo.make_scenario("combined_no_consent")
                receiver = demo.DemoReceiver()
                result = demo.HandoffHarness().execute(claim, request, receiver)
                self.assertEqual(result["verdict"], "blocked")
                self.assertEqual(receiver.inbox, [])


class HandoffAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        demo.attach_handoff_demo(app)
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_page_and_scenario_catalog(self):
        self.assertIn("Agent 交接", self.client.get("/handoff").text)
        self.assertEqual(len(self.client.get("/api/handoff/scenarios").json()["scenarios"]), 14)

    def test_caller_cannot_override_rules_claims_or_consent(self):
        for extra in ({"rules": []}, {"consent": True}, {"items": []}):
            response = self.client.post("/api/handoff/run", headers={"X-Handoff-Demo": "1"}, json={"case_id": "public", **extra})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post("/api/handoff/run", headers={"X-Handoff-Demo": "1"}, json={"case_id": "unknown"}).status_code, 422)

    def test_cross_origin_and_unmarked_requests_rejected(self):
        for headers in ({}, {"X-Handoff-Demo": "1", "Origin": "https://outside.example"}):
            response = self.client.post("/api/handoff/run", headers=headers, json={"case_id": "public"})
            self.assertEqual(response.status_code, 403)

    def test_api_runs_real_pipeline_and_does_not_modify_originals(self):
        paths = [demo.HERE.parent / "customer360-ontology.ttl"] + [demo.HERE / "data" / (name + ".json") for name in ("full", "securities", "business", "ontology")]
        before = {p: p.read_bytes() for p in paths}
        response = self.client.post("/api/handoff/run", headers={"X-Handoff-Demo": "1"}, json={"case_id": "fee_mask"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["delivered"])
        self.assertFalse(result["used_llm"])
        self.assertFalse(result["used_hermit"])
        self.assertFalse(result["pg_included"])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_incomplete_execution_returns_error_not_success(self):
        with patch.object(demo.HandoffHarness, "infer", side_effect=RuntimeError("private fixture error")):
            response = self.client.post("/api/handoff/run", headers={"X-Handoff-Demo": "1"}, json={"case_id": "public"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private fixture error", response.text)
        self.assertIn("未交接", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
