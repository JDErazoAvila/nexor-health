from __future__ import annotations

import logging
import signal
import threading

from .config import Config
from .server import serve
from .store import SyncStore
from .worker import SyncService


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = Config.from_env()
    store = SyncStore(config.database_path)
    store.reconcile_interrupted_runs()
    service = SyncService(config, store)
    service.client()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    scheduler = threading.Thread(
        target=service.scheduler_loop,
        args=(stop,),
        name="siempresalud-scheduler",
        daemon=True,
    )
    scheduler.start()
    try:
        serve(config, store, service, stop)
    finally:
        stop.set()
        scheduler.join(timeout=5)


if __name__ == "__main__":
    main()
