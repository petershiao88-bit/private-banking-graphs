"""實驗 3：預先定義 workflow（本體驅動、程式填欄位）能答對多少？範本的表達上限是多少？剩下的需要什麼？

三種量測，用全部 73 題（三份題庫）：
1. deterministic：完全不用 LLM，程式用本體標籤填欄位、執行範本、評分。
2. oracle：窮舉欄位組合；有一組能答對就算「範本表達得了」（＝ LLM 只負責把欄位填對時的上限）。
3. 獨立性：deterministic workflow 的錯誤答案，交給本體檢查（硬擋＋質疑）能不能攔下？
   （預期：攔不太下，因為填欄位和檢查用的是同一套詞表，兩個讀者不獨立。）
輸出：experiments/results/exp3_workflow_vs_plan.json／.md
"""

from collections import Counter, defaultdict
import json
import time

import common
from c360_agent import plan as planning
from workflows import ANSWER_NOTES, Workflows

SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml"]


def main():
    kb = common.kb()
    wf = Workflows(kb)
    rows = []
    t0 = time.time()
    for name in SETS:
        for q in common.questions(name):
            template, slots, plan = wf.run_deterministic(q["question"], q["role"])
            slots = {"calls": [{k: v for k, v in c.items() if v} for c in slots["calls"]]}
            verdict = common.evaluate.score(q, {"decision": plan["decision"], "metrics": plan["metrics"], "plan": plan,
                                                "answer": ANSWER_NOTES}, kb)
            gate = planning.Gate(kb, q["role"]).check(plan, q["question"])
            oracle = wf.oracle(q)
            composed = None if oracle else wf.oracle_composed(q)
            rows.append({"set": name, "qid": q["id"], "category": q["category"], "question": q["question"],
                         "template": template, "slots": slots,
                         "decision": plan["decision"], "metrics": plan["metrics"],
                         "outcome": verdict["outcome"], "problems": verdict["problems"],
                         "gate_hard": [e["code"] for e in gate["errors"]],
                         "gate_soft": [e["code"] for e in gate["challenges"]],
                         "oracle": bool(oracle), "oracle_slots": oracle[1] if oracle else None,
                         "composed": bool(oracle or composed), "composed_calls": composed})
    elapsed = time.time() - t0
    summary = summarize(rows, elapsed)
    out = common.ROOT / "experiments" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "exp3_workflow_vs_plan.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False,
                                                               indent=1, default=str), encoding="utf-8")
    md = render(summary, rows)
    (out / "exp3_workflow_vs_plan.md").write_text(md, encoding="utf-8")
    print(md)


def summarize(rows, elapsed):
    n = len(rows)
    out = Counter(r["outcome"] for r in rows)
    by_set = defaultdict(Counter)
    for r in rows:
        by_set[r["set"]][r["outcome"]] += 1
        by_set[r["set"]]["n"] += 1
        by_set[r["set"]]["oracle"] += r["oracle"]
    wrong = [r for r in rows if r["outcome"] == "silent_wrong"]
    return {"n": n, "seconds": round(elapsed, 1), "outcomes": dict(out), "oracle": sum(r["oracle"] for r in rows),
            "composed": sum(r["composed"] for r in rows),
            "not_expressible": [{"qid": r["qid"], "question": r["question"]} for r in rows if not r["composed"]],
            "by_set": {k: dict(v) for k, v in by_set.items()},
            "by_category": {c: {"n": sum(1 for r in rows if r["category"] == c),
                                "correct": sum(1 for r in rows if r["category"] == c and r["outcome"] == "correct"),
                                "oracle": sum(1 for r in rows if r["category"] == c and r["oracle"])}
                            for c in sorted({r["category"] for r in rows})},
            "silent_wrong": len(wrong),
            "wrong_caught_hard": sum(1 for r in wrong if r["gate_hard"]),
            "wrong_caught_soft": sum(1 for r in wrong if r["gate_soft"] and not r["gate_hard"])}


def render(s, rows):
    pct = lambda a, b: f"{a}/{b}（{a / b * 100:.0f}%）" if b else "—"
    o = s["outcomes"]
    md = ["# 實驗 3：預先定義 workflow vs LLM 組計畫", "",
          f"三份題庫共 {s['n']} 題。workflow 範本：metric_lookup、concept_is_a、concept_relation，欄位型別都是本體類別。"
          f"全部計算 {s['seconds']} 秒（含 oracle 窮舉）。", "",
          "## 結果", "",
          "| 做法 | 正確 | 默默答錯 | 保守未答 |", "|---|---|---|---|",
          f"| workflow＋程式填欄位（完全不用 LLM） | {pct(o.get('correct', 0), s['n'])} | {o.get('silent_wrong', 0)} | {o.get('safe_miss', 0)} |",
          f"| workflow 的表達上限（欄位一定填對，oracle） | {pct(s['oracle'], s['n'])} | — | — |",
          f"| 允許組合兩個範本呼叫（LLM 拆解問題＋填欄位） | {pct(s['composed'], s['n'])} | — | — |", "",
          "組合兩個範本後仍表達不了：" + ("；".join(f"{x['qid']} {x['question']}" for x in s["not_expressible"]) or "（無）"), "",
          "| 題庫 | 程式填欄位 | 表達上限 |", "|---|---|---|"]
    for name, c in s["by_set"].items():
        md.append(f"| {name} | {pct(c.get('correct', 0), c['n'])} | {pct(c.get('oracle', 0), c['n'])} |")
    md += ["", "| 題型 | 題數 | 程式填欄位答對 | 表達上限 |", "|---|---|---|---|"]
    for c, v in s["by_category"].items():
        md.append(f"| {c} | {v['n']} | {v['correct']} | {v['oracle']} |")
    md += ["", f"workflow 的 {s['silent_wrong']} 個默默答錯，本體檢查硬擋攔下 {s['wrong_caught_hard']} 個、質疑攔下 {s['wrong_caught_soft']} 個。", "",
           "## workflow 答錯或答不了的題目", ""]
    for r in rows:
        if r["outcome"] != "correct":
            md.append(f"- {r['qid']}｜{r['category']}｜{r['question']} → {r['template']} {r['slots']} → {r['decision']} "
                      f"{r['metrics']}｜{r['outcome']}；{'；'.join(r['problems'])}｜上限{'可' if r['oracle'] else '不可'}表達"
                      f"｜檢查：硬擋 {r['gate_hard'] or '—'}、質疑 {r['gate_soft'] or '—'}")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    main()
