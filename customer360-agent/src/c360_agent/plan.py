"""語意計畫：模型先交出結構化的判斷，再由本體檢查（gate）決定能不能作答。

計畫格式（JSON）：
{
  "decision": "answer" | "clarify" | "out_of_scope",
  "terms": [{"text": "問題裡的用語", "classes": ["類別 ID"], "metrics": ["指標 ID"]}],
  "metrics": ["最後採用的指標 ID"],
  "classes": ["回答用到的類別 ID"],
  "is_a": [["子類別 ID", "上層類別 ID"]],
  "clarification": "decision=clarify 時要問使用者的問題",
  "reason": "decision=out_of_scope 時的原因",
  "ontology_version": "本體版號"
}
"""

import json
import re

from .knowledge import Knowledge

DECISIONS = ("answer", "clarify", "out_of_scope")

PLAN_CONTRACT = """\
## 輸出格式：語意計畫

先在心裡依「推理步驟」想清楚，然後只輸出一個 JSON 物件（可以放在 ```json 區塊內），欄位如下：

```json
{
  "decision": "answer | clarify | out_of_scope",
  "terms": [{"text": "問題裡的業務用語", "classes": ["對應的類別 ID"], "metrics": ["對應的指標 ID"]}],
  "metrics": ["最後採用的指標 ID；沒有就給 []"],
  "classes": ["回答用到的類別 ID"],
  "is_a": [["子類別 ID", "上層類別 ID"]],
  "exclude": ["問題要排除的類別 ID，或 subsidiary:bank／subsidiary:securities；沒有就給 []"],
  "clarification": "decision=clarify 時，要問使用者的一句話",
  "reason": "decision=out_of_scope 時，說明為何不在範圍內",
  "ontology_version": "{version}"
}
```

- answer：可以用本體回答（概念題也算）。metrics 或 classes 至少要有一項。
- clarify：問題有歧義（例如銀行／證券同名商品沒指明），先問清楚。可以在 metrics 列出候選。
- out_of_scope：指標不在清單、屬於待定範圍、或需要的資料本體沒有。
- is_a 只寫你在回答中依賴的「是一種」判斷，系統會用 OWL 推理逐條驗證。
- terms 的 classes 要寫出用語「本身」指的類別（例如「外匯 AUM」→ fh:AUM＋bank:ForeignExchangeProduct），系統會檢查選到的指標是否真的涵蓋這些類別。
- 問題有「不屬於／不包含／排除」時，把排除的對象寫進 exclude，系統會檢查指標沒有落在排除範圍。
- 只能用 context／工具中出現過的 ID，不要自己組 ID。
"""

ANSWER_CONTRACT = """\
## 輸出格式：回答＋結果

先用繁體中文回答使用者（引用指標／類別 ID 與本體版號；不可自行推算金額），
最後附上一個 ```json 區塊，格式與「語意計畫」相同（decision、terms、metrics、classes、is_a、clarification、reason、ontology_version）。
"""


# 檢查代碼依「需要什麼知識才能判斷」分層，實驗用來比較各層的攔截能力。
CHECK_LEVELS = {
    "schema": 1, "empty_answer": 1, "unknown_class": 1, "unknown_metric": 1,      # L1 存在性（詞彙表）
    "not_permitted": 2,                                                         # L2 權限
    "false_is_a": 3, "gap_metric": 3, "deprecated_class": 3,                    # L3 推理（OWL 閉包、待定範圍）
    "ambiguous_subsidiary": 4, "cue_conflict": 4,                               # L4 對照問題
    "term_metric_mismatch": 5, "exclusion_violated": 5,                         # L5 計畫內部一致性
    "missing_subsidiary": 4,
    "anchor_missing": 6, "anchor_conflict": 6,                                  # L6 本體標籤錨點（獨立重讀問題）
    "unparsed": 1,
}
# 硬擋＝本體能確定推出的錯誤；質疑＝靠問題文字判讀，可能誤判，只退回給模型確認或轉為澄清，不直接擋。
SOFT_CODES = {"ambiguous_subsidiary", "cue_conflict", "missing_subsidiary", "anchor_missing", "anchor_conflict"}
# 指標種類的錨點詞（問題裡出現就代表要這一種指標）；先套同義詞再比對。
KIND_ANCHORS = {"aum": ("AUM",), "lum": ("LUM",), "fee": ("手收",), "interest": ("利收",)}
SUMMARY_ANCHORS = ("總 AUM", "總AUM", "總手收")
NEGATION_WORDS = ("不屬於", "不包含", "不含", "排除", "除了", "以外", "非")


class PlanError(ValueError):
    pass


# ---------------------------------------------------------------------- 解析


def extract_json(text):
    """從模型輸出取出最後一個 JSON 物件：優先 ```json 區塊，其次最後一個括號平衡的 {...}。"""
    if not text:
        raise PlanError("模型沒有輸出內容")
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    for block in reversed(blocks):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    candidates = []
    depth, start, in_str, escape = 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"' and depth > 0:
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start:i + 1])
    for chunk in reversed(candidates):
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    raise PlanError("找不到可解析的 JSON 結果")


def normalize(raw):
    """容忍常見的小格式偏差（單一字串、大小寫、缺欄位），回傳標準化的計畫 dict。"""
    if not isinstance(raw, dict):
        raise PlanError("結果必須是 JSON 物件")

    def str_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise PlanError(f"欄位應為字串陣列：{value!r}")
        out = []
        for v in value:
            if isinstance(v, dict) and "id" in v:
                v = v["id"]
            if not isinstance(v, str):
                raise PlanError(f"陣列元素應為字串：{v!r}")
            v = v.strip().strip("`")
            if v and v not in out:
                out.append(v)
        return out

    decision = str(raw.get("decision", "")).strip().lower()
    terms = []
    for t in raw.get("terms") or []:
        if isinstance(t, dict):
            terms.append({"text": str(t.get("text", "")), "classes": str_list(t.get("classes")),
                          "metrics": str_list(t.get("metrics"))})
    pairs = []
    for pair in raw.get("is_a") or []:
        if isinstance(pair, dict):
            pair = [pair.get("class") or pair.get("subclass") or pair.get("class_id"),
                    pair.get("ancestor") or pair.get("superclass") or pair.get("ancestor_id")]
        if isinstance(pair, (list, tuple)) and len(pair) == 2 and all(isinstance(x, str) for x in pair):
            pairs.append([pair[0].strip().strip("`"), pair[1].strip().strip("`")])
        else:
            raise PlanError(f"is_a 每一項應為 [子類別, 上層類別]：{pair!r}")
    return {"decision": decision, "terms": terms, "metrics": str_list(raw.get("metrics")),
            "classes": str_list(raw.get("classes")), "is_a": pairs,
            "exclude": str_list(raw.get("exclude")),
            "clarification": str(raw.get("clarification") or "").strip(),
            "reason": str(raw.get("reason") or "").strip(),
            "ontology_version": str(raw.get("ontology_version") or "").strip()}


def parse(text):
    """模型輸出 → (plan dict 或 None, 錯誤訊息或 None)。"""
    try:
        return normalize(extract_json(text)), None
    except PlanError as exc:
        return None, str(exc)


# ---------------------------------------------------------------------- 檢查


class Gate:
    """用本體檢查語意計畫。errors 會擋下回答；warnings 會附在回答階段提醒模型。"""

    def __init__(self, kb: Knowledge, role, strict_subsidiary=True, anchors=None):
        self.kb, self.role = kb, role
        self.strict_subsidiary = strict_subsidiary
        self.explicit_cues = {"bank": ["銀行"], "securities": ["證券", "複委託"]}
        self.cues = _derived_cues(kb, self.explicit_cues)
        gate_cfg = kb.settings.agent.get("gate") or {}
        self.anchors = gate_cfg.get("anchors", True) if anchors is None else anchors
        self.product_stems = _product_stems(kb)

    def check(self, plan, question=""):
        kb = self.kb
        errors, warnings = [], []

        def err(code, message):
            errors.append({"code": code, "message": message})

        def warn(code, message):
            warnings.append({"code": code, "message": message})

        if plan["decision"] not in DECISIONS:
            err("schema", f"decision 必須是 {', '.join(DECISIONS)}，收到 {plan['decision']!r}")
        if plan["ontology_version"] and plan["ontology_version"] != kb.version:
            warn("version", f"計畫標示本體版號 {plan['ontology_version']}，目前是 {kb.version}；回答請以 {kb.version} 為準")

        classes = list(plan["classes"])
        for t in plan["terms"]:
            classes += [c for c in t["classes"] if c not in classes]
        for cid in classes:
            if cid not in kb.classes:
                hint = self._suggest_class(cid)
                err("unknown_class", f"本體沒有類別 {cid}" + (f"；是不是 {hint}？" if hint else ""))
            elif kb.classes[cid]["deprecated"]:
                err("deprecated_class", f"{cid} 已下架，改用 {'、'.join(kb.classes[cid]['replaced_by']) or '（未指定）'}")

        metric_ids = list(plan["metrics"])
        for t in plan["terms"]:
            metric_ids += [m for m in t["metrics"] if m not in metric_ids]
        visible = []
        for mid in metric_ids:
            if mid not in kb.metrics:
                gap = next((g for g in kb.gaps if g["id"] == mid), None)
                if gap:
                    err("gap_metric", f"{mid} 屬於待定範圍（{gap['reason']}），不可當成指標使用")
                else:
                    hint = self._suggest_metric(mid)
                    err("unknown_metric", f"沒有指標 {mid}" + (f"；相近的有 {hint}" if hint else ""))
            elif kb.metric_access(mid, self.role)["effect"] == "deny":
                err("not_permitted", f"{mid} 不在目前角色的可用範圍內，不可使用")
            elif mid in plan["metrics"]:
                visible.append(mid)

        for child, ancestor in plan["is_a"]:
            if child not in kb.classes or ancestor not in kb.classes:
                missing = [x for x in (child, ancestor) if x not in kb.classes]
                err("unknown_class", f"is_a 用到不存在的類別：{'、'.join(missing)}")
            elif kb.is_a(child, ancestor) is None:
                chain = "；".join(kb.classes[child]["chain"]) or "（頂層類別）"
                err("false_is_a", f"{child} 不是 {ancestor} 的子類別。{child} 的上層鏈：{chain}")

        if plan["decision"] == "answer" and not plan["metrics"] and not classes:
            err("empty_answer", "decision=answer 時，metrics 或 classes 至少要有一項")
        if plan["decision"] == "clarify" and not plan["clarification"]:
            err("schema", "decision=clarify 時要寫 clarification（要問使用者的問題）")
        if plan["decision"] == "out_of_scope" and not plan["reason"]:
            err("schema", "decision=out_of_scope 時要寫 reason")

        chosen = set(visible)
        for mid in visible:
            m = kb.metrics[mid]
            both = chosen & set(m.components)
            if both:
                warn("summary_with_components",
                     f"{mid} 是總指標，與分項 {'、'.join(sorted(both))} 同時出現：只能分別列示，不可加總")
        if plan["decision"] == "answer":
            for mid, twins in self.subsidiary_twins(visible, question).items():
                if self._mentions_subsidiary(question):
                    continue
                message = (f"{mid} 只代表{_sub_label(kb.metrics[mid].subsidiary)}；問題沒有指明子公司，"
                           f"另一邊還有 {'、'.join(twins)}。請改為 clarify，或把兩邊都列入並分開說明")
                (err if self.strict_subsidiary else warn)("ambiguous_subsidiary", message)

        # L5：用語宣告的類別要被選到的指標涵蓋（例如「外匯 AUM」不能用外匯手收回答）
        for t in plan["terms"]:
            term_classes = [c for c in t["classes"] if c in kb.classes]
            for mid in t["metrics"]:
                if mid not in kb.metrics or not term_classes:
                    continue
                missing = [c for c in term_classes if not self.covers(mid, c)]
                if missing:
                    err("term_metric_mismatch",
                        f"「{t['text']}」指的是 {'＋'.join(term_classes)}，但 {mid} 沒有涵蓋 {'、'.join(missing)}"
                        f"（{mid} 是 {kb.metrics[mid].class_id}，商品 {'、'.join(kb.metrics[mid].product_ids) or '—'}）")
        # L5：排除條件
        for x in plan.get("exclude") or []:
            for mid in visible:
                if self.excluded(mid, x):
                    err("exclusion_violated", f"{mid} 落在排除範圍 {x} 內")
        # L4：問題同時提到兩家子公司（且沒有否定詞），指標卻只有一家
        q = question or ""
        negated = any(w in q for w in NEGATION_WORDS)
        both = {sub for sub, cues in self.explicit_cues.items() if any(cue in q for cue in cues)}
        if plan["decision"] == "answer" and len(both) >= 2 and not negated and visible:
            got = {kb.metrics[m].subsidiary for m in visible}
            if len(got) == 1:
                err("missing_subsidiary", f"問題同時提到銀行與證券，但只選了{_sub_label(next(iter(got)))}的指標")
        # L6：用本體標籤當錨點，獨立重讀問題
        if self.anchors and plan["decision"] == "answer" and visible:
            for code, message in self.anchor_check(q, visible):
                err(code, message)
        # L4：問題只提到一家子公司（且沒有否定詞），指標卻屬於另一家
        mentioned = {sub for sub, cues in self.explicit_cues.items() if any(cue in (question or "") for cue in cues)}
        if len(mentioned) == 1 and not any(w in (question or "") for w in NEGATION_WORDS):
            for mid in visible:
                sub = kb.metrics[mid].subsidiary
                if sub not in mentioned:
                    err("cue_conflict", f"問題只提到{_sub_label(next(iter(mentioned)))}，但 {mid} 屬於{_sub_label(sub)}")

        hard = [e for e in errors if e["code"] not in SOFT_CODES]
        soft = [e for e in errors if e["code"] in SOFT_CODES]
        return {"passed": not hard, "errors": hard, "challenges": soft, "warnings": warnings, "metrics": visible}

    def anchor_check(self, question, metric_ids):
        """問題裡出現的商品詞與指標種類詞（本體標籤＋同義詞），必須被選到的指標涵蓋；指標也不能跟問題的錨點無關。"""
        kb = self.kb
        text = kb._with_synonyms(question)
        problems = []
        stems = {stem: classes for stem, classes in self.product_stems.items()
                 if stem in text and not _negated(text, stem) and not _modifier(text, stem)}
        stems = _longest(stems)
        kinds = {kind for kind, words in KIND_ANCHORS.items() if any(w in text for w in words)}
        hit = lambda m, c: self.covers(m, c, any_component=True)  # noqa: E731 — 總指標只要有分項涵蓋即可
        for stem, classes in stems.items():
            if not any(any(hit(m, c) for c in classes) for m in metric_ids):
                problems.append(("anchor_missing", f"問題提到「{stem}」，但選到的指標都沒有涵蓋 {'／'.join(sorted(classes))}"))
        for kind in kinds:
            if not any(kb.metrics[m].kind == kind for m in metric_ids):
                problems.append(("anchor_missing", f"問題問的是 {kind.upper() if kind in ('aum', 'lum') else KIND_ANCHORS[kind][0]}，選到的指標沒有這一種"))
        for m in metric_ids:
            metric = kb.metrics[m]
            if stems and not any(any(hit(m, c) for c in classes) for classes in stems.values()):
                problems.append(("anchor_conflict", f"{m} 跟問題提到的「{'、'.join(stems)}」都無關"))
            if kinds and metric.kind not in kinds:
                problems.append(("anchor_conflict", f"{m} 是 {metric.kind}，但問題問的是 {'、'.join(sorted(kinds))}"))
        # 只出現在指標名稱裡的縮寫（DCI、ELI、FCI、SI、ETF…）：本體沒有對應類別，改用指標名稱當錨點
        for token in sorted(set(re.findall(r"[A-Z]{2,}", question)) - {"AUM", "LUM", "ID"}):
            named = [m.id for m in kb.visible_metrics(self.role) if re.search(rf"(?<![A-Z]){token}(?![A-Z])", m.name)]
            if named and not any(m in named for m in metric_ids):
                problems.append(("anchor_missing", f"問題提到「{token}」，名稱含 {token} 的指標有 {'、'.join(named)}，但都沒有選"))
        if any(a in question for a in SUMMARY_ANCHORS) and not any(kb.metrics[m].components for m in metric_ids):
            problems.append(("anchor_missing", "問題問的是總指標，但選到的都是分項指標"))
        return problems

    def covers(self, mid, cid, any_component=False):
        """指標是否涵蓋類別：指標類別或商品類別是它的子類別；總指標看分項（預設全部分項都要涵蓋）。"""
        kb = self.kb
        m = kb.metrics[mid]
        if kb.is_a(m.class_id, cid) or any(kb.is_a(p, cid) for p in m.product_ids):
            return True
        if not m.components:
            return False
        check = any if any_component else all
        return check(self.covers(c, cid, any_component) for c in m.components)

    def excluded(self, mid, x):
        kb = self.kb
        m = kb.metrics[mid]
        if x.startswith("subsidiary:"):
            return m.subsidiary == x.split(":", 1)[1]
        if x not in kb.classes:
            return False
        return bool(kb.is_a(m.class_id, x) or any(kb.is_a(p, x) for p in m.product_ids))

    # ------------------------------------------------------------------ 輔助

    def subsidiary_twins(self, metric_ids, question=None):
        """同種類、商品類別名稱相同、但子公司不同的指標（由本體標籤推得），且未被選入。

        有給問題時，只留下「問題字面分不出來」的雙胞胎：若問題與選中指標名稱的字面重疊明顯多於雙胞胎（例如 DCI、信託、自營），
        就不算歧義。"""
        kb, chosen = self.kb, set(metric_ids)
        if question is not None:
            raw = self.subsidiary_twins(metric_ids)
            q = self._features(question)
            out = {}
            for mid, twins in raw.items():
                mine = q & self._features(kb.metrics[mid].name, mid)
                tied = [t for t in twins if mine <= (q & self._features(kb.metrics[t].name, t))]
                if tied:
                    out[mid] = tied
            return out
        out = {}
        for mid in metric_ids:
            m = kb.metrics[mid]
            if m.components or not m.product_ids:
                continue
            labels = sorted(kb.label(p) for p in m.product_ids)
            twins = [o.id for o in kb.visible_metrics(self.role)
                     if o.subsidiary != m.subsidiary and o.kind == m.kind and not o.components
                     and sorted(kb.label(p) for p in o.product_ids) == labels]
            missing = [t for t in twins if t not in chosen]   # 逐一檢查：每個沒被選到的雙胞胎都算（列舉題只選一部分也會被質疑）
            if missing:
                out[mid] = missing
        return out

    def _features(self, text, metric_id=None):
        """有業務意義的區分特徵：英文縮寫、指標名稱括號內的限定詞、境內／境外、商品類別錨點。"""
        kb = self.kb
        if not hasattr(self, "_qualifiers"):
            quals = set()
            for m in kb.metrics.values():
                quals.update(q for q in re.findall(r"（([^）]+)）", m.name) if len(q) <= 4)
            self._qualifiers = quals | {"境內", "境外"}
        text = kb._with_synonyms(text or "")
        feats = set(re.findall(r"[A-Z]{2,}", text)) - {"AUM", "LUM"}
        feats |= {w for w in self._qualifiers if w in text}
        if metric_id:
            for p in kb.metrics[metric_id].product_ids:
                feats |= {stem for stem, classes in self.product_stems.items() if p in classes}
        else:
            feats |= set(_longest({stem: None for stem in self.product_stems if stem in text and not _modifier(text, stem)}))
        return feats

    def _mentions_subsidiary(self, question):
        return any(cue in (question or "") for cues in self.cues.values() for cue in cues)

    def _suggest_class(self, cid):
        local = cid.split(":")[-1].lower()
        hits = [c for c in self.kb.classes if c.split(":")[-1].lower() == local]
        return "、".join(hits[:3])

    def _suggest_metric(self, mid):
        tail = mid.split(".")[-1]
        hits = [m.id for m in self.kb.visible_metrics(self.role) if m.id.split(".")[-1] == tail]
        return "、".join(hits[:3])


def _product_stems(kb):
    """商品類別標籤去掉「銀行」「商品」「金融」等通用字，得到錨點詞 → 類別集合（例如 基金 → bank:FundProduct、securities:FundProduct）。"""
    stems = {}
    for cid, c in kb.classes.items():
        if not kb.is_a(cid, "fh:FinancialProduct") or cid == "fh:FinancialProduct":
            continue
        stem = re.sub(r"(銀行|證券|金融|投資|商品|\s)", "", c["label"])
        if len(stem) >= 2:
            stems.setdefault(stem, set()).add(cid)
    return stems


def _derived_cues(kb, explicit):
    """子公司線索＝明示字（銀行／證券／複委託）＋只屬於某子公司的「人員／組織」類別標籤（理專、行員、私人銀行部門），由本體推得。
    商品名稱不算線索：「ETF」只在銀行有，不代表使用者限定銀行。"""
    cues = {k: list(v) for k, v in explicit.items()}
    actor_roots = ("fh:Employee", "fh:Department")
    for cid, c in kb.classes.items():
        layer = c["layer"]
        if layer in cues and any(kb.is_a(cid, r) for r in actor_roots):
            label = c["label"].replace("銀行", "").replace("證券", "").strip()
            for word in {c["label"], label}:
                if len(word) >= 2 and word not in cues[layer]:
                    cues[layer].append(word)
    for t in kb.terms.values():           # 業務字典的人員／組織詞條（例如「理專」「私銀」）
        for m in t["mappings"]:
            c = kb.classes.get(m["class"])
            if c and c["layer"] in cues and any(kb.is_a(m["class"], r) for r in actor_roots) and t["name"] not in cues[c["layer"]]:
                cues[c["layer"]].append(t["name"])
    return cues


def _longest(stems):
    """最長詞優先：「信託保管」已比對到，就不再單獨算「信託」。"""
    return {s: v for s, v in stems.items() if not any(s != t and s in t for t in stems)}


def _modifier(text, stem):
    """「債券型基金」「股票型 ETF」「台幣計價的基金」：商品詞後面接「型」或「計價」是另一個商品的屬性，不是錨點。
    （「結構型」本身就是類別名稱，不受影響）"""
    i = text.find(stem)
    while i >= 0:
        rest = text[i + len(stem):].lstrip()
        if not (rest.startswith("型") or rest.startswith("計價")):
            return False
        i = text.find(stem, i + 1)
    return True


def _negated(text, stem):
    i = text.find(stem)
    window = text[max(0, i - 4):i]
    return any(w in window for w in ("不屬於", "不包含", "不含", "排除", "除了", "非"))


def _sub_label(sub):
    return {"bank": "銀行", "securities": "證券"}.get(sub, sub)


def format_feedback(result):
    if not result["errors"]:
        return format_challenge(result)
    lines = ["本體檢查沒有通過，請修正後重新輸出完整的 JSON 計畫："]
    lines += [f"- [{e['code']}] {e['message']}" for e in result["errors"]]
    if result.get("challenges"):
        lines += ["另外請確認："] + [f"- [{e['code']}] {e['message']}" for e in result["challenges"]]
    if result["warnings"]:
        lines += ["提醒："] + [f"- [{w['code']}] {w['message']}" for w in result["warnings"]]
    return "\n".join(lines)


def format_challenge(result):
    lines = ["本體檢查對照問題文字後，對下列判斷有疑問（這是質疑，不一定是錯）：",
             *[f"- [{e['code']}] {e['message']}" for e in result.get("challenges", [])],
             "請重新確認：若原判斷正確，輸出相同的 JSON 計畫並在 reason 欄簡短說明理由；若有誤，輸出修正後的計畫（必要時改為 clarify）。"]
    return "\n".join(lines)


def handoff(kb, plan, question, to_role):
    """多 agent 交接：把一個 agent 的語意計畫交給另一個角色前，用接收方的角色重新檢查並去敏。

    回傳 {"status": pass|redacted|blocked, "plan": 交出去的計畫, "removed": [被拿掉的指標], "gate": 接收方的檢查結果}。
    - 接收方看不到的指標直接拿掉（不透露名稱給接收方）；全部被拿掉就改為 out_of_scope。
    - 其他硬擋錯誤（例如自編 ID）→ blocked，不交接。
    """
    removed = [m for m in plan["metrics"] if m in kb.metrics and kb.metric_access(m, to_role)["effect"] == "deny"]
    kept = [m for m in plan["metrics"] if m not in removed]
    out = normalize({**plan, "metrics": kept,
                     "terms": [{**t, "metrics": [m for m in t["metrics"] if m not in removed]} for t in plan["terms"]]})
    if removed and not kept and not out["classes"]:
        out = normalize({**out, "decision": "out_of_scope", "reason": "接收方角色的可用範圍內沒有這些指標"})
    gate = Gate(kb, to_role).check(out, question)
    if gate["errors"]:
        return {"status": "blocked", "plan": None, "removed": removed, "gate": gate}
    return {"status": "redacted" if removed else "pass", "plan": out, "removed": removed, "gate": gate}
