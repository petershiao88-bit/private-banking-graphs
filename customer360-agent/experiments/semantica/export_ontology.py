"""把 PoC 讀到的本體（類別、上層、物件屬性、PG 指標、詞條）匯出成中性的 c360-ontology.json。

在 customer360-agent 目錄執行（用 PoC 自己的環境，不需要 Semantica）：
    PYTHONPATH=src:../customer360-rdf/src python experiments/semantica/export_ontology.py
"""

import json
from pathlib import Path

from c360_agent import settings
from c360_agent.knowledge import Knowledge

OUT = Path(__file__).resolve().parent / "c360-ontology.json"


def main():
    kb = Knowledge(settings.load())
    cur = kb.cfg.curie
    out = {"version": kb.version, "classes": [], "metrics": [], "terms": [], "object_properties": []}
    for c in kb.classes.values():
        out["classes"].append({k: c[k] for k in ("id", "label", "definition", "layer", "subsidiary", "parents", "ancestors")})
    for m in kb.metrics.values():
        out["metrics"].append({"id": m.id, "name": m.name, "definition": m.definition, "subsidiary": m.subsidiary,
                               "kind": m.kind, "class_id": m.class_id, "product_ids": list(m.product_ids),
                               "components": list(m.components)})
    for t in kb.terms.values():
        out["terms"].append({"id": t["id"], "name": t["name"], "definition": t["definition"], "mappings": t["mappings"]})
    for p in kb.studio.state()["properties"]:
        if p["kind"] == "object":
            out["object_properties"].append({"id": cur(p["uri"]), "label": p["label"],
                                             "domain": [cur(d) for d in p["domain"]], "range": [cur(r) for r in p["range"]]})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: len(v) for k, v in out.items() if isinstance(v, list)}, "→", OUT)


if __name__ == "__main__":
    main()
