"""Offline checks for retrieval, citations, API errors, and graph immutability."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from rdflib import Graph

import graph_qa
from serve import create_explorer


class GraphQATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_explorer()
        cls.client_context = TestClient(cls.app)
        cls.client = cls.client_context.__enter__()
        cls.ontology = Graph().parse(graph_qa.HERE.parent / "customer360-ontology.ttl", format="turtle")

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_total_aum_follows_components_to_sources(self):
        result = graph_qa.retrieve(self.app.state.session, self.ontology, "證券總 AUM 的定義是什麼？它來自哪些資料表？")
        self.assertEqual(result["roots"], ["securities.total_aum"])
        sources = result["sources"]
        components = [source for source in sources if source.get("relation") == "HAS_COMPONENT_METRIC"]
        self.assertEqual(len(components), 5)
        self.assertTrue(any(source.get("relation") == "HAS_SOURCE_TABLE" for source in sources))
        self.assertTrue(any(source.get("details", {}).get("calculation_status") == "pending_tool_definition" for source in sources))
        self.assertFalse(result["truncated"])

    def test_department_and_original_rdf_definition(self):
        result = graph_qa.retrieve(self.app.state.session, self.ontology, "私銀有哪些指標？")
        self.assertEqual(result["roots"], ["https://example.org/ontology/bank#PrivateBankingDepartment"])
        self.assertEqual(sum(source.get("relation") == "USES_METRIC" for source in result["sources"]), 44)
        self.assertTrue(any("銀行從事私人銀行業務" in source.get("definition", "") for source in result["sources"]))

    def test_unknown_question_does_not_call_model(self):
        with patch("graph_qa.create_llm") as factory:
            response = self.client.post("/api/graph-qa/ask", headers={"X-Graph-QA": "1"}, json={"question": "火星海底咖啡館"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["used_llm"])
        factory.assert_not_called()

    def test_paid_endpoint_rejects_foreign_origin_and_simple_posts(self):
        for headers in ({}, {"X-Graph-QA": "1", "Origin": "https://outside.example"}):
            response = self.client.post("/api/graph-qa/ask", headers=headers, json={"question": "證券總 AUM"})
            self.assertEqual(response.status_code, 403)

    def test_answer_has_evidence_and_never_mutates_graph(self):
        before = self.app.state.session.build_graph_dict()
        llm = MagicMock()
        llm.generate.side_effect = ['{"route":"pg"}', "計算口徑仍待定。[N1]"]
        with patch("graph_qa.create_llm", return_value=llm):
            response = self.client.post("/api/graph-qa/ask", headers={"X-Graph-QA": "1"}, json={"question": "證券總 AUM"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["used_llm"])
        self.assertTrue(result["citations_valid"])
        self.assertEqual(self.app.state.session.build_graph_dict(), before)
        self.assertIn("pending_tool_definition", llm.generate.call_args.args[0])
        llm.provider.client.close.assert_called_once()

    def test_page_and_safe_status(self):
        self.assertIn("圖譜問答", self.client.get("/ask").text)
        self.assertIn('href="/ask"', self.client.get("/").text)
        status = self.client.get("/api/graph-qa/status").json()
        self.assertTrue(status["configured"])
        self.assertNotIn("key", str(status).lower())

    def test_model_errors_are_redacted(self):
        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("secret-example-must-not-be-returned")
        with patch("graph_qa.create_llm", return_value=llm):
            response = self.client.post("/api/graph-qa/ask", headers={"X-Graph-QA": "1"}, json={"question": "證券總 AUM"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret-example", response.text)


if __name__ == "__main__":
    unittest.main()
