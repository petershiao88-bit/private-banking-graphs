"""本體發版前的回歸關卡（ontology CI）：對目前（或指定）的本體跑完四個實驗，檢查門檻，不過就回傳非 0。

用法：
  python experiments/run_all.py                      # 用 config.yaml 指到的本體
  C360A_CONFIG=/path/agent.yaml python experiments/run_all.py   # 用另一份本體（例如改版中的沙盒）
  python experiments/run_all.py --quick              # 跳過較慢的 SHACL 全量比對與 workflow 窮舉

門檻（來自 docs/ontology-adoption-findings.md 的結論）：
- 硬擋誤擋正確答案：三份題庫都必須是 0（C2）
- 硬擋＋質疑對注入錯誤的攔截率：≥ 95%（C2、C3）
- SHACL 與程式版一致：100%（C6）
- workflow 範本組合後的表達上限：≥ 90%（C7）
- 檢索前 5 名＋本體擴充的召回：≥ 95%（C8）
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
SETS = ["questions.yaml", "holdout.yaml", "holdout2.yaml", "holdout3.yaml"]


def run(script, *args):
    start = time.time()
    proc = subprocess.run([sys.executable, "-B", str(HERE / script), *args], capture_output=True, text=True, cwd=HERE)
    if proc.returncode != 0:
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        raise SystemExit(f"{script} 執行失敗")
    return time.time() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    checks = []

    for name in SETS:
        run("exp1_fault_injection.py", name)
        stem = "exp1_fault_injection" + ("" if name == "questions.yaml" else "_" + name.split(".")[0])
        t = json.loads((RESULTS / f"{stem}.json").read_text(encoding="utf-8"))["totals"]
        caught = (t["hard_only"] + t["soft_only"]) / t["wrong"]
        checks.append((f"[{name}] 硬擋誤擋正確答案", t["hard_fp"], t["hard_fp"] == 0, "= 0"))
        checks.append((f"[{name}] 注入錯誤攔截率（硬擋＋質疑）", f"{caught:.0%}", caught >= 0.95, "≥ 95%"))
        checks.append((f"[{name}] 質疑誤擋（參考）", f"{t['soft_fp']}/{t['questions']}", True, "記錄"))

    if not args.quick:
        run("exp2_shacl_vs_code.py")
        s = json.loads((RESULTS / "exp2_shacl_vs_code.json").read_text(encoding="utf-8"))["summary"]
        checks.append(("SHACL 與程式版完全一致", f"{s['exact']}/{s['plans']}", s["exact"] == s["plans"], "100%"))
        run("exp3_workflow_vs_plan.py")
        s = json.loads((RESULTS / "exp3_workflow_vs_plan.json").read_text(encoding="utf-8"))["summary"]
        checks.append(("workflow 組合後表達上限", f"{s['composed'] / s['n']:.0%}", s["composed"] / s["n"] >= 0.90, "≥ 90%"))
        checks.append(("workflow 程式填欄位（參考）", f"{s['outcomes'].get('correct', 0) / s['n']:.0%}", True, "記錄"))

    run("exp4_grounding_budget.py")
    s = json.loads((RESULTS / "exp4_grounding_budget.json").read_text(encoding="utf-8"))["summary"]
    recall = s["recall"]["5"]["all_exp"] / s["n"] if "5" in s["recall"] else s["recall"][5]["all_exp"] / s["n"]
    checks.append(("檢索前 5 名＋本體擴充召回", f"{recall:.0%}", recall >= 0.95, "≥ 95%"))

    width = max(len(c[0]) for c in checks)
    failed = 0
    print("\n本體回歸關卡")
    for label, value, ok, rule in checks:
        failed += not ok
        print(f"  {'✓' if ok else '✗'} {label:<{width}}  {value!s:>8}  （門檻 {rule}）")
    print("\n" + ("全部通過，可以發版。" if not failed else f"{failed} 項未通過，請先處理再發版。"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
