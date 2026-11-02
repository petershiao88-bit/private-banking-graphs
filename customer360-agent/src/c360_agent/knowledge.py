"""知識層：把本體（含 OWL 推理）、PG 指標、業務字典與權限整理成 agent 用得到的查詢介面。

所有資料都從本體專案讀取，這裡不另存一份：改了本體專案、重新載入就生效。
"""

from dataclasses import dataclass, field
import hashlib
import json
import re

from .settings import Settings

KIND_ROOTS = {"aum": "fh:AUM", "lum": "fh:LUM", "fee": "fh:FeeIncome", "interest": "fh:InterestIncome"}
KIND_LABELS = {"aum": "AUM", "lum": "LUM", "fee": "手收", "interest": "利收"}
SUBSIDIARY_LABELS = {"bank": "銀行", "securities": "證券", "holding": "金控"}
TABLE_ROLE_LABELS = {"primary": "金額來源", "valuation_support": "估值輔助", "date_lookup_only": "僅日期查詢"}


class KnowledgeError(ValueError):
    """查詢參數錯誤（例如不存在的類別或指標 ID）。"""


@dataclass
class Metric:
    id: str
    name: str
    definition: str
    subsidiary: str
    kind: str
    class_id: str
    product_ids: list
    tables: list                      # [{table, role, inherited_from?}]
    table_status: str                 # observed／partial_scope／via_components
    fields: list                      # [{field, status, candidates: [{table, column, meaning}]}]
    notes: list                       # 來源疑點與口徑提醒
    components: list = field(default_factory=list)
    excluded: list = field(default_factory=list)
    calculation_status: str | None = None
    adopted_by: list = field(default_factory=list)
    source_file: str = ""

    @property
    def is_summary(self):
        return bool(self.components)


class Knowledge:
    """一次載入、之後只讀。`reload()` 重讀本體專案。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.reload()

    # ------------------------------------------------------------------ 載入

    def reload(self):
        from ontology_kit.config import Config
        from semantic_studio.core.studio import Studio

        self.cfg = Config(self.settings.ontology_config)
        self.studio = Studio(self.cfg)
        onto = self.studio.onto
        if onto.reasoning_error:
            raise KnowledgeError("本體 OWL 推理失敗，無法建立 agent 知識：" + onto.reasoning_error)
        self.version, self.status, self.date = self.cfg.version, self.cfg.status, self.cfg.date
        self.release = self._release_info()
        self._load_classes(onto)
        self._load_metrics()
        self._load_terms()
        self.policy = self.studio.policy
        self.roles = {r["id"]: r["label"] for r in self.policy["roles"]}
        self.synonyms = dict(self.cfg.data.get("studio", {}).get("synonyms") or {})
        self.synonyms.update(self.settings.agent.get("synonyms") or {})
        self.aggregate_deny = bool(self.settings.agent.get("aggregate_inherits_component_deny", True))

    def _release_info(self):
        """比對模組檔與 release/<版號>/manifest.json 的雜湊：工作版本是否就是已發佈的版本。"""
        manifest_path = self.cfg.release_dir() / "manifest.json"
        info = {"version": self.version, "release_iri": self.cfg.version_iri(self.cfg.ontology_uri),
                "released": False, "matches_release": False, "bundle_sha256": None}
        if not manifest_path.is_file():
            return info
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        info["released"] = True
        info["bundle_sha256"] = (manifest.get("files") or {}).get("customer360-release.ttl")
        recorded = {m["file"]: m.get("sha256") for m in manifest.get("modules", [])}
        current = {m.file: hashlib.sha256(m.path.read_bytes()).hexdigest() for m in self.cfg.release_modules()}
        info["matches_release"] = bool(recorded) and recorded == current
        return info

    def _load_classes(self, onto):
        cfg = self.cfg
        self._uri_to_id = {u: cfg.curie(u) for u in list(onto.classes) + list(onto.properties)}
        labels = {cfg.curie(u): c["label"] for u, c in onto.classes.items()}
        self.ancestors = {cfg.curie(u): [cfg.curie(a) for a in onto.ancestors.get(u, [])] for u in onto.classes}
        self._paths = {(cfg.curie(e["class"]), cfg.curie(e["ancestor"])): [cfg.curie(p) for p in e["path"]]
                       for e in onto.report["entailments"]}
        self._asserted = {(cfg.curie(e["class"]), cfg.curie(e["ancestor"])) for e in onto.report["entailments"]
                          if e["asserted"]}
        children = {cid: [] for cid in labels}
        for uri, c in onto.classes.items():
            for parent in c["parents"]:
                if parent in onto.classes:
                    children[cfg.curie(parent)].append(cfg.curie(uri))

        def prop(p, inherited_from=None):
            ranges = [self._uri_to_id.get(r, cfg.curie(r)) for r in p["range"]]
            view = {"id": cfg.curie(p["uri"]), "label": p["label"], "kind": p["kind"], "range": ranges,
                    "range_labels": [labels.get(r, r) for r in ranges], "definition": p["definition"]}
            if inherited_from:
                view["inherited_from"] = inherited_from
            return view

        self.properties = {cfg.curie(u): prop(p) for u, p in onto.properties.items()}
        for pid, p in self.properties.items():
            p["domain"] = [cfg.curie(d) for d in onto.properties[self.expand(pid)]["domain"]]
        self.classes = {}
        for uri, c in onto.classes.items():
            cid = cfg.curie(uri)
            own = [prop(onto.properties[p]) for p in c["properties"]]
            inherited = [prop(p, a) for a in self.ancestors[cid] for p in onto.properties.values()
                         if self.expand(a) in p["domain"]]
            self.classes[cid] = {
                "id": cid, "uri": uri, "label": c["label"], "definition": c["definition"],
                "layer": c["layer"], "subsidiary": c["subsidiary"], "maturity": c["maturity"],
                "deprecated": c["deprecated"], "replaced_by": [cfg.curie(u) for u in c["replaced_by"]],
                "parents": [cfg.curie(p) for p in c["parents"] if p in onto.classes],
                "ancestors": self.ancestors[cid], "children": sorted(children[cid]),
                "chain": self.chain_text(cid, labels), "properties": own, "inherited_properties": inherited,
            }

    def _load_metrics(self):
        cfg = self.cfg
        pg_dir = cfg.path_of("pg_models")
        terms = {t["id"]: t for t in self.studio.pg_terms}
        raw, adopted, self.gaps = {}, {}, []
        for path in sorted(pg_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "ontology_version" not in data:
                continue
            for concept in data.get("concepts") or []:
                if isinstance(concept, dict) and ("table_sources" in concept or "component_metric_ids" in concept):
                    raw[concept["id"]] = (path.name, concept)
            for gap in data.get("pending_scope") or []:
                self.gaps.append({"id": gap["id"], "status": gap.get("status", ""), "reason": gap.get("reason", ""),
                                  "source_file": path.name})
            if isinstance(data.get("department"), dict):
                for mid in data.get("metric_ids") or []:
                    adopted.setdefault(mid, []).append(data["department"]["name"])
        self.metrics = {}
        for mid, (source_file, c) in raw.items():
            class_id = cfg.curie(c["class_uri"])
            kind = c.get("metric_kind") or self._kind_of(class_id)
            if kind not in KIND_ROOTS:
                kind = self._kind_of(class_id)
            term = terms.get(mid)
            product_ids = [cfg.curie(m["class"]) for m in (term or {}).get("mappings", []) if m["role"] != "primary"]
            sources = c.get("table_sources") or {}
            tables = [{"table": t["table"], "role": t["role"]} for t in sources.get("tables", [])]
            fields = [{"field": f["field"], "status": f.get("status", ""),
                       "candidates": [{"table": x.get("table"), "column": x.get("column"), "meaning": x.get("meaning", "")}
                                      for x in f.get("candidates") or []]}
                      for f in c.get("fields") or []]
            notes = []
            observations = c.get("observations") or {}
            for key, value in observations.items():
                if key == "gaps":
                    notes.extend(str(v) for v in value or [])
                elif isinstance(value, str) and key != "coverage":
                    notes.append(value)
            self.metrics[mid] = Metric(
                id=mid, name=c["name"], definition=c.get("definition") or "", subsidiary=c.get("subsidiary") or "",
                kind=kind, class_id=class_id, product_ids=product_ids, tables=tables,
                table_status="partial_scope" if sources.get("status") == "partial_scope" else "observed",
                fields=fields, notes=notes, components=list(c.get("component_metric_ids") or []),
                excluded=list(c.get("excluded_metric_ids") or []), calculation_status=c.get("calculation_status"),
                adopted_by=adopted.get(mid, []), source_file=source_file)
        for m in self.metrics.values():
            if m.components:
                m.table_status = "via_components"
                seen = set()
                for comp in m.components:
                    for t in self.metrics[comp].tables:
                        key = (t["table"], t["role"])
                        if key not in seen:
                            seen.add(key)
                            m.tables.append({**t, "inherited_from": comp})
        self.summary_of = {comp: m.id for m in self.metrics.values() for comp in m.components}

    def _load_terms(self):
        """非指標的字典詞條（PG 既有概念＋業務字典），只用來把業務用語對到類別。"""
        cfg = self.cfg
        self.terms = {}
        skip = tuple(self.settings.agent.get("exclude_term_prefixes") or ())
        for t in self.studio.all_terms():
            if t["id"] in self.metrics or (skip and t["id"].startswith(skip)):
                continue
            self.terms[t["id"]] = {"id": t["id"], "name": t["name"], "definition": t["definition"],
                                   "origin": t["origin"], "source": t["source"],
                                   "mappings": [{"class": cfg.curie(m["class"]), "role": m["role"]}
                                                for m in t["mappings"]], "raw": t}

    # ------------------------------------------------------------------ 類別

    def expand(self, cid):
        from semantic_studio.core.common import expand
        try:
            return expand(self.cfg, cid)
        except ValueError as exc:
            raise KnowledgeError(str(exc)) from None

    def label(self, cid):
        if cid in self.classes:
            return self.classes[cid]["label"]
        if cid in self.properties:
            return self.properties[cid]["label"]
        if cid in self.metrics:
            return self.metrics[cid].name
        return cid

    def require_class(self, cid):
        cid = (cid or "").strip()
        if cid not in self.classes:
            raise KnowledgeError(f"本體沒有這個類別：{cid}")
        return self.classes[cid]

    def is_a(self, cid, ancestor):
        """回傳推理路徑（[cid, …, ancestor]）；不成立回傳 None。cid == ancestor 視為成立。"""
        if cid == ancestor:
            return [cid]
        return self._paths.get((cid, ancestor))

    def is_inferred(self, cid, ancestor):
        return cid != ancestor and (cid, ancestor) not in self._asserted and self.is_a(cid, ancestor) is not None

    def chain_text(self, cid, labels=None):
        labels = labels or {k: v["label"] for k, v in self.classes.items()}
        tops = [a for a in self.ancestors.get(cid, []) if not self.ancestors.get(a)]
        chains = [" ⊑ ".join(labels.get(x, x) for x in self._paths[(cid, top)]) for top in tops
                  if (cid, top) in self._paths]
        return chains

    def _kind_of(self, class_id):
        for kind, root in KIND_ROOTS.items():
            if self.is_a(class_id, root):
                return kind
        return "other"

    # ------------------------------------------------------------------ 權限

    def _term_record(self, mid):
        record = next((t for t in self.studio.pg_terms if t["id"] == mid), None)
        if record is None:
            raise KnowledgeError(f"找不到指標：{mid}")
        return record

    def metric_access(self, mid, role):
        """{effect: allow|deny, reasons: [...]}；總指標可繼承分項的拒絕。"""
        if mid not in self.metrics:
            raise KnowledgeError(f"找不到指標：{mid}")
        self._check_role(role)
        result = self.studio.evaluator.for_term(self._term_record(mid), role)
        reasons = [f"規則 {m['rule']}（{m['note'] or m['effect']}）" for m in result["matches"] if m["effect"] == "deny"]
        effect = "deny" if result["effect"] == "deny" else "allow"
        metric = self.metrics[mid]
        if self.aggregate_deny and metric.components and effect != "deny":
            blocked = [c for c in metric.components if self.metric_access(c, role)["effect"] == "deny"]
            if blocked:
                effect = "deny"
                reasons.append("涵蓋被拒絕的分項：" + "、".join(self.metrics[c].name for c in blocked))
        return {"effect": effect, "reasons": reasons}

    def class_access(self, cid, role):
        self._check_role(role)
        result = self.studio.evaluator.for_class(self.expand(cid), role)
        return {"effect": result["effect"], "reasons": [f"規則 {m['rule']}" for m in result["matches"]
                                                         if m["effect"] == "deny"]}

    def visible_metrics(self, role):
        return [m for m in self.metrics.values() if self.metric_access(m.id, role)["effect"] != "deny"]

    def _check_role(self, role):
        if role not in self.roles:
            raise KnowledgeError(f"角色未定義：{role}（可用：{', '.join(self.roles)}）")

    # ------------------------------------------------------------------ 查詢

    def metrics_matching(self, role=None, kind=None, subsidiary=None, product=None, metric_class=None,
                         include_summary=True):
        """依種類／子公司／商品類別（含子類別，依 OWL 閉包）篩選指標。"""
        if product:
            self.require_class(product)
        if metric_class:
            self.require_class(metric_class)
        result = []
        for m in (self.visible_metrics(role) if role else self.metrics.values()):
            if kind and m.kind != kind:
                continue
            if subsidiary and m.subsidiary != subsidiary:
                continue
            if metric_class and not self.is_a(m.class_id, metric_class):
                continue
            if product and not any(self.is_a(p, product) for p in m.product_ids):
                continue
            if not include_summary and m.components:
                continue
            result.append(m)
        return sorted(result, key=lambda m: (m.subsidiary, m.kind, m.id))

    def search(self, query, role=None, limit=8):
        """業務用語 → 候選（指標、詞條、類別）。字元雙字組重疊＋同義詞，名稱權重高於定義。"""
        text = self._with_synonyms(query)
        q = _grams(text) - STOP_GRAMS
        if not q:
            return []
        hits = []

        def score(name, definition="", related=""):
            core = re.sub(r"（[^）]*）", "", name).replace("私銀－", "")   # 名稱主幹：去掉括號說明與共同前綴
            n, d, r = (_grams(self._with_synonyms(x)) - STOP_GRAMS for x in (core, definition, related))
            # 餘弦式正規化：長問句不會把正確候選的分數壓到門檻以下（實驗 4 的發現）
            norm = max((len(q) * max(len(n), 1)) ** 0.5, 1)
            s = (3 * len(q & n) + 1.0 * len(q & r - n)) / norm + 0.5 * len(q & d) / max(len(q), 1)
            if _clean(name) and _clean(name) in _clean(text):
                s += 2
            return s

        visible = {m.id for m in self.visible_metrics(role)} if role else set(self.metrics)
        for m in self.metrics.values():
            if m.id in visible:
                related = " ".join(self.label(x) for x in [m.class_id, *m.product_ids])
                hits.append(("metric", m.id, m.name, score(m.name, m.definition, related)))
        for t in self.terms.values():
            hits.append(("term", t["id"], t["name"], score(t["name"], t["definition"])))
        for c in self.classes.values():
            if not c["deprecated"]:
                hits.append(("class", c["id"], c["label"], score(c["label"], c["definition"] or "")))
        for p in self.properties.values():
            hits.append(("property", p["id"], p["label"], score(p["label"], p["definition"] or "")))
        hits = [h for h in hits if h[3] > 0.6]
        hits.sort(key=lambda h: (-h[3], h[0] != "metric", h[1]))
        return [{"type": h[0], "id": h[1], "name": h[2], "score": round(h[3], 2)} for h in hits[:limit]]

    def _with_synonyms(self, text):
        """業務用語換成本體用語（長詞優先），查詢與候選名稱都做同樣的轉換。"""
        out = text or ""
        for word in sorted(self.synonyms, key=len, reverse=True):
            target = self.synonyms[word]
            if word in target:          # 例如 債 → 債券：已經是「債券」的地方不要再換
                parts = out.split(target)
                out = target.join(p.replace(word, " " + target + " ") for p in parts)
            else:
                out = out.replace(word, " " + target + " ")
        return out

    # ------------------------------------------------------------------ 卡片（給工具與 context 用）

    def class_card(self, cid):
        c = self.require_class(cid)
        card = {k: c[k] for k in ("id", "label", "definition", "layer", "subsidiary", "maturity", "deprecated",
                                  "replaced_by", "parents", "children", "chain")}
        card["ancestors"] = [{"id": a, "label": self.label(a), "inferred": self.is_inferred(cid, a)}
                             for a in c["ancestors"]]
        card["properties"] = [{k: p[k] for k in ("id", "label", "kind", "range")} | (
            {"inherited_from": p["inherited_from"]} if "inherited_from" in p else {})
            for p in c["properties"] + c["inherited_properties"]]
        card["metric_count"] = sum(1 for m in self.metrics.values()
                                   if self.is_a(m.class_id, cid) or any(self.is_a(p, cid) for p in m.product_ids))
        return card

    def metric_card(self, mid, detail="compact"):
        m = self.metrics.get(mid)
        if m is None:
            raise KnowledgeError(f"找不到指標：{mid}")
        card = {"id": m.id, "name": m.name, "kind": KIND_LABELS.get(m.kind, m.kind),
                "subsidiary": SUBSIDIARY_LABELS.get(m.subsidiary, m.subsidiary),
                "class": m.class_id, "class_chain": self.classes[m.class_id]["chain"],
                "products": [{"id": p, "label": self.label(p)} for p in m.product_ids],
                "definition": m.definition,
                "tables": [{"table": t["table"], "role": TABLE_ROLE_LABELS.get(t["role"], t["role"])}
                           | ({"via": t["inherited_from"]} if "inherited_from" in t else {}) for t in m.tables],
                "table_status": m.table_status}
        if m.components:
            card["components"] = [{"id": c, "name": self.metrics[c].name} for c in m.components]
            card["excluded"] = m.excluded
            card["warning"] = "總指標只涵蓋列出的分項；總指標與其分項不可再一起加總。"
        if m.id in self.summary_of:
            card["part_of"] = self.summary_of[m.id]
        if detail == "full":
            card["field_candidates"] = {f["field"]: [f"{c['table']}.{c['column']}（{c['meaning']}）" for c in f["candidates"]]
                                        for f in m.fields if f["candidates"]}
            card["pending_fields"] = [f["field"] for f in m.fields if not f["candidates"]]
            card["notes"] = m.notes
            card["calculation_status"] = m.calculation_status
            card["adopted_by"] = m.adopted_by
        return card

    def fingerprint(self):
        """這份知識的雜湊：本體模組＋PG＋字典＋權限，用來標記 context 包與評測結果。"""
        h = hashlib.sha256()
        files = [m.path for m in self.cfg.modules] + sorted(self.cfg.path_of("pg_models").glob("*.json"))
        files += [self.cfg.path_of("dictionary_terms"), self.cfg.path_of("access_policy")]
        for path in files:
            if path and path.is_file():
                h.update(path.name.encode())
                h.update(path.read_bytes())
        return h.hexdigest()


# 問句裡的通用字（不帶業務意義），檢索時忽略
STOP_GRAMS = {"指標", "標是", "哪個", "個指", "哪些", "些指", "是哪", "要看", "看哪", "要用", "用哪", "從哪", "哪裡",
              "哪張", "張表", "什麼", "是什", "客戶", "戶的", "的指", "各是", "分別"}


def _clean(text):
    return re.sub(r"[\s　（）()「」『』、，,。．.：:；;／/－\-—_]+", "", text or "").lower()


def _grams(text):
    text = _clean(text)
    grams = {text[i:i + 2] for i in range(len(text) - 1)}
    words = set(re.findall(r"[a-z]{2,}", text))
    return grams | words
