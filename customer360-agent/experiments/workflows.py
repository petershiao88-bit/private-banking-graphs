"""實驗 3 的 workflow：正式範本在 src/c360_agent/workflows.py；這裡只加上實驗用的 oracle（窮舉欄位組合的表達上限）。"""

from itertools import combinations
import re

import common
from c360_agent import plan as planning
from c360_agent.workflows import ANSWER_NOTES, KINDS, Workflows as _Base  # noqa: F401

SUBS = [None, "bank", "securities"]


class Workflows(_Base):
    def to_plan(self, template, slots, metrics=None, classes=None):
        if template == "metric_lookup":
            if not metrics:
                return planning.normalize({"decision": "out_of_scope", "reason": "範本查無對應指標", "metrics": []})
            return planning.normalize({"decision": "answer", "metrics": metrics,
                                       "exclude": [f"subsidiary:{slots['exclude_subsidiary']}"] if slots.get("exclude_subsidiary") else []})
        return planning.normalize({"decision": "answer", "classes": classes or [], "metrics": []})

    def run_deterministic(self, question, role):
        request = self.fill(question)
        plan, log = self.execute(request, role)
        template = "+".join(sorted({c["template"] for c in request["calls"]})) or "none"
        slots = {"calls": request["calls"]}
        return template, slots, plan

    def oracle(self, q):
        """窮舉欄位組合（最多兩個商品、兩種指標），找得到一組正確答案就回傳那一組。查詢結果快取、先用集合比對篩選。"""
        kb = self.kb
        role = q["role"]
        e = q["expect"]
        if not e["metrics"] and "answer" in e["decision"]:
            for a in kb.classes:            # 概念題：任一類別與期望類別的 is_a／relation
                for b in e["classes"]:
                    for template in ("concept_is_a", "concept_relation"):
                        classes = self.concept(template, a, b)
                        if classes and set(e["classes"]) <= set(classes):
                            return template, {"a": a, "b": b}
            return None
        if "out_of_scope" in e["decision"] and not e["metrics"]:
            return "metric_lookup", {"note": "任何查無結果的組合即可"}
        expected = set(e["metrics"])
        forbidden = set(e["forbidden"])

        def ok(found):
            if not found or found & forbidden:
                return False
            if e["match"] == "exact":
                return found == expected
            if e["match"] == "superset":
                return expected <= found
            return bool(expected & found)

        cache = {}

        def lookup(kind, products, sub, excl, summary, tok):
            key = (kind, products, sub, excl, summary, tok)
            if key not in cache:
                r = self.metric_lookup(role, kind=kind, products=list(products), subsidiary=sub,
                                       exclude_subsidiary=excl, summary=summary, token=tok)
                cache[key] = None if r is None else frozenset(r)
            return cache[key]

        product_sets = [()] + [(s,) for s in sorted(self.stems)] + list(combinations(sorted(self.stems), 2))
        tokens = [None] + list(self.tokens)
        kinds_needed = {kb.metrics[m].kind for m in expected}
        kind_sets = [tuple(sorted(kinds_needed))] if len(kinds_needed) <= 2 else []
        for kinds in kind_sets:
            for products in product_sets:
                for sub in SUBS:
                    for excl in (None, "bank", "securities"):
                        for summary in (False, True):
                            for tok in tokens:
                                parts = [lookup(k, products, sub, excl, summary, tok) for k in kinds]
                                if any(p is None for p in parts):
                                    continue
                                found = set().union(*parts)
                                if ok(found):
                                    plan = self.to_plan("metric_lookup", {"exclude_subsidiary": excl}, metrics=sorted(found))
                                    verdict = common.evaluate.score(q, {"decision": plan["decision"], "metrics": plan["metrics"],
                                                                        "plan": plan, "answer": ANSWER_NOTES}, kb)
                                    if verdict["outcome"] == "correct":
                                        return "metric_lookup", {"kinds": kinds, "products": products, "subsidiary": sub,
                                                                 "exclude_subsidiary": excl, "summary": summary, "token": tok}
        return None




def _ok(e, found):
    expected, forbidden = set(e["metrics"] or []), set(e["forbidden"])
    if not found or found & forbidden:
        return False
    if e["match"] == "exact":
        return found == expected
    if e["match"] == "superset":
        return expected <= found
    return bool(expected & found)


def oracle_composed(self, q):
    """兩次 metric_lookup 的聯集（各自一種指標、最多一個商品、可指定子公司／縮寫）：模擬 LLM 把問題拆成兩個範本呼叫。"""
    kb, e = self.kb, q["expect"]
    if not e["metrics"]:
        return None
    calls = []
    toks = [None] + list(self.tokens)
    for kind in KINDS:
        for stem in [None] + sorted(self.stems):
            for sub in SUBS:
                for tok in toks:
                    r = self.metric_lookup(q["role"], kind=kind, products=[stem] if stem else [], subsidiary=sub, token=tok)
                    if r:
                        calls.append(((kind, stem, sub, tok), frozenset(r)))
    for i, (a, ra) in enumerate(calls):
        if _ok(e, set(ra)):
            return [a]
        for b, rb in calls[i + 1:]:
            if _ok(e, set(ra | rb)):
                return [a, b]
    return None



Workflows.oracle_composed = oracle_composed
