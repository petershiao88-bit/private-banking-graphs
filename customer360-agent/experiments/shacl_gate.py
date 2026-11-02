"""實驗 2 用的 SHACL 版本體檢查：語意計畫 → RDF，與本體＋指標＋權限放在同一張圖，用 plan-shapes.ttl 驗證。

分工：
- 本體（含 OWL 推理的 subClassOf 閉包）、指標事實、權限規則 → 資料圖（一次建好）。
- 問題文字的特徵（商品錨點、指標種類、縮寫、子公司明示字、否定詞）→ 由程式抽出後寫成 pl:mentions* 三元組。
  SHACL／SPARQL 不擅長做中文斷詞與同義詞，這部分留在程式；規則本身留在 shapes。
- 少數「推導事實」先物化：pg:twin（銀行／證券同名商品的指標）、pg:hiddenFor（角色看不到的指標，供歧義判斷用）。
"""

import time

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

import common
from c360_agent import plan as planning

PL = Namespace("urn:c360:plan#")
PG = Namespace("urn:c360:pg#")
POL = Namespace("urn:c360:policy#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SHAPES = common.ROOT / "experiments" / "plan-shapes.ttl"


class ShaclGate:
    def __init__(self, kb):
        self.kb = kb
        self.gate = planning.Gate(kb, "rm")  # 只借用特徵抽取工具（錨點表、縮寫、子公司線索）
        self.shapes = Graph().parse(SHAPES, format="turtle")
        self.base = self._base_graph()

    # ------------------------------------------------------------------ 資料圖

    def iri(self, cid):
        return URIRef(self.kb.expand(cid)) if ":" in cid and cid.split(":")[0] in ("fh", "bank", "securities") else PG[cid]

    def metric(self, mid):
        return PG["m." + mid]

    def _base_graph(self):
        kb = self.kb
        g = Graph()
        for t in kb.studio.onto.inferred_graph():
            g.add(t)
        for m in kb.metrics.values():
            node = self.metric(m.id)
            g.add((node, RDF.type, PG.Metric))
            g.add((node, PG.subsidiary, Literal(m.subsidiary)))
            g.add((node, PG.kind, PG["kind_" + m.kind]))
            for cid in [m.class_id] + m.product_ids:
                g.add((node, PG.mapped, URIRef(kb.expand(cid))))
                g.add((node, PG.mappedAny, URIRef(kb.expand(cid))))
            for comp in m.components:
                g.add((node, PG.component, self.metric(comp)))
                g.add((node, PG.part, self.metric(comp)))
                for cid in [kb.metrics[comp].class_id] + kb.metrics[comp].product_ids:
                    g.add((node, PG.mappedAny, URIRef(kb.expand(cid))))
            for f in self.gate._features(m.name, m.id):
                g.add((node, PG.feature, Literal(f)))
            for tok in set(__import__("re").findall(r"[A-Z]{2,}", m.name)) - {"AUM", "LUM", "ID"}:
                g.add((node, PG.nameToken, Literal(tok)))
            for role in kb.roles:
                if kb.metric_access(m.id, role)["effect"] == "deny":
                    g.add((node, PG.hiddenFor, Literal(role)))
            for twin in self.gate.subsidiary_twins([m.id]).get(m.id, []):
                g.add((node, PG.twin, self.metric(twin)))
        for gap in kb.gaps:
            g.add((self.metric(gap["id"]), RDF.type, PG.PendingScope))
        for kind in ("aum", "lum", "fee", "interest"):
            g.add((PG["kind_" + kind], RDF.type, PG.KindAnchor))
        for stem, classes in self.gate.product_stems.items():
            node = PG["anchor_" + stem]
            g.add((node, RDF.type, PG.ProductAnchor))
            for c in classes:
                g.add((node, PG.anchorClass, URIRef(kb.expand(c))))
        for rule in kb.policy["rules"]:
            r = POL[rule["id"]]
            g.add((r, RDF.type, POL.Rule))
            g.add((r, POL.role, Literal(rule["role"])))
            g.add((r, POL.effect, Literal(rule["effect"])))
            for c in rule["classes"]:
                g.add((r, POL["class"], URIRef(c)))
        return g

    # ------------------------------------------------------------------ 計畫 → RDF

    def plan_graph(self, plan, question, role):
        kb, g = self.kb, Graph()
        p = PL["plan"]

        def ref(cid):
            return URIRef(kb.expand(cid)) if cid.split(":")[0] in ("fh", "bank", "securities") and ":" in cid else PG["x." + cid]

        g.add((p, RDF.type, PL.Plan))
        g.add((p, PL.role, Literal(role)))
        if plan["decision"]:
            g.add((p, PL.decision, Literal(plan["decision"])))
        if plan["clarification"]:
            g.add((p, PL.clarification, Literal(plan["clarification"])))
        if plan["reason"]:
            g.add((p, PL.reason, Literal(plan["reason"])))
        for m in plan["metrics"]:
            g.add((p, PL.selects, self.metric(m)))
        for c in plan["classes"]:
            g.add((p, PL.usesClass, ref(c)))
        for t in plan["terms"]:
            node = BNode()
            g.add((p, PL["term"], node))
            for c in t["classes"]:
                g.add((node, PL.declaresClass, ref(c)))
            for m in t["metrics"]:
                g.add((node, PL.mapsTo, self.metric(m)))
        for sub, sup in plan["is_a"]:
            node = BNode()
            g.add((p, PL.claim, node))
            g.add((node, PL.sub, ref(sub)))
            g.add((node, PL.sup, ref(sup)))
        for x in plan.get("exclude") or []:
            if x.startswith("subsidiary:"):
                g.add((p, PL.excludesSubsidiary, Literal(x.split(":", 1)[1])))
            else:
                g.add((p, PL.excludes, ref(x)))
        # 問題特徵（程式抽取；與程式版 Gate 用同一套詞表）
        q = question or ""
        text = kb._with_synonyms(q)
        negated = any(w in q for w in planning.NEGATION_WORDS)
        explicit = {s for s, cues in self.gate.explicit_cues.items() if any(c in q for c in cues)}
        if any(any(c in q for c in cues) for cues in self.gate.cues.values()):
            g.add((p, PL.mentionsSubsidiary, Literal(True)))
        if len(explicit) == 1 and not negated:
            g.add((p, PL.onlySubsidiary, Literal(next(iter(explicit)))))
        if len(explicit) >= 2 and not negated:
            g.add((p, PL.mentionsBothSubsidiaries, Literal(True)))
        for f in self.gate._features(q):
            g.add((p, PL.mentionsFeature, Literal(f)))
        for stem in self.gate.product_stems:
            if stem in text and not planning._negated(text, stem) and not planning._modifier(text, stem):
                g.add((p, PL.mentionsAnchor, PG["anchor_" + stem]))
        for kind, words in planning.KIND_ANCHORS.items():
            if any(w in text for w in words):
                g.add((p, PL.mentionsAnchor, PG["kind_" + kind]))
        import re
        for tok in set(re.findall(r"[A-Z]{2,}", q)) - {"AUM", "LUM", "ID"}:
            if any(re.search(rf"(?<![A-Z]){tok}(?![A-Z])", m.name) for m in kb.visible_metrics(role)):
                g.add((p, PL.mentionsToken, Literal(tok)))
        if any(a in q for a in planning.SUMMARY_ANCHORS):
            g.add((p, PL.asksSummary, Literal(True)))
        return g

    # ------------------------------------------------------------------ 驗證

    def check(self, plan, question, role):
        data = Graph()
        for t in self.base:
            data.add(t)
        for t in self.plan_graph(plan, question, role):
            data.add(t)
        start = time.time()
        conforms, report, _ = validate(data, shacl_graph=self.shapes, inference="none", advanced=True,
                                       allow_warnings=True)
        elapsed = time.time() - start
        hard, soft = set(), set()
        for result in report.subjects(RDF.type, SH.ValidationResult):
            shape = report.value(result, SH.sourceShape)
            severity = report.value(result, SH.resultSeverity)
            name = self.shapes.value(shape, SH.name) or self._parent_name(shape)
            code = str(name) if name else "?"
            (soft if severity == SH.Warning else hard).add(code)
        return {"hard": sorted(hard), "soft": sorted(soft), "seconds": elapsed}

    def _parent_name(self, shape):
        for parent in self.shapes.subjects(SH.property, shape):
            name = self.shapes.value(parent, SH.name)
            if name:
                return name
        for parent in self.shapes.subjects(SH.sparql, shape):
            return self.shapes.value(parent, SH.name)
        return None
