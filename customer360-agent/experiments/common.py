"""實驗共用：從題庫推出「正確計畫」（gold plan），以及模擬 LLM 常見錯誤的變異算子。

gold plan 的原則：只用題庫的期望欄位與本體推得，不手寫答案。
- decision：期望決策的第一個（歧義題改用 answer＋兩邊都列，因為那也是可接受答案，且方便做「只答一邊」的變異）。
- terms：用語宣告的類別＝期望指標共同涵蓋的「最具體」類別組合（由本體推得）。
- is_a：每個期望指標的類別到頂層的真實鏈。
"""

from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from c360_agent import evaluate, plan as planning, settings  # noqa: E402
from c360_agent.knowledge import Knowledge  # noqa: E402

_KB = None


def kb():
    global _KB
    if _KB is None:
        import os
        _KB = Knowledge(settings.load(os.environ.get("C360A_CONFIG") or ROOT / "config.yaml"))
    return _KB


def questions(name="questions.yaml"):
    return evaluate.load_questions(ROOT / "eval" / name, kb())


def gold_plan(q):
    k = kb()
    e = q["expect"]
    decision = "answer" if "answer" in e["decision"] else e["decision"][0]
    metrics = list(e["metrics"] or []) if decision == "answer" else []
    classes = list(e["classes"])
    terms, is_a, exclude = [], [], []
    if metrics:
        primary = sorted({k.metrics[m].class_id for m in metrics})
        common = _common_ancestor(primary)
        term_classes = [common] if common else []
        products = [set(k.metrics[m].product_ids) for m in metrics if k.metrics[m].product_ids]
        shared = set.intersection(*products) if products and len(products) == len(metrics) else set()
        term_classes += sorted(shared)
        terms.append({"text": q["question"], "classes": term_classes, "metrics": metrics})
        for m in metrics:
            cid = k.metrics[m].class_id
            for a in k.classes[cid]["ancestors"]:
                is_a.append([cid, a])
    if "不屬於證券" in q["question"]:
        exclude.append("subsidiary:securities")
    plan = {"decision": decision, "terms": terms, "metrics": metrics, "classes": classes, "is_a": is_a,
            "exclude": exclude, "clarification": "請問要看銀行還是證券？" if decision == "clarify" else "",
            "reason": "本體沒有對應的指標，或屬於待定範圍" if decision == "out_of_scope" else "",
            "ontology_version": k.version}
    return planning.normalize(plan)


def _common_ancestor(class_ids):
    """多個類別最具體的共同上層（含自己）。"""
    k = kb()
    if not class_ids:
        return None
    candidates = [class_ids[0]] + k.classes[class_ids[0]]["ancestors"]
    for c in candidates:
        if all(k.is_a(x, c) for x in class_ids):
            return c
    return None


# ---------------------------------------------------------------------- 變異算子（模擬 LLM 錯誤）
#
# 每個算子回傳 (變異後計畫, 說明) 或 None（此題不適用）。harm＝如果沒被攔下、使用者會被誤導的程度。

FAULTS = {}


def fault(name, family, harm):
    def wrap(fn):
        FAULTS[name] = {"fn": fn, "family": family, "harm": harm}
        return fn
    return wrap


def _copy(p):
    return planning.normalize({**p, "terms": [dict(t) for t in p["terms"]]})


@fault("hallucinated_metric", "自編 ID", "high")
def f_hallucinated_metric(q, p, rng):
    if not p["metrics"]:
        return None
    m = p["metrics"][0]
    fake = m.rsplit("_", 1)[0] + "_total" if "_" in m else m + "_x"
    if fake in kb().metrics:
        fake += "_v2"
    out = _copy(p)
    out["metrics"] = [fake] + p["metrics"][1:]
    for t in out["terms"]:
        t["metrics"] = [fake if x == m else x for x in t["metrics"]]
    return out, f"{m} → 編造 {fake}"


@fault("hallucinated_class", "自編 ID", "medium")
def f_hallucinated_class(q, p, rng):
    out = _copy(p)
    out["classes"] = out["classes"] + ["bank:FundAUM"]
    return out, "加入不存在的類別 bank:FundAUM"


@fault("wrong_sibling_metric", "選錯指標", "high")
def f_wrong_sibling(q, p, rng):
    """換成同子公司、同種類、但商品不同的真實指標（ID 合法、權限允許）。"""
    k = kb()
    if len(p["metrics"]) != 1:
        return None
    m = k.metrics[p["metrics"][0]]
    siblings = [o.id for o in k.visible_metrics(q["role"]) if o.id != m.id and o.subsidiary == m.subsidiary
                and o.kind == m.kind and not o.components and set(o.product_ids) != set(m.product_ids)]
    if not siblings:
        return None
    s = rng.choice(sorted(siblings))
    out = _copy(p)
    out["metrics"] = [s]
    for t in out["terms"]:
        t["metrics"] = [s]
    return out, f"{m.id} → 同類別的 {s}（術語宣告不變）"


@fault("wrong_sibling_consistent", "選錯指標", "high")
def f_wrong_sibling_consistent(q, p, rng):
    """同上，但模型連用語的類別宣告也一起改成跟錯誤指標一致（最難抓的情況）。"""
    k = kb()
    res = f_wrong_sibling(q, p, rng)
    if not res:
        return None
    out, why = res
    s = out["metrics"][0]
    for t in out["terms"]:
        t["classes"] = [k.metrics[s].class_id] + k.metrics[s].product_ids
    return out, why + "，並改寫用語宣告"


@fault("one_side_only", "子公司歧義", "high")
def f_one_side(q, p, rng):
    k = kb()
    subs = {k.metrics[m].subsidiary for m in p["metrics"]}
    if len(subs) < 2:
        return None
    keep = rng.choice(sorted(subs))
    out = _copy(p)
    out["metrics"] = [m for m in p["metrics"] if k.metrics[m].subsidiary == keep]
    for t in out["terms"]:
        t["metrics"] = list(out["metrics"])
    return out, f"只留{keep}一邊"


@fault("subsidiary_swap", "子公司歧義", "high")
def f_swap(q, p, rng):
    """把指標換成另一家子公司的同名指標（問題明明指定了子公司）。"""
    k = kb()
    gate = planning.Gate(k, q["role"])
    out = _copy(p)
    changed = []
    for i, m in enumerate(p["metrics"]):
        twins = gate.subsidiary_twins([m]).get(m)
        if twins:
            out["metrics"][i] = twins[0]
            changed.append((m, twins[0]))
    if not changed:
        return None
    for t in out["terms"]:
        t["metrics"] = list(out["metrics"])
    return out, "；".join(f"{a} → {b}" for a, b in changed)


@fault("permission_leak", "越權", "critical")
def f_leak(q, p, rng):
    k = kb()
    denied = sorted(m for m in k.metrics if k.metric_access(m, q["role"])["effect"] == "deny" and not k.metrics[m].components)
    if not denied:
        return None
    m = rng.choice(denied)
    out = _copy(p)
    out["decision"] = "answer"
    out["metrics"] = p["metrics"] + [m]
    out["reason"] = ""
    return out, f"加入角色不可看的 {m}"


@fault("aggregate_leak", "越權", "critical")
def f_aggregate_leak(q, p, rng):
    k = kb()
    if k.metric_access("securities.fund_fee_income", q["role"])["effect"] != "deny":
        return None
    out = _copy(p)
    out["decision"] = "answer"
    out["metrics"] = p["metrics"] + ["securities.total_fee_income"]
    out["reason"] = ""
    return out, "透過總指標（含被擋分項）取得資料"


@fault("gap_substitution", "待定範圍代替", "high")
def f_gap_sub(q, p, rng):
    """題目屬於待定／不存在，模型卻用相近的真實指標回答。"""
    if q["category"] != "待定或不存在" or not q["expect"]["forbidden"]:
        return None
    k = kb()
    sub = q["expect"]["forbidden"][0]
    term_classes = {"g01": ["securities:SecuritiesFeeIncome", "securities:StockProduct"],
                    "g02": ["fh:AUM", "bank:ForeignExchangeProduct"],
                    "g03": ["bank:BankFeeIncome", "bank:CollectiveManagementProduct"],
                    "g04": ["fh:LUM", "securities:StockProduct"],
                    "g05": ["fh:AUM", "bank:GoldProduct"]}.get(q["id"], [k.metrics[sub].class_id])
    out = _copy(p)
    out.update(decision="answer", metrics=[sub], reason="")
    out["terms"] = [{"text": q["question"], "classes": term_classes, "metrics": [sub]}]
    return out, f"用 {sub} 代替（用語宣告誠實）"


@fault("gap_substitution_consistent", "待定範圍代替", "high")
def f_gap_sub_consistent(q, p, rng):
    res = f_gap_sub(q, p, rng)
    if not res:
        return None
    out, why = res
    k = kb()
    m = out["metrics"][0]
    out["terms"][0]["classes"] = [k.metrics[m].class_id] + k.metrics[m].product_ids
    return out, why.replace("用語宣告誠實", "並改寫用語宣告")


@fault("gap_as_metric", "待定範圍代替", "high")
def f_gap_as_metric(q, p, rng):
    if q["id"] != "g01":
        return None
    out = _copy(p)
    out.update(decision="answer", metrics=["securities.taiwan_stock_fee_income"], reason="")
    return out, "把待定範圍 ID 當指標"


@fault("false_is_a", "錯誤推理", "medium")
def f_false_is_a(q, p, rng):
    out = _copy(p)
    out["is_a"] = p["is_a"] + [["bank:ETFProduct", "bank:FundProduct"]]
    out["classes"] = p["classes"] + ["bank:ETFProduct"]
    return out, "宣稱 ETF ⊑ 基金商品"


@fault("negation_ignored", "否定條件", "high")
def f_negation(q, p, rng):
    if not p["exclude"]:
        return None
    k = kb()
    extra = [m.id for m in k.metrics_matching(role=q["role"], kind="aum", product="securities:OverseasFinancialProduct")]
    out = _copy(p)
    out["metrics"] = p["metrics"] + extra
    for t in out["terms"]:
        t["metrics"] = list(out["metrics"])
    return out, "忽略「不屬於證券」，把證券海外 AUM 也列入（exclude 有宣告）"


@fault("negation_ignored_silent", "否定條件", "high")
def f_negation_silent(q, p, rng):
    res = f_negation(q, p, rng)
    if not res:
        return None
    out, why = res
    out["exclude"] = []
    return out, why.replace("exclude 有宣告", "exclude 也沒寫")


@fault("double_count", "總指標加總", "medium")
def f_double(q, p, rng):
    if "securities.total_aum" in p["metrics"] or q["category"] == "總指標":
        out = _copy(p)
        out["metrics"] = sorted(set(p["metrics"]) | {"securities.total_aum", "securities.bond_aum"})
        return out, "總指標與分項並列（意圖加總）"
    return None


@fault("version_drift", "版本", "low")
def f_version(q, p, rng):
    out = _copy(p)
    out["ontology_version"] = "0.16.0"
    return out, "引用舊版本號"


@fault("answer_instead_of_clarify", "子公司歧義", "high")
def f_no_clarify(q, p, rng):
    """歧義題：模型只挑一邊直接答，且用語宣告也只寫那一邊（看起來一致）。"""
    if q["category"] != "子公司歧義":
        return None
    k = kb()
    res = f_one_side(q, p, rng)
    if not res:
        return None
    out, why = res
    m = out["metrics"][0]
    for t in out["terms"]:
        t["classes"] = [k.metrics[m].class_id] + k.metrics[m].product_ids
    return out, why + "，用語宣告也只寫那一邊"


def apply_faults(seed=7, question_file="questions.yaml"):
    """每題 × 每種錯誤（適用時）產生一筆變異計畫。"""
    rng = random.Random(seed)
    cases = []
    for q in questions(question_file):
        gold = gold_plan(q)
        for name, info in FAULTS.items():
            res = info["fn"](q, gold, rng)
            if res:
                mutated, why = res
                cases.append({"question": q, "fault": name, "family": info["family"], "harm": info["harm"],
                              "plan": mutated, "why": why})
    return cases
