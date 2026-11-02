"""Run the official Semantica Explorer against a disposable, local graph snapshot."""

import argparse
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def create_explorer(view="full", port=8866):
    # Graph browsing stays local; the optional question page calls OpenRouter.
    os.environ["SEMANTICA_ALLOW_ANONYMOUS"] = "true"
    os.environ["ALLOWED_ORIGINS"] = f"http://127.0.0.1:{port},http://localhost:{port}"
    from semantica.context import ContextGraph
    from semantica.explorer.app import create_app
    from semantica.explorer.session import GraphSession

    graph = ContextGraph(advanced_analytics=False, extract_entities=False, extract_relationships=False)
    graph.load_from_file(HERE / "data" / (view + ".json"))
    session = GraphSession(graph)
    app = create_app(session=session)
    from ontology_hub import attach_local_ontology
    attach_local_ontology(app)
    from graph_qa import attach_graph_qa
    attach_graph_qa(app, view=view, port=port)
    from handoff_demo import attach_handoff_demo
    attach_handoff_demo(app, port=port)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=["securities", "business", "ontology", "full"], default="full")
    parser.add_argument("--port", type=int, default=8866)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if args.open_browser:
        import threading
        import time
        import urllib.request
        import webbrowser

        def open_when_ready():
            url = f"http://127.0.0.1:{args.port}"
            for _ in range(60):
                try:
                    with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                        if response.status == 200:
                            webbrowser.open(url)
                            return
                except OSError:
                    time.sleep(0.5)
        threading.Thread(target=open_when_ready, daemon=True).start()
    import uvicorn
    uvicorn.run(create_explorer(args.view, args.port), host="127.0.0.1", port=args.port, log_level="warning")
