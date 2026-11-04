from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path

from .client import UcpCatalogClient
from .config import Config, ROOT
from .store import SyncStore


logger = logging.getLogger("nexor.siempresalud_sync")


def load_nexor_references() -> set[str]:
    catalog_path = Path(
        os.environ.get(
            "NEXOR_CATALOG_JS",
            str(ROOT / "productos_siempresalud_catalogo.js"),
        )
    )
    if not catalog_path.exists():
        logger.warning("NEXOR catalog file not found at %s; supplier matching is disabled.", catalog_path)
        return set()
    text = catalog_path.read_text(encoding="utf-8")
    match = re.match(r"\s*window\.NEXOR_PRODUCTS\s*=\s*(\[.*\])\s*;?\s*$", text, re.S)
    if not match:
        raise RuntimeError(f"Unexpected NEXOR catalog format in {catalog_path}.")
    products = json.loads(match.group(1))
    references: set[str] = set()
    for product in products:
        reference = product.get("reference")
        if isinstance(reference, str) and reference.strip():
            references.add(reference.strip())
        for variant in product.get("variants", []):
            sku = variant.get("sku")
            if isinstance(sku, str) and sku.strip():
                references.add(sku.strip())
    return references


class SyncService:
    def __init__(self, config: Config, store: SyncStore) -> None:
        self.config = config
        self.store = store
        self._thread_lock = threading.Lock()

    def client(self) -> UcpCatalogClient:
        return UcpCatalogClient(
            private_key_path=self.config.private_key_path,
            private_key_password=self.config.private_key_password,
            agent_profile_url=self.config.agent_profile_url,
            signature_agent_url=self.config.signature_agent_url,
            timeout=self.config.request_timeout_seconds,
            max_attempts=self.config.max_request_attempts,
        )

    def run(self, scopes: set[str], run_id: str | None = None) -> dict[str, int]:
        if not scopes:
            raise ValueError("At least one synchronization scope is required.")
        run_id = run_id or self.store.start_run(scopes)
        heartbeat_stop = threading.Event()

        def heartbeat() -> None:
            while not heartbeat_stop.wait(30):
                self.store.heartbeat(run_id)

        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        try:
            products, complete = self.client().fetch_catalog()
            references = load_nexor_references()
            stats = self.store.apply_catalog(run_id, products, scopes, complete, references)
            self.store.update_run_stats(run_id, stats)
            self.store.finish_run(run_id, "succeeded", catalog_complete=complete)
            self.store.schedule_success(scopes)
            logger.info("Sync %s succeeded (complete=%s): %s", run_id, complete, stats)
            return stats
        except Exception as exc:
            self.store.finish_run(run_id, "failed", str(exc))
            self.store.schedule_failure(scopes)
            logger.exception("Sync %s failed: %s", run_id, exc)
            raise
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=2)

    def manual_sync(self) -> str:
        if not self._thread_lock.acquire(blocking=False):
            raise RuntimeError("Another synchronization is already running.")
        scopes = {"inventory", "price", "catalog"}
        try:
            run_id = self.store.start_run(scopes)
        except Exception:
            self._thread_lock.release()
            raise

        def run_all() -> None:
            try:
                self.run(scopes, run_id)
            except Exception:
                logger.exception("Manual synchronization could not complete.")
            finally:
                self._thread_lock.release()

        try:
            thread = threading.Thread(target=run_all, name="manual-siempresalud-sync", daemon=True)
            thread.start()
        except Exception as exc:
            self.store.finish_run(run_id, "failed", f"No se pudo iniciar el trabajador: {exc}")
            self.store.schedule_failure(scopes)
            self._thread_lock.release()
            raise
        return run_id

    def scheduler_loop(self, stop: threading.Event) -> None:
        logger.info("Persistent scheduler started.")
        while not stop.is_set():
            scopes = self.store.due_scopes()
            if scopes and self._thread_lock.acquire(blocking=False):
                try:
                    self.run(scopes)
                except Exception:
                    logger.exception("Scheduled synchronization could not complete.")
                finally:
                    self._thread_lock.release()
            stop.wait(self.config.sync_interval_seconds)
