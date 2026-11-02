"""Semantic Studio 本機伺服器：python -m semantic_studio [--config config.yaml] [--port 8870] [--open]

只監聽 config 的 studio.host（預設 127.0.0.1）。寫入型 API 需要 header X-Studio: 1。
"""

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from ontology_kit.config import Config

from .core import Studio, StudioError

WEB = Path(__file__).resolve().parent / "web"
MAX_BODY = 2 * 1024 * 1024


def make_handler(studio):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SemanticStudio/1.0"

        def log_message(self, fmt, *args):
            pass

        def send(self, status, body, content_type="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else (
                body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8"))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            query = parse_qs(url.query)
            try:
                if url.path in ("/", "/index.html"):
                    return self.send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
                if url.path.startswith("/static/"):
                    target = (WEB / url.path[len("/static/"):]).resolve()
                    if not target.is_relative_to(WEB) or not target.is_file():
                        return self.send(404, {"error": "not found"})
                    kind = "text/javascript" if target.suffix == ".js" else (mimetypes.guess_type(target.name)[0] or "application/octet-stream")
                    if kind.startswith("text/") or kind.endswith("javascript"):
                        kind += "; charset=utf-8"
                    return self.send(200, target.read_bytes(), kind)
                if url.path == "/api/state":
                    return self.send(200, studio.state())
                if url.path == "/api/node":
                    return self.send(200, studio.node_detail(query.get("id", [""])[0]))
                if url.path == "/api/turtle":
                    return self.send(200, studio.turtle(query.get("what", ["ontology"])[0]), "text/turtle; charset=utf-8")
                return self.send(404, {"error": "not found"})
            except StudioError as error:
                return self.send(400, {"error": str(error)})
            except Exception as error:  # 不讓連線直接斷掉（瀏覽器會顯示 ERR_EMPTY_RESPONSE）
                return self.fail(error)

        def fail(self, error):
            traceback.print_exc(file=sys.stderr)
            return self.send(500, {"error": f"{type(error).__name__}: {error}"})

        def do_POST(self):
            if self.headers.get("X-Studio") != "1":
                return self.send(403, {"error": "missing X-Studio header"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self.send(413, {"error": "body too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                path = urlparse(self.path).path
                if path == "/api/term/preview":
                    return self.send(200, studio.preview_term(body["term"]))
                if path == "/api/term/save":
                    studio.save_term(body["term"], body.get("original_id"))
                    return self.send(200, studio.state())
                if path == "/api/term/delete":
                    studio.delete_term(body["id"])
                    return self.send(200, studio.state())
                if path == "/api/import":
                    added = studio.import_terms(body["text"], body.get("format", "csv"), body.get("source") or "匯入的業務字典")
                    return self.send(200, {"added": added, "state": studio.state()})
                if path == "/api/policy/save":
                    studio.save_policy(body["policy"])
                    return self.send(200, studio.state())
                if path == "/api/suggest":
                    return self.send(200, studio.suggest(body.get("name", ""), body.get("definition", "")))
                if path == "/api/reload":
                    studio.reload()
                    return self.send(200, studio.state())
                return self.send(404, {"error": "not found"})
            except (StudioError, KeyError, ValueError, TypeError) as error:
                return self.send(400, {"error": str(error)})
            except Exception as error:
                return self.fail(error)

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m semantic_studio", description="Semantic Studio 本機前端")
    parser.add_argument("--config")
    parser.add_argument("--port", type=int)
    parser.add_argument("--open", action="store_true", help="啟動後開啟瀏覽器")
    args = parser.parse_args(argv)
    cfg = Config(args.config)
    settings = cfg.data["studio"]
    host, port = settings.get("host", "127.0.0.1"), args.port or settings.get("port", 8870)
    studio = Studio(cfg)
    server = ThreadingHTTPServer((host, port), make_handler(studio))
    url = f"http://{host}:{port}/"
    print(f"Semantic Studio：{url}（Ctrl+C 結束）")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
