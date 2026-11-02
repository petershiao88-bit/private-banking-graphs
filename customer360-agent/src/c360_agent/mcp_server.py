"""把本體工具開成 MCP 伺服器（stdio，JSON-RPC 2.0；不需要額外套件）。

用法：python -m c360_agent.mcp_server --role rm
MCP 客戶端設定範例（command／args）：
  {"command": "/路徑/customer360-agent/.venv/bin/python",
   "args": ["-m", "c360_agent.mcp_server", "--role", "rm"],
   "env": {"PYTHONPATH": "/路徑/customer360-agent/src"}}

除了 6 個工具，還提供兩個 resource：角色 context 包（context://<role>）與語意計畫格式（context://plan-contract）。
另有一個工具 check_plan：讓外部 agent 自己送語意計畫來做本體檢查。
"""

import argparse
import json
import sys

from . import packs, plan as planning, settings as settings_mod
from .knowledge import Knowledge
from .tools import SCHEMAS, ToolBox

PROTOCOL_VERSION = "2024-11-05"

CHECK_PLAN_SCHEMA = {
    "name": "check_plan",
    "description": "用本體檢查語意計畫（JSON 字串或物件）：類別／指標是否存在、權限、is_a 是否成立、銀行／證券歧義、總指標加總提醒。",
    "parameters": {"type": "object", "properties": {
        "plan": {"description": "語意計畫（格式見 resource context://plan-contract）"},
        "question": {"type": "string", "description": "使用者原始問題（用來判斷是否已指明子公司）"}},
        "required": ["plan"]},
}


HANDOFF_SCHEMA = {
    "name": "handoff_plan",
    "description": "多 agent 交接：把語意計畫交給另一個角色前，用接收方角色重新檢查並拿掉對方不可看的指標（含總指標繼承分項的拒絕）。",
    "parameters": {"type": "object", "properties": {
        "plan": {"description": "語意計畫（JSON 字串或物件）"},
        "to_role": {"type": "string", "description": "接收方角色 ID，例如 customer"},
        "question": {"type": "string"}},
        "required": ["plan", "to_role"]},
}


class Server:
    def __init__(self, kb: Knowledge, role):
        self.kb, self.role = kb, role
        self.box = ToolBox(kb, role)
        self.gate = planning.Gate(kb, role)

    def tools(self):
        return [{"name": s["name"], "description": s["description"], "inputSchema": s["parameters"]}
                for s in SCHEMAS + [CHECK_PLAN_SCHEMA, HANDOFF_SCHEMA]]

    def resources(self):
        return [{"uri": f"context://{self.role}", "name": f"角色 context 包（{self.kb.roles[self.role]}）",
                 "mimeType": "text/markdown"},
                {"uri": "context://plan-contract", "name": "語意計畫格式", "mimeType": "text/markdown"}]

    def handle(self, request):
        method, params, rid = request.get("method"), request.get("params") or {}, request.get("id")
        if method == "initialize":
            result = {"protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                      "capabilities": {"tools": {}, "resources": {}},
                      "serverInfo": {"name": "customer360-ontology", "version": self.kb.version},
                      "instructions": f"客戶360 本體 v{self.kb.version} 的查詢工具；角色 {self.kb.roles[self.role]}。"}
        elif method in ("notifications/initialized", "initialized") or method.startswith("notifications/"):
            return None
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": self.tools()}
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if name == "check_plan":
                output = self._check_plan(args)
            elif name == "handoff_plan":
                output = self._handoff(args)
            else:
                output = self.box.call(name, args)
            result = {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
                      "isError": "error" in output}
        elif method == "resources/list":
            result = {"resources": self.resources()}
        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri == f"context://{self.role}":
                text = packs.build(self.kb, self.role)["markdown"]
            elif uri == "context://plan-contract":
                text = planning.PLAN_CONTRACT.replace("{version}", self.kb.version)
            else:
                return _error(rid, -32602, f"沒有這個 resource：{uri}")
            result = {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}
        else:
            return _error(rid, -32601, f"不支援的方法：{method}") if rid is not None else None
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _check_plan(self, args):
        raw = args.get("plan")
        try:
            plan = planning.normalize(json.loads(raw) if isinstance(raw, str) else raw)
        except (planning.PlanError, json.JSONDecodeError) as exc:
            return {"error": f"計畫格式錯誤：{exc}"}
        return self.gate.check(plan, args.get("question", ""))


def _handoff_impl(server, args):
    raw = args.get("plan")
    try:
        plan = planning.normalize(json.loads(raw) if isinstance(raw, str) else raw)
        server.kb._check_role(args.get("to_role", ""))
    except (planning.PlanError, json.JSONDecodeError, ValueError) as exc:
        return {"error": f"參數錯誤：{exc}"}
    result = planning.handoff(server.kb, plan, args.get("question", ""), args["to_role"])
    return {"status": result["status"], "plan": result["plan"], "removed_count": len(result["removed"]),
            "errors": result["gate"]["errors"], "challenges": result["gate"]["challenges"]}


Server._handoff = _handoff_impl


def _error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def serve(server, stdin=sys.stdin, stdout=sys.stdout):
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "JSON 解析失敗")
        else:
            try:
                response = server.handle(request)
            except Exception as exc:  # noqa: BLE001 — 單一請求出錯不應讓伺服器停掉
                response = _error(request.get("id"), -32603, f"{type(exc).__name__}: {exc}")
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description="客戶360 本體 MCP 伺服器（stdio）")
    parser.add_argument("--config")
    parser.add_argument("--role", default=None)
    args = parser.parse_args(argv)
    cfg = settings_mod.load(args.config)
    kb = Knowledge(cfg)
    serve(Server(kb, args.role or cfg.agent.get("default_role", "rm")))


if __name__ == "__main__":
    main()
