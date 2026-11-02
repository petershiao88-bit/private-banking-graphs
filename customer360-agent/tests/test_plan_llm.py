"""語意計畫解析與本體檢查；Qwen 輸出格式（思考、工具呼叫）與 HTTP 用戶端。"""

import json
from pathlib import Path
import unittest

from tests import shared_kb
from tests.fake_server import FakeQwen
from c360_agent import plan as planning
from c360_agent.llm import (LLMError, OpenAICompatible, ToolsUnsupported, parse_prompt_tool_calls,
                            split_thinking)
from c360_agent.settings import LLMSettings


class ExtractTest(unittest.TestCase):
    def test_fenced_last_block_wins(self):
        text = '說明 ```json\n{"decision":"clarify"}\n``` 後來改成 ```json\n{"decision":"answer","metrics":["a"]}\n```'
        self.assertEqual(planning.extract_json(text)["decision"], "answer")

    def test_bare_object_with_braces_in_strings(self):
        text = '我的結論如下 {"decision": "out_of_scope", "reason": "沒有 {外匯 AUM}"} 完畢'
        self.assertEqual(planning.extract_json(text)["reason"], "沒有 {外匯 AUM}")

    def test_normalize_tolerates_variants(self):
        plan = planning.normalize({"decision": "Answer", "metrics": "bank.fund_aum",
                                   "is_a": [{"class": "bank:BankAUM", "ancestor": "fh:AUM"}],
                                   "classes": [{"id": "`bank:BankAUM`"}]})
        self.assertEqual(plan["decision"], "answer")
        self.assertEqual(plan["metrics"], ["bank.fund_aum"])
        self.assertEqual(plan["is_a"], [["bank:BankAUM", "fh:AUM"]])
        self.assertEqual(plan["classes"], ["bank:BankAUM"])

    def test_parse_errors(self):
        self.assertIsNotNone(planning.parse("沒有 JSON")[1])
        self.assertIsNotNone(planning.parse('{"is_a": [["only-one"]]}')[1])


class GateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = shared_kb()

    def check(self, raw, question="", role="rm"):
        return planning.Gate(self.kb, role).check(planning.normalize(raw), question)

    def codes(self, result):
        return {e["code"] for e in result["errors"] + result["challenges"]}

    def test_valid_plan_passes(self):
        r = self.check({"decision": "answer", "metrics": ["bank.fund_fee_income"],
                        "is_a": [["bank:BankFeeIncome", "fh:Metric"]], "ontology_version": "0.17.0"}, "銀行基金手收")
        self.assertTrue(r["passed"], r)

    def test_each_error_code(self):
        self.assertEqual(self.codes(self.check({"decision": "maybe"})), {"schema"})
        self.assertIn("unknown_class", self.codes(self.check({"decision": "answer", "classes": ["bank:Fund"]})))
        self.assertIn("unknown_metric", self.codes(self.check({"decision": "answer", "metrics": ["bank.fx_aum"]})))
        self.assertIn("gap_metric", self.codes(self.check({"decision": "answer",
                                                           "metrics": ["securities.taiwan_stock_fee_income"]}, "台股")))
        self.assertIn("not_permitted", self.codes(self.check({"decision": "answer", "metrics": ["bank.fund_aum"]},
                                                             "銀行", role="customer")))
        self.assertIn("false_is_a", self.codes(self.check({"decision": "answer", "classes": ["bank:ETFProduct"],
                                                           "is_a": [["bank:ETFProduct", "bank:FundProduct"]]})))
        self.assertIn("empty_answer", self.codes(self.check({"decision": "answer"})))
        self.assertIn("schema", self.codes(self.check({"decision": "clarify"})))
        self.assertIn("schema", self.codes(self.check({"decision": "out_of_scope"})))

    def test_subsidiary_ambiguity_is_derived_from_ontology(self):
        r = self.check({"decision": "answer", "metrics": ["bank.fund_fee_income"]}, "基金手收怎麼算")
        self.assertEqual(self.codes(r), {"ambiguous_subsidiary"})
        self.assertTrue(self.check({"decision": "answer", "metrics": ["bank.fund_fee_income"]}, "銀行基金手收")["passed"])
        both = self.check({"decision": "answer", "metrics": ["bank.fund_fee_income", "securities.fund_fee_income"]},
                          "基金手收怎麼算")
        self.assertTrue(both["passed"])
        stock = self.check({"decision": "answer", "metrics": ["bank.overseas_stock_aum"]}, "海外股票 AUM")
        self.assertTrue(stock["passed"])  # 歧義是「質疑」，不是硬擋
        self.assertIn("securities.foreign_stock_aum", stock["challenges"][0]["message"])
        # 客戶看不到銀行基金手收，就沒有歧義可言
        cust = planning.Gate(self.kb, "customer").check(
            planning.normalize({"decision": "answer", "metrics": ["securities.bond_aum"]}), "債券 AUM")
        self.assertTrue(cust["passed"], cust)

    def test_lexical_checks_are_challenges_not_blocks(self):
        g = planning.Gate(self.kb, "rm")
        # 只有字面依據的問題 → challenges；本體能確定推出的 → errors
        r = self.check({"decision": "answer", "metrics": ["bank.etf_fee_income"]}, "銀行基金手收")
        self.assertTrue(r["passed"])
        self.assertEqual({e["code"] for e in r["challenges"]}, {"anchor_missing", "anchor_conflict"})
        self.assertFalse(self.check({"decision": "answer", "metrics": ["bank.fund_aum"]}, "", role="customer")["passed"])
        # 修飾語不是錨點；縮寫與限定詞可以分辨銀行／證券；理專由本體推得屬於銀行
        self.assertEqual(self.check({"decision": "answer", "metrics": ["bank.fund_fee_income", "securities.fund_fee_income"]},
                                    "債券型基金的手收")["challenges"], [])
        self.assertEqual(g.subsidiary_twins(["bank.dci_fee_income"], "DCI 手收"), {})
        self.assertEqual(g.subsidiary_twins(["bank.overseas_bond_trust_aum"], "信託的海外債 AUM"), {})
        self.assertIn("理專", g.cues["bank"])
        self.assertEqual(self.check({"decision": "answer", "metrics": ["bank.fund_fee_income"]}, "理專賣基金的佣金")["challenges"], [])

    def test_term_and_exclusion_consistency(self):
        r = self.check({"decision": "answer", "terms": [{"text": "外匯 AUM", "classes": ["fh:AUM", "bank:ForeignExchangeProduct"],
                                                          "metrics": ["bank.fx_fee_income"]}], "metrics": ["bank.fx_fee_income"]})
        self.assertEqual(r["errors"][0]["code"], "term_metric_mismatch")
        r = self.check({"decision": "answer", "metrics": ["bank.overseas_stock_aum", "securities.bond_aum"],
                        "exclude": ["subsidiary:securities"]}, "不屬於證券的海外商品 AUM")
        self.assertEqual([e["code"] for e in r["errors"]], ["exclusion_violated"])

    def test_gold_plans_never_hard_blocked(self):
        """三份題庫的正確計畫：硬擋誤擋必須是 0（質疑可以有少量）。"""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
        import common
        for name in ("questions.yaml", "holdout.yaml", "holdout2.yaml", "holdout3.yaml"):
            for q in common.questions(name):
                r = planning.Gate(self.kb, q["role"]).check(common.gold_plan(q), q["question"])
                self.assertEqual(r["errors"], [], (name, q["id"]))

    def test_summary_with_components_warns(self):
        r = self.check({"decision": "answer", "metrics": ["securities.total_aum", "securities.bond_aum"]}, "證券")
        self.assertTrue(r["passed"])
        self.assertEqual(r["warnings"][0]["code"], "summary_with_components")

    def test_version_mismatch_warns(self):
        r = self.check({"decision": "answer", "classes": ["fh:AUM"], "ontology_version": "0.16.0"})
        self.assertTrue(r["passed"])
        self.assertEqual(r["warnings"][0]["code"], "version")

    def test_feedback_lists_errors(self):
        r = self.check({"decision": "answer", "metrics": ["bank.fx_aum"]})
        self.assertIn("unknown_metric", planning.format_feedback(r))


class QwenFormatTest(unittest.TestCase):
    def test_split_thinking_variants(self):
        self.assertEqual(split_thinking("<think>a</think>\n答案"), ("答案", "a"))
        self.assertEqual(split_thinking("想法\n</think>\n答案"), ("答案", "想法"))
        self.assertEqual(split_thinking("答案", "欄位思考"), ("答案", "欄位思考"))
        self.assertEqual(split_thinking("<think>被截斷"), ("", "被截斷"))
        self.assertEqual(split_thinking("沒有思考"), ("沒有思考", ""))

    def test_prompt_tool_calls(self):
        calls, rest = parse_prompt_tool_calls('先查\n<tool_call>\n{"name": "is_a", "arguments": {"class_id": "a", "ancestor_id": "b"}}\n</tool_call>'
                                              '\n<tool_call>{"name":"list_gaps","arguments":{}}</tool_call>')
        self.assertEqual([c["name"] for c in calls], ["is_a", "list_gaps"])
        self.assertEqual(json.loads(calls[0]["arguments"])["class_id"], "a")
        self.assertEqual(rest, "先查")
        bad, _ = parse_prompt_tool_calls("<tool_call>{oops</tool_call>")
        self.assertEqual(bad[0]["name"], "__invalid__")


def settings_for(server, **kw):
    return LLMSettings(base_url=server.base_url, model=kw.pop("model", "auto"), retries=kw.pop("retries", 0),
                       timeout=10, **kw)


class HttpClientTest(unittest.TestCase):
    def test_models_auto_and_thinking_tags(self):
        with FakeQwen(lambda m, t: ("text", "二")) as server:
            llm = OpenAICompatible(settings_for(server))
            r = llm.chat([{"role": "user", "content": "1+1"}])
            self.assertEqual(llm.model, "Qwen/Qwen3-8B")
            self.assertEqual((r.content, r.thinking), ("二", "先找對應的類別，再確認上層鏈。"))
            self.assertEqual(r.usage["completion_tokens"], 42)
            self.assertNotIn("tools", server.requests[-1]["payload"])

    def test_reasoning_field_and_open_think(self):
        for mode in ("field", "open"):
            with FakeQwen(lambda m, t: ("text", "好"), thinking=mode) as server:
                r = OpenAICompatible(settings_for(server)).chat([{"role": "user", "content": "x"}])
                self.assertEqual(r.content, "好", mode)
                self.assertTrue(r.thinking, mode)

    def test_native_tool_calls(self):
        with FakeQwen(lambda m, t: ("tool", ("search_terms", {"query": "基金"}))) as server:
            llm = OpenAICompatible(settings_for(server, tool_calling="auto"))
            r = llm.chat([{"role": "user", "content": "x"}], tools=[{"type": "function", "function": {"name": "search_terms"}}])
            self.assertEqual((r.tool_mode, r.tool_calls[0]["name"]), ("native", "search_terms"))
            self.assertEqual(llm.tool_mode, "native")

    def test_tool_call_text_without_parser(self):
        with FakeQwen(lambda m, t: ("tool", ("list_gaps", {})), tool_parser=False) as server:
            r = OpenAICompatible(settings_for(server)).chat([{"role": "user", "content": "x"}],
                                                            tools=[{"type": "function", "function": {"name": "list_gaps"}}])
            self.assertEqual((r.tool_mode, r.tool_calls[0]["name"]), ("prompt", "list_gaps"))

    def test_tools_rejected_raises_for_fallback(self):
        with FakeQwen(lambda m, t: ("text", "x"), tools_supported=False) as server:
            llm = OpenAICompatible(settings_for(server, tool_calling="auto"))
            with self.assertRaises(ToolsUnsupported):
                llm.chat([{"role": "user", "content": "x"}], tools=[{"type": "function", "function": {"name": "a"}}])
            llm.tool_mode = "native"
            with self.assertRaises(LLMError):
                llm.chat([{"role": "user", "content": "x"}], tools=[{"type": "function", "function": {"name": "a"}}])

    def test_retry_on_server_error_and_extra_body(self):
        with FakeQwen(lambda m, t: ("text", "ok"), fail_first=1) as server:
            llm = OpenAICompatible(settings_for(server, model="qwen", retries=1,
                                                extra_body={"chat_template_kwargs": {"enable_thinking": False}}))
            self.assertEqual(llm.chat([{"role": "user", "content": "x"}]).content, "ok")
            self.assertEqual(server.requests[-1]["payload"]["chat_template_kwargs"], {"enable_thinking": False})
            self.assertEqual(llm.tokenize("基金手收"), 2)

    def test_thinking_off(self):
        with FakeQwen(lambda m, t: ("text", "ok"), thinking="none") as server:
            llm = OpenAICompatible(settings_for(server, model="qwen", thinking="off"))
            llm.chat([{"role": "system", "content": "s"}, {"role": "user", "content": "問題"}])
            payload = server.requests[-1]["payload"]
            self.assertEqual(payload["messages"][-1]["content"], "問題 /no_think")
            self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
        with FakeQwen(lambda m, t: ("text", "ok"), thinking="none", reject_kwargs=True) as server:
            llm = OpenAICompatible(settings_for(server, model="qwen", thinking="off"))
            self.assertEqual(llm.chat([{"role": "user", "content": "x"}]).content, "ok")
            self.assertNotIn("chat_template_kwargs", server.requests[-1]["payload"])

    def test_unreachable_endpoint(self):
        llm = OpenAICompatible(LLMSettings(base_url="http://127.0.0.1:9/v1", model="q", retries=0, timeout=2))
        with self.assertRaises(LLMError):
            llm.chat([{"role": "user", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
