"""實驗 4：整包塞入還是先檢索？量測「從問題找到正確指標」的召回率，以及 context 隨指標數量的成長。

1. 召回率：kb.search(問題) 的前 k 個指標，是否涵蓋所有期望指標（全中）／至少一個（有中）。
2. 本體擴充：前 k 個再加上本體關係帶出的指標——銀行／證券雙胞胎、總指標與分項、同種類且同商品的指標。
3. 成本：骨架 token＋k 張指標卡的 token，對照整包 context 的 token；並外推指標數量增加時整包塞入的大小。
輸出：experiments/results/exp4_grounding_budget.json／.md
"""

import json
import statistics

import common
from c360_agent import packs, plan as planning

SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml"]
KS = [1, 3, 5, 8, 12, 20]


def expand(kb, gate, ids):
    out = set(ids)
    for m in ids:
        metric = kb.metrics[m]
        out |= set(gate.subsidiary_twins([m]).get(m, []))
        out |= set(metric.components)
        if m in kb.summary_of:
            out.add(kb.summary_of[m])
        for o in kb.metrics.values():
            if o.kind == metric.kind and o.subsidiary == metric.subsidiary and set(o.product_ids) & set(metric.product_ids):
                out.add(o.id)
    return out


def main():
    kb = common.kb()
    rows = []
    for name in SETS:
        for q in common.questions(name):
            expected = set(q["expect"]["metrics"] or [])
            if not expected:
                continue
            gate = planning.Gate(kb, q["role"])
            ranked = [h["id"] for h in kb.search(q["question"], role=q["role"], limit=60) if h["type"] == "metric"]
            row = {"set": name, "qid": q["id"], "category": q["category"], "expected": sorted(expected),
                   "ranks": {m: (ranked.index(m) + 1 if m in ranked else None) for m in expected}}
            for k in KS:
                top = set(ranked[:k])
                big = expand(kb, gate, top)
                row[f"all@{k}"] = expected <= top
                row[f"any@{k}"] = bool(expected & top)
                row[f"all_exp@{k}"] = expected <= big
                row[f"size_exp@{k}"] = len(big)
            rows.append(row)
    n = len(rows)
    rm = packs.build(kb, "rm")
    skeleton = packs.build(kb, "rm", skeleton=True)
    card_tokens = statistics.mean(packs.estimate_tokens(json.dumps(kb.metric_card(m, "full"), ensure_ascii=False))
                                  for m in kb.metrics)
    per_metric_pack = (rm["tokens_est"] - skeleton["tokens_est"]) / len(kb.metrics)
    summary = {"n": n, "pack_tokens": rm["tokens_est"], "skeleton_tokens": skeleton["tokens_est"],
               "card_tokens": round(card_tokens), "per_metric_pack_tokens": round(per_metric_pack, 1),
               "recall": {k: {"all": sum(r[f"all@{k}"] for r in rows), "any": sum(r[f"any@{k}"] for r in rows),
                              "all_exp": sum(r[f"all_exp@{k}"] for r in rows),
                              "size_exp": round(statistics.mean(r[f"size_exp@{k}"] for r in rows), 1)} for k in KS},
               "misses_at_8": [{"qid": r["qid"], "expected": r["expected"], "ranks": r["ranks"]} for r in rows
                               if not r["all_exp@8"]]}
    out = common.ROOT / "experiments" / "results"
    (out / "exp4_grounding_budget.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False,
                                                               indent=1), encoding="utf-8")
    md = render(summary)
    (out / "exp4_grounding_budget.md").write_text(md, encoding="utf-8")
    print(md)


def render(s):
    n = s["n"]
    pct = lambda a: f"{a}/{n}（{a / n * 100:.0f}%）"
    md = ["# 實驗 4：整包塞入還是先檢索？", "",
          f"三份題庫中有期望指標的 {n} 題。檢索器＝目前工具用的 `kb.search`（字元雙字組＋本體同義詞＋商品／類別標籤）。", "",
          "## 召回率", "",
          "| 前 k 個 | 全部期望指標都在 | 至少一個在 | 加上本體擴充後全部在 | 擴充後平均指標數 | 估計 token（骨架＋卡片） |",
          "|---|---|---|---|---|---|"]
    for k, v in s["recall"].items():
        tokens = s["skeleton_tokens"] + round(v["size_exp"] * s["card_tokens"])
        md.append(f"| {k} | {pct(v['all'])} | {pct(v['any'])} | {pct(v['all_exp'])} | {v['size_exp']} | ≈{tokens} |")
    md += ["", f"對照：整包理專 context 約 {s['pack_tokens']} token（骨架 {s['skeleton_tokens']}＋44 項指標，每項約 {s['per_metric_pack_tokens']} token；"
               f"完整指標卡每張約 {s['card_tokens']} token）。", "",
           "## 指標數量增加時，整包塞入的大小（外推）", "",
           "| 指標數 | 整包 context（估計 token） | 占 32k context 的比例 |", "|---|---|---|"]
    for count in (44, 100, 200, 500, 1000, 3000):
        tokens = s["skeleton_tokens"] + round(count * s["per_metric_pack_tokens"])
        md.append(f"| {count} | {tokens:,} | {tokens / 32768 * 100:.0f}% |")
    md += ["", "## 前 8 個＋本體擴充仍漏掉的題目", ""]
    md += [f"- {m['qid']}：期望 {m['expected']}，在檢索結果的名次 {m['ranks']}" for m in s["misses_at_8"]] or ["（無）"]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
