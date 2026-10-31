"""Export RDF declarations + the complete PG metadata as a Fabric Graph bundle.

Offline only. Never changes the ontology, PG inputs, or a remote workspace.
"""

import argparse
import base64
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import zlib

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from build_ontology import ROOT, check_outputs, expected_graph

SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/graphIndex/definition/"
NODE_COLUMNS = ["id", "kind", "display_name", "definition", "subsidiary", "metric_kind",
                "pg_label", "origin", "semantic_status", "properties_json", "rdf_annotations_json"]
EDGE_COLUMNS = ["id", "kind", "source_id", "target_id", "source_kind", "target_kind",
                "display_name", "origin", "semantic_status", "predicate_uri"]
TRIPLE_COLUMNS = ["subject", "predicate", "object", "object_kind", "datatype", "language"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_pg():
    spec = importlib.util.spec_from_file_location("fabric_pg_builder", ROOT / "department-pg/build_cypher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_combined_graph()


def project(rdf, pg):
    """Preserve PG IDs/properties and add explicitly marked RDF schema declarations."""
    metric_ids = {e["target"] for e in pg["relationships"] if e["type"] == "USES_METRIC"}
    rdf_kinds = {}
    for rdf_type, kind in [(OWL.Class, "OntologyClass"), (OWL.ObjectProperty, "ObjectProperty"),
                           (OWL.DatatypeProperty, "DataProperty"), (OWL.AnnotationProperty, "AnnotationProperty")]:
        rdf_kinds.update({str(s): kind for s in rdf.subjects(RDF.type, rdf_type)})
    nodes = {}
    for n in pg["nodes"]:
        p = n["properties"]
        kind = rdf_kinds.get(n["id"], n["label"])
        if n["id"] in metric_ids:
            kind = "Metric"
        elif p.get("concept_kind") == "department":
            kind = "Department"
        nodes[n["id"]] = dict.fromkeys(NODE_COLUMNS, "") | {
            "id": n["id"], "kind": kind, "pg_label": n["label"], "origin": "pg",
            "display_name": p.get("name") or p.get("table") or n["id"],
            "definition": p.get("definition", ""), "subsidiary": p.get("subsidiary", ""),
            "metric_kind": p.get("metric_kind", ""), "semantic_status": "metadata_only",
            "properties_json": canonical(p), "rdf_annotations_json": "[]",
        }
    for node_id, kind in sorted(rdf_kinds.items()):
        uri = URIRef(node_id)
        n = nodes.setdefault(node_id, dict.fromkeys(NODE_COLUMNS, "") | {
            "id": node_id, "kind": kind, "origin": "rdf", "properties_json": "{}",
            "semantic_status": "rdf_schema_declaration",
        })
        if n["origin"] == "pg":
            n["origin"] = "pg+rdf"
        n["display_name"] = str(rdf.value(uri, RDFS.label) or node_id.rsplit("#", 1)[-1])
        n["definition"] = str(rdf.value(uri, SKOS.definition) or rdf.value(uri, RDFS.comment) or "")
        n["rdf_annotations_json"] = canonical(sorted(
            [{"predicate": str(p), "value": str(o), "language": o.language or "",
              "datatype": str(o.datatype or "")} for p, o in rdf.predicate_objects(uri) if isinstance(o, Literal)],
            key=canonical))
    edges = []

    def add(edge_id, source, kind, target, origin, status, predicate="", name=""):
        if source not in nodes or target not in nodes:
            raise ValueError(f"Unresolved graph endpoint: {source} -> {target}")
        edges.append(dict(zip(EDGE_COLUMNS, [edge_id, kind, source, target,
            nodes[source]["kind"], nodes[target]["kind"], name or kind, origin, status, predicate])))

    for e in pg["relationships"]:
        add(e["id"], e["source"], e["type"], e["target"], "pg", "metadata_only")
    for predicate, kind in [(RDFS.subClassOf, "RDF_SUBCLASS_OF"), (RDFS.domain, "RDF_DOMAIN"),
                             (RDFS.range, "RDF_RANGE")]:
        for s, o in rdf.subject_objects(predicate):
            if str(s) in nodes and str(o) in nodes:
                add("rdf:" + canonical([str(s), str(predicate), str(o)]), str(s), kind, str(o),
                    "rdf", "rdf_schema_declaration", str(predicate))
    # Domain/range arrows are declarations, never instance-level property assertions.
    for p in sorted(rdf.subjects(RDF.type, OWL.ObjectProperty)):
        for s in rdf.objects(p, RDFS.domain):
            for o in rdf.objects(p, RDFS.range):
                add("rdf-relation:" + canonical([str(s), str(p), str(o)]), str(s),
                    "RDF_DECLARED_" + str(p).rsplit("#", 1)[-1], str(o), "rdf",
                    "domain_range_visual_projection", str(p), str(rdf.value(p, RDFS.label) or p))
    triples = [{"subject": str(s), "predicate": str(p), "object": str(o),
                "object_kind": "literal" if isinstance(o, Literal) else "uri" if isinstance(o, URIRef) else "bnode",
                "datatype": str(o.datatype or "") if isinstance(o, Literal) else "",
                "language": (o.language or "") if isinstance(o, Literal) else ""} for s, p, o in rdf]
    return {"nodes": sorted(nodes.values(), key=lambda x: x["id"]),
            "edges": sorted(edges, key=lambda x: x["id"]), "rdf_triples": sorted(triples, key=canonical)}


def graph_parts(data):
    """Use separate typed Delta tables; the published schema doesn't allow filters."""
    nodes, edges = defaultdict(list), defaultdict(list)
    for n in data["nodes"]:
        nodes[n["kind"]].append(n)
    for e in data["edges"]:
        edges[(e["kind"], e["source_kind"], e["target_kind"])].append(e)
    parts = {
        "graphType.json": {"$schema": SCHEMA_BASE + "graphType/1.0.0/schema.json", "nodeTypes": [], "edgeTypes": []},
        "graphDefinition.json": {"$schema": SCHEMA_BASE + "graphDefinition/1.0.0/schema.json", "nodeTables": [], "edgeTables": []},
        "dataSources.json": {"$schema": SCHEMA_BASE + "dataSources/1.1.0/schema.json",
            "itemReferences": [{"name": "Customer360Lakehouse", "item": {
                "workspaceId": "{{WORKSPACE_ID}}", "itemId": "{{LAKEHOUSE_ID}}"}}], "dataSources": []},
        "stylingConfiguration.json": {"$schema": SCHEMA_BASE + "stylingConfiguration/1.0.0/schema.json",
            "modelLayout": {"positions": {}, "styles": {}, "pan": {"x": 0, "y": 0}, "zoomLevel": 0.8},
            "visualFormat": {}},
    }
    tables = []
    type_part, definition = parts["graphType.json"], parts["graphDefinition.json"]

    def table(alias, rows, columns):
        suffix = ("n_" if columns == NODE_COLUMNS else "e_") + re.sub(r"[^a-z0-9_]", "_", alias.lower())
        suffix = suffix[:85] + "_" + digest(alias)[:8]
        tables.append({"suffix": suffix, "columns": columns, "rows": rows})
        parts["dataSources.json"]["dataSources"].append({"name": alias, "type": "DeltaTable",
            "properties": {"referenceName": "Customer360Lakehouse", "path": "{{TABLE_PATH:" + suffix + "}}"}})
        return {"id": alias + "_mapping", "dataSourceName": alias,
                "propertyMappings": [{"propertyName": c, "sourceColumn": c} for c in columns]}

    for index, (kind, rows) in enumerate(sorted(nodes.items())):
        alias = kind + "_node"
        type_part["nodeTypes"].append({"alias": alias, "labels": [kind], "primaryKeyProperties": ["id"],
            "properties": [{"name": c, "type": "STRING"} for c in NODE_COLUMNS]})
        definition["nodeTables"].append(table(alias, rows, NODE_COLUMNS) | {"nodeTypeAlias": alias})
        parts["stylingConfiguration.json"]["modelLayout"]["positions"][alias] = {
            "x": (index % 4) * 320, "y": (index // 4) * 220}
        parts["stylingConfiguration.json"]["visualFormat"][alias] = {
            "defaultDisplayProperty": "display_name",
            "color": {"Department": "#B45309", "Metric": "#2563EB", "SourceTable": "#059669",
                      "OntologyClass": "#7C3AED"}.get(kind, "#64748B")}
    for (kind, source, target), rows in sorted(edges.items()):
        alias = kind + "_" + source + "_" + target + "_edge"
        if len(alias) > 48:
            alias = alias[:35] + "_" + digest(alias)[:12]
        type_part["edgeTypes"].append({"alias": alias, "labels": [kind],
            "sourceNodeType": {"alias": source + "_node"}, "destinationNodeType": {"alias": target + "_node"},
            "properties": [{"name": c, "type": "STRING"} for c in EDGE_COLUMNS]})
        definition["edgeTables"].append(table(alias, rows, EDGE_COLUMNS) | {
            "edgeTypeAlias": alias, "edgeIdMapping": ["id"],
            "sourceNodeKeyColumns": ["source_id"], "destinationNodeKeyColumns": ["target_id"]})
        parts["stylingConfiguration.json"]["visualFormat"][alias] = {"defaultDisplayProperty": "display_name"}
    for suffix, columns, rows in [("audit_nodes", NODE_COLUMNS, data["nodes"]),
                                  ("audit_edges", EDGE_COLUMNS, data["edges"]),
                                  ("audit_rdf_triples", TRIPLE_COLUMNS, data["rdf_triples"])]:
        tables.append({"suffix": suffix, "columns": columns, "rows": rows})
    return parts, tables


QUERIES = {
    "01-private-securities.gql": """// 私銀優先看證券；回傳節點與邊供 Graph diagram 顯示。
MATCH (d:Department)-[r:USES_METRIC]->(m:Metric)
FILTER d.id = 'bank.private_banking' AND m.subsidiary = 'securities'
RETURN d, r, m
LIMIT 100
""",
    "02-summary-components.gql": """// 總指標與分項；HAS_COMPONENT_METRIC 不是可執行加總公式。
MATCH (d:Department)-[r:USES_METRIC]->(t:Metric)-[h:HAS_COMPONENT_METRIC]->(c:Metric)
FILTER d.id = 'bank.private_banking' AND t.subsidiary = 'securities'
RETURN d, r, t, h, c
LIMIT 100
""",
    "03-metric-sources.gql": """// 金額來源；估值與日期來源另以不同邊保留。
MATCH (m:Metric)-[r:HAS_SOURCE_TABLE]->(s:SourceTable)
FILTER m.subsidiary = 'securities'
RETURN m, r, s
LIMIT 200
""",
    "04-rdf-schema.gql": """// RDF 類別階層，屬 schema 宣告。
MATCH (c:OntologyClass)-[r:RDF_SUBCLASS_OF]->(p:OntologyClass)
RETURN c, r, p
LIMIT 200
""",
    "05-private-all-metrics.gql": """MATCH (d:Department)-[r:USES_METRIC]->(m:Metric)
FILTER d.id = 'bank.private_banking'
RETURN d, r, m
LIMIT 100
""",
    "06-valuation-and-dates.gql": """MATCH (m:Metric)-[r]->(s:SourceTable)
FILTER m.subsidiary = 'securities' AND
       (r.kind = 'USES_VALUATION_SOURCE' OR r.kind = 'USES_DATE_LOOKUP_SOURCE')
RETURN m, r, s
LIMIT 100
""",
}


def notebook(bundle):
    def cell(kind, source):
        result = {"cell_type": kind, "id": digest([kind, source])[:12],
                  "metadata": {}, "source": source.splitlines(keepends=True)}
        if kind == "code":
            result.update(execution_count=None, outputs=[])
        return result
    packed = base64.b64encode(zlib.compress(canonical(bundle).encode("utf-8"), 9)).decode("ascii")
    runtime = (ROOT / "tools/fabric_graph_runtime.py").read_text(encoding="utf-8")
    cells = [cell("markdown", "# 客戶360 RDF＋PG → Microsoft Fabric Graph\n\n"
        "只匯入目前 metadata 與 RDF schema。先把 Notebook 加入指定工作區並附加預定 Lakehouse。"
        "各表帶有版本與內容雜湊；已存在且相同的表會略過，不同則停止，不覆蓋。"
        "Graph model 建立開關預設關閉，先核對目標再執行。\n"),
        cell("code", "# 填入已選定的工作區與 Lakehouse UUID。名稱不足以驗證目標。\n"
             "WORKSPACE_ID = ''\nLAKEHOUSE_ID = ''\nCREATE_GRAPH_MODEL = False\n"),
        cell("code", runtime + "\n\nBUNDLE_B64 = " + repr(packed) + "\n"
             "bundle = decode_bundle(BUNDLE_B64)\n"
             "print(bundle['manifest']['counts'])\n"),
        cell("code", "# 此儲存格會建立獨立 Delta metadata 表；不執行原始業務 SQL。\n"
             "import notebookutils\n"
             "prepared = prepare_tables(spark, notebookutils.runtime.context, bundle, WORKSPACE_ID, LAKEHOUSE_ID)\n"
             "print('Prepared graph tables:', len(prepared['table_paths']))\n"),
        cell("code", "# 只有開關為 True 才會在指定工作區新增 Graph model；不更新既有 model。\n"
             "if CREATE_GRAPH_MODEL:\n"
             "    created = create_graph_model(notebookutils, prepared, WORKSPACE_ID)\n"
             "    print(created)\n"
             "else:\n"
             "    print('Graph model 尚未建立。核對工作區後將 CREATE_GRAPH_MODEL 設為 True，再執行此儲存格。')\n"),
        cell("markdown", "## 互動檢視\n開啟新建 Graph model，確認來源同步完成，再切換 Query。"
             "先執行以下證券檢視，結果切換 Diagram。\n\n```gql\n" + QUERIES["01-private-securities.gql"] + "```\n"
             "其他查詢在匯入包 queries 目錄。沒有計算金額，也不代表已綁定客戶實例或資料庫驗證。\n")]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Synapse PySpark",
            "language": "python", "name": "synapse_pyspark"}, "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


def build_bundle():
    check_outputs()
    config, rdf = expected_graph()
    pg = load_pg()
    data = project(rdf, pg)
    parts, tables = graph_parts(data)
    source_files = [ROOT / "build-config.json", *[ROOT / p for p in config["sources"]],
                    *[ROOT / p for p in config["outputs"].values()],
                    *sorted((ROOT / "department-pg").glob("*.json"))]
    manifest = {"version": config["version"], "projection_version": "1.0.0",
        "scope": "metadata_and_rdf_schema_only", "cloud_status": "not_deployed",
        "counts": {"pg_nodes": len(pg["nodes"]), "pg_edges": len(pg["relationships"]),
                   "rdf_triples": len(rdf), "graph_nodes": len(data["nodes"]), "graph_edges": len(data["edges"]),
                   "node_types": len(parts["graphType.json"]["nodeTypes"]),
                   "edge_types": len(parts["graphType.json"]["edgeTypes"]), "delta_tables": len(tables)},
        "source_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in source_files},
        "node_counts": dict(sorted(Counter(n["kind"] for n in data["nodes"]).items())),
        "edge_counts": dict(sorted(Counter(e["kind"] for e in data["edges"]).items()))}
    manifest["content_sha256"] = digest({"data": data, "parts": parts, "manifest": manifest})
    manifest["table_prefix"] = "c360_v" + config["version"].replace(".", "_") + "_" + manifest["content_sha256"][:8]
    return {"manifest": manifest, "data": data, "parts": parts, "tables": tables}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/fabric-v0.16.0")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / "outputs").resolve()):
        raise ValueError("Bundle must stay inside project outputs")
    bundle = build_bundle()
    out.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write("manifest.json", bundle["manifest"])
    write("fabric-bundle.json", bundle)
    for key, rows in bundle["data"].items():
        (out / (key + ".jsonl")).write_text("".join(canonical(r) + "\n" for r in rows), encoding="utf-8")
    for name, part in bundle["parts"].items():
        write("graph-model-template/" + name, part)
    for name, query in QUERIES.items():
        target = out / "queries" / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(query, encoding="utf-8")
    write("Customer360-Fabric-Import.ipynb", notebook(bundle))
    for filename in ["customer360-ontology.ttl", "customer360-ontology.owl"]:
        shutil.copyfile(ROOT / filename, out / filename)
    shutil.copyfile(ROOT / "FABRIC-GRAPH.md", out / "README.md")
    print(json.dumps(bundle["manifest"]["counts"], ensure_ascii=False, indent=2))
    print("Local bundle:", out)


if __name__ == "__main__":
    main()
