"""Check source fidelity and deployment boundaries of the Fabric projection."""

import base64
import json
from pathlib import Path
import sys
import unittest

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import export_fabric_graph as export
import fabric_graph_runtime as runtime


class FabricExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = export.build_bundle()
        cls.pg = export.load_pg()
        cls.data = cls.bundle["data"]

    def test_pg_all_ids_properties_edges_survive(self):
        nodes = {n["id"]: n for n in self.data["nodes"]}
        for n in self.pg["nodes"]:
            actual = nodes[n["id"]]
            self.assertEqual(actual["pg_label"], n["label"])
            self.assertEqual(json.loads(actual["properties_json"]), n["properties"])
        actual = {(e["id"], e["source_id"], e["kind"], e["target_id"])
                  for e in self.data["edges"] if e["origin"] == "pg"}
        expected = {(e["id"], e["source"], e["type"], e["target"]) for e in self.pg["relationships"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len({n["id"] for n in self.data["nodes"]}), len(self.data["nodes"]))
        self.assertEqual(len({e["id"] for e in self.data["edges"]}), len(self.data["edges"]))

    def test_rdf_triples_round_trip_and_schema_markers(self):
        _, original = export.expected_graph()
        restored = Graph()
        for row in self.data["rdf_triples"]:
            subject = BNode(row["subject"]) if row["subject"].startswith("_:") else URIRef(row["subject"])
            obj = (Literal(row["object"], lang=row["language"] or None,
                           datatype=URIRef(row["datatype"]) if row["datatype"] else None)
                   if row["object_kind"] == "literal" else URIRef(row["object"]))
            restored.add((subject, URIRef(row["predicate"]), obj))
        self.assertTrue(isomorphic(restored, original))
        self.assertEqual(len(restored), 434)
        for edge in self.data["edges"]:
            if edge["kind"].startswith("RDF_DECLARED_"):
                self.assertEqual(edge["semantic_status"], "domain_range_visual_projection")

    def test_private_securities_scope_is_preserved(self):
        nodes = {n["id"]: n for n in self.data["nodes"]}
        self.assertEqual(nodes["bank.private_banking"]["kind"], "Department")
        metrics = {e["target_id"] for e in self.data["edges"] if e["kind"] == "USES_METRIC"}
        self.assertEqual(len(metrics), 44)
        self.assertTrue(all(nodes[i]["kind"] == "Metric" for i in metrics))
        self.assertNotIn("securities.stock_pledge_lum", metrics)
        self.assertNotIn("securities.stock_pledge_aum", metrics)
        self.assertNotIn("securities.taiwan_stock_fee_income", metrics)
        self.assertNotIn("bank.collective_account_fee_income", metrics)
        totals = {"securities.total_aum", "securities.total_fee_income"}
        self.assertEqual(sum(e["kind"] == "HAS_COMPONENT_METRIC" for e in self.data["edges"]), 9)
        self.assertFalse(any(e["source_id"] in totals and e["kind"] == "HAS_SOURCE_TABLE" for e in self.data["edges"]))

    def test_typed_mappings_partition_every_node_and_edge_once(self):
        tables = self.bundle["tables"]
        actual_nodes = [r for t in tables if t["suffix"].startswith("n_") for r in t["rows"]]
        actual_edges = [r for t in tables if t["suffix"].startswith("e_") for r in t["rows"]]
        self.assertCountEqual(actual_nodes, self.data["nodes"])
        self.assertCountEqual(actual_edges, self.data["edges"])
        node_types = {n["alias"]: n for n in self.bundle["parts"]["graphType.json"]["nodeTypes"]}
        for edge in self.bundle["parts"]["graphType.json"]["edgeTypes"]:
            self.assertIn(edge["sourceNodeType"]["alias"], node_types)
            self.assertIn(edge["destinationNodeType"]["alias"], node_types)
        workspace, lakehouse = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
        parent = "abfss://" + workspace + "@onelake.dfs.fabric.microsoft.com/" + lakehouse + "/Tables/"
        paths = {t["suffix"]: parent + t["suffix"]
                 for t in tables}
        parts = runtime.materialize_parts(self.bundle["parts"], paths, workspace, lakehouse)
        payload = runtime.request_payload(parts, "TestGraph")
        self.assertEqual(len(payload["definition"]["parts"]), 4)
        for part in payload["definition"]["parts"]:
            self.assertEqual(json.loads(base64.b64decode(part["payload"])), parts[part["path"]])
        self.assertNotIn("{{TABLE_PATH:", json.dumps(parts))
        self.assertTrue(all(s["properties"]["path"].startswith("Tables/")
                            for s in parts["dataSources.json"]["dataSources"]))
        self.assertIn("{{TABLE_PATH:", json.dumps(self.bundle["parts"]))
        with self.assertRaises(ValueError):
            runtime.materialize_parts(self.bundle["parts"], dict.fromkeys(paths, "abfss://other/Tables/x"), workspace, lakehouse)

    def test_notebook_compiles_and_cannot_choose_workspace_implicitly(self):
        notebook = export.notebook(self.bundle)
        scope = {}
        for i, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"cell-{i}", "exec")
        exec("".join(notebook["cells"][1]["source"]), scope)
        self.assertEqual(scope["WORKSPACE_ID"], "")
        self.assertEqual(scope["LAKEHOUSE_ID"], "")
        self.assertFalse(scope["CREATE_GRAPH_MODEL"])
        workspace, lakehouse = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
        context = {"currentWorkspaceId": workspace, "defaultLakehouseId": lakehouse,
                   "defaultLakehouseWorkspaceId": workspace}
        self.assertEqual(runtime.validated_target(context, workspace, lakehouse), (workspace, lakehouse))
        with self.assertRaises(ValueError):
            runtime.validated_target(context | {"defaultLakehouseWorkspaceId": lakehouse}, workspace, lakehouse)
        with self.assertRaises(ValueError):
            runtime.validated_target(context | {"defaultLakehouseId": workspace}, workspace, lakehouse)
        self.assertEqual(export.build_bundle(), self.bundle)


if __name__ == "__main__":
    unittest.main()
