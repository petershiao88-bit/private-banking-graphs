"""共用常數與錯誤型別。"""

import re

from rdflib import Namespace

SH = Namespace("http://www.w3.org/ns/shacl#")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
EFFECTS = ("allow", "deny")
# PG 既有的五種類別欄位 → 統一的對應角色
PG_FIELDS = {"class_uri": "primary", "class_uris": "primary", "specific_product_class_uri": "product",
             "product_class_uris": "product", "business_scope_class_uri": "business_scope"}


class StudioError(ValueError):
    """使用者可修正的輸入錯誤，前端會原樣顯示訊息。"""


def expand(cfg, value):
    """CURIE（fh:AUM）或完整 IRI → 完整 IRI。"""
    value = str(value).strip()
    if value.startswith(("http://", "https://")):
        return value
    prefix, _, local = value.partition(":")
    for layer in cfg.layers.values():
        if layer.prefix == prefix and local:
            return layer.namespace + local
    raise StudioError(f"無法解析類別：{value}")
