"""測試共用：把 src 加進匯入路徑，並提供共用的知識層（載入一次）。"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

_KB = None


def shared_kb():
    global _KB
    if _KB is None:
        from c360_agent import knowledge, settings
        _KB = knowledge.Knowledge(settings.load(ROOT / "config.yaml"))
    return _KB
