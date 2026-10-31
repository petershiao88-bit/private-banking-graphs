"""Local OpenRouter configuration for Semantica; no API calls on import."""

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
OPENROUTER_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str = field(repr=False)
    model: str
    max_tokens: int
    base_url: str = OPENROUTER_URL


def read_settings(env_path=None):
    """Read only this project's .env; process variables take precedence."""
    values = dict(dotenv_values(env_path or HERE / ".env", encoding="utf-8-sig"))
    for name in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL", "OPENROUTER_MAX_TOKENS"):
        if name in os.environ:
            values[name] = os.environ[name]
    api_key = (values.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key or api_key.lower() in {"your-api-key", "your_openrouter_api_key"}:
        raise ValueError("請先在 semantica-poc/.env 填入 OPENROUTER_API_KEY。")
    base_url = (values.get("OPENROUTER_BASE_URL") or OPENROUTER_URL).strip().rstrip("/")
    if base_url != OPENROUTER_URL:
        raise ValueError("OpenRouter 連線網址應為 https://openrouter.ai/api/v1。")
    model = (values.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini").strip()
    if "/" not in model or any(char.isspace() for char in model):
        raise ValueError("OPENROUTER_MODEL 請填入 provider/model 格式的模型 ID。")
    try:
        max_tokens = int(values.get("OPENROUTER_MAX_TOKENS") or "1024")
    except (ValueError, TypeError):
        raise ValueError("OPENROUTER_MAX_TOKENS 必須是 1 到 4096 的整數。") from None
    if not 1 <= max_tokens <= 4096:
        raise ValueError("OPENROUTER_MAX_TOKENS 必須是 1 到 4096 的整數。")
    return OpenRouterSettings(api_key=api_key, model=model, max_tokens=max_tokens)


def create_llm(settings=None):
    """Return Semantica's provider, explicitly routed to OpenRouter."""
    from semantica.llms import OpenAI

    settings = settings or read_settings()
    llm = OpenAI(model=settings.model, api_key=settings.api_key, base_url=settings.base_url)
    if not llm.is_available():
        raise RuntimeError("缺少模型依賴，請先安裝 requirements-llm.txt。")
    # Semantica 0.7.0 does not forward these constructor settings to its SDK.
    # Configure the SDK directly to avoid retries making duplicate paid calls.
    llm.provider.client = llm.provider.client.with_options(timeout=30.0, max_retries=0)
    return llm


def main():
    parser = argparse.ArgumentParser(description="檢查本機 OpenRouter 設定；預設不連線。")
    parser.add_argument("--test", action="store_true", help="發送一個固定文字的 API 測試請求，可能產生少量費用")
    args = parser.parse_args()
    try:
        settings = read_settings()
        if not args.test:
            print("OpenRouter 設定可讀取；尚未發送 API 請求。")
            return 0
        llm = create_llm(settings)
        result = llm.generate("Reply with exactly: OK", temperature=0, max_tokens=16)
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("模型未回傳文字。")
        print("OpenRouter / Semantica 測試成功，已收到模型文字回應。")
        return 0
    except (ValueError, ImportError) as exc:
        if isinstance(exc, ImportError):
            print("缺少依賴，請安裝 requirements-llm.txt。")
        else:
            print(str(exc))
        return 1
    except Exception as exc:
        # Do not print raw provider errors, response bodies, prompts, or keys.
        status = getattr(exc, "status_code", None)
        descriptions = {401: "API key 無效或已停用", 402: "餘額或額度不足", 403: "此 key 沒有存取權限", 404: "模型 ID 或端點不存在", 429: "已達速率或用量限制"}
        print("連線未成功：" + descriptions.get(status, "請檢查網路、模型設定或稍後重試") + "。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
