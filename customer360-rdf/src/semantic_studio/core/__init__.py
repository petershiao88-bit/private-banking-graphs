"""Semantic Studio 後端核心。

ontology     載入本體與 OWL 推理
dictionary   業務字典詞條（PG 既有＋新詞條）
permissions  類別權限規則與繼承
validation   SHACL 驗證
views        給前端的 JSON
studio       對外唯一入口
"""

from .common import StudioError
from .studio import Studio

__all__ = ["Studio", "StudioError"]
