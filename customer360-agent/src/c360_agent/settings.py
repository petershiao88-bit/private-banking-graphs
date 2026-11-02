"""讀 config.yaml，並把本體專案（customer360-rdf）的 src 加進匯入路徑。"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import sys

import yaml

AGENT_ROOT = Path(__file__).resolve().parents[2]  # src/c360_agent/settings.py → 專案根目錄
ENV_OVERRIDES = {"base_url": "C360A_BASE_URL", "model": "C360A_MODEL", "tool_calling": "C360A_TOOL_CALLING",
                 "thinking": "C360A_THINKING"}


class SettingsError(ValueError):
    pass


@dataclass
class LLMSettings:
    base_url: str
    model: str = "auto"
    api_key: str = "EMPTY"
    timeout: float = 300
    retries: int = 2
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 32768
    tool_calling: str = "auto"
    extra_body: dict = field(default_factory=dict)
    use_env_proxy: bool = False
    thinking: str = "keep"


@dataclass
class Settings:
    path: Path
    data: dict
    ontology_config: Path
    packs_dir: Path
    runs_dir: Path
    questions: Path
    llm: LLMSettings
    agent: dict
    eval: dict


def default_path():
    if os.environ.get("C360A_CONFIG"):
        return Path(os.environ["C360A_CONFIG"])
    return AGENT_ROOT / "config.yaml"


def load(path=None):
    path = Path(path or default_path()).resolve()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    base = path.parent

    def resolve(value):
        return (base / value).resolve()

    paths = data["paths"]
    raw = dict(data.get("llm") or {})
    for key, env in ENV_OVERRIDES.items():
        if os.environ.get(env):
            raw[key] = os.environ[env]
    key_env = raw.pop("api_key_env", "QWEN_API_KEY")
    api_key = os.environ.get("C360A_API_KEY") or os.environ.get(key_env or "") or "EMPTY"
    if raw.get("tool_calling", "auto") not in ("auto", "native", "prompt"):
        raise SettingsError("llm.tool_calling 只能是 auto、native 或 prompt")
    if raw.get("thinking", "keep") not in ("keep", "off"):
        raise SettingsError("llm.thinking 只能是 keep 或 off")
    llm = LLMSettings(api_key=api_key, **{k: v for k, v in raw.items() if k in LLMSettings.__dataclass_fields__})
    llm.base_url = llm.base_url.rstrip("/")
    llm.extra_body = llm.extra_body or {}
    settings = Settings(path, data, resolve(paths["ontology_project"]), resolve(paths["packs"]),
                        resolve(paths["runs"]), resolve(paths["questions"]), llm,
                        dict(data.get("agent") or {}), dict(data.get("eval") or {}))
    if not settings.ontology_config.is_file():
        raise SettingsError(f"找不到本體專案設定：{settings.ontology_config}（請檢查 paths.ontology_project）")
    attach_ontology_project(settings.ontology_config)
    return settings


def attach_ontology_project(ontology_config):
    """讓 `import ontology_kit`、`import semantic_studio` 指到本體專案的程式。"""
    src = str(Path(ontology_config).resolve().parent / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
