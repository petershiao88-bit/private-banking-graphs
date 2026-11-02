"""離線後端：不需要模型，用來在接上 Qwen 之前先檢查整條流程（提示詞組裝、解析、本體檢查、評分、報告）。

heuristic：只靠關鍵字檢索挑指標（等於「沒有語言模型的純檢索」），結果不代表任何模型的能力。
"""

import json
import re

from .knowledge import Knowledge
from .llm import ChatResult


class HeuristicResponder:
    def __init__(self, kb: Knowledge):
        self.kb = kb

    def __call__(self, messages, tools=None):
        system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        question = next((m["content"] for m in messages if m["role"] == "user"), "")
        last = messages[-1]
        role = _role_of(system)
        if "已通過本體檢查的語意計畫" in system:
            plan = re.search(r"```json\s*(\{.*?\})\s*```", system, re.S)
            data = json.loads(plan.group(1)) if plan else {}
            names = "、".join(f"{self.kb.label(m)}（{m}）" for m in data.get("metrics", []))
            return ChatResult(content=f"依本體 v{self.kb.version}，對應指標：{names or '（無）'}。", model="heuristic")
        if "workflow 呼叫" in system:
            if last["role"] == "user" and last["content"].startswith("範本執行結果"):
                return ChatResult(content=messages[-2]["content"], model="heuristic")   # 堅持原呼叫
            from .workflows import Workflows
            request = Workflows(self.kb).fill(question)
            return ChatResult(content=json.dumps(request, ensure_ascii=False), model="heuristic")
        if last["role"] == "user" and last["content"].startswith("本體檢查"):
            plan = {"decision": "clarify", "metrics": [], "classes": [],
                    "clarification": "這個問題有歧義或超出範圍，請說明要看銀行還是證券，或換個說法。",
                    "ontology_version": self.kb.version}
            return ChatResult(content=json.dumps(plan, ensure_ascii=False), model="heuristic")
        hits = self.kb.search(question, role=role if role in self.kb.roles else None, limit=6)
        metrics = [h["id"] for h in hits if h["type"] == "metric"]
        classes = [h["id"] for h in hits if h["type"] == "class"][:2]
        if metrics:
            top = [m for m in metrics if self._score(hits, m) >= self._score(hits, metrics[0]) - 0.01]
            plan = {"decision": "answer", "metrics": top, "classes": classes}
        elif classes:
            plan = {"decision": "answer", "metrics": [], "classes": classes}
        else:
            plan = {"decision": "out_of_scope", "metrics": [], "classes": [], "reason": "找不到對應的指標或類別"}
        plan["ontology_version"] = self.kb.version
        text = "（heuristic）" + "、".join(plan["metrics"] or plan["classes"]) + "\n```json\n" + json.dumps(plan, ensure_ascii=False) + "\n```"
        return ChatResult(content=text, model="heuristic")

    @staticmethod
    def _score(hits, mid):
        return next(h["score"] for h in hits if h["id"] == mid)


def _role_of(system):
    match = re.search(r"目前使用者的角色：.*?（(\w+)）", system)
    return match.group(1) if match else None
