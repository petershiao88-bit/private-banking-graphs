"""OpenAI 相容的聊天端點用戶端（vLLM／Ollama／LM Studio／SGLang 上的 Qwen 都適用），只用標準函式庫。

- Qwen3 的思考內容：`reasoning_content` 欄位或 content 裡的 <think>…</think>，一律拆出來另存，不混進答案。
- 工具呼叫：native（OpenAI tools 參數）或 prompt（Qwen 原生 <tool_call>{json}</tool_call> 格式）；
  auto 模式先試 native，伺服器拒絕 tools 參數就改用 prompt。若伺服器沒開 tool parser，
  模型把 <tool_call> 寫在 content 裡，也會被解析出來。
"""

from dataclasses import dataclass, field
import json
import re
import time
import urllib.error
import urllib.request
import uuid

from .settings import LLMSettings

THINK_BLOCK = re.compile(r"<think>(.*?)</think>", re.S)
TOOL_CALL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)


class LLMError(RuntimeError):
    pass


class ToolsUnsupported(LLMError):
    """伺服器不接受 tools 參數（auto 模式會改用 prompt 工具呼叫）。"""


@dataclass
class ChatResult:
    content: str
    thinking: str = ""
    tool_calls: list = field(default_factory=list)   # [{"id", "name", "arguments"(str)}]
    usage: dict = field(default_factory=dict)
    latency: float = 0.0
    finish_reason: str | None = None
    model: str = ""
    tool_mode: str = "none"                           # native／prompt／none


def split_thinking(content, reasoning=None):
    """回傳 (答案, 思考)。處理完整的 <think> 區塊，以及模板預先填入 <think>、只剩 </think> 的情況。"""
    content = content or ""
    thoughts = [reasoning] if reasoning else []
    thoughts += [m.strip() for m in THINK_BLOCK.findall(content)]
    content = THINK_BLOCK.sub("", content)
    if "</think>" in content:
        head, _, content = content.partition("</think>")
        thoughts.append(head.replace("<think>", "").strip())
    elif content.lstrip().startswith("<think>"):  # 思考沒寫完就被截斷
        thoughts.append(content.replace("<think>", "").strip())
        content = ""
    return content.strip(), "\n\n".join(t for t in thoughts if t)


def parse_prompt_tool_calls(content):
    """從文字取出 <tool_call>{"name":…, "arguments":…}</tool_call>；回傳 (呼叫清單, 去掉呼叫後的文字)。"""
    calls = []
    for block in TOOL_CALL_BLOCK.findall(content or ""):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            calls.append({"id": _call_id(), "name": "__invalid__", "arguments": block})
            continue
        args = data.get("arguments", data.get("parameters", {}))
        calls.append({"id": _call_id(), "name": str(data.get("name", "")),
                      "arguments": args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)})
    return calls, TOOL_CALL_BLOCK.sub("", content or "").strip()


def no_think(messages):
    """關閉 Qwen3 思考：在最後一則使用者訊息加上官方的軟開關 /no_think（不支援的模型會當成一般文字）。"""
    messages = [dict(m) for m in messages]
    for m in reversed(messages):
        if m["role"] == "user" and isinstance(m.get("content"), str):
            if "/no_think" not in m["content"]:
                m["content"] = m["content"] + " /no_think"
            break
    return messages


def _merge(target, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


def _call_id():
    return "call_" + uuid.uuid4().hex[:12]


class OpenAICompatible:
    def __init__(self, settings: LLMSettings):
        self.s = settings
        self.model = None if settings.model in (None, "", "auto") else settings.model
        self.tool_mode = settings.tool_calling  # auto 會在第一次需要時決定
        handlers = [] if settings.use_env_proxy else [urllib.request.ProxyHandler({})]
        self.opener = urllib.request.build_opener(*handlers)

    # ------------------------------------------------------------------ HTTP

    def _request(self, method, path, payload=None, timeout=None, root=False):
        base = self.s.base_url
        if root:
            base = re.sub(r"/v\d+$", "", base)
        url = base + path
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.s.api_key}"}
        last = None
        for attempt in range(int(self.s.retries) + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with self.opener.open(req, timeout=timeout or self.s.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:2000]
                if 400 <= exc.code < 500:
                    raise LLMError(f"HTTP {exc.code} {url}：{body}") from None
                last = LLMError(f"HTTP {exc.code} {url}：{body}")
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last = LLMError(f"連不到 {url}：{getattr(exc, 'reason', exc)}")
            time.sleep(min(2 ** attempt, 8))
        raise last

    def models(self):
        data = self._request("GET", "/models", timeout=30)
        return [m.get("id") for m in data.get("data", []) if m.get("id")]

    def resolve_model(self):
        if not self.model:
            ids = self.models()
            if not ids:
                raise LLMError("/models 沒有回傳任何模型；請在 config.yaml 的 llm.model 指定模型名稱")
            self.model = ids[0]
        return self.model

    def tokenize(self, text):
        """vLLM 的 /tokenize；其他伺服器不支援時回傳 None。"""
        try:
            data = self._request("POST", "/tokenize", {"model": self.resolve_model(), "prompt": text},
                                 timeout=60, root=True)
        except LLMError:
            return None
        return data.get("count") if isinstance(data, dict) else None

    # ------------------------------------------------------------------ 聊天

    def chat(self, messages, tools=None, max_tokens=None, temperature=None):
        if self.s.thinking == "off":
            messages = no_think(messages)
        payload = {"model": self.resolve_model(), "messages": messages,
                   "temperature": self.s.temperature if temperature is None else temperature,
                   "max_tokens": max_tokens or self.s.max_tokens}
        if self.s.thinking == "off":
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        _merge(payload, self.s.extra_body or {})
        native = bool(tools) and self.tool_mode in ("auto", "native")
        if native:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        start = time.time()
        try:
            data = self._request("POST", "/chat/completions", payload)
        except LLMError as exc:
            if "HTTP 400" in str(exc) and "chat_template_kwargs" in payload and \
                    "chat_template_kwargs" not in (self.s.extra_body or {}):
                payload.pop("chat_template_kwargs")   # 伺服器不認得這個參數：只靠 /no_think 關閉思考
                try:
                    data = self._request("POST", "/chat/completions", payload)
                except LLMError as again:
                    exc = again
                else:
                    exc = None
            if exc is not None:
                if native and self.tool_mode == "auto" and "HTTP 400" in str(exc):
                    raise ToolsUnsupported(str(exc)) from None
                raise exc
        latency = time.time() - start
        if native and self.tool_mode == "auto":
            self.tool_mode = "native"
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"回應格式不符合 OpenAI chat completions：{str(data)[:500]}") from None
        content, thinking = split_thinking(message.get("content") or "",
                                           message.get("reasoning_content") or message.get("reasoning"))
        calls, mode = [], "none"
        for call in message.get("tool_calls") or []:
            fn = call.get("function") or {}
            args = fn.get("arguments", "{}")
            calls.append({"id": call.get("id") or _call_id(), "name": fn.get("name", ""),
                          "arguments": args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)})
            mode = "native"
        if not calls and "<tool_call>" in content:
            calls, content = parse_prompt_tool_calls(content)
            mode = "prompt" if calls else "none"
        return ChatResult(content=content, thinking=thinking, tool_calls=calls, usage=data.get("usage") or {},
                          latency=round(latency, 3), finish_reason=choice.get("finish_reason"),
                          model=data.get("model") or self.model, tool_mode=mode)


class ScriptedLLM:
    """測試與離線演練用：依序回傳預先寫好的回應，或呼叫 responder(messages, tools) 產生回應。"""

    def __init__(self, responses=None, responder=None, model="scripted"):
        self.responses = list(responses or [])
        self.responder = responder
        self.model = model
        self.tool_mode = "native"
        self.requests = []

    def resolve_model(self):
        return self.model

    def tokenize(self, text):
        return None

    def chat(self, messages, tools=None, max_tokens=None, temperature=None):
        self.requests.append({"messages": json.loads(json.dumps(messages, ensure_ascii=False)), "tools": tools})
        if self.responder:
            item = self.responder(messages, tools)
        elif self.responses:
            item = self.responses.pop(0)
        else:
            raise LLMError("ScriptedLLM 沒有更多預設回應")
        if isinstance(item, ChatResult):
            return item
        if isinstance(item, dict):
            calls = [{"id": _call_id(), "name": c["name"],
                      "arguments": c["arguments"] if isinstance(c["arguments"], str)
                      else json.dumps(c["arguments"], ensure_ascii=False)} for c in item.get("tool_calls", [])]
            content, thinking = split_thinking(item.get("content", ""))
            return ChatResult(content=content, thinking=thinking, tool_calls=calls, model=self.model,
                              usage=item.get("usage", {}), tool_mode="native" if calls else "none")
        content, thinking = split_thinking(str(item))
        calls, content2 = parse_prompt_tool_calls(content)
        return ChatResult(content=content2 if calls else content, thinking=thinking, tool_calls=calls,
                          model=self.model, tool_mode="prompt" if calls else "none")
