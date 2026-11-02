"""評測：同一份題庫 × 多種模式，逐題評分，輸出 results.jsonl／summary.json／report.md／report.html。

評分結果（outcome）：
- correct       決策可接受，且指標、類別、提及檢查都對，沒有越權或自編 ID。
- safe_miss     沒答對，但選擇了澄清／不在範圍／被系統擋下（保守，不會誤導使用者）。
- silent_wrong  給了回答（decision=answer），但內容錯：指標不對、越權、自編 ID、該澄清卻直接答。
- format_error  模型沒有交出可解析的結果，或呼叫失敗。
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import time

import yaml

from .agent import MODES, Agent
from .knowledge import Knowledge

SAFE_DECISIONS = ("clarify", "out_of_scope", "blocked")
OUTCOMES = ("correct", "safe_miss", "silent_wrong", "format_error")


class QuestionError(ValueError):
    pass


# ---------------------------------------------------------------------- 題庫


def load_questions(path, kb: Knowledge = None):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    items = data.get("questions") if isinstance(data, dict) else data
    seen, out = set(), []
    for q in items or []:
        if q["id"] in seen:
            raise QuestionError(f"題目 ID 重複：{q['id']}")
        seen.add(q["id"])
        expect = dict(q.get("expect") or {})
        expect.setdefault("decision", ["answer"])
        if isinstance(expect["decision"], str):
            expect["decision"] = [expect["decision"]]
        expect.setdefault("metrics", None)
        expect.setdefault("match", "exact")
        expect.setdefault("forbidden", [])
        expect.setdefault("classes", [])
        expect.setdefault("mention_any", [])
        out.append({"id": q["id"], "category": q.get("category", ""), "role": q.get("role", "rm"),
                    "question": q["question"], "expect": expect, "note": q.get("note", "")})
    if kb is not None:
        problems = validate_questions(out, kb)
        if problems:
            raise QuestionError("題庫與本體不一致：\n- " + "\n- ".join(problems))
    return out


def validate_questions(questions, kb):
    problems = []
    gap_ids = {g["id"] for g in kb.gaps}
    for q in questions:
        e = q["expect"]
        if q["role"] not in kb.roles:
            problems.append(f"{q['id']}：角色 {q['role']} 未定義")
        for mid in (e["metrics"] or []) + e["forbidden"]:
            if mid not in kb.metrics and mid not in gap_ids:
                problems.append(f"{q['id']}：指標 {mid} 不存在")
        for cid in e["classes"]:
            if cid not in kb.classes:
                problems.append(f"{q['id']}：類別 {cid} 不存在")
        if e["match"] not in ("exact", "superset", "any"):
            problems.append(f"{q['id']}：match 只能是 exact／superset／any")
        for mid in e["metrics"] or []:
            if q["role"] in kb.roles and mid in kb.metrics and kb.metric_access(mid, q["role"])["effect"] == "deny":
                problems.append(f"{q['id']}：期望指標 {mid} 對角色 {q['role']} 是拒絕，題目設計矛盾")
    return problems


# ---------------------------------------------------------------------- 評分


def score(question, transcript, kb: Knowledge):
    e = question["expect"]
    decision = transcript.get("decision")
    out_metrics = list(transcript.get("metrics") or [])
    plan = transcript.get("plan") or {}
    out_classes = set(plan.get("classes") or [])
    for term in plan.get("terms") or []:
        out_classes.update(term.get("classes") or [])
    checks, problems = {}, []

    if decision in (None, "unparsed", "error"):
        return {"outcome": "format_error", "checks": {"parsed": False},
                "problems": [transcript.get("error") or "沒有可解析的結果"]}

    checks["decision"] = decision in e["decision"]
    if not checks["decision"]:
        problems.append(f"決策 {decision}，期望 {'／'.join(e['decision'])}")

    invalid = [m for m in out_metrics if m not in kb.metrics]
    leaks = [m for m in out_metrics if m in kb.metrics and kb.metric_access(m, question["role"])["effect"] == "deny"]
    forbidden = [m for m in out_metrics if m in e["forbidden"]]
    checks["invalid_ids"], checks["leaks"], checks["forbidden"] = invalid, leaks, forbidden
    if invalid:
        problems.append("不存在的指標 ID：" + "、".join(invalid))
    if leaks:
        problems.append("越權使用：" + "、".join(leaks))
    if forbidden:
        problems.append("用了不該用的指標：" + "、".join(forbidden))

    if decision == "answer":
        if e["metrics"] is not None:
            expected, got = set(e["metrics"]), set(out_metrics)
            if e["match"] == "exact":
                ok = got == expected
            elif e["match"] == "superset":
                ok = expected <= got
            else:
                ok = bool(expected & got)
            checks["metrics"] = ok
            if not ok:
                missing, extra = sorted(expected - got), sorted(got - expected)
                problems.append("指標不符" + (f"；缺 {'、'.join(missing)}" if missing else "")
                                + (f"；多 {'、'.join(extra)}" if extra and e["match"] == "exact" else ""))
        if e["classes"]:
            missing = [c for c in e["classes"] if c not in out_classes]
            checks["classes"] = not missing
            if missing:
                problems.append("結果缺少類別：" + "、".join(missing))
        if e["mention_any"]:
            text = transcript.get("answer") or ""
            checks["mention"] = any(word in text for word in e["mention_any"])
            if not checks["mention"]:
                problems.append("回答沒有提到：" + "／".join(e["mention_any"]))

    hard_fail = bool(invalid or leaks or forbidden)
    passed = checks["decision"] and not hard_fail and all(
        checks.get(k, True) for k in ("metrics", "classes", "mention"))
    if passed:
        outcome = "correct"
    elif decision in SAFE_DECISIONS and not hard_fail:
        outcome = "safe_miss"
    else:
        outcome = "silent_wrong"
    return {"outcome": outcome, "checks": checks, "problems": problems}


# ---------------------------------------------------------------------- 執行


class Runner:
    def __init__(self, kb: Knowledge, llm, run_dir, modes=None, level=None, progress=print):
        self.kb, self.llm, self.run_dir = kb, llm, Path(run_dir)
        self.modes = list(modes or MODES)
        self.level = level
        self.progress = progress or (lambda *_: None)
        self._agents = {}

    def agent(self, mode, role):
        key = (mode, role)
        if key not in self._agents:
            self._agents[key] = Agent(self.kb, self.llm, role, mode, level=self.level)
        return self._agents[key]

    def run(self, questions, repeat=1, resume=True):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "prompts").mkdir(exist_ok=True)
        results_path = self.run_dir / "results.jsonl"
        done = set()
        if resume and results_path.exists():
            for line in results_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    done.add((r["question_id"], r["mode"], r["repeat"]))
        total = len(questions) * len(self.modes) * repeat
        count = len(done)
        with results_path.open("a", encoding="utf-8") as out:
            for rep in range(repeat):
                for q in questions:
                    for mode in self.modes:
                        if (q["id"], mode, rep) in done:
                            continue
                        agent = self.agent(mode, q["role"])
                        started = time.time()
                        transcript = agent.ask(q["question"])
                        self._save_prompts(agent, mode, q["role"])
                        verdict = score(q, transcript, self.kb)
                        record = {"question_id": q["id"], "category": q["category"], "mode": mode, "repeat": rep,
                                  "role": q["role"], "question": q["question"], "expect": q["expect"],
                                  "note": q["note"], **verdict, "transcript": transcript,
                                  "wall_seconds": round(time.time() - started, 2)}
                        out.write(json.dumps(record, ensure_ascii=False) + "\n")
                        out.flush()
                        count += 1
                        self.progress(f"[{count}/{total}] {q['id']} {mode:<8} {verdict['outcome']:<12} "
                                      f"{transcript.get('decision')} {','.join(transcript.get('metrics') or [])[:80]}")
        return load_results(self.run_dir)

    def _save_prompts(self, agent, mode, role):
        for stage, text in agent.system_prompts.items():
            path = self.run_dir / "prompts" / f"{mode}.{role}.{stage}.md"
            if not path.exists() or stage == "answer":
                if stage == "answer":
                    path = self.run_dir / "prompts" / f"{mode}.{role}.answer.latest.md"
                path.write_text(text, encoding="utf-8")


def load_results(run_dir):
    path = Path(run_dir) / "results.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(results):
    by_mode = defaultdict(list)
    for r in results:
        by_mode[r["mode"]].append(r)
    modes = [m for m in MODES if m in by_mode] + [m for m in by_mode if m not in MODES]
    summary = {"modes": {}, "categories": {}, "total": len(results)}
    for mode in modes:
        items = by_mode[mode]
        n = len(items)
        outcomes = Counter(r["outcome"] for r in items)
        gates = [r["transcript"]["gate"] for r in items if r["transcript"].get("gate")]
        enforced = [g for g in gates if g and g[0].get("enforced")]
        tokens = [r["transcript"].get("usage", {}) for r in items]
        summary["modes"][mode] = {
            "n": n,
            **{k: outcomes.get(k, 0) for k in OUTCOMES},
            "accuracy": _ratio(outcomes.get("correct", 0), n),
            "silent_wrong_rate": _ratio(outcomes.get("silent_wrong", 0), n),
            "leaks": sum(1 for r in items if r["checks"].get("leaks")),
            "invalid_ids": sum(1 for r in items if r["checks"].get("invalid_ids")),
            "gate_first_pass": _ratio(sum(1 for g in enforced if g[0]["passed"]), len(enforced)) if enforced else None,
            "would_block": sum(1 for g in gates if g and not g[0].get("enforced") and not g[-1]["passed"]),
            "would_challenge": sum(1 for g in gates if g and not g[0].get("enforced") and g[-1].get("challenges")),
            "challenged": sum(1 for g in gates if g and g[0].get("enforced") and any(x.get("challenges") for x in g)),
            "escalated": sum(1 for r in items if r["transcript"].get("escalated")),
            "blocked": sum(1 for r in items if r["transcript"].get("decision") == "blocked"),
            "avg_prompt_tokens": _avg(t.get("prompt_tokens", 0) for t in tokens),
            "avg_completion_tokens": _avg(t.get("completion_tokens", 0) for t in tokens),
            "avg_latency": _avg(r["transcript"].get("latency", 0) for r in items),
            "avg_llm_calls": _avg(r["transcript"].get("llm_calls", 0) for r in items),
            "avg_tool_calls": _avg(r["transcript"].get("tool_calls", 0) for r in items),
            "pack_tokens_est": items[0]["transcript"]["pack"]["tokens_est"] if items else None,
        }
    cats = defaultdict(lambda: defaultdict(list))
    for r in results:
        cats[r["category"]][r["mode"]].append(r["outcome"] == "correct")
    for cat, per_mode in cats.items():
        summary["categories"][cat] = {m: {"correct": sum(v), "n": len(v)} for m, v in per_mode.items()}
    return summary


def _ratio(a, b):
    return round(a / b, 3) if b else None


def _avg(values):
    values = list(values)
    return round(sum(values) / len(values), 1) if values else None
