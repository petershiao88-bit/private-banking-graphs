"""實驗 7：各模式每題的輸入 token 估計（給地端 Qwen 容量規劃用）。

依據：各模式實際送出的 system prompt（docs/sample-report-heuristic/prompts，角色 rm）× 離線演練的平均呼叫次數；
作答階段另以實際的「已驗證計畫＋指標卡片」prompt 估計。真實數字以 Qwen 評測報告的 usage 為準。
"""

import json
from pathlib import Path

import common
from c360_agent.packs import estimate_tokens

RUN = common.ROOT / "docs" / "sample-report-heuristic"


def main():
    summary = json.loads((RUN / "summary.json").read_text(encoding="utf-8"))["modes"]
    prompts = RUN / "prompts"
    tok = lambda f: estimate_tokens((prompts / f).read_text(encoding="utf-8")) if (prompts / f).exists() else 0  # noqa: E731
    answer = tok("plan.rm.answer.latest.md") or tok("workflow.rm.answer.latest.md")
    stage = {"baseline": "baseline.rm.single.md", "context": "context.rm.single.md", "plan": "plan.rm.plan.md",
             "tools": "tools.rm.tools.md", "workflow": "workflow.rm.workflow.md"}
    rows = []
    for mode, f in stage.items():
        s = summary.get(mode)
        if not s:
            continue
        system = tok(f)
        calls = s["avg_llm_calls"]
        answer_calls = 1 if mode in ("plan", "workflow") else 0
        main_calls = max(calls - answer_calls, 1)
        total = round(system * main_calls + answer * answer_calls * (1 if mode in ("plan", "workflow") else 0))
        rows.append({"mode": mode, "system_tokens": system, "avg_calls": calls, "est_input_tokens": total})
    md = ["# 實驗 7：每題輸入 token 估計（理專角色）", "",
          "| 模式 | system prompt（估計 token） | 平均呼叫次數（離線演練） | 每題輸入 token（估計） |", "|---|---|---|---|"]
    md += [f"| {r['mode']} | {r['system_tokens']} | {r['avg_calls']} | ≈{r['est_input_tokens']:,} |" for r in rows]
    md += ["", f"作答階段（已驗證計畫＋指標卡片）約 {answer} token。tools 模式的工具結果另計，真實模型通常要多 2～4 輪。",
           "未計輸出 token 與 Qwen3 的思考 token；思考開啟時輸出可能是答案的數倍。"]
    out = common.ROOT / "experiments" / "results"
    (out / "exp7_cost.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "exp7_cost.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
