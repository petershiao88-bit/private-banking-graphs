"""單 agent 的四種模式（同一個模型、同一題，差別只在本體怎麼進入 CoT）。

| 模式      | 本體進入方式                                    | 呼叫次數         | 本體檢查 |
|-----------|-------------------------------------------------|------------------|----------|
| baseline  | 平鋪的指標資料字典（模擬寬表 agent）             | 1                | 只記錄   |
| context   | 角色 context 包整包放進 system prompt            | 1                | 只記錄   |
| plan      | context 包＋先交語意計畫 → 本體檢查 → 再作答     | 2～(2+重試)      | 強制     |
| tools     | 只給類別骨架，指標細節用工具查 → 本體檢查        | 多輪             | 強制     |
| workflow  | 只給類別骨架＋範本；LLM 填範本欄位／拆題，本體執行 → 本體檢查 | 2～4  | 強制     |

「只記錄」：照樣算出檢查結果寫進紀錄，但不擋回答，用來看「如果有檢查，會擋下什麼」。
"""

import json
import time

from . import packs, plan as planning
from .knowledge import Knowledge
from .llm import LLMError, ToolsUnsupported
from .tools import ToolBox, describe_for_prompt
from .workflows import WorkflowError, Workflows

MODES = ("baseline", "context", "plan", "tools", "workflow")

AGENT_SYSTEM = """\
你是金控私人銀行的語意助理（單一 agent）。你的工作是把使用者的業務問題對應到本體裡的類別與指標，
說明定義、範圍、上層關係與資料來源（底表），讓後續的取數工具能用對的指標。
你不能查實際數字，也不能自行推算金額。回答一律用繁體中文。
目前使用者的角色：{role_label}（{role}）。本體版號：{version}。
"""

BASELINE_SYSTEM = """\
你是金控私人銀行的資料助理。請依下方的指標資料字典，回答使用者的問題：找出對應的指標並說明來源底表。
你不能查實際數字，也不能自行推算金額。回答一律用繁體中文。
"""

TOOLS_NOTE = """\
## 工具模式

指標清單、待定範圍與指標細節不在這份 context 裡，請用工具查詢後再回答：
先用 search_terms 把問題裡的用語對到 ID，需要時用 list_metrics／get_metric／get_class／is_a／list_gaps 確認。
只能使用工具回傳過的指標與類別 ID。
"""

PROMPT_TOOL_FORMAT = """\
## 可用工具

{tools}

呼叫方式：輸出一個或多個
<tool_call>
{{"name": "工具名稱", "arguments": {{"參數": "值"}}}}
</tool_call>
呼叫工具時不要寫其他內容，工具結果會以 <tool_response> 回給你。查夠了就直接輸出最終回答，不要再有 <tool_call>。
"""

ANSWER_STAGE = """\
## 已通過本體檢查的語意計畫

```json
{plan}
```

## 指標卡片（只可使用這些指標）

```json
{cards}
```
{class_cards}{warnings}
請依上述內容回答使用者：說明採用的指標（名稱與 ID）、所屬類別與上層鏈、衡量的商品、資料來源底表與待確認的口徑。
引用本體版號 {version}。不可加入計畫以外的指標，不可自行推算金額。
"""


class Agent:
    def __init__(self, kb: Knowledge, llm, role, mode, level=None, strict_subsidiary=True):
        if mode not in MODES:
            raise ValueError(f"mode 只能是 {MODES}")
        self.kb, self.llm, self.role, self.mode = kb, llm, role, mode
        self.level = level or kb.settings.agent.get("pack_level", "compact")
        self.max_rounds = int(kb.settings.agent.get("max_tool_rounds", 8))
        self.plan_retries = int(kb.settings.agent.get("plan_retries", 1))
        self.gate = planning.Gate(kb, role, strict_subsidiary=strict_subsidiary)
        if mode == "baseline":
            self.pack = packs.build(kb, "baseline")
        elif mode in ("tools", "workflow"):
            self.pack = packs.build(kb, role, self.level, skeleton=True)
            self.workflows = Workflows(kb) if mode == "workflow" else None
        else:
            self.pack = packs.build(kb, role, self.level)
        self.system_prompts = {}

    # ------------------------------------------------------------------ 共用

    def _header(self):
        return AGENT_SYSTEM.format(role_label=self.kb.roles[self.role], role=self.role, version=self.kb.version)

    def _system(self, stage):
        if self.mode == "baseline":
            text = BASELINE_SYSTEM + "\n" + self.pack["markdown"] + "\n" + planning.ANSWER_CONTRACT
        elif self.mode == "context":
            text = self._header() + "\n" + self.pack["markdown"] + "\n" + planning.ANSWER_CONTRACT
        elif self.mode == "plan":
            text = self._header() + "\n" + self.pack["markdown"] + "\n" + _contract(self.kb)
        elif self.mode == "workflow":
            text = self._header() + "\n" + self.pack["markdown"] + "\n" + self.workflows.contract()
        else:
            text = self._header() + "\n" + self.pack["markdown"] + "\n" + TOOLS_NOTE + "\n" + planning.ANSWER_CONTRACT
            if self.llm.tool_mode == "prompt":
                text += "\n" + PROMPT_TOOL_FORMAT.format(tools=describe_for_prompt())
        self.system_prompts[stage] = text
        return text

    def _new_transcript(self, question):
        return {"question": question, "role": self.role, "mode": self.mode, "level": self.pack["level"],
                "ontology_version": self.kb.version, "knowledge_fingerprint": self.kb.fingerprint()[:16],
                "pack": {"role": self.pack["role"], "level": self.pack["level"], "sha256": self.pack["sha256"][:16],
                         "tokens_est": self.pack["tokens_est"]},
                "model": None, "calls": [], "gate": [], "plan": None, "decision": None, "metrics": [],
                "classes": [], "answer": "", "error": None, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def _call(self, transcript, stage, messages, tools=None, round_no=0):
        result = self.llm.chat(messages, tools=tools)
        transcript["model"] = result.model
        transcript["calls"].append({"stage": stage, "round": round_no, "content": result.content,
                                    "thinking": result.thinking, "tool_calls": result.tool_calls,
                                    "tool_results": [], "usage": result.usage, "latency": result.latency,
                                    "finish_reason": result.finish_reason, "tool_mode": result.tool_mode})
        return result

    def _finish(self, transcript):
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        for call in transcript["calls"]:
            for key in usage:
                usage[key] += int(call["usage"].get(key) or 0)
        transcript["usage"] = usage
        transcript["latency"] = round(sum(c["latency"] for c in transcript["calls"]), 3)
        transcript["llm_calls"] = len(transcript["calls"])
        transcript["tool_calls"] = sum(len(c["tool_calls"]) for c in transcript["calls"])
        transcript["system_prompt_sha"] = {k: _sha(v) for k, v in self.system_prompts.items()}
        return transcript

    def _record_plan(self, transcript, plan, question, enforced):
        result = self.gate.check(plan, question)
        transcript["gate"].append({**result, "enforced": enforced})
        return result

    # ------------------------------------------------------------------ 入口

    def ask(self, question):
        transcript = self._new_transcript(question)
        try:
            if self.mode in ("baseline", "context"):
                self._single(transcript, question)
            elif self.mode == "plan":
                self._plan_then_answer(transcript, question)
            elif self.mode == "workflow":
                self._workflow(transcript, question)
            else:
                self._tools_loop(transcript, question)
        except LLMError as exc:
            transcript["decision"] = "error"
            transcript["error"] = str(exc)
        return self._finish(transcript)

    # ------------------------------------------------------------------ baseline／context：一次呼叫

    def _single(self, t, question):
        messages = [{"role": "system", "content": self._system("single")}, {"role": "user", "content": question}]
        result = self._call(t, "single", messages)
        self._adopt_answer(t, question, result.content, enforced=False)

    def _adopt_answer(self, t, question, content, enforced):
        plan, error = planning.parse(content)
        t["answer"] = _strip_json(content)
        if plan is None:
            t["decision"] = "unparsed"
            t["error"] = error
            return None
        t["plan"] = plan
        gate = self._record_plan(t, plan, question, enforced) if self.mode != "baseline" else self._baseline_gate(t, plan, question)
        t["decision"] = plan["decision"] or "unparsed"
        t["metrics"], t["classes"] = plan["metrics"], plan["classes"]
        return gate

    def _baseline_gate(self, t, plan, question):
        """baseline 沒有角色概念，但仍用使用者的角色計算檢查結果，看寬表 agent 會不會越權或亂用 ID。"""
        return self._record_plan(t, plan, question, enforced=False)

    # ------------------------------------------------------------------ plan：計畫 → 檢查 → 回答

    def _plan_then_answer(self, t, question):
        messages = [{"role": "system", "content": self._system("plan")}, {"role": "user", "content": question}]
        plan, retries, challenged, attempt = None, 0, False, 0
        while True:
            result = self._call(t, "plan", messages, round_no=attempt)
            attempt += 1
            plan, error = planning.parse(result.content)
            if plan is None:
                t["gate"].append({"passed": False, "errors": [{"code": "unparsed", "message": error}],
                                  "challenges": [], "warnings": [], "metrics": [], "enforced": True})
                feedback = f"無法解析你的輸出（{error}）。請只輸出一個 JSON 物件。"
            else:
                gate = self._record_plan(t, plan, question, enforced=True)
                if gate["passed"] and (not gate["challenges"] or challenged):
                    break                                  # 質疑已問過一次：模型堅持就放行，質疑轉為作答提醒
                if gate["passed"]:
                    challenged = True
                    feedback = planning.format_challenge(gate)
                    messages += [{"role": "assistant", "content": result.content}, {"role": "user", "content": feedback}]
                    continue
                feedback = planning.format_feedback(gate)
                plan = None
            if retries >= self.plan_retries:
                break
            retries += 1
            messages += [{"role": "assistant", "content": result.content}, {"role": "user", "content": feedback}]
        if plan is None:
            self._blocked(t)
            return
        if self._escalate(t, plan):
            return
        t["plan"] = plan
        t["decision"], t["metrics"], t["classes"] = plan["decision"], plan["metrics"], plan["classes"]
        if plan["decision"] == "clarify":
            t["answer"] = plan["clarification"]
            return
        if plan["decision"] == "out_of_scope":
            t["answer"] = plan["reason"]
            return
        gate = t["gate"][-1]
        answer_messages = [{"role": "system", "content": self._header() + "\n" + self._answer_context(plan, gate)},
                           {"role": "user", "content": question}]
        self.system_prompts["answer"] = answer_messages[0]["content"]
        result = self._call(t, "answer", answer_messages)
        t["answer"] = _strip_json(result.content)

    # ------------------------------------------------------------------ workflow：LLM 填範本 → 本體執行 → 檢查 → 回答

    def _workflow(self, t, question):
        wf = self.workflows
        messages = [{"role": "system", "content": self._system("workflow")}, {"role": "user", "content": question}]
        plan, retries, challenged, attempt = None, 0, False, 0
        t["workflow_log"] = []
        while True:
            result = self._call(t, "workflow", messages, round_no=attempt)
            attempt += 1
            try:
                request = wf.parse(result.content)
            except (WorkflowError, planning.PlanError) as exc:
                t["gate"].append({"passed": False, "errors": [{"code": "workflow_schema", "message": str(exc)}],
                                  "challenges": [], "warnings": [], "metrics": [], "enforced": True})
                feedback = f"範本呼叫不合法：{exc}。請修正後重新輸出完整的 JSON。"
                plan = None
            else:
                plan, log = wf.execute(request, self.role)
                t["workflow_log"].append({"request": request, "log": log})
                gate = self._record_plan(t, plan, question, enforced=True)
                if gate["passed"] and (not gate["challenges"] or challenged):
                    break
                results = json.dumps(log, ensure_ascii=False)
                if gate["passed"]:
                    challenged = True
                    messages += [{"role": "assistant", "content": result.content},
                                 {"role": "user", "content": "範本執行結果：" + results + "\n\n" + planning.format_challenge(gate)}]
                    continue
                feedback = "範本執行結果：" + results + "\n\n" + planning.format_feedback(gate)
                plan = None
            if retries >= self.plan_retries:
                break
            retries += 1
            messages += [{"role": "assistant", "content": result.content}, {"role": "user", "content": feedback}]
        if plan is None:
            self._blocked(t)
            return
        if self._escalate(t, plan):
            return
        t["plan"] = plan
        t["decision"], t["metrics"], t["classes"] = plan["decision"], plan["metrics"], plan["classes"]
        if plan["decision"] == "clarify":
            t["answer"] = plan["clarification"]
            return
        if plan["decision"] == "out_of_scope":
            t["answer"] = plan["reason"]
            return
        gate = t["gate"][-1]
        answer_messages = [{"role": "system", "content": self._header() + "\n" + self._answer_context(plan, gate)},
                           {"role": "user", "content": question}]
        self.system_prompts["answer"] = answer_messages[0]["content"]
        result = self._call(t, "answer", answer_messages)
        t["answer"] = _strip_json(result.content)

    def _answer_context(self, plan, gate):
        cards = [self.kb.metric_card(mid, "full") for mid in gate["metrics"]]
        class_ids = list(dict.fromkeys(plan["classes"] + [c for term in plan["terms"] for c in term["classes"]]))
        class_cards = ""
        if class_ids:
            view = [self.kb.class_card(c) for c in class_ids if c in self.kb.classes]
            class_cards = "\n## 類別卡片\n\n```json\n" + json.dumps(view, ensure_ascii=False, indent=1) + "\n```\n"
        notes = gate["warnings"] + gate.get("challenges", [])
        warnings = ""
        if notes:
            warnings = "\n## 提醒（回答中必須說明）\n\n" + "\n".join(f"- {w['message']}" for w in notes) + "\n"
        return ANSWER_STAGE.format(plan=json.dumps(plan, ensure_ascii=False, indent=1),
                                   cards=json.dumps(cards, ensure_ascii=False, indent=1),
                                   class_cards=class_cards, warnings=warnings, version=self.kb.version)

    def _escalate(self, t, plan):
        """質疑退回模型一次之後，若最後的計畫仍被質疑：預設轉成向使用者澄清（實驗 5：避免附和翻盤與默默答錯）；
        agent.challenge_policy=warn 時則照答、質疑轉成作答提醒。"""
        gate = t["gate"][-1] if t["gate"] else None
        policy = self.kb.settings.agent.get("challenge_policy", "escalate")
        if policy != "escalate" or not gate or not gate.get("challenges") or plan["decision"] != "answer":
            return False
        t["plan"] = plan
        t["decision"] = "clarify"
        t["metrics"], t["classes"] = plan["metrics"], plan["classes"]
        t["escalated"] = True
        items = "\n".join(f"- {c['message']}" for c in gate["challenges"])
        names = "、".join(f"{self.kb.metrics[m].name}（{m}）" for m in plan["metrics"] if m in self.kb.metrics)
        t["answer"] = (f"這題目前找到的指標是：{names or '（無）'}。但本體檢查對照您的問題後仍有疑問，請先確認：\n{items}")
        return True

    def _blocked(self, t):
        last = t["gate"][-1] if t["gate"] else {"errors": []}
        t["decision"] = "blocked"
        t["metrics"], t["classes"] = [], []
        reasons = "；".join(e["message"] for e in last["errors"]) or "沒有產生可檢查的計畫"
        t["answer"] = f"這個問題目前無法在本體上驗證，系統不提供回答。原因：{reasons}"

    # ------------------------------------------------------------------ tools：多輪工具呼叫

    def _tools_loop(self, t, question):
        box = ToolBox(self.kb, self.role)
        try:
            self._run_tools(t, question, box)
        except ToolsUnsupported:
            self.llm.tool_mode = "prompt"   # 伺服器不收 tools 參數：改用提示詞工具呼叫，從頭再跑
            t["calls"].clear()
            t["gate"].clear()
            t["tool_fallback"] = "prompt"
            self._run_tools(t, question, ToolBox(self.kb, self.role))

    def _run_tools(self, t, question, box):
        messages = [{"role": "system", "content": self._system("tools")}, {"role": "user", "content": question}]
        schemas = box.schemas()
        retries, challenged = 0, False
        for round_no in range(self.max_rounds + self.plan_retries + 1):
            native = self.llm.tool_mode in ("auto", "native")
            result = self._call(t, "tools", messages, tools=schemas if native else None, round_no=round_no)
            if result.tool_calls:
                record = t["calls"][-1]
                if result.tool_mode == "native":
                    messages.append({"role": "assistant", "content": result.content or "",
                                     "tool_calls": [{"id": c["id"], "type": "function",
                                                     "function": {"name": c["name"], "arguments": c["arguments"]}}
                                                    for c in result.tool_calls]})
                    for c in result.tool_calls:
                        output = box.call(c["name"], c["arguments"])
                        record["tool_results"].append(output)
                        messages.append({"role": "tool", "tool_call_id": c["id"], "name": c["name"],
                                         "content": json.dumps(output, ensure_ascii=False)})
                else:
                    blocks = "\n".join(f'<tool_call>\n{json.dumps({"name": c["name"], "arguments": _loads(c["arguments"])}, ensure_ascii=False)}\n</tool_call>'
                                       for c in result.tool_calls)
                    messages.append({"role": "assistant", "content": blocks})
                    outputs = []
                    for c in result.tool_calls:
                        output = box.call(c["name"], c["arguments"])
                        record["tool_results"].append(output)
                        outputs.append("<tool_response>\n" + json.dumps(output, ensure_ascii=False) + "\n</tool_response>")
                    messages.append({"role": "user", "content": "\n".join(outputs)})
                if round_no >= self.max_rounds - 1:
                    messages.append({"role": "user", "content": "工具呼叫次數已達上限，請直接輸出最終回答與 JSON 結果。"})
                continue
            plan, error = planning.parse(result.content)
            if plan is None:
                t["gate"].append({"passed": False, "errors": [{"code": "unparsed", "message": error}],
                                  "challenges": [], "warnings": [], "metrics": [], "enforced": True})
                feedback = f"無法解析你的結果（{error}）。請輸出回答，最後附上 ```json 結果區塊。"
            else:
                gate = self._record_plan(t, plan, question, enforced=True)
                if gate["passed"] and (not gate["challenges"] or challenged):
                    t["tools_used"] = [c["name"] for c in box.calls]
                    if self._escalate(t, plan):
                        return
                    t["plan"] = plan
                    t["decision"], t["metrics"], t["classes"] = plan["decision"], plan["metrics"], plan["classes"]
                    t["answer"] = _strip_json(result.content)
                    return
                if gate["passed"]:
                    challenged = True
                    messages += [{"role": "assistant", "content": result.content},
                                 {"role": "user", "content": planning.format_challenge(gate)}]
                    continue
                feedback = planning.format_feedback(gate)
            if retries >= self.plan_retries:
                break
            retries += 1
            messages += [{"role": "assistant", "content": result.content}, {"role": "user", "content": feedback}]
        t["tools_used"] = [c["name"] for c in box.calls]
        self._blocked(t)


def _contract(kb):
    return planning.PLAN_CONTRACT.replace("{version}", kb.version)


def _strip_json(text):
    """回答裡去掉最後的 JSON 區塊，留下給人看的文字。"""
    import re
    text = re.sub(r"```json\s*\{.*?\}\s*```\s*$", "", text or "", flags=re.S).strip()
    return text


def _loads(text):
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def _sha(text):
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
