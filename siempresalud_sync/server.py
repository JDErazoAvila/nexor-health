from __future__ import annotations

import hmac
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import Config
from .store import SyncStore
from .worker import SyncService


logger = logging.getLogger("nexor.siempresalud_sync")
DASHBOARD_PATH = Path(__file__).with_name("dashboard.html")


def make_handler(config: Config, store: SyncStore, service: SyncService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "NEXORSync/1.0"

        def log_message(self, format: str, *args: object) -> None:
            logger.info("%s - %s", self.address_string(), format % args)

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            value = self.headers.get("Authorization", "")
            supplied = value[7:] if value.startswith("Bearer ") else ""
            if not hmac.compare_digest(supplied, config.admin_token):
                self._json(401, {"error": "Token de administración inválido."})
                return False
            return True

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = DASHBOARD_PATH.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                    "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
                )
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path.startswith("/api/") and not self._authorized():
                return
            if path == "/api/dashboard":
                self._json(200, store.dashboard())
                return
            self._json(404, {"error": "Ruta no encontrada."})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if not self._authorized():
                return
            if path == "/api/sync":
                try:
                    run_id = service.manual_sync()
                except RuntimeError as exc:
                    self._json(409, {"error": str(exc)})
                    return
                self._json(
                    202,
                    {"message": "Sincronización manual iniciada.", "run_id": run_id},
                )
                return
            self._json(404, {"error": "Ruta no encontrada."})

    return Handler


def serve(
    config: Config,
    store: SyncStore,
    service: SyncService,
    stop: threading.Event,
) -> None:
    httpd = ThreadingHTTPServer((config.host, config.port), make_handler(config, store, service))
    logger.info("Dashboard listening on %s:%s", config.host, config.port)
    shutdown = threading.Thread(target=lambda: (stop.wait(), httpd.shutdown()), daemon=True)
    shutdown.start()
    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        httpd.server_close()
        shutdown.join(timeout=2)
