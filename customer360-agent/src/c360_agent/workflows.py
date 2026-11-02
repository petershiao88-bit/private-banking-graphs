"""預先定義、本體型別化的 workflow 範本（實驗 3 的結論落地）。

LLM 只負責「選範本、填欄位、必要時拆成多個呼叫」；範本由本體執行，結果一定符合本體。

範本：
- metric_lookup(kind, products[], subsidiary?, exclude_subsidiary?, summary?, token?)
    種類＝aum／lum／fee／interest；products＝商品錨點（本體商品類別標籤的主幹，例如 基金、債券、海外）；
    多個商品取交集；token＝只出現在指標名稱裡的縮寫或限定詞（DCI、ELI、FCI、SI、信託、自營…）。
- concept_is_a(a, b)        a 是不是 b 的子類別（OWL 閉包）
- concept_relation(a, b)    a、b 之間的關係屬性
"""

import json
import os
import re

from . import plan as planning
from .knowledge import Knowledge

KINDS = ["aum", "lum", "fee", "interest"]
TEMPLATES = ("metric_lookup", "concept_is_a", "concept_relation")
RELATION_WORDS = ("關係", "歸屬", "連到", "跟誰")
ISA_WORDS = ("算不算", "是不是", "是否屬於", "屬不屬於")


class WorkflowError(ValueError):
    pass


class Workflows:
    def __init__(self, kb: Knowledge):
        self.kb = kb
        self.gate = planning.Gate(kb, "rm")
        self.stems = self.gate.product_stems
        acronyms = {t for m in kb.metrics.values() for t in re.findall(r"[A-Z]{2,}", m.name)} - {"AUM", "LUM"}
        qualifiers = {q for m in kb.metrics.values() for q in re.findall(r"（([^）]{1,4})）", m.name)}
        if os.environ.get("C360A_NO_NAME_QUALIFIERS"):   # 實驗用：只靠本體類別，不借指標名稱裡的限定詞
            qualifiers = {q for q in qualifiers if re.fullmatch(r"[A-Z]{2,}", q)}
        self.tokens = sorted(acronyms | qualifiers)

    # ------------------------------------------------------------------ 給 LLM 的說明

    def contract(self):
        kinds = "、".join(KINDS)
        stems = "、".join(sorted(self.stems))
        tokens = "、".join(self.tokens)
        return f"""\
## 輸出格式：workflow 呼叫

你不用自己挑指標 ID。請把問題拆成下列範本呼叫，由系統依本體執行；只輸出一個 JSON 物件：

```json
{{"decision": "answer | clarify | out_of_scope",
 "calls": [
   {{"template": "metric_lookup", "kind": "fee", "products": ["基金"], "subsidiary": null,
    "exclude_subsidiary": null, "summary": false, "token": null}},
   {{"template": "concept_is_a", "a": "bank:ETFProduct", "b": "bank:FundProduct"}},
   {{"template": "concept_relation", "a": "fh:Customer", "b": "fh:FinancialProduct"}}
 ],
 "clarification": "decision=clarify 時要問使用者的一句話",
 "reason": "decision=out_of_scope 時的原因"}}
```

- metric_lookup 欄位只能用下列值：
  - kind：{kinds}（AUM／LUM／手收／利收）；
  - products：{stems}（可給多個，取交集；只寫問題真正在問的商品，「債券型基金」是基金不是債券）；
  - subsidiary／exclude_subsidiary：bank、securities 或 null（「不屬於證券」→ exclude_subsidiary=securities）；
  - summary：問的是「總」指標時為 true；
  - token：{tokens}（只出現在指標名稱裡的縮寫或限定詞）。
- 問題問了多件事（例如「A 的手收跟 B 的 AUM」），就拆成多個呼叫。
- 問題沒指明銀行或證券、兩邊都可能時，subsidiary 留 null，系統會把兩邊都找出來。
- 概念題（是不是、什麼關係）用 concept_is_a／concept_relation，a、b 填類別 ID。
- 系統執行後若對結果有疑問，會把結果和疑問回給你，你可以修改呼叫或改為 clarify。
"""

    # ------------------------------------------------------------------ 解析與型別檢查

    def parse(self, text):
        raw = planning.extract_json(text)
        if not isinstance(raw, dict):
            raise WorkflowError("輸出必須是 JSON 物件")
        decision = str(raw.get("decision", "")).strip().lower()
        if decision not in planning.DECISIONS:
            raise WorkflowError(f"decision 必須是 {planning.DECISIONS}")
        calls = raw.get("calls") or []
        if not isinstance(calls, list):
            raise WorkflowError("calls 必須是陣列")
        problems = []
        clean = []
        for i, c in enumerate(calls, 1):
            if not isinstance(c, dict) or c.get("template") not in TEMPLATES:
                problems.append(f"第 {i} 個呼叫的 template 只能是 {', '.join(TEMPLATES)}")
                continue
            if c["template"] == "metric_lookup":
                kind = c.get("kind")
                products = c.get("products") or []
                if isinstance(products, str):
                    products = [products]
                if kind is not None and kind not in KINDS:
                    problems.append(f"第 {i} 個呼叫的 kind 只能是 {KINDS}，收到 {kind!r}")
                bad = [p for p in products if p not in self.stems]
                if bad:
                    problems.append(f"第 {i} 個呼叫的 products 有不認得的值 {bad}；可用：{'、'.join(sorted(self.stems))}")
                for key in ("subsidiary", "exclude_subsidiary"):
                    if c.get(key) not in (None, "bank", "securities"):
                        problems.append(f"第 {i} 個呼叫的 {key} 只能是 bank、securities 或 null")
                tok = c.get("token")
                if tok is not None and tok not in self.tokens:
                    problems.append(f"第 {i} 個呼叫的 token 只能是 {'、'.join(self.tokens)}")
                clean.append({"template": "metric_lookup", "kind": kind, "products": products,
                              "subsidiary": c.get("subsidiary"), "exclude_subsidiary": c.get("exclude_subsidiary"),
                              "summary": bool(c.get("summary")), "token": tok})
            else:
                a, b = c.get("a"), c.get("b")
                missing = [x for x in (a, b) if x not in self.kb.classes]
                if missing:
                    problems.append(f"第 {i} 個呼叫用到本體沒有的類別 {missing}")
                clean.append({"template": c["template"], "a": a, "b": b})
        if decision == "answer" and not calls:
            problems.append("decision=answer 時至少要有一個呼叫")
        if problems:
            raise WorkflowError("；".join(problems))
        return {"decision": decision, "calls": clean, "clarification": str(raw.get("clarification") or ""),
                "reason": str(raw.get("reason") or "")}

    # ------------------------------------------------------------------ 執行

    def metric_lookup(self, role, kind=None, products=(), subsidiary=None, exclude_subsidiary=None,
                      summary=False, token=None):
        kb = self.kb
        result = None
        for stem in products or [None]:
            classes = self.stems.get(stem, {None}) if stem else {None}
            found = set()
            for c in classes:
                found |= {m.id for m in kb.metrics_matching(role=role, kind=kind, product=c,
                                                            subsidiary=subsidiary, include_summary=summary)}
            result = found if result is None else result & found
        result = result or set()
        if exclude_subsidiary:
            result = {m for m in result if kb.metrics[m].subsidiary != exclude_subsidiary}
        if token:
            result = {m for m in result if re.search(rf"(?<![A-Z]){re.escape(token)}(?![A-Z])", kb.metrics[m].name)}
        if summary:
            sums = {m for m in result if kb.metrics[m].components}
            result = sums or result
        if not products and not token and not summary and kind:
            return None  # 只有種類、沒有任何商品條件：不接受（避免回傳整類指標）
        return sorted(result)

    def concept(self, template, a, b):
        kb = self.kb
        if template == "concept_is_a":
            return [a, b]
        linked = [p for p in kb.properties.values() if p["kind"] == "object" and (
            (any(kb.is_a(a, d) for d in p["domain"]) and any(kb.is_a(b, r) for r in p["range"])) or
            (any(kb.is_a(b, d) for d in p["domain"]) and any(kb.is_a(a, r) for r in p["range"])))]
        return [a, b] if linked else None

    def execute(self, request, role):
        """執行範本呼叫 → (語意計畫, 執行紀錄)。"""
        log, metrics, classes, is_a = [], set(), [], []
        for call in request["calls"]:
            if call["template"] == "metric_lookup":
                args = {k: call[k] for k in ("kind", "products", "subsidiary", "exclude_subsidiary", "summary", "token")}
                found = self.metric_lookup(role, **args)
                log.append({"call": call, "result": found if found is not None else "（只有種類、沒有商品條件，不執行）"})
                metrics |= set(found or [])
            else:
                result = self.concept(call["template"], call["a"], call["b"])
                if call["template"] == "concept_is_a":
                    path = self.kb.is_a(call["a"], call["b"])
                    log.append({"call": call, "result": {"is_a": path is not None, "path": path or []}})
                    if path:
                        is_a.append([call["a"], call["b"]])
                else:
                    log.append({"call": call, "result": result or "（兩者之間沒有關係屬性）"})
                classes += [c for c in (result or []) if c not in classes]
        excl = [f"subsidiary:{c['exclude_subsidiary']}" for c in request["calls"]
                if c["template"] == "metric_lookup" and c.get("exclude_subsidiary")]
        decision = request["decision"]
        reason = request["reason"]
        if decision == "answer" and not metrics and not classes:
            decision, reason = "out_of_scope", "範本依本體執行後查無對應的指標或關係（可能屬於待定範圍或不存在）"
        plan = planning.normalize({"decision": decision, "metrics": sorted(metrics), "classes": classes, "is_a": is_a,
                                   "exclude": sorted(set(excl)), "clarification": request["clarification"],
                                   "reason": reason, "ontology_version": self.kb.version})
        return plan, log

    # ------------------------------------------------------------------ 不用 LLM 的填欄位（基準線與離線演練）

    def fill(self, question):
        kb = self.kb
        text = kb._with_synonyms(question)
        negated = any(w in question for w in planning.NEGATION_WORDS)
        explicit = {s for s, cues in self.gate.explicit_cues.items() if any(c in question for c in cues)}
        derived = {s for s, cues in self.gate.cues.items() if any(c in question for c in cues)}
        kinds = [k for k, words in planning.KIND_ANCHORS.items() if any(w in text for w in words)]
        products = list(planning._longest({s: None for s in self.stems
                                            if s in text and not planning._negated(text, s) and not planning._modifier(text, s)}))
        tokens = [t for t in self.tokens if re.search(rf"(?<![A-Za-z]){re.escape(t)}(?![A-Za-z])", question)]
        labels = sorted(((c["label"], cid) for cid, c in kb.classes.items()), key=lambda x: -len(x[0]))
        mentioned = []
        for label, cid in labels:
            if label in question and not any(label in m for m, _ in mentioned):
                mentioned.append((label, cid))
        for t in kb.terms.values():
            if t["name"] in question and t["mappings"] and not any(t["name"] in m for m, _ in mentioned):
                mentioned.append((t["name"], t["mappings"][0]["class"]))
        if not kinds and len(mentioned) >= 2:
            ordered = sorted(mentioned, key=lambda x: question.find(x[0]))
            template = "concept_is_a" if any(w in question for w in ISA_WORDS) else "concept_relation"
            return {"decision": "answer", "calls": [{"template": template, "a": ordered[0][1], "b": ordered[1][1]}],
                    "clarification": "", "reason": ""}
        sub = excl = None
        if negated and len(explicit) == 1:
            excl = next(iter(explicit))
        elif len(explicit) == 1:
            sub = next(iter(explicit))
        elif len(derived) == 1 and not explicit:
            sub = next(iter(derived))
        calls = []
        for kind in kinds or [None]:
            for tok in tokens or [None]:
                calls.append({"template": "metric_lookup", "kind": kind, "products": products, "subsidiary": sub,
                              "exclude_subsidiary": excl, "summary": any(a in question for a in planning.SUMMARY_ANCHORS),
                              "token": tok})
        return {"decision": "answer", "calls": calls, "clarification": "", "reason": ""}


# 範本執行後的回答固定附上的口徑提醒（實驗 3 評分用）
ANSWER_NOTES = "（範本提醒：總指標與分項不可重複加總；待定範圍尚未定義；金額需由工具取數；依本體關係 fh:holds 持有；不是子類別時無法證明）"


def request_json(request):
    return json.dumps(request, ensure_ascii=False)
