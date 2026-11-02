"""給 agent 呼叫的本體查詢工具（已綁定角色）。

每個工具都只回傳 JSON 可序列化的結果；錯誤以 {"error": "..."} 回傳，讓模型自行修正。
角色看不到的指標與不存在的指標，回覆同一句話，不透露它是否存在。
"""

import json

from .knowledge import KIND_LABELS, Knowledge, KnowledgeError

NOT_AVAILABLE = "目前可用範圍內沒有這項指標：{id}"
KIND_CHOICES = list(KIND_LABELS)
SUBSIDIARY_CHOICES = ["bank", "securities"]

SCHEMAS = [
    {"name": "search_terms",
     "description": "用業務用語找候選的指標、詞條、類別與屬性。問題裡的名詞先用這個工具對應到 ID。",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string", "description": "業務用語，例如「基金手收」「複委託債券庫存」"},
         "limit": {"type": "integer", "description": "最多回傳幾筆，預設 8"}},
         "required": ["query"]}},
    {"name": "get_class",
     "description": "查本體類別：定義、上層鏈（含 OWL 推理）、直接子類別、可用屬性、相關指標數。",
     "parameters": {"type": "object", "properties": {
         "class_id": {"type": "string", "description": "類別 ID，例如 bank:FundProduct、fh:AUM"}},
         "required": ["class_id"]}},
    {"name": "is_a",
     "description": "判斷 class_id 是否為 ancestor_id 的子類別（依 OWL 推理閉包），回傳推理路徑。",
     "parameters": {"type": "object", "properties": {
         "class_id": {"type": "string"}, "ancestor_id": {"type": "string"}},
         "required": ["class_id", "ancestor_id"]}},
    {"name": "list_metrics",
     "description": "依條件列出本角色可用的指標。product 會包含其子類別。條件都可省略。",
     "parameters": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": KIND_CHOICES, "description": "aum／lum／fee（手收）／interest（利收）"},
         "subsidiary": {"type": "string", "enum": SUBSIDIARY_CHOICES},
         "product": {"type": "string", "description": "商品類別 ID，例如 bank:OverseasFinancialProduct、fh:FinancialProduct"},
         "metric_class": {"type": "string", "description": "指標類別 ID，例如 fh:FeeIncome、bank:BankAUM"}}}},
    {"name": "get_metric",
     "description": "查指標細節：所屬類別與上層鏈、商品、底表與角色、欄位候選、口徑疑點；總指標會列出分項。",
     "parameters": {"type": "object", "properties": {
         "metric_id": {"type": "string", "description": "指標 ID，例如 bank.fund_fee_income"}},
         "required": ["metric_id"]}},
    {"name": "list_gaps",
     "description": "列出待定範圍：本體已知但尚未定義來源或口徑的項目（不可用相近指標代替）。",
     "parameters": {"type": "object", "properties": {}}},
]


class ToolBox:
    def __init__(self, kb: Knowledge, role):
        kb._check_role(role)
        self.kb, self.role = kb, role
        self.calls = []

    def schemas(self):
        return [{"type": "function", "function": s} for s in SCHEMAS]

    def call(self, name, arguments=None):
        """執行工具；arguments 可以是 dict 或 JSON 字串。回傳結果 dict，並記錄呼叫。"""
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError as exc:
                result = {"error": f"參數不是合法 JSON：{exc}"}
                self.calls.append({"name": name, "arguments": arguments, "result": result})
                return result
        arguments = arguments or {}
        fn = getattr(self, "tool_" + str(name), None)
        if fn is None:
            result = {"error": f"沒有這個工具：{name}（可用：{', '.join(s['name'] for s in SCHEMAS)}）"}
        else:
            try:
                result = fn(**arguments)
            except TypeError as exc:
                result = {"error": f"參數錯誤：{exc}"}
            except KnowledgeError as exc:
                result = {"error": str(exc)}
        self.calls.append({"name": name, "arguments": arguments, "result": result})
        return result

    # ------------------------------------------------------------------ 工具本體

    def tool_search_terms(self, query, limit=8):
        hits = self.kb.search(query, role=self.role, limit=max(1, min(int(limit or 8), 20)))
        return {"query": query, "hits": hits}

    def tool_get_class(self, class_id):
        return self.kb.class_card(class_id.strip())

    def tool_is_a(self, class_id, ancestor_id):
        self.kb.require_class(class_id.strip())
        self.kb.require_class(ancestor_id.strip())
        path = self.kb.is_a(class_id.strip(), ancestor_id.strip())
        return {"class_id": class_id, "ancestor_id": ancestor_id, "result": path is not None,
                "path": [f"{self.kb.label(x)} {x}" for x in path] if path else [],
                "inferred": self.kb.is_inferred(class_id.strip(), ancestor_id.strip())}

    def tool_list_metrics(self, kind=None, subsidiary=None, product=None, metric_class=None):
        if kind and kind not in KIND_CHOICES:
            raise KnowledgeError(f"kind 只能是 {KIND_CHOICES}")
        if subsidiary and subsidiary not in SUBSIDIARY_CHOICES:
            raise KnowledgeError(f"subsidiary 只能是 {SUBSIDIARY_CHOICES}")
        items = self.kb.metrics_matching(role=self.role, kind=kind, subsidiary=subsidiary,
                                         product=(product or "").strip() or None,
                                         metric_class=(metric_class or "").strip() or None)
        return {"count": len(items), "metrics": [
            {"id": m.id, "name": m.name, "class": m.class_id, "products": m.product_ids,
             **({"components": m.components} if m.components else {})} for m in items]}

    def tool_get_metric(self, metric_id):
        metric_id = metric_id.strip()
        if metric_id not in self.kb.metrics or self.kb.metric_access(metric_id, self.role)["effect"] == "deny":
            return {"error": NOT_AVAILABLE.format(id=metric_id)}
        return self.kb.metric_card(metric_id, "full")

    def tool_list_gaps(self):
        return {"gaps": self.kb.gaps}


def describe_for_prompt():
    """工具說明（給不支援原生 tools 的模型，放進 system prompt）。"""
    lines = []
    for s in SCHEMAS:
        props = s["parameters"].get("properties", {})
        required = set(s["parameters"].get("required", []))
        args = ", ".join(f"{k}{'' if k in required else '?'}: {v.get('type', 'string')}" for k, v in props.items())
        lines.append(f"- {s['name']}({args})：{s['description']}")
    return "\n".join(lines)
