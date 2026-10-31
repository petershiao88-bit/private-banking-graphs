"""Real HermiT checks plus offline LLM/tool integration checks. No API calls."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from graph_qa import answer_with_tools, ground_answer
from llm_config import OpenRouterSettings
from owl_reasoner import HERE, OwlReasoner, ToolPlan, plan_question

SEC = "https://example.org/ontology/securities#SecuritiesAUM"
BANK = "https://example.org/ontology/bank#BankAUM"
METRIC = "https://example.org/ontology/holding#Metric"


class OwlReasonerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reasoner = OwlReasoner()
        cls.source_before = hashlib.sha256(cls.reasoner.source.read_bytes()).hexdigest()
        cls.report, _ = cls.reasoner.classify(force=True)

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(cls.reasoner.source.read_bytes()).hexdigest() == cls.source_before

    def test_real_hermit_classification_has_only_owl_input(self):
        self.assertEqual(self.report["engine"], "HermiT")
        self.assertEqual(len(self.report["classes"]), 43)
        self.assertFalse(self.report["pg_included"])
        self.assertIn(METRIC, self.report["classes"][SEC])
        self.assertFalse(any(uri.startswith("securities.") for uri in self.report["classes"]))

    def test_transitive_subclass_has_two_asserted_supporting_axioms(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=SEC, parent_uri=METRIC))
        self.assertEqual(result["verdict"], "entailed")
        self.assertFalse(result["asserted_directly"])
        self.assertEqual(len(result["supporting_asserted_path"]), 2)
        self.assertTrue(result["cached"])

    def test_unproven_relationship_is_not_returned_as_false(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=BANK, parent_uri=SEC))
        self.assertEqual(result["verdict"], "not_entailed")
        self.assertIn("無法證明", result["summary"])

    def test_superclasses_and_datatype_limitations(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=SEC))
        self.assertEqual({parent["uri"] for parent in result["parents"]}, {METRIC, "https://example.org/ontology/holding#AUM"})
        consistency = self.reasoner.execute(ToolPlan(route="ontology", tool="check_consistency"))
        self.assertEqual(consistency["verdict"], "consistent_with_limitations")
        self.assertFalse(consistency["consistency_complete"])
        self.assertTrue(consistency["limitations"])

    def test_pg_or_unknown_uri_is_rejected_before_reasoning(self):
        for uri in ("securities.total_aum", "https://outside.example/Class"):
            with patch.object(self.reasoner, "classify") as classify:
                with self.assertRaises(ValueError):
                    self.reasoner.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=uri))
                classify.assert_not_called()

    def test_isolated_inconsistent_fixture_is_detected(self):
        with tempfile.TemporaryDirectory(dir=HERE / "data") as folder:
            source = Path(folder) / "fixture.ttl"
            source.write_text('''@prefix h: <https://example.org/ontology/holding#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
h:TestA a owl:Class ; owl:disjointWith h:TestB .
h:TestB a owl:Class .
h:testIndividual a h:TestA, h:TestB .
''', encoding="utf-8")
            fixture = OwlReasoner(source)
            result = fixture.execute(ToolPlan(route="ontology", tool="check_consistency"))
            self.assertEqual(result["verdict"], "inconsistent")
            self.assertTrue(result["consistency_complete"])

    def test_stale_ontology_cannot_reuse_previous_report(self):
        with tempfile.TemporaryDirectory(dir=HERE / "data") as folder:
            source = Path(folder) / "fixture.ttl"
            source.write_bytes(self.reasoner.content)
            fixture = OwlReasoner(source)
            source.write_bytes(self.reasoner.content + b"\n# Changed\n")
            result = fixture.execute(ToolPlan(route="ontology", tool="check_consistency"))
            self.assertEqual(result["status"], "error")

    def test_llm_plan_is_validated_and_then_real_tool_executes(self):
        llm = MagicMock()
        llm.generate.side_effect = [json.dumps({"route": "ontology", "tool": "check_subclass", "class_uri": SEC, "parent_uri": METRIC}), "證券 AUM 是金控指標的子類別。[R1]"]
        settings = OpenRouterSettings(api_key="unused-test-key", model="test/model", max_tokens=100)
        context = {"sources": [], "roots": [], "truncated": False, "graph": {"nodes": 146, "edges": 246}}
        with patch("graph_qa.create_llm", return_value=llm):
            result = answer_with_tools("test", context, self.reasoner, settings)
        self.assertEqual(result["tool_calls"][0]["verdict"], "entailed")
        self.assertEqual(result["tool_calls"][0]["engine"], "HermiT")
        self.assertTrue(result["citations_valid"])
        self.assertEqual(llm.generate.call_count, 2)
        self.assertIn('"verdict": "entailed"', llm.generate.call_args.args[0])

    def test_pg_plan_does_not_call_reasoner(self):
        llm = MagicMock()
        llm.generate.side_effect = ['{"route":"pg"}', "來源待確認。[N1]"]
        settings = OpenRouterSettings(api_key="unused-test-key", model="test/model", max_tokens=100)
        context = {"sources": [{"id": "N1", "kind": "node"}], "roots": [], "truncated": False, "graph": {"nodes": 146, "edges": 246}}
        with patch("graph_qa.create_llm", return_value=llm), patch.object(self.reasoner, "execute") as execute:
            result = answer_with_tools("test", context, self.reasoner, settings)
        execute.assert_not_called()
        self.assertEqual(result["route"], "pg")

    def test_planner_cannot_add_arbitrary_tools_or_extra_arguments(self):
        llm = MagicMock()
        llm.generate.return_value = '{"route":"ontology","tool":"apply_axiom","code":"do_something"}'
        with self.assertRaises(ValueError):
            plan_question(llm, "test", self.reasoner.catalog)

    def test_unknown_verdict_cannot_be_reworded_as_negation(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=BANK, parent_uri=SEC))
        answer, guard = ground_answer("銀行 AUM 不是證券 AUM。", {"sources": []}, [result], "test")
        self.assertIn("無法證明", answer)
        self.assertNotIn("不是", answer)
        self.assertEqual(guard, "canonical_tool_verdict")

    def test_existing_source_tables_cannot_be_reported_as_missing(self):
        context = {"roots": ["metric"], "sources": [{"id": "N1", "entity_id": "metric", "definition": "定義待確認"}, {"id": "E1", "relation": "HAS_SOURCE_TABLE", "target_label": "TEST.TABLE"}]}
        answer, guard = ground_answer("目前未提供具體資料表。", context, [], "來源資料表是哪些？")
        self.assertIn("TEST.TABLE [E1]", answer)
        self.assertNotIn("未提供", answer)
        self.assertEqual(guard, "source_table_completeness")


if __name__ == "__main__":
    unittest.main()
