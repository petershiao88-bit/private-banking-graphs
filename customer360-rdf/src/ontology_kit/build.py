"""建置合併本體：把 config 列出的全部模組合成 build/ 下的 Turtle 與 RDF/XML（勿手改產物）。"""

from rdflib import Graph
from rdflib.compare import isomorphic

from . import versioning
from .release import build_bundle


class StaleBuild(ValueError):
    pass


def expected_graph(cfg):
    for m in cfg.modules:
        if not m.path.is_relative_to(cfg.root):
            raise ValueError(f"模組必須在專案內：{m.file}")
    previous = versioning.load_previous(cfg)
    return build_bundle(cfg, previous[0] if previous else None, modules=cfg.modules)


def outputs(cfg):
    return {"turtle": cfg.path_of("build_turtle"), "xml": cfg.path_of("build_xml")}


def check(cfg):
    expected = expected_graph(cfg)
    for kind, path in outputs(cfg).items():
        if not path.is_file() or not isomorphic(Graph().parse(path, format=kind), expected):
            raise StaleBuild(f"{versioning.display(cfg, path)} 與來源模組不一致，請執行 python -m ontology_kit build")
    return {"result": "PASS", "version": cfg.version, "modules": len(cfg.modules), "triples": len(expected)}


def build(cfg):
    graph = expected_graph(cfg)
    payloads = {}
    for kind, path in outputs(cfg).items():
        payload = graph.serialize(format=kind, encoding="utf-8")
        if not isomorphic(graph, Graph().parse(data=payload, format=kind)):
            raise ValueError(f"序列化後內容不一致：{kind}")
        payloads[path] = payload
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return check(cfg)
