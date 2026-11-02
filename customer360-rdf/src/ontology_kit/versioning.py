"""版本控制：版號一致性、升版、與前一版的差異和發佈門檻（參考 FIBO 的成熟度與下架規則）。"""

import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF

from . import components

LEVELS = ("none", "patch", "minor", "major")
# module：類別或屬性換了宣告所在的模組（FIBO 式重整），內容不變，屬 minor。
CLASS_IMPACT = {"label": "patch", "definition": "patch", "parents": "major", "governance_level": "major",
                "subsidiary": "major", "layer": "major", "deprecated": "minor", "replaced_by": "minor",
                "module": "minor"}
PROPERTY_IMPACT = {"label": "patch", "definition": "patch", "kind": "major", "domain": "major", "range": "major",
                   "governance_level": "major", "deprecated": "minor", "replaced_by": "minor", "module": "minor"}


def parse(version):
    return tuple(int(x) for x in version.split("."))


def bump_level(old, new):
    a, b = parse(old), parse(new)
    if b < a:
        return "downgrade"
    if b == a:
        return "none"
    return "major" if b[0] > a[0] else "minor" if b[1] > a[1] else "patch"


def display(cfg, path):
    """輸出不寫機器絕對路徑：專案內用相對路徑，專案外只留資料夾名。"""
    path = Path(path).resolve()
    return path.relative_to(cfg.root).as_posix() if path.is_relative_to(cfg.root) else path.name


# ---------- 版號一致性 ----------

def catalog_entries(cfg):
    return {e.attrib["name"]: e.attrib["uri"] for e in ET.parse(cfg.path_of("catalog")).getroot()}


def catalog_path(cfg, path):
    """模組檔相對於 catalog 所在資料夾的路徑（catalog 的 uri 欄位寫法）。"""
    return Path(os.path.relpath(path, cfg.path_of("catalog").parent)).as_posix()


def touchpoints(cfg):
    """所有帶版號或成熟度的位置。回傳 [{file, field, found, expected, ok}]。"""
    out = []
    maturity = URIRef(cfg.annotations["maturity"])

    def add(path, field, found, expected):
        out.append({"file": display(cfg, path), "field": field,
                    "found": found, "expected": expected, "ok": found == expected})

    for m in cfg.modules:
        graph = Graph().parse(m.path, format="turtle")
        iri = URIRef(m.iri)
        add(m.path, "owl:Ontology", str((iri, RDF.type, OWL.Ontology) in graph), "True")
        add(m.path, "owl:versionIRI", str(graph.value(iri, OWL.versionIRI)), cfg.version_iri(m.iri))
        add(m.path, "owl:versionInfo", str(graph.value(iri, OWL.versionInfo) or ""),
            f"{cfg.version} / {cfg.status} / {cfg.date}")
        add(m.path, "hasMaturityLevel", str(graph.value(iri, maturity)), cfg.maturity_levels[m.maturity])
        header = m.path.read_text(encoding="utf-8").splitlines()[0]
        found = re.search(r"v(\d+\.\d+\.\d+)", header)
        add(m.path, "首行註解版號", found.group(1) if found else None, cfg.version)

    catalog = catalog_entries(cfg)
    for m in cfg.modules:
        add(cfg.path_of("catalog"), f"catalog {m.iri}", catalog.get(m.iri), catalog_path(cfg, m.path))
        versioned = [name for name in catalog if name.startswith(m.iri + "/")]
        add(cfg.path_of("catalog"), f"catalog {m.iri}/<版號>",
            ",".join(name.rsplit("/", 1)[1] for name in versioned), cfg.version)
    bundle_versioned = [n for n in catalog if n.startswith(cfg.ontology_uri + "/")]
    add(cfg.path_of("catalog"), f"catalog {cfg.ontology_uri}/<版號>",
        ",".join(n.rsplit("/", 1)[1] for n in bundle_versioned), cfg.version)
    known = {m.iri for m in cfg.modules} | {cfg.ontology_uri}
    stray = sorted(n for n in catalog if n not in known and n.rsplit("/", 1)[0] not in known)
    add(cfg.path_of("catalog"), "未在 config 的 catalog 項目", ",".join(stray) or None, None)

    for path in sorted(cfg.path_of("pg_models").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("ontology_version"), str):
            add(path, "ontology_version", data["ontology_version"], cfg.version)
    for path in cfg.literal_files():
        if path.suffix == ".json":
            text = path.read_text(encoding="utf-8")
            add(path, "版號字面值", cfg.version if f'"{cfg.version}"' in text else None, cfg.version)
    return out


def check(cfg):
    return [t for t in touchpoints(cfg) if not t["ok"]]


def scan_literals(cfg, version):
    """除 TTL／catalog／config／PG JSON 之外，仍寫著某個版號的位置（警告用）。"""
    managed = {m.path for m in cfg.modules} | {cfg.path_of("catalog"), cfg.path}
    managed |= set(cfg.path_of("pg_models").glob("*.json"))
    managed |= {cfg.path_of("build_turtle"), cfg.path_of("build_xml")}  # 由 ontology_kit build 重新產生
    hits = []
    pattern = re.compile(re.escape(version) + r"(?!\d)")
    for path in cfg.scan_files():
        if path in managed:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{display(cfg, path)}:{number}")
    return hits


# ---------- 升版 ----------

def _read(path):
    """保留原檔換行（CRLF／LF）；PG 檔有逐位元組比對的保存性測試。"""
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def plan_bump(cfg, new_version, new_date):
    old, old_date = cfg.version, cfg.date
    if bump_level(old, new_version) in ("none", "downgrade"):
        raise ValueError(f"新版號 {new_version} 必須大於目前的 {old}")
    edits = {}

    def edit(path, transform):
        text = edits.get(path, _read(path))
        new = transform(text)
        if new == text:
            raise ValueError(f"{display(cfg, path)} 找不到要替換的版號")
        edits[path] = new

    for m in cfg.modules:
        def ttl(text, m=m):
            text = text.replace(f"<{m.iri}/{old}>", f"<{m.iri}/{new_version}>")
            text = text.replace(f'"{old} / {cfg.status} / {old_date}"', f'"{new_version} / {cfg.status} / {new_date}"')
            first, _, rest = text.partition("\n")
            return first.replace(f"v{old}", f"v{new_version}").replace(old_date, new_date) + "\n" + rest
        edit(m.path, ttl)
    edit(cfg.path_of("catalog"), lambda t: t.replace(f'/{old}"', f'/{new_version}"'))

    for path in sorted(cfg.path_of("pg_models").glob("*.json")):
        text = _read(path)
        if re.search(r'"ontology_version"\s*:\s*"' + re.escape(old) + '"', text):
            edit(path, lambda t: re.sub(r'("ontology_version"\s*:\s*")' + re.escape(old) + '"',
                                        lambda m: m.group(1) + new_version + '"', t))
    for path in cfg.literal_files():
        text = edits.get(path, _read(path))
        if f'"{old}"' in text or f"'{old}'" in text:
            edit(path, lambda t: t.replace(f'"{old}"', f'"{new_version}"').replace(f"'{old}'", f"'{new_version}'"))

    def config_yaml(text):
        text = re.sub(r'(?m)^(\s*version:\s*)[\'"]?' + re.escape(old) + r'[\'"]?[ \t]*(\r?)$', rf'\g<1>"{new_version}"\g<2>', text, count=1)
        text = re.sub(r'(?m)^(\s*date:\s*)[\'"]?' + re.escape(old_date) + r'[\'"]?[ \t]*(\r?)$', rf'\g<1>"{new_date}"\g<2>', text, count=1)
        if cfg.release_dir(old).is_dir():
            relative = Path(os.path.relpath(cfg.release_dir(old), cfg.base)).as_posix()
            text = re.sub(r"(?m)^(\s*previous_release:)[^\r\n]*", rf"\g<1> {relative}", text, count=1)
        return text
    edit(cfg.path, config_yaml)
    return edits


def apply_edits(edits):
    for path, text in edits.items():
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)


# ---------- 差異與發佈門檻 ----------

def load_previous(cfg):
    """回傳 (版號, 類別 records, 屬性 records, 說明) 或 None。"""
    previous = cfg.path_of("previous_release")
    if previous and (previous / "class-components.json").is_file():
        data = json.loads((previous / "class-components.json").read_text(encoding="utf-8"))
        return data["version"], data["classes"], data["properties"], f"release {previous.name}"
    if previous:
        raise FileNotFoundError(f"previous_release 找不到 class-components.json：{previous}")
    base = cfg.path_of("baseline_sources")
    if base and (base / "build-config.json").is_file():
        build_config = json.loads((base / "build-config.json").read_text(encoding="utf-8"))
        entries = [(name, base / name, None) for name in build_config["sources"]]
        graph, owner = components.load_modules(entries)
        classes, properties = components.extract(graph, owner, cfg)
        return build_config["version"], classes, properties, f"快照 {display(cfg, base)}"
    return None


def _compare(before, after, impact, kind):
    changes = []
    old, new = {r["uri"]: r for r in before}, {r["uri"]: r for r in after}
    for uri in sorted(new.keys() - old.keys()):
        changes.append({"kind": kind, "change": "added", "id": new[uri]["id"], "uri": uri,
                        "label": new[uri]["label"], "impact": "minor"})
    for uri in sorted(old.keys() - new.keys()):
        changes.append({"kind": kind, "change": "removed", "id": old[uri]["id"], "uri": uri,
                        "label": old[uri]["label"], "impact": "major",
                        "was_deprecated": bool(old[uri].get("deprecated"))})
    for uri in sorted(old.keys() & new.keys()):
        fields = {f: {"before": old[uri].get(f), "after": new[uri].get(f)}
                  for f in impact if old[uri].get(f) != new[uri].get(f)}
        if fields:
            level = max((impact[f] for f in fields), key=LEVELS.index)
            changes.append({"kind": kind, "change": "modified", "id": new[uri]["id"], "uri": uri,
                            "label": new[uri]["label"], "fields": fields, "impact": level})
    return changes


def diff(cfg, previous, classes, properties):
    if previous is None:
        return {"previous": None, "changes": [], "required": "none", "actual": None, "gate": []}
    prev_version, prev_classes, prev_properties, source = previous
    changes = _compare(prev_classes, classes, CLASS_IMPACT, "class") + \
        _compare(prev_properties, properties, PROPERTY_IMPACT, "property")
    required = max((c["impact"] for c in changes), key=LEVELS.index, default="none")
    actual = bump_level(prev_version, cfg.version)
    gate = []
    if actual == "downgrade":
        gate.append(f"版號 {cfg.version} 小於前一版 {prev_version}")
    if changes and actual == "none":
        gate.append("本體有變更但版號未升")
    effective = "minor" if required == "major" and parse(cfg.version)[0] == 0 else required  # 0.x：破壞性變更升 minor 即可
    if actual != "downgrade" and LEVELS.index(actual) < LEVELS.index(effective):
        gate.append(f"變更需要至少 {effective} 升版，實際為 {actual}")
    if cfg.release["require_deprecation_before_removal"]:
        for c in changes:
            if c["change"] == "removed" and not c["was_deprecated"]:
                gate.append(f"{c['id']} 在前一版未標 owl:deprecated 就被移除")
    return {"previous": {"version": prev_version, "source": source}, "changes": changes,
            "required": required, "actual": actual, "gate": gate}


def render_changelog(cfg, result):
    lines = [f"# CHANGELOG v{cfg.version}（{cfg.date}）", ""]
    if result["previous"] is None:
        return "\n".join(lines + ["沒有可比對的前一版。", ""])
    prev = result["previous"]
    lines += [f"比對基準：v{prev['version']}（{prev['source']}）。",
              f"變更需要的升版等級：**{result['required']}**；實際升版：**{result['actual']}**。", ""]
    if result["gate"]:
        lines += ["## 發佈門檻未通過", ""] + [f"- {g}" for g in result["gate"]] + [""]
    else:
        lines += ["發佈門檻：通過。", ""]
    names = {"class": "類別", "property": "屬性"}
    for change, title in (("added", "新增"), ("removed", "移除")):
        items = [c for c in result["changes"] if c["change"] == change]
        if items:
            lines += [f"## {title}", ""]
            lines += [f"- {names[c['kind']]} `{c['id']}` {c['label'] or ''}（影響：{c['impact']}）" for c in items]
            lines.append("")
    modified = [c for c in result["changes"] if c["change"] == "modified"]
    moves = {}
    for c in modified:
        if "module" in c["fields"]:
            key = (c["fields"]["module"]["before"], c["fields"]["module"]["after"])
            moves.setdefault(key, []).append(c["id"])
    if moves:
        lines += ["## 模組重整（定義不變，只換宣告所在的模組）", "", "| 原模組 | 新模組 | 類別／屬性 |", "|---|---|---|"]
        lines += [f"| {old} | {new} | {'、'.join(f'`{i}`' for i in ids)} |" for (old, new), ids in sorted(moves.items())]
        lines.append("")
    rows = [(c, field, values) for c in modified for field, values in c["fields"].items() if field != "module"]
    if rows:
        lines += ["## 內容修改", "", "| 種類 | ID | 欄位 | 之前 | 之後 | 影響 |", "|---|---|---|---|---|---|"]
        for c, field, values in rows:
            before = json.dumps(values["before"], ensure_ascii=False).replace("|", "／")
            after = json.dumps(values["after"], ensure_ascii=False).replace("|", "／")
            lines.append(f"| {names[c['kind']]} | `{c['id']}` | {field} | {before} | {after} | {c['impact']} |")
        lines.append("")
    if not result["changes"]:
        lines += ["本體內容與前一版相同。", ""]
    return "\n".join(lines)
