"""Build a dependency-free browser viewer from the existing graph snapshots."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "offline"


def main():
    views = {name: json.loads((HERE / "data" / f"{name}.json").read_text(encoding="utf-8"))
             for name in ("full", "business", "securities", "ontology")}
    for name, graph in views.items():
        ids = {n["id"] for n in graph["nodes"]}
        assert len(ids) == len(graph["nodes"]), name
        assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"]), name
    payload = {"views": views, "exported": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "manifest": json.loads((HERE / "data/manifest.json").read_text(encoding="utf-8"))}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("&", "\\u0026")
    template = (HERE / "offline-viewer.html").read_text(encoding="utf-8")
    assert template.count("__GRAPH_DATA__") == 1
    html = template.replace("__GRAPH_DATA__", data)
    OUT.mkdir(exist_ok=True)
    target = OUT / "客戶360-Semantica圖譜-離線版.html"
    target.write_text(html, encoding="utf-8")
    report = {"file": target.name, "bytes": target.stat().st_size,
              "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "views": {k: {"nodes": len(v["nodes"]), "edges": len(v["edges"])} for k, v in views.items()}}
    (OUT / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
