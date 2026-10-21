"""Local Excalidraw server for the diagrams folder ($CODE_DIAGRAM_ROOT, default ~/diagrams): open a diagram with one http:// link, auto-save edits to disk.

Usage: python3 server.py [port]    (default 7878, listens on 127.0.0.1 only)
  http://diagrams.localhost:7878/                         list all diagrams
  http://diagrams.localhost:7878/?file=<repo>/<flow>.excalidraw   open one diagram
  http://diagrams.localhost:7878/open/<absolute path>:<line>       open a code line in IntelliJ
"""
import html
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

DIAGRAMS_ROOT = Path(os.environ.get("CODE_DIAGRAM_ROOT", Path.home() / "diagrams"))
CODE_ROOT = Path.home() / "repos"
OPEN_PREFIX = "/open/"
EDITOR_PAGE = Path(__file__).with_name("editor.html")
DEFAULT_PORT = 7878


def resolve_diagram(relative_path: str) -> Optional[Path]:
    """Return the absolute path only if it is an .excalidraw file inside DIAGRAMS_ROOT."""
    candidate = (DIAGRAMS_ROOT / relative_path).resolve()
    inside_root = DIAGRAMS_ROOT.resolve() in candidate.parents
    if not inside_root or candidate.suffix != ".excalidraw":
        return None
    return candidate


def idea_url_for(open_path: str) -> Optional[str]:
    """Turn a decoded '/open/<absolute path>:<line>' into an idea:// URL, only for an existing file under CODE_ROOT.

    The link carries the file in its path, not a query, because VS Code's markdown preview
    percent-encodes '=' and '&' in an idea:// query before handing the link on, and IntelliJ can't read that.
    """
    file_and_line = open_path[len(OPEN_PREFIX):]
    file_part, _, line_part = file_and_line.rpartition(":")
    if not line_part.isdigit():
        file_part, line_part = file_and_line, "1"
    code_file = Path(file_part).resolve()
    if CODE_ROOT.resolve() not in code_file.parents or not code_file.is_file():
        return None
    return f"idea://open?file={quote(str(code_file))}&line={line_part}"


def render_opened(file_and_line: str) -> str:
    return (
        "<!doctype html><meta charset=utf-8><title>Opened in IntelliJ</title>"
        "<body style='font:16px -apple-system,sans-serif;margin:40px'>"
        f"<p>Opened in IntelliJ:</p><p><code>{html.escape(file_and_line)}</code></p><p>You can close this tab.</p>"
    )


def list_diagrams() -> list:
    found = []
    for path in sorted(DIAGRAMS_ROOT.rglob("*.excalidraw")):
        found.append(str(path.relative_to(DIAGRAMS_ROOT)))
    return found


def render_index(diagram_paths: list) -> str:
    rows = []
    for relative_path in diagram_paths:
        rows.append(f'<li><a href="/?file={quote(relative_path)}">{html.escape(relative_path)}</a></li>')
    return (
        "<!doctype html><meta charset=utf-8><title>Diagrams</title>"
        "<body style='font:16px -apple-system,sans-serif;max-width:800px;margin:40px auto'>"
        f"<h1>Diagrams</h1><p>{html.escape(str(DIAGRAMS_ROOT))}</p><ul>{''.join(rows)}</ul>"
    )


class DiagramHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/" and "file" in query:
            self._send(200, "text/html", EDITOR_PAGE.read_bytes())
        elif url.path == "/":
            self._send(200, "text/html", render_index(list_diagrams()).encode())
        elif url.path == "/api/file":
            self._read_diagram(query.get("file", [""])[0])
        elif unquote(url.path).startswith(OPEN_PREFIX):
            self._open_in_intellij(unquote(url.path))
        else:
            self._send(404, "text/plain", b"not found")

    def do_PUT(self):
        url = urlparse(self.path)
        if url.path != "/api/file" or not self._is_same_origin():
            self._send(403, "text/plain", b"forbidden")
            return
        query = parse_qs(url.query)
        self._write_diagram(query.get("file", [""])[0], float(query.get("base_mtime", ["0"])[0]))

    def _is_same_origin(self) -> bool:
        # Blocks other web pages in Chrome from writing files through this server.
        origin = self.headers.get("Origin", "")
        return origin == f"http://{self.headers.get('Host', '')}"

    def _read_diagram(self, relative_path: str):
        diagram = resolve_diagram(relative_path)
        if diagram is None or not diagram.exists():
            self._send(404, "application/json", b'{"error": "no such diagram"}')
            return
        try:
            scene = json.loads(diagram.read_text())
        except PermissionError:
            # macOS privacy settings: the app running this server needs access to the diagrams folder.
            self._send(500, "application/json", b'{"error": "macOS blocked access: give Code Diagram Server Full Disk Access"}')
            return
        body = json.dumps({"mtime": diagram.stat().st_mtime, "scene": scene})
        self._send(200, "application/json", body.encode())

    def _write_diagram(self, relative_path: str, base_mtime: float):
        diagram = resolve_diagram(relative_path)
        if diagram is None:
            self._send(403, "text/plain", b"forbidden")
            return
        # Someone (Claude, or another tab) changed the file since this tab loaded it: don't overwrite.
        if diagram.exists() and diagram.stat().st_mtime > base_mtime + 0.001:
            self._send(409, "application/json", b'{"error": "changed on disk"}')
            return
        scene_text = self.rfile.read(int(self.headers["Content-Length"])).decode()
        json.loads(scene_text)
        temp_path = diagram.with_suffix(".excalidraw.tmp")
        temp_path.write_text(scene_text)
        os.replace(temp_path, diagram)
        self._send(200, "application/json", json.dumps({"mtime": diagram.stat().st_mtime}).encode())

    def _open_in_intellij(self, open_path: str):
        idea_url = idea_url_for(open_path)
        if idea_url is None:
            self._send(404, "text/plain", b"no such code file under ~/repos")
            return
        # Opened here, not by redirecting: VS Code's built-in browser won't follow a redirect to idea://.
        subprocess.run(["open", idea_url], check=False)
        self._send(200, "text/html", render_opened(open_path[len(OPEN_PREFIX) - 1:]).encode())

    def _send(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main(port: int):
    DIAGRAMS_ROOT.mkdir(exist_ok=True)
    print(f"Serving {DIAGRAMS_ROOT} at http://localhost:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), DiagramHandler).serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT)
