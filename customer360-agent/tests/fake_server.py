"""仿 vLLM／Ollama 上 Qwen 的 OpenAI 相容伺服器（只用於測試）。

可切換的行為：
- tools_supported=False：收到 tools 參數就回 400（模擬沒開 --enable-auto-tool-choice 的 vLLM）。
- tool_parser=False：工具呼叫以 Qwen 原生 <tool_call> 文字放在 content（模擬沒開 tool parser）。
- thinking="tags"｜"field"｜"open"｜"none"：思考內容放在 <think> 標籤、reasoning_content 欄位、只有 </think>，或沒有。
- fail_first=N：前 N 次請求回 500（測重試）。
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading


class FakeQwen:
    def __init__(self, brain, tools_supported=True, tool_parser=True, thinking="tags", fail_first=0,
                 model="Qwen/Qwen3-8B", reject_kwargs=False, truncate_to=None):
        self.brain = brain
        self.reject_kwargs, self.truncate_to = reject_kwargs, truncate_to
        self.tools_supported, self.tool_parser, self.thinking = tools_supported, tool_parser, thinking
        self.fail_first, self.model = fail_first, model
        self.requests = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/v1/models":
                    self._send(200, {"object": "list", "data": [{"id": server.model, "object": "model"}]})
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                server.requests.append({"path": self.path, "payload": payload})
                if server.fail_first > 0:
                    server.fail_first -= 1
                    self._send(500, {"error": "temporary"})
                    return
                if self.path == "/tokenize":
                    self._send(200, {"count": len(payload.get("prompt", "")) // 2})
                    return
                if self.path != "/v1/chat/completions":
                    self._send(404, {"error": "not found"})
                    return
                if server.reject_kwargs and "chat_template_kwargs" in payload:
                    self._send(400, {"error": "unknown field chat_template_kwargs"})
                    return
                if payload.get("tools") and not server.tools_supported:
                    self._send(400, {"object": "error", "message": '"auto" tool choice requires --enable-auto-tool-choice'})
                    return
                self._send(200, server.respond(payload))

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    def respond(self, payload):
        kind, value = self.brain(payload["messages"], payload.get("tools"))
        message = {"role": "assistant", "content": ""}
        thought = "先找對應的類別，再確認上層鏈。"
        if kind == "tool":
            name, args = value
            if self.tool_parser and payload.get("tools"):
                message["tool_calls"] = [{"id": "call_x1", "type": "function",
                                          "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}]
                message["content"] = None
            else:
                message["content"] = "<tool_call>\n" + json.dumps({"name": name, "arguments": args}, ensure_ascii=False) + "\n</tool_call>"
        else:
            message["content"] = value
        if self.thinking == "tags":
            message["content"] = f"<think>\n{thought}\n</think>\n\n" + (message["content"] or "")
        elif self.thinking == "field":
            message["reasoning_content"] = thought
        elif self.thinking == "open":
            message["content"] = f"{thought}\n</think>\n\n" + (message["content"] or "")
        return {"id": "chatcmpl-x", "object": "chat.completion", "model": self.model,
                "choices": [{"index": 0, "message": message,
                             "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
                "usage": {"prompt_tokens": min(sum(len(str(m.get("content") or "")) for m in payload["messages"]) // 2,
                                               self.truncate_to or 10 ** 9),
                          "completion_tokens": 42, "total_tokens": 0}}
