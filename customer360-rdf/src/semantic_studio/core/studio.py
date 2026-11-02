"""Studio：把本體、字典、權限、SHACL 組在一起的唯一入口（伺服器只呼叫這裡）。

只會寫入 config 的 paths.dictionary_terms 與 paths.access_policy；本體 TTL、PG JSON 一律唯讀。
"""

import threading

from rdflib import Namespace

from ontology_kit.config import Config

from . import dictionary, ontology, permissions, views
from .common import StudioError
from .validation import Validator


class Studio:
    def __init__(self, cfg=None):
        self.cfg = cfg or Config()
        settings = self.cfg.data["studio"]
        self.dict_ns = Namespace(settings["dictionary_namespace"])
        self.mapping_roles = settings["mapping_roles"]
        self.include_pg = settings.get("include_pg_terms", True)
        self.synonyms = settings.get("synonyms") or {}
        self.lock = threading.RLock()
        self.reload()

    # ---------- 載入 ----------

    def reload(self):
        with self.lock:
            self.onto = ontology.load(self.cfg)
            self.validator = Validator(self.cfg, self.dict_ns)
            self.terms = dictionary.load_terms(self.cfg, self.mapping_roles)
            self.pg_terms = dictionary.load_pg_terms(self.cfg, self.mapping_roles) if self.include_pg else []
            self.policy = permissions.load(self.cfg, self.onto.classes)
            self.evaluator = permissions.Evaluator(self.cfg, self.policy, self.onto.ancestors)
            self.validation = self.validator.validate(self.onto.inferred_graph(),
                                                      dictionary.to_graph(self.dict_ns, self.all_terms()))

    def all_terms(self):
        return self.pg_terms + self.terms

    def find_term(self, term_id):
        return next((t for t in self.all_terms() if t["id"] == term_id), None)

    # ---------- 字典編輯 ----------

    def _checked_term(self, raw):
        term = dictionary.normalize(self.cfg, self.mapping_roles, raw, raw.get("source") or "業務字典", True)
        for mapping in term["mappings"]:
            if mapping["class"] not in self.onto.classes:
                raise StudioError(f"類別未在本體宣告：{self.cfg.curie(mapping['class'])}")
        return term

    def preview_term(self, raw):
        with self.lock:
            term = self._checked_term(raw)
            graph = dictionary.to_graph(self.dict_ns, [term])
            validation = self.validator.validate(self.onto.inferred_graph(), graph)
            return {"term": views.term_view(self, term),
                    "permissions": self.evaluator.all_roles(self.evaluator.for_term, term),
                    "validation": [v for v in validation["results"] if v["node"] == "term:" + term["id"]],
                    "turtle": graph.serialize(format="turtle")}

    def save_term(self, raw, original_id=None):
        with self.lock:
            term = self._checked_term(raw)
            if any(t["id"] == term["id"] for t in self.pg_terms):
                raise StudioError(f"{term['id']} 是 PG 既有詞條，請換一個 ID")
            terms = [t for t in self.terms if t["id"] != (original_id or term["id"])]
            if any(t["id"] == term["id"] for t in terms):
                raise StudioError(f"詞條 ID 已存在：{term['id']}")
            dictionary.write_terms(self.cfg, terms + [term])
            self.reload()

    def delete_term(self, term_id):
        with self.lock:
            if not any(t["id"] == term_id for t in self.terms):
                raise StudioError(f"找不到可刪除的詞條：{term_id}（PG 既有詞條不能從這裡刪除）")
            dictionary.write_terms(self.cfg, [t for t in self.terms if t["id"] != term_id])
            self.reload()

    def import_terms(self, text, fmt, source):
        with self.lock:
            existing = {t["id"] for t in self.all_terms()}
            new = []
            for raw in dictionary.parse_import(text, fmt, source):
                term = dictionary.normalize(self.cfg, self.mapping_roles, raw, source, True)
                if term["id"] in existing:
                    raise StudioError(f"詞條 ID 已存在：{term['id']}")
                existing.add(term["id"])
                new.append(term)
            if not new:
                raise StudioError("沒有可匯入的詞條")
            dictionary.write_terms(self.cfg, self.terms + new)
            self.reload()
            return [t["id"] for t in new]

    def suggest(self, name, definition=""):
        return dictionary.suggest(self.cfg, self.onto, self.synonyms, name, definition)

    # ---------- 權限 ----------

    def save_policy(self, data):
        with self.lock:
            permissions.write(self.cfg, permissions.normalize(self.cfg, self.onto.classes, data))
            self.reload()

    # ---------- 對前端的輸出 ----------

    def state(self):
        with self.lock:
            return views.state(self)

    def node_detail(self, node_id):
        with self.lock:
            return views.node_detail(self, node_id)

    def turtle(self, what):
        with self.lock:
            return views.turtle(self, what)
