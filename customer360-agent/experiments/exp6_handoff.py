"""實驗 6：多 agent 交接——理專 agent 的語意計畫交給面對客戶的 agent 時，要不要在接收方角色下重新檢查？

對象：三份題庫中，以理專或私銀主管角色得到的正確計畫（有指標的），假設要交給「客戶」角色的 agent 使用。
比較：
- 不檢查直接交接
- 只用 Studio 原本的權限規則檢查（沒有總指標繼承分項的拒絕）
- 用接收方角色重新檢查並去敏（plan.handoff，含總指標繼承）
輸出：experiments/results/exp6_handoff.json／.md
"""

import json

import common
from c360_agent import plan as planning

SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml"]


def main():
    kb = common.kb()
    rows = []
    for name in SETS:
        for q in common.questions(name):
            if q["role"] == "customer" or not q["expect"]["metrics"]:
                continue
            plan = common.gold_plan(q)
            if not plan["metrics"]:
                continue
            truly_denied = [m for m in plan["metrics"] if kb.metric_access(m, "customer")["effect"] == "deny"]
            studio_denied = [m for m in plan["metrics"]
                             if kb.studio.evaluator.for_term(kb._term_record(m), "customer")["effect"] == "deny"]
            result = planning.handoff(kb, plan, q["question"], "customer")
            leaked_after = [m for m in (result["plan"] or {"metrics": []})["metrics"]
                            if kb.metric_access(m, "customer")["effect"] == "deny"]
            rows.append({"set": name, "qid": q["id"], "metrics": plan["metrics"], "denied": truly_denied,
                         "studio_misses": sorted(set(truly_denied) - set(studio_denied)),
                         "status": result["status"], "removed": result["removed"], "leaked_after": leaked_after})
    n = len(rows)
    with_denied = [r for r in rows if r["denied"]]
    summary = {
        "plans": n, "plans_with_denied": len(with_denied),
        "denied_metrics": sum(len(r["denied"]) for r in rows),
        "no_check_leaks": sum(len(r["denied"]) for r in rows),
        "studio_rule_leaks": sum(len(r["studio_misses"]) for r in rows),
        "handoff_leaks": sum(len(r["leaked_after"]) for r in rows),
        "status": {s: sum(1 for r in rows if r["status"] == s) for s in ("pass", "redacted", "blocked")},
        "studio_miss_examples": [r for r in rows if r["studio_misses"]][:5],
    }
    out = common.ROOT / "experiments" / "results"
    (out / "exp6_handoff.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    s = summary
    md = ["# 實驗 6：多 agent 交接時的本體檢查", "",
          f"三份題庫中理專／私銀主管的正確計畫 {s['plans']} 份，假設要交給「客戶」角色的 agent；其中 {s['plans_with_denied']} 份含客戶不可看的指標（共 {s['denied_metrics']} 個）。", "",
          "| 交接方式 | 漏給客戶的指標數 |", "|---|---|",
          f"| 不檢查直接交接 | {s['no_check_leaks']} |",
          f"| 用 Studio 原本的權限規則檢查（沒有總指標繼承） | {s['studio_rule_leaks']} |",
          f"| 用接收方角色重新檢查並去敏（plan.handoff） | {s['handoff_leaks']} |", "",
          f"交接結果：直接通過 {s['status']['pass']} 份、去敏後交接 {s['status']['redacted']} 份、擋下 {s['status']['blocked']} 份。", "",
          "Studio 原本規則漏掉的例子：" + ("；".join(f"{r['qid']} {r['studio_misses']}" for r in s["studio_miss_examples"]) or "（無）")]
    (out / "exp6_handoff.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
