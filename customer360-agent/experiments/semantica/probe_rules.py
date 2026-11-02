"""不接 LLM，看 Semantica 規則推理（Reasoner＋ExplanationGenerator）回傳的推理路徑。

事實：subClassOf(子, 父)、instance_of(指標, 類別)、about_product(指標, 商品類別)。
規則：上層關係遞移、指標沿上層鏈繼承類別。
"""

import json
import logging
from pathlib import Path

logging.disable(logging.CRITICAL)
from semantica.reasoning import ExplanationGenerator, Reasoner  # noqa: E402

from load_c360 import DATA  # noqa: E402

HERE = Path(__file__).resolve().parent
RULES = [
    "IF subClassOf(?x, ?y) AND subClassOf(?y, ?z) THEN subClassOf(?x, ?z)",
    "IF instance_of(?m, ?c) AND subClassOf(?c, ?d) THEN instance_of(?m, ?d)",
]
GOALS = [
    ("銀行基金手收是一種指標嗎？", "instance_of(bank.fund_fee_income, fh:Metric)"),
    ("證券複委託基金手收是銀行手收嗎？（應為否）", "instance_of(securities.fund_fee_income, bank:BankFeeIncome)"),
    ("理專是一種職員嗎？", "subClassOf(bank:FinancialAdvisor, fh:Employee)"),
]


def build():
    r = Reasoner()
    for rule in RULES:
        r.add_rule(rule)
    for c in DATA["classes"]:
        for p in c["parents"]:
            r.add_fact(f'subClassOf({c["id"]}, {p})')
    for m in DATA["metrics"]:
        r.add_fact(f'instance_of({m["id"]}, {m["class_id"]})')
        for p in m["product_ids"]:
            r.add_fact(f'about_product({m["id"]}, {p})')
    return r


def premises_tree(r, fact, depth=0, max_depth=6):
    """backward_chain 只回傳一層前提；逐層展開，看完整證明樹長什麼樣。"""
    res = r.backward_chain(fact)
    if res is None or depth >= max_depth:
        return {"fact": fact, "proved": res is not None}
    node = {"fact": res.conclusion, "rule": res.rule_used.name if res.rule_used else "（既有事實）"}
    if res.rule_used:
        node["premises"] = [premises_tree(r, p, depth + 1) for p in res.premises]
    return node


def main():
    r = build()
    gen = ExplanationGenerator()
    out = {"facts": len(r.facts), "rules": RULES, "goals": []}
    for title, goal in GOALS:
        res = r.backward_chain(goal)
        row = {"question": title, "goal": goal, "proved": res is not None}
        if res is not None:
            exp = gen.generate_explanation(res)
            path = exp.reasoning_path
            row["reasoning_path"] = {
                "start_facts": path.start_facts, "end_conclusion": path.end_conclusion,
                "steps": [s.description for s in path.steps], "total_confidence": path.total_confidence}
            row["natural_language"] = exp.natural_language
            row["full_proof_tree"] = premises_tree(r, goal)
        out["goals"].append(row)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "probe_rules.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
