from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from siempresalud_sync.config import Config
from siempresalud_sync.server import make_handler
from siempresalud_sync.store import SyncStore


class FakeService:
    called = False

    def manual_sync(self) -> str:
        self.called = True
        return "manual-test"


class DashboardApiTests(unittest.TestCase):
    def test_dashboard_requires_token_and_manual_sync_is_protected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Config(
                database_path=Path(directory) / "sync.sqlite3",
                private_key_path=Path(directory) / "key.pem",
                private_key_password=None,
                agent_profile_url="https://nexor.example/.well-known/ucp",
                signature_agent_url="https://nexor.example/.well-known/ucp",
                admin_token="t" * 40,
                host="127.0.0.1",
                port=0,
            )
            store = SyncStore(config.database_path)
            service = FakeService()
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), make_handler(config, store, service)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                page = urllib.request.urlopen(base_url + "/", timeout=3)
                self.assertEqual(page.status, 200)
                self.assertIn(b"Sincronizaci", page.read())

                with self.assertRaises(urllib.error.HTTPError) as unauthorized:
                    urllib.request.urlopen(base_url + "/api/dashboard", timeout=3)
                self.assertEqual(unauthorized.exception.code, 401)
                unauthorized.exception.close()

                request = urllib.request.Request(
                    base_url + "/api/dashboard",
                    headers={"Authorization": f"Bearer {config.admin_token}"},
                )
                response = urllib.request.urlopen(request, timeout=3)
                self.assertEqual(response.status, 200)

                request = urllib.request.Request(
                    base_url + "/api/sync",
                    data=b"",
                    headers={"Authorization": f"Bearer {config.admin_token}"},
                    method="POST",
                )
                response = urllib.request.urlopen(request, timeout=3)
                self.assertEqual(response.status, 202)
                self.assertTrue(service.called)
            finally:
                server.shutdown()
                thread.join(timeout=3)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
