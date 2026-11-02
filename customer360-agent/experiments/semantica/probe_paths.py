"""不接 LLM，觀察 Semantica 的 query_with_reasoning 回傳什麼推理路徑與來源。

三種設定：
  A. ContextGraph 物件（官方文件主推的寫法）＋關鍵字檢索（雲端拿不到向量模型，不用向量庫）
  B. {"entities","relationships"} 字典＋關鍵字檢索
  C. 直接指定正確的起點節點（假設檢索完全正確），呼叫同一個路徑建構函式

LLM 換成 StubLLM：只記下 Semantica 組好的 prompt，回傳固定字串。
"""

import json
import logging
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)
from semantica.context import ContextRetriever  # noqa: E402

from load_c360 import DATA, build_context_graph, build_kg_dict  # noqa: E402

HERE = Path(__file__).resolve().parent

QUESTIONS = [
    {"id": "q1", "ask": "這位客戶在銀行的基金手收是多少", "spaced": "銀行 基金 手收",
     "gold": ["bank.fund_fee_income"], "trap": ["securities.fund_fee_income"]},
    {"id": "q2", "ask": "客戶的複委託基金庫存有多少", "spaced": "複委託 基金 AUM",
     "gold": ["securities.fund_aum"], "trap": ["bank.fund_aum"]},
    {"id": "q3", "ask": "基金手收是多少", "spaced": "基金 手收",
     "gold": [], "trap": [], "ambiguous": ["bank.fund_fee_income", "securities.fund_fee_income"]},
    {"id": "q4", "ask": "理專的手收怎麼算", "spaced": "理專 手收",
     "gold": ["bank.product_fee_income"], "trap": []},
    {"id": "q5", "ask": "銀行 AUM 算不算指標", "spaced": "銀行 AUM 指標",
     "gold": ["bank:BankAUM", "fh:Metric"], "trap": []},
]


class StubLLM:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt, **_):
        self.prompts.append(prompt)
        return "（StubLLM：不作答）"


def reasoning_section(prompt):
    marker = "Reasoning Paths (Multi-hop connections):"
    if marker not in prompt:
        return ""
    return prompt.split(marker, 1)[1].split("Instructions:", 1)[0].strip()


def run_retriever(label, graph, query):
    llm = StubLLM()
    retriever = ContextRetriever(knowledge_graph=graph, use_graph_expansion=True, max_expansion_hops=2)
    result = retriever.query_with_reasoning(query, llm_provider=llm, max_results=10, max_hops=2)
    prompt = llm.prompts[-1] if llm.prompts else ""
    return {
        "setup": label, "query": query,
        "num_sources": result.get("num_sources"),
        "sources": [{"source": s["source"], "score": round(float(s["score"]), 3),
                     "content": s["content"][:60]} for s in result.get("sources", [])],
        "reasoning_path": result.get("reasoning_path"),
        "num_reasoning_paths": result.get("num_reasoning_paths"),
        "confidence": round(float(result.get("confidence", 0.0)), 3),
        "prompt_reasoning_section": reasoning_section(prompt),
        "llm_called": bool(llm.prompts),
    }


def run_oracle(kg, seeds, max_hops=2):
    retriever = ContextRetriever(knowledge_graph=kg)
    entities = {e["id"]: e for e in kg["entities"]}
    paths = retriever._build_reasoning_path([entities[s] for s in seeds if s in entities], max_hops=max_hops)
    return [{"hops": p["hops"],
             "text": " ".join(
                 part for i, e in enumerate(p["entities"])
                 for part in ([e.get("name") or e.get("id")] +
                              ([f'--[{p["relationships"][i]["type"]}]-->'] if i < len(p["relationships"]) else [])))}
            for p in paths]


def main():
    cg, kg = build_context_graph(), build_kg_dict()
    out = {"ontology_version": DATA["version"], "nodes": len(kg["entities"]),
           "edges": len(kg["relationships"]), "runs": []}
    for q in QUESTIONS:
        row = {"question": q, "retrieval": [], "oracle": {}}
        for text in (q["ask"], q["spaced"]):
            row["retrieval"].append(run_retriever("A ContextGraph", cg, text))
            row["retrieval"].append(run_retriever("B kg dict", kg, text))
        seeds = q["gold"] or q.get("ambiguous", [])
        row["oracle"] = {"seeds": seeds, "paths": run_oracle(kg, seeds)}
        out["runs"].append(row)
    path = HERE / "results" / "probe_paths.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in out["runs"]:
        q = row["question"]
        print(f'\n=== {q["id"]} {q["ask"]}')
        for r in row["retrieval"]:
            src = [s["source"] for s in r["sources"]]
            print(f'  [{r["setup"]}] 「{r["query"]}」 sources={r["num_sources"]} paths={r["num_reasoning_paths"]} '
                  f'conf={r["confidence"]} llm_called={r["llm_called"]}')
            print(f'      sources: {src}')
            print(f'      reasoning_path: {r["reasoning_path"]!r}')
        print(f'  [C oracle seeds={row["oracle"]["seeds"]}] {len(row["oracle"]["paths"])} paths')
        for p in row["oracle"]["paths"][:6]:
            print("      ", p["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
