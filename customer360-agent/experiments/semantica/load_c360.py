"""把 customer360 本體（c360-ontology.json）轉成 Semantica 的兩種圖格式。

- build_context_graph()：官方文件主推的 ContextGraph 物件（AgentContext 的 knowledge_graph）。
- build_kg_dict()：{"entities", "relationships"} 字典格式（ContextGraph.to_kg_dict() 的輸出形狀）。

節點：類別（Class）、PG 指標（Metric）、業務詞條（Term）。
邊：subClassOf（子→父）、物件屬性（domain→range，型別＝屬性標籤）、
     指標 instance_of 類別、指標 about_product 商品類別、指標 has_component 分項、詞條 maps_to 類別。
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "c360-ontology.json").read_text(encoding="utf-8"))


def _nodes_edges():
    nodes, edges = [], []
    for c in DATA["classes"]:
        nodes.append({"id": c["id"], "type": "Class", "name": c["label"],
                      "content": f'{c["label"]}（{c["id"]}）：{c["definition"]}',
                      "layer": c["layer"], "description": c["definition"]})
        for p in c["parents"]:
            edges.append({"source": c["id"], "target": p, "type": "subClassOf"})
    for m in DATA["metrics"]:
        nodes.append({"id": m["id"], "type": "Metric", "name": m["name"],
                      "content": f'{m["name"]}（{m["id"]}）：{m["definition"]}',
                      "subsidiary": m["subsidiary"], "description": m["definition"]})
        edges.append({"source": m["id"], "target": m["class_id"], "type": "instance_of"})
        for p in m["product_ids"]:
            edges.append({"source": m["id"], "target": p, "type": "about_product"})
        for comp in m["components"]:
            edges.append({"source": m["id"], "target": comp, "type": "has_component"})
    for t in DATA["terms"]:
        nodes.append({"id": "term:" + t["id"], "type": "Term", "name": t["name"],
                      "content": f'{t["name"]}：{t["definition"]}', "description": t["definition"]})
        for mp in t["mappings"]:
            edges.append({"source": "term:" + t["id"], "target": mp["class"], "type": "maps_to_" + mp["role"]})
    for p in DATA["object_properties"]:
        for d in p["domain"]:
            for r in p["range"]:
                edges.append({"source": d, "target": r, "type": p["label"]})
    ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in ids and e["target"] in ids]
    return nodes, edges


def build_context_graph():
    from semantica.context import ContextGraph

    graph = ContextGraph()
    nodes, edges = _nodes_edges()
    for n in nodes:
        props = {k: v for k, v in n.items() if k not in ("id", "type", "content")}
        graph.add_node(n["id"], n["type"], content=n["content"], **props)
    for e in edges:
        graph.add_edge(e["source"], e["target"], edge_type=e["type"])
    return graph


def build_kg_dict():
    nodes, edges = _nodes_edges()
    entities = [{"id": n["id"], "name": n["name"], "type": n["type"], "text": n["name"],
                 "metadata": {"description": n["description"]}} for n in nodes]
    return {"entities": entities, "relationships": edges}


if __name__ == "__main__":
    nodes, edges = _nodes_edges()
    print(len(nodes), "nodes,", len(edges), "edges; version", DATA["version"])
