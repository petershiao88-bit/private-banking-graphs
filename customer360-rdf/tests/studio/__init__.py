"""studio 測試；把 src/ 加進 import 路徑。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
