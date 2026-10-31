"""Real Semantica inference, scope boundaries and the active question backend."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from rdflib import URIRef, RDFS

from graph_qa import answer_with_tools, ground_answer
from llm_config import OpenRouterSettings
from ontology_tools import HERE, ToolPlan
from semantica_reasoner import RULES, SemanticaReasoner
from serve import create_explorer

SEC = "https://example.org/ontology/securities#SecuritiesAUM"
BANK = "https://example.org/ontology/bank#BankAUM"
AUM = "https://example.org/ontology/holding#AUM"
METRIC = "https://example.org/ontology/holding#Metric"


class SemanticaReasonerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reasoner = SemanticaReasoner()
        cls.original = cls.reasoner.source.read_bytes()
        # A Java/subprocess replacement that raises ensures the native engine
        # really runs in Python, rather than accidentally delegating to HermiT.
        from semantica.reasoning import Reasoner
        with patch("subprocess.Popen", side_effect=AssertionError("No Java or subprocess allowed")), patch("semantica.reasoning.Reasoner", wraps=Reasoner) as native:
            cls.report, _ = cls.reasoner.classify(force=True)
            native.assert_called_once()

    @classmethod
    def tearDownClass(cls):
        assert cls.reasoner.source.read_bytes() == cls.original

    def test_real_native_inference_has_only_declared_ontology_input(self):
        report = self.report
        self.assertEqual(report["engine"], "Semantica Reasoner")
        self.assertFalse(report["used_hermit"])
        self.assertFalse(report["pg_included"])
        self.assertEqual(len(report["classes"]), 43)
        self.assertEqual(len(report["input"]["facts"]), 80)
        self.assertEqual(report["input"]["rules"], RULES)
        self.assertTrue(report["inference_trace"])
        self.assertTrue(all(uri in self.reasoner.classes for uri in report["input"]["class_token_map"].values()))

    def test_all_43_class_results_match_independent_rdf_reachability(self):
        # Compare a different implementation against the actual rule engine,
        # covering the whole class hierarchy, not only the example path.
        for uri in self.reasoner.classes:
            reachable = {str(parent) for parent in self.reasoner.graph.transitive_objects(URIRef(uri), RDFS.subClassOf)} - {uri}
            self.assertEqual(set(self.report["classes"][uri]), reachable, uri)

    def test_transitive_query_has_native_trace_and_original_axioms(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=SEC, parent_uri=METRIC))
        self.assertEqual(result["verdict"], "entailed")
        self.assertEqual(result["engine"], "Semantica Reasoner")
        self.assertFalse(result["asserted_directly"])
        self.assertEqual(len(result["supporting_asserted_path"]), 2)
        self.assertEqual(result["native_inference"]["conclusion"], result["native_goal"])
        self.assertIn(result["native_inference"]["rule"], RULES)
        self.assertTrue(result["cached"])

    def test_direct_reflexive_and_reverse_directions(self):
        for child, parent, expected in ((SEC, AUM, "entailed"), (SEC, SEC, "entailed"), (METRIC, SEC, "not_entailed")):
            with self.subTest(child=child, parent=parent):
                result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=child, parent_uri=parent))
                self.assertEqual(result["verdict"], expected)

    def test_unproven_does_not_mean_false(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri=BANK, parent_uri=SEC))
        self.assertEqual(result["verdict"], "not_entailed")
        answer, guard = ground_answer("銀行 AUM 不是證券 AUM。", {"sources": []}, [result], "test")
        self.assertIn("無法證明", answer)
        self.assertNotIn("不是", answer)
        self.assertEqual(guard, "canonical_tool_verdict")

    def test_superclasses_use_semantica_closure(self):
        result = self.reasoner.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=SEC))
        self.assertEqual({parent["uri"] for parent in result["parents"]}, {AUM, METRIC})
        self.assertFalse(result["consistency_checked"])
        self.assertFalse(result["consistency_complete"])

    def test_consistency_is_explicitly_unsupported_without_classifying(self):
        with patch.object(self.reasoner, "classify") as classify:
            result = self.reasoner.execute(ToolPlan(route="ontology", tool="check_consistency"))
        classify.assert_not_called()
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["verdict"], "unsupported_consistency")
        self.assertNotIn("ontology_consistent", result)
        self.assertIn("無法判定", result["summary"])

    def test_pg_ids_and_unknown_classes_are_rejected_before_engine(self):
        for uri in ("securities.total_aum", "https://outside.example/Class", "https://example.org/ontology/bank#InventedClass"):
            with patch.object(self.reasoner, "classify") as classify:
                with self.assertRaises(ValueError):
                    self.reasoner.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=uri))
                classify.assert_not_called()

    def test_future_unsupported_axioms_cannot_silently_produce_a_verdict(self):
        header = '''@prefix h: <https://example.org/ontology/holding#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
h:TestA a owl:Class ; rdfs:subClassOf h:TestB .
h:TestB a owl:Class .
'''
        for extra in ("h:TestA owl:equivalentClass h:TestB .", "h:TestA owl:disjointWith h:TestB .", "h:TestA rdfs:subClassOf [ a owl:Restriction ; owl:onProperty h:p ; owl:someValuesFrom h:TestB ] .", "h:p a owl:FunctionalProperty .", "h:TestA rdfs:subClassOf h:Undeclared ."):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory(dir=HERE / "data") as folder:
                source = Path(folder) / "unsupported.ttl"
                source.write_text(header + extra, encoding="utf-8")
                fixture = SemanticaReasoner(source)
                with patch.object(fixture, "classify") as classify:
                    result = fixture.execute(ToolPlan(route="ontology", tool="check_subclass", class_uri="https://example.org/ontology/holding#TestA", parent_uri="https://example.org/ontology/holding#TestB"))
                classify.assert_not_called()
                self.assertEqual(result["verdict"], "unsupported_axioms")
                self.assertEqual(result["status"], "unsupported")

    def test_source_changes_cannot_reuse_previous_results(self):
        with tempfile.TemporaryDirectory(dir=HERE / "data") as folder:
            source = Path(folder) / "ontology.ttl"
            source.write_bytes(self.original)
            fixture = SemanticaReasoner(source)
            source.write_bytes(self.original + b"\n# changed\n")
            result = fixture.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=SEC))
            self.assertEqual(result["status"], "error")

    def test_native_execution_failure_is_not_a_logical_verdict(self):
        with patch.object(self.reasoner, "classify", side_effect=RuntimeError("fixture failure")):
            result = self.reasoner.execute(ToolPlan(route="ontology", tool="get_superclasses", class_uri=SEC))
        self.assertEqual(result["status"], "error")
        self.assertNotIn("verdict", result)
        self.assertNotIn("fixture failure", result["summary"])


class ActiveQuestionBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_explorer()
        cls.context = TestClient(cls.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_status_and_page_advertise_actual_engine_and_limitations(self):
        status = self.client.get("/api/graph-qa/status").json()
        self.assertEqual(status["reasoner"], "Semantica Reasoner")
        self.assertFalse(status["consistency_supported"])
        self.assertFalse(status["used_hermit"])
        self.assertIsInstance(self.app.state.reasoner, SemanticaReasoner)
        page = self.client.get("/ask").text
        self.assertIn("Semantica", page)
        self.assertNotIn("HermiT", page)

    def test_question_uses_actual_semantica_result_and_preserves_graph(self):
        before = self.app.state.session.build_graph_dict()
        llm = MagicMock()
        llm.generate.side_effect = [json.dumps({"route": "ontology", "tool": "check_subclass", "class_uri": SEC, "parent_uri": METRIC}), "證券 AUM 是金控指標的子類別。[R1]"]
        with patch("graph_qa.create_llm", return_value=llm), patch("subprocess.Popen", side_effect=AssertionError("No Java or subprocess allowed")):
            response = self.client.post("/api/graph-qa/ask", headers={"X-Graph-QA": "1"}, json={"question": "證券 AUM 是否屬於金控指標？"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tool_calls"][0]["engine"], "Semantica Reasoner")
        self.assertEqual(data["tool_calls"][0]["verdict"], "entailed")
        self.assertTrue(data["citations_valid"])
        self.assertEqual(llm.generate.call_count, 2)
        self.assertEqual(self.app.state.session.build_graph_dict(), before)

    def test_unsupported_consistency_is_never_rewritten_by_llm(self):
        llm = MagicMock()
        llm.generate.return_value = '{"route":"ontology","tool":"check_consistency"}'
        with patch("graph_qa.create_llm", return_value=llm):
            response = self.client.post("/api/graph-qa/ask", headers={"X-Graph-QA": "1"}, json={"question": "本體是否一致？"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tool_calls"][0]["verdict"], "unsupported_consistency")
        self.assertEqual(llm.generate.call_count, 1)
        self.assertIn("無法判定", data["answer"])

    def test_pg_questions_do_not_call_rule_engine(self):
        llm = MagicMock()
        llm.generate.side_effect = ['{"route":"pg"}', "來源待確認。[N1]"]
        settings = OpenRouterSettings(api_key="unused-test-key", model="test/model", max_tokens=100)
        context = {"sources": [{"id": "N1", "kind": "node"}], "roots": [], "truncated": False, "graph": {"nodes": 146, "edges": 246}}
        with patch("graph_qa.create_llm", return_value=llm), patch.object(self.app.state.reasoner, "execute") as execute:
            result = answer_with_tools("test", context, self.app.state.reasoner, settings)
        execute.assert_not_called()
        self.assertEqual(result["route"], "pg")


if __name__ == "__main__":
    unittest.main()
