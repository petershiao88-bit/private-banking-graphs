"""把推理結果發佈成 agent 可直接放進 prompt 的 CoT context（Markdown＋JSON）。"""


def build(cfg, classes, properties, report, meta):
    by_uri = {c["uri"]: c for c in classes}
    props = {p["uri"]: p for p in properties}
    labels = {**{p["uri"]: p["label"] for p in properties}, **{c["uri"]: c["label"] for c in classes}}
    children = {c["uri"]: [] for c in classes}
    for c in classes:
        for parent in c["parents"]:
            children.setdefault(parent, []).append(c["uri"])

    def ref(uri):
        return {"id": cfg.curie(uri), "label": labels.get(uri, cfg.curie(uri))}

    def prop_view(uri, inherited_from=None):
        p = props[uri]
        view = {"id": p["id"], "label": p["label"], "kind": p["kind"],
                "range": [ref(r) for r in p["range"]], "definition": p["definition"]}
        if inherited_from:
            view["inherited_from"] = ref(inherited_from)
        return view

    items = []
    for c in classes:
        ancestor_uris = [a["uri"] for a in report["ancestors"][c["uri"]]]
        inferred = [e["ancestor"] for e in report["entailments"] if e["class"] == c["uri"] and not e["asserted"]]
        chains = []
        for e in report["entailments"]:
            if e["class"] == c["uri"] and not any(x["class"] == e["ancestor"] for x in report["entailments"]):
                chains.append(" ⊑ ".join(labels[u] for u in e["path"]))  # 只列到頂層類別的完整鏈
        inherited = [prop_view(p["uri"], a) for a in ancestor_uris for p in properties if a in p["domain"]]
        items.append({
            "id": c["id"], "uri": c["uri"], "label": c["label"], "definition": c["definition"],
            "layer": c["layer"], "governance_level": c["governance_level"], "subsidiary": c["subsidiary"],
            "module": c["module"], "maturity": c["maturity"],
            "deprecated": c["deprecated"], "replaced_by": [ref(u) for u in c["replaced_by"]],
            "direct_parents": [ref(u) for u in c["parents"]],
            "ancestors": [ref(u) for u in ancestor_uris],
            "inferred_ancestors": [ref(u) for u in inferred],
            "chains": sorted(chains),
            "children": [ref(u) for u in sorted(children.get(c["uri"], []))],
            "properties": [prop_view(u) for u in c["properties"]],
            "inherited_properties": inherited,
        })
    return {
        "ontology": cfg.label, "version": cfg.version, "date": cfg.date, "status": cfg.status,
        "release_iri": cfg.version_iri(cfg.ontology_uri), **meta,
        "engine": report["engine"],
        "usage_rules": cfg.context["usage_rules"],
        "reasoning_steps": cfg.context["reasoning_steps"],
        "layers": [{"key": key, "title": layer.title, "prefix": layer.prefix,
                    "governance_level": layer.governance_level, "subsidiary": layer.subsidiary,
                    "classes": [i["id"] for i in items if i["layer"] == key]}
                   for key, layer in cfg.layers.items()],
        "classes": items,
    }


def render_markdown(pack):
    lines = [f"# {pack['ontology']}：agent context（v{pack['version']}）", "",
             f"本體版本 `{pack['release_iri']}`（{pack['status']}，{pack['date']}）。"
             f"release 包 SHA-256 `{pack['bundle_sha256'][:16]}`；推理引擎 {pack['engine']}。", "",
             "## 使用規則", ""]
    lines += [f"{i}. {rule}" for i, rule in enumerate(pack["usage_rules"], 1)]
    lines += ["", "## 推理步驟", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(pack["reasoning_steps"], 1)]
    for layer in pack["layers"]:
        members = [c for c in pack["classes"] if c["layer"] == layer["key"]]
        if not members:
            continue
        lines += ["", f"## {layer['title']}（`{layer['prefix']}:`）", ""]
        for c in members:
            flags = [c["maturity"]] + (["deprecated"] if c["deprecated"] else [])
            lines += [f"### {c['label']} `{c['id']}`（{'、'.join(flags)}）", "", f"- 定義：{c['definition']}"]
            if c["replaced_by"]:
                lines.append("- 改用：" + "、".join(f"{r['label']} `{r['id']}`" for r in c["replaced_by"]))
            if c["chains"]:
                inferred = {r["id"] for r in c["inferred_ancestors"]}
                note = "（含推理）" if inferred else ""
                lines.append(f"- 上層鏈{note}：" + "；".join(c["chains"]))
            else:
                lines.append("- 上層鏈：無（頂層類別）")
            if c["children"]:
                lines.append("- 直接子類：" + "、".join(f"{r['label']} `{r['id']}`" for r in c["children"]))
            props = [f"{p['label']} `{p['id']}` → {'、'.join(r['label'] for r in p['range'])}" for p in c["properties"]]
            props += [f"{p['label']} `{p['id']}` → {'、'.join(r['label'] for r in p['range'])}"
                      f"（繼承自{p['inherited_from']['label']}）" for p in c["inherited_properties"]]
            if props:
                lines.append("- 可用屬性：" + "；".join(props))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
