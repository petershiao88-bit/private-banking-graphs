"""四種模式走完整流程（經 HTTP 假伺服器），以及評分、報告、命令列。"""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from tests import ROOT, shared_kb
from tests.fake_server import FakeQwen
from c360_agent import evaluate, report
from c360_agent.__main__ import main
from c360_agent.agent import Agent
from c360_agent.llm import OpenAICompatible, ScriptedLLM
from c360_agent.settings import LLMSettings


def plan_json(**kw):
    base = {"decision": "answer", "terms": [], "metrics": [], "classes": [], "is_a": [], "ontology_version": "0.17.0"}
    base.update(kw)
    return "```json\n" + json.dumps(base, ensure_ascii=False) + "\n```"


class QwenLikeBrain:
    """像 Qwen 一樣：工具模式先查再答；計畫模式第一次選錯（只選銀行），被擋下後改為澄清。"""

    def __init__(self):
        self.seen = []

    def __call__(self, messages, tools):
        system = messages[0]["content"]
        last = messages[-1]
        self.seen.append(last.get("content"))
        if "已通過本體檢查的語意計畫" in system:
            return "text", "依本體 v0.17.0，銀行基金手收為 bank.fund_fee_income，來源 DSFND.PB_FUND_SPREAD_DAILY。"
        if "工具模式" in system:
            used = any(m["role"] == "tool" or "<tool_response>" in str(m.get("content")) for m in messages)
            if not used:
                return "tool", ("list_metrics", {"kind": "fee", "product": "bank:FundProduct"})
            if str(last.get("content", "")).startswith("本體檢查"):
                return "text", "兩邊都有。" + plan_json(metrics=["bank.fund_fee_income", "securities.fund_fee_income"])
            return "text", "銀行基金手收。" + plan_json(metrics=["bank.fund_fee_income"])
        if "語意計畫" in system:
            if str(last.get("content", "")).startswith("本體檢查"):
                return "text", plan_json(decision="clarify", clarification="請問要看銀行還是證券複委託的基金手收？",
                                         metrics=["bank.fund_fee_income", "securities.fund_fee_income"])
            return "text", plan_json(metrics=["bank.fund_fee_income"], classes=["bank:BankFeeIncome"])
        return "text", "基金手收是 bank.fund_fee_income。" + plan_json(metrics=["bank.fund_fee_income"])


def http_llm(server, **kw):
    return OpenAICompatible(LLMSettings(base_url=server.base_url, model="auto", retries=0, timeout=10, **kw))


class AgentModesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_context_records_but_does_not_block(self):
        with FakeQwen(QwenLikeBrain()) as server:
            t = Agent(self.kb, http_llm(server), "rm", "context").ask("基金手收怎麼算？")
        self.assertEqual(t["decision"], "answer")
        self.assertFalse(t["gate"][0]["enforced"])
        self.assertEqual(t["gate"][0]["challenges"][0]["code"], "ambiguous_subsidiary")
        self.assertEqual(t["llm_calls"], 1)
        self.assertNotIn("```json", t["answer"])

    def test_plan_retries_then_clarifies(self):
        with FakeQwen(QwenLikeBrain()) as server:
            t = Agent(self.kb, http_llm(server), "rm", "plan").ask("基金手收怎麼算？")
        self.assertEqual([bool(g["challenges"]) for g in t["gate"]], [True, False])  # 先被質疑，模型改為澄清
        self.assertEqual(t["decision"], "clarify")
        self.assertIn("銀行還是證券", t["answer"])
        self.assertEqual(t["llm_calls"], 2)
        self.assertTrue(all(c["thinking"] for c in t["calls"]))

    def test_plan_answer_stage_gets_only_verified_cards(self):
        with FakeQwen(QwenLikeBrain()) as server:
            agent = Agent(self.kb, http_llm(server), "rm", "plan")
            t = agent.ask("銀行基金手收怎麼算？")
            answer_system = server.requests[-1]["payload"]["messages"][0]["content"]
        self.assertEqual((t["decision"], t["metrics"]), ("answer", ["bank.fund_fee_income"]))
        self.assertIn("DSFND.PB_FUND_SPREAD_DAILY", answer_system)
        self.assertNotIn("securities.fund_fee_income", answer_system)
        self.assertIn("answer", agent.system_prompts)

    def test_plan_blocked_after_retries(self):
        bad = plan_json(metrics=["bank.fx_aum"])
        t = Agent(self.kb, ScriptedLLM([bad, bad]), "rm", "plan").ask("外匯 AUM")
        self.assertEqual(t["decision"], "blocked")
        self.assertIn("無法在本體上驗證", t["answer"])
        self.assertEqual(len(t["gate"]), 2)

    def test_tools_native(self):
        with FakeQwen(QwenLikeBrain()) as server:
            t = Agent(self.kb, http_llm(server, tool_calling="auto"), "rm", "tools").ask("基金手收怎麼算？")
            tool_msgs = [m for m in server.requests[-1]["payload"]["messages"] if m["role"] == "tool"]
        self.assertEqual(t["tools_used"], ["list_metrics"])
        self.assertEqual(t["calls"][0]["tool_mode"], "native")
        self.assertEqual([bool(g["challenges"]) for g in t["gate"]], [True, False])  # 只選銀行被質疑，補上證券後通過
        self.assertEqual(sorted(t["metrics"]), ["bank.fund_fee_income", "securities.fund_fee_income"])
        self.assertEqual(len(tool_msgs), 1)

    def test_tools_fallback_to_prompt_when_server_rejects_tools(self):
        with FakeQwen(QwenLikeBrain(), tools_supported=False) as server:
            llm = http_llm(server, tool_calling="auto")
            agent = Agent(self.kb, llm, "rm", "tools")
            t = agent.ask("銀行基金手收？")
            payloads = [r["payload"] for r in server.requests if r["path"].endswith("/chat/completions")]
        self.assertEqual(t.get("tool_fallback"), "prompt")
        self.assertEqual(llm.tool_mode, "prompt")
        self.assertIn("<tool_call>", agent.system_prompts["tools"])
        self.assertNotIn("tools", payloads[-1])
        self.assertTrue(any("<tool_response>" in str(m["content"]) for m in payloads[-1]["messages"]))
        self.assertEqual(t["decision"], "answer")

    def test_baseline_uses_flat_dictionary(self):
        with FakeQwen(QwenLikeBrain()) as server:
            agent = Agent(self.kb, http_llm(server), "customer", "baseline")
            t = agent.ask("我的基金手收")
        self.assertNotIn("類別階層", agent.system_prompts["single"])
        self.assertIn("bank.fund_aum", agent.system_prompts["single"])  # 寬表沒有權限過濾
        self.assertEqual(t["gate"][0]["errors"][0]["code"], "not_permitted")

    def test_llm_error_is_recorded(self):
        llm = OpenAICompatible(LLMSettings(base_url="http://127.0.0.1:9/v1", model="q", retries=0, timeout=2))
        t = Agent(self.kb, llm, "rm", "plan").ask("x")
        self.assertEqual(t["decision"], "error")
        self.assertIn("連不到", t["error"])


class ScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()
        cls.questions = {q["id"]: q for q in evaluate.load_questions(ROOT / "eval" / "questions.yaml", cls.kb)}

    def outcome(self, qid, **transcript):
        base = {"decision": "answer", "metrics": [], "plan": {"classes": [], "terms": []}, "answer": ""}
        base.update(transcript)
        return evaluate.score(self.questions[qid], base, self.kb)

    def test_question_bank_is_consistent(self):
        self.assertEqual(len(self.questions), 33)

    def test_outcomes(self):
        self.assertEqual(self.outcome("d01", metrics=["bank.fund_fee_income"])["outcome"], "correct")
        self.assertEqual(self.outcome("d01", metrics=["bank.fund_aum"])["outcome"], "silent_wrong")
        self.assertEqual(self.outcome("d01", decision="clarify")["outcome"], "safe_miss")
        self.assertEqual(self.outcome("d01", decision="unparsed")["outcome"], "format_error")
        self.assertEqual(self.outcome("a01", decision="clarify")["outcome"], "correct")
        self.assertEqual(self.outcome("a01", metrics=["bank.fund_fee_income"])["outcome"], "silent_wrong")
        r = self.outcome("p01", decision="out_of_scope", metrics=["bank.fund_aum"])
        self.assertEqual(r["outcome"], "silent_wrong")  # 就算說不在範圍，結果裡帶出越權指標也算錯
        self.assertEqual(r["checks"]["leaks"], ["bank.fund_aum"])
        self.assertEqual(self.outcome("g02", decision="out_of_scope")["outcome"], "correct")
        self.assertEqual(self.outcome("g02", metrics=["bank.fx_fee_income"])["outcome"], "silent_wrong")
        self.assertEqual(self.outcome("d02", metrics=["bank.loan_lumx"])["checks"]["invalid_ids"], ["bank.loan_lumx"])

    def test_classes_and_mentions(self):
        ok = self.outcome("h03", plan={"classes": ["bank:FinancialAdvisor"], "terms": [{"classes": ["fh:Employee"]}]})
        self.assertEqual(ok["outcome"], "correct")
        miss = self.outcome("s02", metrics=["securities.total_aum", "securities.bond_aum"], answer="可以加總")
        self.assertEqual(miss["outcome"], "silent_wrong")
        hit = self.outcome("s02", metrics=["securities.total_aum", "securities.bond_aum"], answer="會重複計算")
        self.assertEqual(hit["outcome"], "correct")


class RunAndReportTest(unittest.TestCase):
    def test_cli_heuristic_eval_writes_reports_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            args = ["--config", str(ROOT / "config.yaml"), "--backend", "heuristic", "eval",
                    "--ids", "d01,a01,p03", "--modes", "context,plan", "--out", str(out)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            lines = (out / "results.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 6)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)  # 續跑：不重複
            self.assertEqual(len((out / "results.jsonl").read_text(encoding="utf-8").splitlines()), 6)
            md = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("## 1. 實驗設定", md)
            self.assertIn("heuristic", md)
            self.assertLess(md.index("## 1. 實驗設定"), md.index("## 3. 逐題紀錄"))
            html = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn('"question_id": "a01"', html)
            self.assertTrue((out / "prompts").is_dir())
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(set(summary["modes"]), {"context", "plan"})
            self.assertEqual(report.write(out)["total"], 6)

    def test_ping_against_fake_server(self):
        import os
        for truncate, expected in ((None, 0), (1000, 1)):
            with FakeQwen(lambda m, t: ("tool", ("search_terms", {"query": "基金手收"})) if t else ("text", "二"),
                          truncate_to=truncate) as server:
                os.environ["C360A_BASE_URL"] = server.base_url
                try:
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code = main(["--config", str(ROOT / "config.yaml"), "ping"])
                finally:
                    del os.environ["C360A_BASE_URL"]
            self.assertEqual(code, expected, out.getvalue())
            text = out.getvalue()
            self.assertIn("Qwen/Qwen3-8B", text)
            self.assertIn("原生工具呼叫可用", text)
            self.assertIn("偵測到思考內容", text)
            self.assertIn("截斷" if truncate else "沒有截斷", text)

    def test_cli_misc_commands(self):
        cfg = ["--config", str(ROOT / "config.yaml")]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(cfg + ["check"]), 0)
            self.assertEqual(main(cfg + ["tool", "is_a", '{"class_id": "bank:BankAUM", "ancestor_id": "fh:AUM"}']), 0)
            self.assertEqual(main(cfg + ["--backend", "heuristic", "ask", "放款餘額", "--mode", "plan"]), 0)
        self.assertIn("題庫 33 題", out.getvalue())
        self.assertIn("bank.loan_lum", out.getvalue())


if __name__ == "__main__":
    unittest.main()


class McpServerTest(unittest.TestCase):
    def test_stdio_roundtrip(self):
        import subprocess
        import sys
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "get_metric", "arguments": {"metric_id": "bank.fund_aum"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "check_plan", "arguments": {"plan": '{"decision":"answer","metrics":["securities.total_fee_income"]}'}}},
            {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "context://customer"}},
            {"jsonrpc": "2.0", "id": 6, "method": "nope"},
        ]
        env = {"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}
        proc = subprocess.run([sys.executable, "-B", "-m", "c360_agent.mcp_server", "--role", "customer",
                               "--config", str(ROOT / "config.yaml")],
                              input="\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n",
                              capture_output=True, text=True, env=env, timeout=120)
        replies = {r["id"]: r for r in map(json.loads, proc.stdout.splitlines())}
        self.assertEqual(sorted(replies), [1, 2, 3, 4, 5, 6], proc.stderr)
        self.assertEqual(replies[1]["result"]["serverInfo"]["version"], "0.17.0")
        self.assertEqual(len(replies[2]["result"]["tools"]), 8)
        self.assertTrue(replies[3]["result"]["isError"])  # 客戶看不到銀行基金 AUM
        gate = json.loads(replies[4]["result"]["content"][0]["text"])
        self.assertEqual(gate["errors"][0]["code"], "not_permitted")
        self.assertIn("角色 客戶", replies[5]["result"]["contents"][0]["text"])
        self.assertEqual(replies[6]["error"]["code"], -32601)


class WorkflowModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_slot_validation_retry_then_answer(self):
        bad = '{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "income", "products": ["債券型"]}]}'
        good = '{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "fee", "products": ["基金"], "subsidiary": "bank"}]}'
        agent = Agent(self.kb, ScriptedLLM([bad, good, "銀行基金手收為 bank.fund_fee_income。"]), "rm", "workflow")
        t = agent.ask("銀行基金手收是哪個指標？")
        self.assertEqual(t["gate"][0]["errors"][0]["code"], "workflow_schema")
        self.assertIn("債券型", t["gate"][0]["errors"][0]["message"])
        self.assertEqual((t["decision"], t["metrics"]), ("answer", ["bank.fund_fee_income"]))
        self.assertIn("可用：", agent.system_prompts["workflow"] + t["gate"][0]["errors"][0]["message"])

    def test_challenge_returns_execution_results(self):
        one_side = '{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "fee", "products": ["基金"], "subsidiary": "bank"}]}'
        both = '{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "fee", "products": ["基金"]}]}'
        llm = ScriptedLLM([one_side, both, "兩邊都有。"])
        t = Agent(self.kb, llm, "rm", "workflow").ask("基金手收怎麼算？")
        self.assertTrue(t["gate"][0]["challenges"])
        self.assertTrue(llm.requests[1]["messages"][-1]["content"].startswith("範本執行結果"))
        self.assertEqual(sorted(t["metrics"]), ["bank.fund_fee_income", "securities.fund_fee_income"])

    def test_empty_lookup_becomes_out_of_scope_and_concepts(self):
        llm = ScriptedLLM(['{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "aum", "products": ["外匯"]}]}'])
        t = Agent(self.kb, llm, "rm", "workflow").ask("銀行外匯的 AUM 怎麼查？")
        self.assertEqual(t["decision"], "out_of_scope")
        llm = ScriptedLLM(['{"decision": "answer", "calls": [{"template": "concept_is_a", "a": "bank:FinancialAdvisor", "b": "fh:Employee"}]}',
                           "理專是職員。"])
        t = Agent(self.kb, llm, "rm", "workflow").ask("理專算不算職員？")
        self.assertEqual(t["plan"]["is_a"], [["bank:FinancialAdvisor", "fh:Employee"]])
        self.assertEqual(t["workflow_log"][0]["log"][0]["result"]["is_a"], True)

    def test_customer_cannot_reach_denied_metrics_through_templates(self):
        llm = ScriptedLLM(['{"decision": "answer", "calls": [{"template": "metric_lookup", "kind": "aum", "products": ["基金"]}]}', "x"])
        t = Agent(self.kb, llm, "customer", "workflow").ask("我的基金 AUM")
        self.assertEqual(t["metrics"], ["securities.fund_aum"])  # 銀行基金 AUM 被權限過濾，範本根本查不到


class BacklogTest(unittest.TestCase):
    def test_buckets(self):
        from c360_agent import backlog
        challenge = {"code": "anchor_missing", "message": "問題提到「台幣」，但選到的指標都沒有涵蓋 bank:TWDFinancialProduct"}
        gate = lambda ch: {"passed": True, "errors": [], "challenges": ch, "warnings": []}  # noqa: E731
        results = [
            {"question_id": "y09", "mode": "plan", "question": "台幣計價的基金 AUM", "outcome": "correct",
             "transcript": {"gate": [gate([challenge])]}},                      # 最後仍被質疑但答對 → 誤質疑
            {"question_id": "a01", "mode": "plan", "question": "基金手收", "outcome": "correct",
             "transcript": {"gate": [gate([{"code": "ambiguous_subsidiary", "message": "x"}]), gate([])]}},  # 促成修正
            {"question_id": "d01", "mode": "context", "question": "基金手收", "outcome": "silent_wrong",
             "transcript": {"gate": [gate([{"code": "anchor_conflict", "message": "y"}])]}},                # 答案仍錯
        ]
        items = {i["key"]: i for i in backlog.build(results)}
        self.assertEqual(items["anchor_missing｜台幣"]["false_count"], 1)
        self.assertEqual(items["ambiguous_subsidiary"]["fixed_count"], 1)
        self.assertEqual(items["anchor_conflict"]["valid_count"], 1)
        self.assertIn("補同義詞", backlog.render(list(items.values())))


class EscalationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def test_persisting_after_challenge_escalates_to_user(self):
        one_side = plan_json(metrics=["bank.fund_fee_income"])
        t = Agent(self.kb, ScriptedLLM([one_side, one_side]), "rm", "plan").ask("基金手收怎麼算？")
        self.assertEqual(t["decision"], "clarify")
        self.assertTrue(t["escalated"])
        self.assertIn("securities.fund_fee_income", t["answer"])
        self.assertEqual(t["llm_calls"], 2)  # 不必再呼叫作答階段

    def test_warn_policy_keeps_answer(self):
        one_side = plan_json(metrics=["bank.fund_fee_income"])
        self.kb.settings.agent["challenge_policy"] = "warn"
        try:
            t = Agent(self.kb, ScriptedLLM([one_side, one_side, "銀行基金手收。"]), "rm", "plan").ask("基金手收怎麼算？")
        finally:
            self.kb.settings.agent["challenge_policy"] = "escalate"
        self.assertEqual(t["decision"], "answer")
        self.assertNotIn("escalated", t)


class HandoffTest(unittest.TestCase):
    def test_handoff_redacts_for_receiver_role(self):
        from c360_agent import plan as planning
        kb = shared_kb()
        plan = planning.normalize({"decision": "answer", "metrics": ["bank.fund_aum", "securities.fund_aum", "securities.total_fee_income"],
                                   "terms": [{"text": "基金", "classes": [], "metrics": ["bank.fund_aum", "securities.fund_aum"]}]})
        r = planning.handoff(kb, plan, "基金 AUM", "customer")
        self.assertEqual(r["status"], "redacted")
        self.assertEqual(r["plan"]["metrics"], ["securities.fund_aum"])
        self.assertEqual(sorted(r["removed"]), ["bank.fund_aum", "securities.total_fee_income"])  # 總指標繼承分項拒絕
        only_bank = planning.normalize({"decision": "answer", "metrics": ["bank.fund_aum"]})
        self.assertEqual(planning.handoff(kb, only_bank, "", "customer")["plan"]["decision"], "out_of_scope")
        fake = planning.normalize({"decision": "answer", "metrics": ["bank.nope"]})
        self.assertEqual(planning.handoff(kb, fake, "", "customer")["status"], "blocked")
