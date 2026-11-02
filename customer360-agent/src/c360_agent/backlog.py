"""質疑紀錄 → 本體維護待辦（結論 C4 的回饋迴路）。

讀一次評測（runs/<資料夾>/results.jsonl），把所有本體檢查的質疑與硬擋依「觸發的詞／代碼」歸類，再用評分結果分成：
- 誤質疑：答案其實是對的 → 多半代表本體缺詞或缺概念（要補同義詞、類別或修飾語規則）
- 有效質疑／有效硬擋：答案確實錯 → 檢查有用，保留
輸出 backlog.md（給人看）與 backlog.json。
"""

from collections import defaultdict
import json
from pathlib import Path
import re

from .evaluate import load_results

ANCHOR = re.compile(r"「([^」]+)」")


def build(results):
    groups = defaultdict(lambda: {"false": [], "fixed": [], "valid": [], "codes": set()})
    for r in results:
        t = r["transcript"]
        correct = r["outcome"] == "correct"
        gates = t.get("gate") or []
        for n, g in enumerate(gates):
            final = n == len(gates) - 1
            for item in (g.get("challenges") or []) + (g.get("errors") or []):
                code = item["code"]
                words = ANCHOR.findall(item["message"])
                key = f"{code}｜{words[0]}" if words else code
                entry = {"qid": r["question_id"], "mode": r["mode"], "question": r["question"],
                         "message": item["message"], "outcome": r["outcome"]}
                groups[key]["codes"].add(code)
                if not correct:
                    bucket = "valid"          # 答案錯：檢查是對的（不管模型有沒有改）
                elif final:
                    bucket = "false"          # 最後被接受的計畫仍被質疑，但答案正確：誤質疑
                else:
                    bucket = "fixed"          # 中途被質疑，之後改對：促成修正
                groups[key][bucket].append(entry)
    items = []
    for key, v in groups.items():
        count = lambda xs: len({(e["qid"], e["mode"]) for e in xs})  # noqa: E731
        items.append({"key": key, "codes": sorted(v["codes"]), "false": v["false"], "fixed": v["fixed"],
                      "valid": v["valid"], "false_count": count(v["false"]), "fixed_count": count(v["fixed"]),
                      "valid_count": count(v["valid"])})
    items.sort(key=lambda x: (-x["false_count"], -x["fixed_count"], -x["valid_count"], x["key"]))
    return items


SUGGESTIONS = {
    "anchor_missing": "問題裡的詞被當成商品／指標種類，但正確答案不涵蓋它：補同義詞、把它加進修飾語規則（例如「X 計價」），或在本體新增對應類別。",
    "anchor_conflict": "選到的指標和問題的錨點無關，但答案其實正確：錨點詞表可能缺了這個指標的別名。",
    "ambiguous_subsidiary": "問題其實已經指向某一家子公司：把那個線索（人員、通路、限定詞）加進本體，讓子公司可以被推得。",
    "cue_conflict": "子公司明示字判讀有誤：檢查明示字清單。",
    "missing_subsidiary": "問題同時提到兩家但只需一家：檢查否定詞或語意。",
}


def render(items, meta=None):
    md = ["# 本體維護待辦（由本體檢查的質疑紀錄產生）", ""]
    if meta:
        md += [f"來源：{meta.get('model', '—')}｜本體 v{meta.get('ontology_version', '—')}｜{meta.get('started', '')}", ""]
    false_items = [i for i in items if i["false_count"]]
    md += ["## 1. 誤質疑（答案其實正確）→ 可能要補本體", ""]
    if not false_items:
        md.append("（無）")
    for i in false_items:
        code = i["codes"][0]
        md += [f"### {i['key']}（{i['false_count']} 次）", "", SUGGESTIONS.get(code, "檢查這條規則是否過嚴。"), ""]
        md += [f"- {e['qid']}／{e['mode']}：{e['question']} → {e['message']}" for e in i["false"][:5]]
        md.append("")
    md += ["## 2. 促成修正的質疑（中途被質疑，模型之後改對）", "", "| 觸發 | 次數 | 例子 |", "|---|---|---|"]
    for i in items:
        if i["fixed_count"]:
            ex = i["fixed"][0]
            md.append(f"| {i['key']} | {i['fixed_count']} | {ex['qid']}／{ex['mode']}：{ex['question']} |")
    md += ["", "## 3. 有效的質疑與硬擋（答案最後仍有錯）", "", "| 觸發 | 次數 | 例子 |", "|---|---|---|"]
    for i in items:
        if i["valid_count"]:
            ex = i["valid"][0]
            md.append(f"| {i['key']} | {i['valid_count']} | {ex['qid']}／{ex['mode']}：{ex['question']} |")
    return "\n".join(md) + "\n"


def write(run_dir):
    run_dir = Path(run_dir)
    results = load_results(run_dir)
    meta_path = run_dir / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None
    items = build(results)
    (run_dir / "backlog.json").write_text(json.dumps(items, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    (run_dir / "backlog.md").write_text(render(items, meta), encoding="utf-8")
    return items
