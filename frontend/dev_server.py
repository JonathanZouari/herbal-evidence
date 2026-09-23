"""Local static server that behaves like the Caddy container: same CSP/security headers, runtime js/config.js
generated from frontend/.env, and extensionless URLs mapped to .html. Stdlib only (no Docker needed).

    python frontend/dev_server.py        # http://localhost:8080
"""

import json
import os
import re
from urllib.parse import unquote
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
KEYS = ("APP_ENV", "API_BASE_URL", "SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")
URL_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:[0-9]+)?$")


def load_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.split(" #")[0].strip().strip('"').strip("'")
    env.update({k: os.environ[k] for k in KEYS if k in os.environ})
    for k in ("API_BASE_URL", "SUPABASE_URL"):
        if not URL_RE.match(env.get(k, "")):
            raise SystemExit(f"{k} missing or invalid in frontend/.env")
    return env


def csp(env: dict) -> str:
    return ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
            f"connect-src 'self' {env['API_BASE_URL']} {env['SUPABASE_URL']}; object-src 'none'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'")


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".css": "text/css",
                      ".woff2": "font/woff2", ".html": "text/html; charset=utf-8"}

    def __init__(self, *args, env: dict, **kwargs):
        self.env = env
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", csp(self.env))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/js/config.js":
            cfg = {k: self.env.get(k, "") for k in KEYS}
            body = f"window.APP_CONFIG = Object.freeze({json.dumps(cfg)});\n".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        decoded = unquote(path)
        if decoded.endswith(".py") or "/." in decoded or "\\" in decoded:
            self.send_error(404)
            return
        if "." not in path.rsplit("/", 1)[-1] and path != "/" and (ROOT / f"{path.lstrip('/')}.html").exists():
            self.path = path + ".html"
        super().do_GET()


if __name__ == "__main__":
    env = load_env()
    port = int(os.environ.get("PORT", env.get("PORT", 8080)))
    print(f"frontend on http://localhost:{port}  (API {env['API_BASE_URL']})")
    ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, env=env)).serve_forever()
