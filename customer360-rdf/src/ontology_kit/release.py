"""發佈流程：版號檢查 → 組 release 包 → 組成元件驗證 → 差異門檻 → OWL 推理 → agent context。"""

import hashlib
from importlib.metadata import version as package_version
import json

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

from . import components, context, reasoning, versioning

BUNDLE = "customer360-release.ttl"


class ReleaseError(RuntimeError):
    def __init__(self, stage, problems):
        super().__init__(f"{stage}未通過：\n- " + "\n- ".join(problems))
        self.stage, self.problems = stage, problems


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def build_bundle(cfg, previous_version, modules=None):
    """合併模組成一個本體：保留各模組標頭與成熟度，拿掉模組間的 owl:imports（已在同一包內）。"""
    released = cfg.release_modules() if modules is None else modules
    released_iris = {m.iri for m in released}
    maturity = URIRef(cfg.annotations["maturity"])
    graph = Graph()
    for layer in cfg.layers.values():
        graph.bind(layer.prefix, layer.namespace)
    graph.bind("fibo-fnd-utl-av", cfg.annotations["maturity"].rsplit("/", 1)[0] + "/")
    problems = []
    for m in released:
        source = Graph().parse(m.path, format="turtle")
        for prefix, namespace in source.namespaces():
            graph.bind(prefix, namespace, override=False)
        for target in source.objects(URIRef(m.iri), OWL.imports):
            if str(target) not in released_iris:
                problems.append(f"{m.file} 匯入了未進入 release 的模組 {target}")
        for triple in source:
            if triple[1] != OWL.imports:  # 依賴已合併在同一包內，改記在 manifest
                graph.add(triple)
        graph.add((URIRef(m.iri), maturity, URIRef(cfg.maturity_levels[m.maturity])))
    if problems:
        raise ReleaseError("模組依賴檢查", problems)
    bundle = URIRef(cfg.ontology_uri)
    graph.add((bundle, RDF.type, OWL.Ontology))
    graph.add((bundle, RDFS.label, Literal(cfg.label, lang=cfg.components["label_lang"])))
    graph.add((bundle, OWL.versionIRI, URIRef(cfg.version_iri(cfg.ontology_uri))))
    graph.add((bundle, OWL.versionInfo, Literal(f"{cfg.version} / {cfg.status} / {cfg.date}")))
    if previous_version and previous_version != cfg.version:
        graph.add((bundle, OWL.priorVersion, URIRef(cfg.version_iri(cfg.ontology_uri, previous_version))))
    for m in released:
        graph.add((bundle, DCTERMS.hasPart, URIRef(m.iri)))
    return graph


def run(cfg, force=False, write=True):
    problems = [f"{t['file']} {t['field']}：{t['found']} ≠ {t['expected']}" for t in versioning.check(cfg)]
    if problems:
        raise ReleaseError("版號一致性", problems)

    graph, classes, properties, issues = components.build(cfg, cfg.release_modules())
    errors = [f"{i['id']} [{i['rule']}] {i['message']}" for i in issues if i["level"] == "error"]
    if errors:
        raise ReleaseError("類別組成元件驗證", errors)
    excluded = {m.file for m in cfg.modules} - {m.file for m in cfg.release_modules()}

    previous = versioning.load_previous(cfg)
    change = versioning.diff(cfg, previous, classes, properties)
    if change["gate"]:
        raise ReleaseError("版本門檻", change["gate"])

    bundle = build_bundle(cfg, previous[0] if previous else None)
    bundle_bytes = bundle.serialize(format="turtle", encoding="utf-8")
    report = reasoning.reason(Graph().parse(data=bundle_bytes, format="turtle"), cfg)
    if report["cycles"] or report["unsatisfiable"]:
        raise ReleaseError("推理檢查", [f"循環 {report['cycles']}", f"不可滿足 {report['unsatisfiable']}"])

    labels = {c["uri"]: c["label"] for c in classes}
    meta = {"bundle_sha256": sha256(bundle_bytes),
            "previous_version": previous[0] if previous else None}
    pack = context.build(cfg, classes, properties, report, meta)

    def as_json(value):
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    files = {
        BUNDLE: bundle_bytes,
        "class-components.json": as_json({"version": cfg.version, "classes": classes,
                                          "properties": properties, "issues": issues}),
        "class-components.md": components.render_markdown(cfg, classes, properties, issues, cfg.version).encode(),
        "reasoning.json": as_json(report),
        "reasoning.md": reasoning.render_markdown(cfg, report, labels).encode(),
        "agent-context.json": as_json(pack),
        "agent-context.md": context.render_markdown(pack).encode(),
        "changes.json": as_json(change),
        "CHANGELOG.md": versioning.render_changelog(cfg, change).encode(),
    }
    manifest = {
        "version": cfg.version, "date": cfg.date, "status": cfg.status,
        "release_iri": cfg.version_iri(cfg.ontology_uri),
        "previous": change["previous"],
        "modules": [{"file": m.file, "iri": m.iri, "layer": m.layer, "maturity": m.maturity,
                     "sha256": sha256(m.path.read_bytes()),
                     "imports": sorted(str(t) for t in Graph().parse(m.path, format="turtle")
                                       .objects(URIRef(m.iri), OWL.imports))}
                    for m in cfg.release_modules()],
        "excluded_modules": sorted(excluded),
        "tools": {"rdflib": package_version("rdflib"), "owlrl": package_version("owlrl")},
        "files": {name: sha256(data) for name, data in sorted(files.items())},
    }
    files["manifest.json"] = as_json(manifest)

    out = cfg.release_dir()
    status = "created"
    if out.exists():
        existing = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
        if existing == files:
            status = "unchanged"
        elif not force:
            raise ReleaseError("發佈", [f"{out} 已存在且內容不同。已發佈的版本不可覆寫；請先升版，或確認後加 --force"])
        else:
            status = "overwritten"
    if write and status != "unchanged":
        out.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (out / name).write_bytes(data)
        (cfg.path_of("release_dir") / "LATEST").write_text(cfg.version + "\n", encoding="utf-8")
    return {"status": status, "dir": str(out), "classes": len(classes), "properties": len(properties),
            "entailed_pairs": report["entailed_pairs"], "inferred_only": report["inferred_only"],
            "changes": len(change["changes"]), "required_bump": change["required"],
            "warnings": [f"{i['id']} [{i['rule']}] {i['message']}" for i in issues if i["level"] == "warning"],
            "files": sorted(files)}
