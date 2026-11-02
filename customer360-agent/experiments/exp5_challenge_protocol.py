"""實驗 5：質疑（soft check）出現後該怎麼處理？模型的反應會不會把對的改錯？

對象：三份題庫裡「會被質疑」的計畫——
- 錯誤計畫（實驗 1 的注入錯誤，只取「沒有硬擋、只有質疑」的，因為硬擋另有處理）
- 正確計畫被誤質疑的（質疑誤擋）

三種處理方式：
- warn：照答，只在回答裡附上質疑內容（不改計畫）
- ask_user：一律轉成向使用者澄清
- llm_recheck：退回給模型確認一次（實驗台目前的做法），模型的反應分三種個性：
    stubborn   一律堅持原計畫
    compliant  一律照質疑修改（加上另一邊、改成涵蓋錨點的指標、拿掉衝突的指標；改不出來就 out_of_scope）
    calibrated 原計畫錯就照質疑修改、原計畫對就堅持（理想上限）
量測：最後的評分結果（正確／保守未答／默默答錯），以及「正確計畫被改錯」的次數。
"""

from collections import Counter, defaultdict
import json

import common
from c360_agent import plan as planning

SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml"]
ANSWER = "重複 待定 工具 持有 fh:holds 不是"


def score(kb, q, plan):
    return common.evaluate.score(q, {"decision": plan["decision"], "metrics": plan["metrics"], "plan": plan,
                                     "answer": ANSWER}, kb)["outcome"]


def comply(kb, gate, plan, result, question):
    """照質疑修改計畫（模擬順從的模型）。"""
    metrics = list(plan["metrics"])
    for c in result["challenges"]:
        code, msg = c["code"], c["message"]
        if code in ("ambiguous_subsidiary", "missing_subsidiary"):
            for m in list(metrics):
                metrics += [t for t in gate.subsidiary_twins([m]).get(m, []) if t not in metrics]
        elif code == "cue_conflict":
            mentioned = {s for s, cues in gate.explicit_cues.items() if any(x in question for x in cues)}
            metrics = [m for m in metrics if kb.metrics[m].subsidiary in mentioned]
        elif code == "anchor_conflict":
            bad = msg.split(" ")[0]
            metrics = [m for m in metrics if m != bad]
        elif code == "anchor_missing":
            stem = msg.split("「")[1].split("」")[0] if "「" in msg else None
            kinds = {kb.metrics[m].kind for m in metrics} or {None}
            if stem in gate.product_stems:
                found = []
                for k in kinds:
                    for cls in gate.product_stems[stem]:
                        found += [x.id for x in kb.metrics_matching(role=gate.role, kind=k, product=cls)]
                metrics = sorted(set(found)) or metrics
    metrics = sorted(set(metrics))
    if not metrics and not plan["classes"]:
        return planning.normalize({**plan, "decision": "out_of_scope", "metrics": [], "reason": "依質疑修改後查無指標"})
    return planning.normalize({**plan, "metrics": metrics, "terms": [], "decision": plan["decision"]})


def main():
    kb = common.kb()
    cases = []
    for name in SETS:
        for q in common.questions(name):
            gold = common.gold_plan(q)
            r = planning.Gate(kb, q["role"]).check(gold, q["question"])
            if r["challenges"] and not r["errors"]:
                cases.append((name, q, gold, "gold"))
        for c in common.apply_faults(question_file=name):
            q, plan = c["question"], c["plan"]
            r = planning.Gate(kb, q["role"]).check(plan, q["question"])
            if r["challenges"] and not r["errors"] and score(kb, q, plan) != "correct":
                cases.append((name, q, plan, c["fault"]))
    table = defaultdict(Counter)
    flips = Counter()
    for name, q, plan, kind in cases:
        gate = planning.Gate(kb, q["role"])
        result = gate.check(plan, q["question"])
        original = score(kb, q, plan)
        group = "正確但被質疑" if kind == "gold" else "錯誤且被質疑"
        table[("warn", group)][original] += 1
        table[("ask_user", group)]["safe_miss" if original != "correct" else "safe_miss"] += 1
        revised = comply(kb, gate, plan, result, q["question"])
        revised_outcome = score(kb, q, revised)
        revised_challenged = bool(gate.check(revised, q["question"])["challenges"])
        for persona in ("stubborn", "compliant", "calibrated"):
            keep = persona == "stubborn" or (persona == "calibrated" and original == "correct")
            final = original if keep else revised_outcome
            table[(f"llm_recheck／{persona}", group)][final] += 1
            if original == "correct" and final != "correct":
                flips[persona] += 1
            # 混合：退回模型一次 → 再檢查；仍被質疑就升級（問使用者），否則採用
            still = result["challenges"] if keep else revised_challenged
            esc = "safe_miss" if still else final
            table[(f"recheck→再檢查→仍有疑問就問使用者／{persona}", group)][esc] += 1
            if original == "correct" and esc not in ("correct", "safe_miss"):
                flips["esc_" + persona] += 1
            # 細分：最後只剩 anchor_missing（指標範圍比問題廣）→ 照答附說明；其他質疑才問使用者
            last = result["challenges"] if keep else gate.check(revised, q["question"])["challenges"]
            only_missing = last and all(c["code"] == "anchor_missing" for c in last)
            esc2 = final if (not last or only_missing) else "safe_miss"
            table[(f"同上，但只剩錨點缺漏時照答附說明／{persona}", group)][esc2] += 1
    groups = ["錯誤且被質疑", "正確但被質疑"]
    n = {g: sum(1 for c in cases if (c[3] == "gold") == (g == "正確但被質疑")) for g in groups}
    rows = []
    for policy in ["warn", "ask_user", "llm_recheck／stubborn", "llm_recheck／compliant", "llm_recheck／calibrated",
                   "recheck→再檢查→仍有疑問就問使用者／stubborn", "recheck→再檢查→仍有疑問就問使用者／compliant",
                   "recheck→再檢查→仍有疑問就問使用者／calibrated",
                   "同上，但只剩錨點缺漏時照答附說明／compliant", "同上，但只剩錨點缺漏時照答附說明／calibrated"]:
        row = {"policy": policy}
        for g in groups:
            c = table[(policy, g)]
            row[g] = {"correct": c["correct"], "safe": c["safe_miss"], "wrong": c["silent_wrong"] + c["format_error"]}
        row["flips"] = flips.get(policy.split("／")[-1], 0) if policy.startswith("llm") else 0
        rows.append(row)
    out = common.ROOT / "experiments" / "results"
    (out / "exp5_challenge_protocol.json").write_text(json.dumps({"n": n, "rows": rows}, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    md = ["# 實驗 5：質疑出現後怎麼處理？", "",
          f"三份題庫中只被質疑（沒有硬擋）的計畫：錯誤計畫 {n['錯誤且被質疑']} 份、正確計畫 {n['正確但被質疑']} 份。", "",
          "| 處理方式 | 錯誤計畫 → 改對 | 錯誤計畫 → 保守 | 錯誤計畫 → 仍默默答錯 | 正確計畫 → 保持正確 | 正確計畫 → 被改成保守 | 正確計畫 → 被改錯 |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        w, g = r["錯誤且被質疑"], r["正確但被質疑"]
        md.append(f"| {r['policy']} | {w['correct']} | {w['safe']} | {w['wrong']} | {g['correct']} | {g['safe']} | {g['wrong']} |")
    md += ["", "- recheck→再檢查：退回模型一次後，對修改後（或堅持的）計畫再跑一次本體檢查；仍被質疑就改成向使用者澄清。",
           "- warn：照原計畫回答，只附上質疑內容。", "- ask_user：一律轉成向使用者澄清（保守）。",
           "- llm_recheck：退回模型確認一次；stubborn＝一律堅持、compliant＝一律照改、calibrated＝錯才改（上限）。"]
    (out / "exp5_challenge_protocol.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
