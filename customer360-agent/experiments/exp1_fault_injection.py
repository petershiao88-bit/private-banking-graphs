"""實驗 1：模擬 LLM 的典型錯誤，看各層本體檢查攔得下多少。

比較兩個面向：
1. 檢查分層（累加）：L1 存在性 → L2 權限 → L3 推理 → L4 對照問題 → L5 計畫內部一致性。
2. 檢查的對象：只看最後輸出（decision＋metrics），或看完整語意計畫（加上 terms／classes／is_a／exclude）。

另外用評分器確認每筆變異確實是「錯的答案」（排除剛好也正確的變異）。
輸出：experiments/results/exp1_fault_injection.json／.md
"""

from collections import defaultdict
import json
import time

import common
from c360_agent import plan as planning

LEVELS = [1, 2, 3, 4, 5, 6]
LEVEL_NAMES = {1: "L1 存在性", 2: "L2 權限", 3: "L3 推理", 4: "L4 對照問題", 5: "L5 計畫一致性", 6: "L6 本體標籤錨點"}
ANSWER_TEXT = "重複 待定 工具 持有 fh:holds 不是"   # 讓 mention 檢查不干擾：這裡只比較指標層面的錯誤


def output_only(plan):
    """只保留最後輸出看得到的東西：decision 與 metrics。"""
    return planning.normalize({"decision": plan["decision"], "metrics": plan["metrics"],
                               "clarification": plan["clarification"] or "x", "reason": plan["reason"] or "x",
                               "ontology_version": plan["ontology_version"]})


def detected_level(result):
    levels = [planning.CHECK_LEVELS.get(e["code"], 9) for e in result["errors"] + result.get("challenges", [])]
    return min(levels) if levels else None


def run(question_file="questions.yaml"):
    kb = common.kb()
    cases = common.apply_faults(question_file=question_file)
    rows = []
    t0 = time.time()
    for c in cases:
        q, plan = c["question"], c["plan"]
        verdict = common.evaluate.score(q, {"decision": plan["decision"], "metrics": plan["metrics"], "plan": plan,
                                            "answer": ANSWER_TEXT}, kb)
        gate = planning.Gate(kb, q["role"])
        full = gate.check(plan, q["question"])
        out = gate.check(output_only(plan), q["question"])
        rows.append({"qid": q["id"], "category": q["category"], "role": q["role"], "fault": c["fault"],
                     "family": c["family"], "harm": c["harm"], "why": c["why"],
                     "actually_wrong": verdict["outcome"] != "correct",
                     "full_level": detected_level(full), "full_codes": sorted({e["code"] for e in full["errors"] + full["challenges"]}),
                     "hard": bool(full["errors"]), "soft": bool(full["challenges"]),
                     "full_warn": sorted({w["code"] for w in full["warnings"]}),
                     "out_level": detected_level(out), "out_codes": sorted({e["code"] for e in out["errors"] + out["challenges"]})})
    elapsed = time.time() - t0
    false_pos = []
    for q in common.questions(question_file):
        g = common.gold_plan(q)
        r = planning.Gate(kb, q["role"]).check(g, q["question"])
        if r["errors"] or r["challenges"]:
            found = r["errors"] + r["challenges"]
            false_pos.append({"qid": q["id"], "codes": [e["code"] for e in found], "hard": bool(r["errors"]),
                              "messages": [e["message"] for e in found]})
    rows.append({"_false_positives": false_pos})
    return rows, elapsed


def summarize(rows):
    false_pos = rows[-1]["_false_positives"]
    rows = rows[:-1]
    by_fault = defaultdict(list)
    for r in rows:
        by_fault[r["fault"]].append(r)
    table = []
    for fault, items in by_fault.items():
        wrong = [r for r in items if r["actually_wrong"]]
        n = len(wrong)
        entry = {"fault": fault, "family": items[0]["family"], "harm": items[0]["harm"], "cases": len(items),
                 "wrong": n, "warned": sum(1 for r in wrong if r["full_warn"])}
        for L in LEVELS:
            entry[f"full_L{L}"] = sum(1 for r in wrong if r["full_level"] and r["full_level"] <= L)
            entry[f"out_L{L}"] = sum(1 for r in wrong if r["out_level"] and r["out_level"] <= L)
        table.append(entry)
    wrong = [r for r in rows if r["actually_wrong"]]
    totals = {"cases": len(rows), "wrong": len(wrong)}
    for L in LEVELS:
        totals[f"full_L{L}"] = sum(1 for r in wrong if r["full_level"] and r["full_level"] <= L)
        totals[f"out_L{L}"] = sum(1 for r in wrong if r["out_level"] and r["out_level"] <= L)
    harmful = [r for r in wrong if r["harm"] in ("critical", "high")]
    totals["harmful"] = len(harmful)
    totals["harmful_full"] = sum(1 for r in harmful if r["full_level"])
    totals["harmful_out"] = sum(1 for r in harmful if r["out_level"])
    totals["false_positives"] = false_pos
    totals["questions"] = len(common.questions(QUESTION_FILE))
    totals["hard_only"] = sum(1 for r in wrong if r["hard"])
    totals["soft_only"] = sum(1 for r in wrong if r["soft"] and not r["hard"])
    totals["hard_fp"] = sum(1 for f in false_pos if f["hard"])
    totals["soft_fp"] = sum(1 for f in false_pos if not f["hard"])
    process = [r for r in rows if not r["actually_wrong"] and r["fault"] in ("hallucinated_class", "false_is_a")]
    totals["process_errors"] = len(process)
    totals["process_caught"] = sum(1 for r in process if r["full_level"])
    totals["missed"] = [{"qid": r["qid"], "fault": r["fault"], "why": r["why"]} for r in wrong if not r["full_level"]]
    return table, totals


def render(table, totals, elapsed):
    pct = lambda a, b: f"{a}/{b}（{a / b * 100:.0f}%）" if b else "—"
    md = [f"# 實驗 1：LLM 錯誤注入 × 本體檢查分層（題庫 {QUESTION_FILE}）", "",
          f"從 {totals['questions']} 題的正確計畫產生 {totals['cases']} 筆錯誤計畫（{len(table)} 種錯誤），其中 {totals['wrong']} 筆經評分器確認確實是錯的答案。"
          f"檢查全部 {totals['cases'] * 2} 次共 {elapsed:.1f} 秒。", "",
          "## 累加攔截率（只計確實錯誤的計畫）", "",
          "| 檢查層級（累加） | 看完整語意計畫 | 只看最後輸出 |", "|---|---|---|"]
    for L in LEVELS:
        md.append(f"| ≤ {LEVEL_NAMES[L]} | {pct(totals[f'full_L{L}'], totals['wrong'])} | {pct(totals[f'out_L{L}'], totals['wrong'])} |")
    md += ["", f"高危害（critical／high）錯誤：完整計畫攔下 {pct(totals['harmful_full'], totals['harmful'])}，"
               f"只看輸出攔下 {pct(totals['harmful_out'], totals['harmful'])}。", "",
           "## 硬擋與質疑", "",
           "| | 攔下錯誤計畫 | 誤擋正確計畫 |", "|---|---|---|",
           f"| 只用硬擋（本體能確定推出的檢查） | {pct(totals['hard_only'], totals['wrong'])} | {totals['hard_fp']}/{totals['questions']} |",
           f"| 再加上質疑（對照問題文字） | {pct(totals['hard_only'] + totals['soft_only'], totals['wrong'])} | {totals['hard_fp'] + totals['soft_fp']}/{totals['questions']} |", "",
           f"正確計畫（{totals['questions']} 題 gold plan）被誤擋：{len(totals['false_positives'])} 題"
           + ("：" + "；".join(f"{f['qid']} {f['codes']}" for f in totals["false_positives"]) if totals["false_positives"] else "") + "。",
           f"不影響最後指標、但推理過程錯誤（自編類別、錯誤的 is_a）：攔下 {pct(totals['process_caught'], totals['process_errors'])}。", "",
           "## 依錯誤類型", "",
           "| 錯誤 | 類別 | 危害 | 確實錯誤 | L1 | L2 | L3 | L4 | L5 | L6（完整計畫） | 只看輸出（≤L6） | 有提醒 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in sorted(table, key=lambda e: (e["family"], e["fault"])):
        n = e["wrong"]
        cells = [e["fault"], e["family"], e["harm"], f"{n}/{e['cases']}"]
        cells += [str(e[f"full_L{L}"]) for L in LEVELS]
        cells += [str(e["out_L6"]), str(e["warned"])]
        md.append("| " + " | ".join(cells) + " |")
    md += ["", "## 沒有被攔下的錯誤", ""]
    md += [f"- {m['qid']}｜{m['fault']}：{m['why']}" for m in totals["missed"]] or ["（無）"]
    return "\n".join(md) + "\n"


QUESTION_FILE = "questions.yaml"

if __name__ == "__main__":
    import sys
    QUESTION_FILE = sys.argv[1] if len(sys.argv) > 1 else "questions.yaml"
    rows, elapsed = run(QUESTION_FILE)
    table, totals = summarize(rows)
    out = common.ROOT / "experiments" / "results"
    out.mkdir(parents=True, exist_ok=True)
    stem = "exp1_fault_injection" + ("" if QUESTION_FILE == "questions.yaml" else "_" + QUESTION_FILE.split(".")[0])
    (out / f"{stem}.json").write_text(json.dumps({"rows": rows, "table": table, "totals": totals},
                                                              ensure_ascii=False, indent=1), encoding="utf-8")
    md = render(table, totals, elapsed)
    (out / f"{stem}.md").write_text(md, encoding="utf-8")
    print(md)
