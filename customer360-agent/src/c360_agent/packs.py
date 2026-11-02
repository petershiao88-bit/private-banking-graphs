"""角色 context 包：把知識層整理成可直接放進 system prompt 的 Markdown（＋同內容的 JSON）。

- 權限在這裡就套用：角色看不到的指標與詞條整條不出現，而不是寫「不可看」請模型遵守。
- `baseline` 包模擬「只有寬表資料字典」的 agent：全部指標平鋪，沒有類別階層、權限、待定範圍與規則。
"""

import hashlib
import json
import re

from .knowledge import KIND_LABELS, SUBSIDIARY_LABELS, TABLE_ROLE_LABELS, Knowledge

AGENT_RULES = [
    "指標只能用「指標清單」裡的 ID。清單沒有的指標，回答「目前可用範圍內沒有這項指標」，不要猜測，也不要改用名稱相近的指標代替。",
    "銀行與證券有同名商品（基金、債券、股票、結構型、海外）。問題沒有指明子公司，而兩邊都有對應指標時，先澄清；若使用者要的是全部，就兩邊並列並分開說明。",
    "標 Σ 的是總指標，只涵蓋列出的分項；總指標與其分項不可再一起加總，也不可把分項自行相加當成總指標。",
    "問題落在「待定範圍」時，說明目前尚未定義，不可用相近指標代替。",
    "「不包含／不屬於／排除」這類條件要依類別階層判斷：不在上層鏈上的才可視為排除。",
]

ROLE_NOTE = "權限已套用：本文件只列出「{label}」可用的指標與詞條。不在清單中的項目，一律視為目前不可用。"


def estimate_tokens(text):
    """粗估 token 數（中文約 1.4 字／token，其餘約 3.5 字元／token）。精確值請用 `ping --tokenize`。"""
    cjk = len(re.findall(r"[　-〿㐀-鿿＀-￯]", text))
    return int(cjk / 1.4 + (len(text) - cjk) / 3.5)


def build(kb: Knowledge, role, level="compact", skeleton=False):
    """回傳 {"role", "level", "markdown", "data", "sha256", "tokens_est"}。

    skeleton=True 只留規則、推理步驟、類別階層與關係（不含指標清單、待定範圍與詞條），給工具模式用：
    指標細節要靠工具查。
    """
    if role == "baseline":
        return _baseline(kb, level)
    kb._check_role(role)
    label = kb.roles[role]
    metrics = kb.visible_metrics(role)
    visible_ids = {m.id for m in metrics}
    hidden = sorted(set(kb.metrics) - visible_ids)
    terms = [t for t in kb.terms.values() if t["mappings"]
             and kb.studio.evaluator.for_term(t["raw"], role)["effect"] not in ("deny", "unmapped")]
    gaps = list(kb.gaps)
    rules = list(kb.cfg.context["usage_rules"]) + AGENT_RULES
    steps = list(kb.cfg.context["reasoning_steps"])

    md = [f"# {kb.cfg.label}：agent context｜角色 {label}（`{role}`）", "",
          _version_line(kb), ROLE_NOTE.format(label=label), "", "## 使用規則", ""]
    md += [f"{i}. {r}" for i, r in enumerate(rules, 1)]
    md += ["", "## 推理步驟", ""] + [f"{i}. {s}" for i, s in enumerate(steps, 1)]
    md += ["", "## 類別階層", "",
           "縮排代表 rdfs:subClassOf（是一種）。OWL 推理已確認：上層的上層也成立，例如銀行手收指標 ⊑ 手收指標 ⊑ 指標。", ""]
    md += _class_tree(kb, level)
    md += ["", "## 關係屬性", ""]
    md += _relations(kb, level)
    if skeleton:
        markdown = "\n".join(md) + "\n"
        data = {"role": role, "role_label": label, "level": "skeleton", "ontology_version": kb.version,
                "release": kb.release, "knowledge_fingerprint": kb.fingerprint(), "usage_rules": rules,
                "reasoning_steps": steps, "metrics": []}
        return _finish(role, "skeleton", markdown, data)
    md += ["", f"## 指標清單（{len(metrics)} 項）", "",
           "類別欄是指標所屬的本體類別；商品欄是指標衡量或收入來源的商品類別。底表只到表級，欄位與計算口徑由工具承接。", ""]
    md += _metric_tables(kb, metrics, level)
    if gaps:
        md += ["", "## 待定範圍（尚未定義，不可用相近指標代替）", ""]
        md += [f"- `{g['id']}`：{g['reason']}" for g in gaps]
    if terms:
        md += ["", "## 其他業務詞條（對應到類別，非指標）", ""]
        md += [f"- {t['name']} `{t['id']}` → " + "＋".join(f"{kb.label(m['class'])} `{m['class']}`" for m in t["mappings"])
               for t in sorted(terms, key=lambda t: t["id"])]
    markdown = "\n".join(md) + "\n"
    data = {"role": role, "role_label": label, "level": level, "ontology_version": kb.version,
            "release": kb.release, "knowledge_fingerprint": kb.fingerprint(),
            "usage_rules": rules, "reasoning_steps": steps,
            "classes": [kb.class_card(c) for c in sorted(kb.classes)],
            "metrics": [kb.metric_card(m.id, level) for m in metrics],
            "hidden_metric_count": len(hidden),
            "gaps": gaps, "terms": [{k: t[k] for k in ("id", "name", "definition", "mappings")} for t in terms]}
    return _finish(role, level, markdown, data)


def _baseline(kb, level):
    """對照組：寬表 agent 常見的平鋪資料字典。"""
    md = [f"# 私銀指標資料字典（{len(kb.metrics)} 項）", "",
          "每列一項指標：ID、名稱、定義、來源底表。", "",
          "| ID | 名稱 | 定義 | 來源底表 |", "|---|---|---|---|"]
    for m in sorted(kb.metrics.values(), key=lambda m: m.id):
        tables = "、".join(t["table"] for t in m.tables if t["role"] == "primary")
        md.append(f"| `{m.id}` | {m.name} | {_cell(m.definition)} | {tables} |")
    markdown = "\n".join(md) + "\n"
    data = {"role": "baseline", "level": level, "ontology_version": kb.version,
            "metrics": [{"id": m.id, "name": m.name, "definition": m.definition,
                         "tables": [t["table"] for t in m.tables if t["role"] == "primary"]}
                        for m in sorted(kb.metrics.values(), key=lambda m: m.id)]}
    return _finish("baseline", level, markdown, data)


def _finish(role, level, markdown, data):
    sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    data["sha256"] = sha
    return {"role": role, "level": level, "markdown": markdown, "data": data, "sha256": sha,
            "tokens_est": estimate_tokens(markdown), "chars": len(markdown)}


def _version_line(kb):
    rel = kb.release
    if rel["matches_release"]:
        state = f"與已發佈 release 一致（bundle `{(rel['bundle_sha256'] or '')[:12]}`）"
    elif rel["released"]:
        state = "工作版本：與已發佈的同版號 release 不一致，結果不可引用為正式版本"
    else:
        state = "工作版本：此版號尚未發佈"
    return (f"本體 `{rel['release_iri']}`（{kb.status}，{kb.date}），{state}。"
            f"知識指紋 `{kb.fingerprint()[:12]}`。")


def _class_tree(kb, level):
    lines = []

    def walk(cid, depth):
        c = kb.classes[cid]
        flags = []
        if c["deprecated"]:
            flags.append("deprecated，改用 " + "、".join(c["replaced_by"]))
        name = c["label"]
        if c["subsidiary"] and c["subsidiary"] not in name:
            name += f"（{c['subsidiary']}）"
        text = f"{'  ' * depth}- {name} `{cid}`"
        if flags:
            text += "（" + "；".join(flags) + "）"
        if level == "full" and c["definition"]:
            text += f"：{c['definition']}"
        lines.append(text)
        for child in sorted(c["children"], key=lambda x: (kb.classes[x]["layer"] != "holding", x)):
            walk(child, depth + 1)

    roots = sorted(cid for cid, c in kb.classes.items() if not c["parents"])
    for root in roots:
        walk(root, 0)
    return lines


def _relations(kb, level):
    lines = []
    objects = [p for p in kb.properties.values() if p["kind"] == "object"]
    for p in sorted(objects, key=lambda p: p["id"]):
        domains = "、".join(f"{kb.label(d)} `{d}`" for d in p["domain"])
        ranges = "、".join(f"{kb.label(r)} `{r}`" for r in p["range"])
        line = f"- {domains} —{p['label']} `{p['id']}`→ {ranges}"
        if level == "full" and p["definition"]:
            line += f"：{p['definition']}"
        lines.append(line)
    datatype = {}
    for p in kb.properties.values():
        if p["kind"] == "datatype":
            for d in p["domain"]:
                datatype.setdefault(d, []).append(p)
    lines += ["", "資料屬性（欄位概念，子類別會繼承）：", ""]
    for d in sorted(datatype):
        items = "、".join(f"{p['label']} `{p['id']}`" for p in sorted(datatype[d], key=lambda p: p["id"]))
        lines.append(f"- {kb.label(d)} `{d}`：{items}")
    return lines


def _metric_tables(kb, metrics, level):
    lines = []
    groups = {}
    for m in metrics:
        groups.setdefault((m.subsidiary, m.kind), []).append(m)
    order = {"bank": 0, "securities": 1}
    kinds = {"aum": 0, "lum": 1, "fee": 2, "interest": 3}
    for (sub, kind) in sorted(groups, key=lambda g: (order.get(g[0], 9), kinds.get(g[1], 9))):
        lines += [f"### {SUBSIDIARY_LABELS.get(sub, sub)}｜{KIND_LABELS.get(kind, kind)}", ""]
        header = "| ID | 名稱 | 類別 | 商品 | 底表 |"
        if level == "full":
            header = "| ID | 名稱 | 類別 | 商品 | 定義 | 底表 |"
        lines += [header, "|" + "---|" * header.count(" | ") + "---|"]
        for m in sorted(groups[(sub, kind)], key=lambda m: (bool(m.components), m.id)):
            name = ("Σ " if m.components else "") + m.name
            products = "＋".join(f"`{p}`" for p in m.product_ids) or "—"
            if m.components:
                products = "分項：" + "、".join(f"`{c}`" for c in m.components)
            tables = _tables(m, level)
            cells = [f"`{m.id}`", name, f"`{m.class_id}`", products]
            if level == "full":
                cells.append(_cell(m.definition))
            cells.append(tables)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def _tables(m, level):
    if m.components:
        return "沿分項"
    if level == "full":
        return "、".join(t["table"] + ("" if t["role"] == "primary" else f"（{TABLE_ROLE_LABELS.get(t['role'], t['role'])}）")
                        for t in m.tables)
    return "、".join(t["table"] for t in m.tables if t["role"] == "primary")


def _cell(text):
    return (text or "").replace("|", "／").replace("\n", " ")


def write_all(kb: Knowledge, out_dir, roles=None, levels=("compact", "full")):
    """寫出 packs/<版號>/<角色>.<level>.md／.json 與 manifest.json；回傳 manifest。"""
    out = out_dir / kb.version
    out.mkdir(parents=True, exist_ok=True)
    roles = list(roles or kb.roles) + ["baseline"]
    manifest = {"ontology_version": kb.version, "release": kb.release,
                "knowledge_fingerprint": kb.fingerprint(), "packs": []}
    for role in roles:
        for level in (levels if role != "baseline" else ("compact",)):
            pack = build(kb, role, level)
            stem = f"{role}.{level}" if role != "baseline" else "baseline"
            (out / f"{stem}.md").write_text(pack["markdown"], encoding="utf-8")
            (out / f"{stem}.json").write_text(json.dumps(pack["data"], ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
            manifest["packs"].append({"file": f"{stem}.md", "role": role, "level": level, "sha256": pack["sha256"],
                                      "chars": pack["chars"], "tokens_est": pack["tokens_est"],
                                      "metrics": len(pack["data"]["metrics"])})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, manifest
