"""實驗 2：SHACL 能不能當語意計畫的檢查器？

把實驗 1 的所有計畫（三份題庫的正確計畫＋錯誤計畫）分別交給程式版 Gate 與 SHACL 版（plan-shapes.ttl），比較：
- 硬擋判斷是否一致、質疑是否一致、檢查代碼是否完全一致；
- 速度；
- 「封閉世界」的必要性：若 shapes 只用一般寫法（只檢查有型別的節點），自編 ID 會不會悄悄通過。
輸出：experiments/results/exp2_shacl_vs_code.json／.md
"""

from collections import Counter
import json
import statistics
import time

import common
from c360_agent import plan as planning
from shacl_gate import ShaclGate

SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml"]
EXISTENCE = {"unknown_metric", "unknown_class"}


def main():
    kb = common.kb()
    t0 = time.time()
    sg = ShaclGate(kb)
    build = time.time() - t0
    rows = []
    for name in SETS:
        items = [(q, common.gold_plan(q), "gold", "") for q in common.questions(name)]
        items += [(c["question"], c["plan"], c["fault"], c["why"]) for c in common.apply_faults(question_file=name)]
        for q, plan, kind, why in items:
            t = time.time()
            code = planning.Gate(kb, q["role"]).check(plan, q["question"])
            code_s = time.time() - t
            sh = sg.check(plan, q["question"], q["role"])
            c_hard = sorted({e["code"] for e in code["errors"]})
            c_soft = sorted({e["code"] for e in code["challenges"]})
            # SHACL 對待定範圍 ID 會同時報 unknown_metric（它不是 pg:Metric）；程式版只報 gap_metric。比對時視為同一件事。
            s_hard = sorted(set(sh["hard"]) - ({"unknown_metric"} if "gap_metric" in sh["hard"] else set()))
            rows.append({"set": name, "qid": q["id"], "case": kind, "why": why,
                         "code_hard": c_hard, "code_soft": c_soft, "shacl_hard": s_hard, "shacl_soft": sh["soft"],
                         "hard_agree": bool(c_hard) == bool(s_hard), "soft_agree": bool(c_soft) == bool(sh["soft"]),
                         "exact": c_hard == s_hard and c_soft == sh["soft"],
                         "code_ms": round(code_s * 1000, 2), "shacl_ms": round(sh["seconds"] * 1000, 1),
                         "closed_world_only": kind == "hallucinated_metric" and set(s_hard) <= EXISTENCE and bool(s_hard)})
    summary = {"plans": len(rows), "build_seconds": round(build, 2),
               "hard_agree": sum(r["hard_agree"] for r in rows), "soft_agree": sum(r["soft_agree"] for r in rows),
               "exact": sum(r["exact"] for r in rows),
               "code_ms_mean": round(statistics.mean(r["code_ms"] for r in rows), 2),
               "shacl_ms_mean": round(statistics.mean(r["shacl_ms"] for r in rows), 1),
               "shacl_ms_p95": round(sorted(r["shacl_ms"] for r in rows)[int(len(rows) * 0.95)], 1),
               "hallucinated": sum(1 for r in rows if r["case"] == "hallucinated_metric"),
               "closed_world_only": sum(r["closed_world_only"] for r in rows),
               "diffs": Counter(f"code={r['code_hard'] + r['code_soft']} / shacl={r['shacl_hard'] + r['shacl_soft']}"
                                for r in rows if not r["exact"]).most_common(12)}
    out = common.ROOT / "experiments" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "exp2_shacl_vs_code.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    md = render(summary)
    (out / "exp2_shacl_vs_code.md").write_text(md, encoding="utf-8")
    print(md)


def render(s):
    n = s["plans"]
    pct = lambda a: f"{a}/{n}（{a / n * 100:.1f}%）"
    lines = ["# 實驗 2：SHACL 當語意計畫檢查器 vs 程式版", "",
             f"三份題庫的正確計畫＋錯誤計畫共 {n} 份，分別交給程式版 Gate 與 SHACL（experiments/plan-shapes.ttl）。", "",
             "| 比較 | 結果 |", "|---|---|",
             f"| 硬擋判斷一致 | {pct(s['hard_agree'])} |",
             f"| 質疑判斷一致 | {pct(s['soft_agree'])} |",
             f"| 檢查代碼完全一致 | {pct(s['exact'])} |",
             f"| 平均耗時 | 程式 {s['code_ms_mean']} ms／SHACL {s['shacl_ms_mean']} ms（p95 {s['shacl_ms_p95']} ms） |",
             f"| 建立資料圖（本體＋閉包＋指標＋權限） | {s['build_seconds']} 秒（一次） |",
             f"| 自編指標 ID 只靠封閉世界 shape 攔下 | {s['closed_world_only']}/{s['hallucinated']} |", "",
             "## 不一致的情況（前 12 種）", ""]
    lines += [f"- {k}：{v} 次" for k, v in s["diffs"]] or ["（無）"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
