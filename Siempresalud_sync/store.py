from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SCHEDULES = {"inventory": 6 * 60 * 60, "price": 12 * 60 * 60, "catalog": 24 * 60 * 60}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _price(variant: dict) -> tuple[int | None, str | None]:
    price = variant.get("price")
    if not isinstance(price, dict):
        return None, None
    amount = price.get("amount")
    currency = price.get("currency")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        return None, None
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha():
        return None, None
    return amount, currency.upper()


class SyncStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = self.connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    scopes_json TEXT NOT NULL,
                    owner_pid INTEGER NOT NULL,
                    owner_host TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL,
                    products_consulted INTEGER NOT NULL DEFAULT 0,
                    products_updated INTEGER NOT NULL DEFAULT 0,
                    inventory_changes INTEGER NOT NULL DEFAULT 0,
                    price_changes INTEGER NOT NULL DEFAULT 0,
                    new_products INTEGER NOT NULL DEFAULT 0,
                    catalog_complete INTEGER,
                    error TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_sync
                    ON sync_runs(status) WHERE status = 'running';
                CREATE TABLE IF NOT EXISTS supplier_products (
                    product_id TEXT PRIMARY KEY,
                    handle TEXT,
                    title TEXT NOT NULL,
                    brand TEXT,
                    categories_json TEXT NOT NULL,
                    description_json TEXT,
                    source_url TEXT,
                    primary_image TEXT,
                    images_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_checked_at TEXT NOT NULL,
                    approval_status TEXT NOT NULL DEFAULT 'pending_review',
                    nexor_match INTEGER NOT NULL DEFAULT 0,
                    absent_from_complete_scan INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS supplier_variants (
                    variant_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL REFERENCES supplier_products(product_id),
                    sku TEXT,
                    presentation TEXT,
                    options_json TEXT NOT NULL,
                    provider_price_amount INTEGER,
                    provider_price_currency TEXT,
                    supplier_available INTEGER,
                    availability_status TEXT,
                    supplier_quantity INTEGER,
                    last_checked_at TEXT NOT NULL,
                    absent_from_complete_scan INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS supplier_variants_sku ON supplier_variants(sku);
                CREATE TABLE IF NOT EXISTS change_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES sync_runs(id),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    field TEXT NOT NULL,
                    old_value_json TEXT,
                    new_value_json TEXT,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS change_history_observed ON change_history(observed_at DESC);
                CREATE TABLE IF NOT EXISTS schedules (
                    name TEXT PRIMARY KEY,
                    interval_seconds INTEGER NOT NULL,
                    last_success_at TEXT,
                    next_due_at REAL NOT NULL,
                    retry_after REAL NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            for name, interval in SCHEDULES.items():
                db.execute(
                    """INSERT OR IGNORE INTO schedules(name, interval_seconds, next_due_at)
                       VALUES (?, ?, 0)""",
                    (name, interval),
                )

    def start_run(self, scopes: set[str]) -> str:
        run_id = str(uuid.uuid4())
        now_epoch = time.time()
        now = utc_now()
        host = socket.gethostname()
        with self.transaction() as db:
            active = db.execute(
                "SELECT id, owner_pid, owner_host, heartbeat_at FROM sync_runs WHERE status = 'running'"
            ).fetchone()
            if active:
                heartbeat = datetime.fromisoformat(active["heartbeat_at"]).timestamp()
                stale = now_epoch - heartbeat > 300
                same_host_dead = False
                if active["owner_host"] == host:
                    try:
                        os.kill(active["owner_pid"], 0)
                    except ProcessLookupError:
                        same_host_dead = True
                if not same_host_dead and not (active["owner_host"] != host and stale):
                    raise RuntimeError(f"Synchronization {active['id']} is already running.")
                db.execute(
                    "UPDATE sync_runs SET status='interrupted', finished_at=?, "
                    "error='Proceso anterior interrumpido.' WHERE id=?",
                    (now, active["id"]),
                )
            db.execute(
                """INSERT INTO sync_runs
                   (id, started_at, status, scopes_json, owner_pid, owner_host, heartbeat_at)
                   VALUES (?, ?, 'running', ?, ?, ?, ?)""",
                (run_id, now, json_text(sorted(scopes)), os.getpid(), host, now),
            )
        return run_id

    def reconcile_interrupted_runs(self) -> None:
        now_epoch = time.time()
        now = utc_now()
        with self.transaction() as db:
            active_runs = db.execute(
                "SELECT id, owner_pid, owner_host, heartbeat_at, scopes_json "
                "FROM sync_runs WHERE status='running'"
            ).fetchall()
            for run in active_runs:
                heartbeat = datetime.fromisoformat(run["heartbeat_at"]).timestamp()
                stale = now_epoch - heartbeat > 300
                dead = False
                if run["owner_host"] == socket.gethostname():
                    try:
                        os.kill(run["owner_pid"], 0)
                    except ProcessLookupError:
                        dead = True
                if not dead and not (run["owner_host"] != socket.gethostname() and stale):
                    continue
                db.execute(
                    "UPDATE sync_runs SET status='interrupted', finished_at=?, "
                    "error='Proceso interrumpido; reintento programado.' WHERE id=?",
                    (now, run["id"]),
                )
                for scope in json.loads(run["scopes_json"]):
                    if scope in SCHEDULES:
                        db.execute(
                            "UPDATE schedules SET next_due_at=?, retry_after=0 WHERE name=?",
                            (now_epoch, scope),
                        )

    def heartbeat(self, run_id: str) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE sync_runs SET heartbeat_at=? WHERE id=? AND status='running'",
                (utc_now(), run_id),
            )

    def finish_run(
        self,
        run_id: str,
        status: str,
        error: str | None = None,
        catalog_complete: bool | None = None,
    ) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE sync_runs SET status=?, finished_at=?, heartbeat_at=?, error=?, catalog_complete=? "
                "WHERE id=? AND status='running'",
                (
                    status,
                    utc_now(),
                    utc_now(),
                    error,
                    None if catalog_complete is None else int(catalog_complete),
                    run_id,
                ),
            )

    def apply_catalog(
        self,
        run_id: str,
        products: list[dict],
        scopes: set[str],
        complete_scan: bool,
        nexor_references: set[str],
    ) -> dict[str, int]:
        if not scopes.issubset(SCHEDULES):
            raise ValueError(f"Unknown synchronization scopes: {sorted(scopes - SCHEDULES.keys())}")
        observed_at = utc_now()
        seen_product_ids: set[str] = set()
        seen_variant_ids: set[str] = set()
        changed_product_ids: set[str] = set()
        new_products = 0
        inventory_changes = 0
        price_changes = 0

        with self.transaction() as db:
            for product in products:
                product_id = product["id"]
                if product_id in seen_product_ids:
                    continue
                seen_product_ids.add(product_id)
                variants = product.get("variants")
                if not isinstance(variants, list) or not variants:
                    raise ValueError(f"Product {product_id} has no UCP variant list.")
                existing = db.execute(
                    "SELECT * FROM supplier_products WHERE product_id=?", (product_id,)
                ).fetchone()
                if existing is None and "catalog" not in scopes:
                    continue
                if existing is None:
                    new_products += 1
                    changed_product_ids.add(product_id)
                    old_product: dict = {}
                else:
                    old_product = dict(existing)
                    if existing["absent_from_complete_scan"]:
                        changed_product_ids.add(product_id)
                        self._record_change(
                            db, run_id, "product", product_id, "returned_to_source",
                            True, False, observed_at
                        )

                title = product.get("title")
                if not isinstance(title, str) or not title.strip():
                    raise ValueError(f"Product {product_id} has no title.")
                metadata = product.get("metadata")
                observed_brand = metadata.get("brand") if isinstance(metadata, dict) else None
                observed_brand = observed_brand if isinstance(observed_brand, str) else None
                brand = (
                    observed_brand
                    if observed_brand is not None
                    else (existing["brand"] if existing else None)
                )
                categories = product.get("categories")
                categories_observed = isinstance(categories, list)
                if not categories_observed:
                    categories = (
                        _decode_json(existing["categories_json"])
                        if existing
                        else []
                    )
                description = product.get("description")
                description_observed = isinstance(description, (dict, str))
                if not description_observed:
                    description = (
                        _decode_json(existing["description_json"])
                        if existing and existing["description_json"]
                        else None
                    )
                media = product.get("media")
                media_observed = isinstance(media, list)
                if not media_observed:
                    images = (
                        _decode_json(existing["images_json"])
                        if existing
                        else []
                    )
                    if not isinstance(images, list):
                        images = []
                    media = []
                else:
                    images = [
                        item["url"]
                        for item in media
                        if isinstance(item, dict)
                        and item.get("type") == "image"
                        and isinstance(item.get("url"), str)
                    ]
                source_url = product.get("url")
                source_url = (
                    source_url
                    if isinstance(source_url, str)
                    else (existing["source_url"] if existing else None)
                )
                updated_product = {
                    "handle": product.get("handle") if isinstance(product.get("handle"), str) else None,
                    "title": title.strip(),
                    "brand": brand,
                    "categories_json": json_text(categories),
                    "description_json": json_text(description) if description is not None else None,
                    "source_url": source_url,
                    "primary_image": images[0] if images else None,
                    "images_json": json_text(images),
                    "last_seen_at": observed_at,
                    "last_checked_at": observed_at,
                    "nexor_match": int(
                        any(
                            isinstance(variant, dict)
                            and isinstance(variant.get("sku"), str)
                            and variant["sku"].strip() in nexor_references
                            for variant in variants
                        )
                    ),
                    "absent_from_complete_scan": 0,
                }
                if "catalog" in scopes or existing is None:
                    old_fields = {
                        "title": old_product.get("title"),
                        "brand": old_product.get("brand"),
                        "categories_json": old_product.get("categories_json"),
                        "description_json": old_product.get("description_json"),
                        "primary_image": old_product.get("primary_image"),
                        "images_json": old_product.get("images_json"),
                    }
                    observed_fields = [("title", "title"), ("brand", "brand")]
                    if categories_observed:
                        observed_fields.append(("categories", "categories_json"))
                    if description_observed:
                        observed_fields.append(("description", "description_json"))
                    if media_observed:
                        observed_fields.append(("images", "images_json"))
                    for field, column in observed_fields:
                        old_value = old_fields.get(column)
                        new_value = updated_product[column]
                        if old_value is not None and old_value != new_value:
                            self._record_change(
                                db, run_id, "product", product_id, field,
                                _decode_json(old_value), _decode_json(new_value), observed_at
                            )
                    approval_status = (
                        "matched_existing"
                        if updated_product["nexor_match"]
                        else "pending_review"
                    )
                    if existing is None:
                        self._record_change(
                            db, run_id, "product", product_id, "product_added", None,
                            {"title": updated_product["title"], "source_url": source_url},
                            observed_at,
                        )
                    db.execute(
                        """INSERT INTO supplier_products
                           (product_id, handle, title, brand, categories_json, description_json,
                            source_url, primary_image, images_json, first_seen_at, last_seen_at,
                            last_checked_at, approval_status, nexor_match, absent_from_complete_scan)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                           ON CONFLICT(product_id) DO UPDATE SET
                             handle=excluded.handle, title=excluded.title, brand=excluded.brand,
                             categories_json=excluded.categories_json,
                             description_json=excluded.description_json, source_url=excluded.source_url,
                             primary_image=excluded.primary_image, images_json=excluded.images_json,
                             last_seen_at=excluded.last_seen_at, last_checked_at=excluded.last_checked_at,
                             nexor_match=excluded.nexor_match, absent_from_complete_scan=0""",
                        (
                            product_id,
                            updated_product["handle"],
                            updated_product["title"],
                            updated_product["brand"],
                            updated_product["categories_json"],
                            updated_product["description_json"],
                            updated_product["source_url"],
                            updated_product["primary_image"],
                            updated_product["images_json"],
                            observed_at,
                            observed_at,
                            observed_at,
                            approval_status,
                            updated_product["nexor_match"],
                        ),
                    )
                    if existing is not None and any(
                        old_fields.get(column) != updated_product[column]
                        for column in ("title", "brand", "categories_json", "description_json", "images_json")
                    ):
                        changed_product_ids.add(product_id)
                else:
                    db.execute(
                        "UPDATE supplier_products SET last_seen_at=?, last_checked_at=? WHERE product_id=?",
                        (observed_at, observed_at, product_id),
                    )

                for variant in variants:
                    if not isinstance(variant, dict) or not isinstance(variant.get("id"), str):
                        raise ValueError(f"Product {product_id} contains a variant without an ID.")
                    variant_id = variant["id"]
                    seen_variant_ids.add(variant_id)
                    previous = db.execute(
                        "SELECT * FROM supplier_variants WHERE variant_id=?", (variant_id,)
                    ).fetchone()
                    if previous is None and "catalog" not in scopes:
                        continue
                    sku = variant.get("sku") if isinstance(variant.get("sku"), str) else None
                    presentation = variant.get("title") if isinstance(variant.get("title"), str) else None
                    options = variant.get("options")
                    if not isinstance(options, list):
                        options = []
                    amount, currency = _price(variant)
                    availability = variant.get("availability")
                    available = availability.get("available") if isinstance(availability, dict) else None
                    if not isinstance(available, bool):
                        available = None
                    status = availability.get("status") if isinstance(availability, dict) else None
                    status = status if isinstance(status, str) else None
                    is_new_variant = previous is None
                    if previous and previous["absent_from_complete_scan"]:
                        changed_product_ids.add(product_id)
                        self._record_change(
                            db, run_id, "variant", variant_id, "returned_to_source",
                            True, False, observed_at
                        )
                    if is_new_variant:
                        changed_product_ids.add(product_id)
                        self._record_change(
                            db, run_id, "variant", variant_id, "variant_added", None,
                            {
                                "sku": sku,
                                "presentation": presentation,
                                "provider_reference_price": (
                                    {"amount": amount, "currency": currency}
                                    if amount is not None
                                    else None
                                ),
                                "supplier_availability": (
                                    {"available": available, "status": status}
                                    if available is not None
                                    else None
                                ),
                            },
                            observed_at,
                        )

                    old_price = (
                        (previous["provider_price_amount"], previous["provider_price_currency"])
                        if previous
                        else (None, None)
                    )
                    new_price = (amount, currency)
                    should_update_price = "price" in scopes or is_new_variant
                    chosen_price = new_price if should_update_price and amount is not None else old_price
                    if previous and should_update_price and amount is not None and old_price != new_price:
                        self._record_change(
                            db, run_id, "variant", variant_id, "provider_reference_price",
                            {"amount": old_price[0], "currency": old_price[1]},
                            {"amount": amount, "currency": currency},
                            observed_at,
                        )
                        price_changes += 1
                        changed_product_ids.add(product_id)

                    old_availability = (
                        previous["supplier_available"] if previous else None,
                        previous["availability_status"] if previous else None,
                    )
                    new_availability = (available, status)
                    should_update_inventory = "inventory" in scopes or is_new_variant
                    chosen_availability = (
                        new_availability
                        if should_update_inventory and available is not None
                        else old_availability
                    )
                    chosen_status = (
                        status if should_update_inventory and available is not None else old_availability[1]
                    )
                    if previous and should_update_inventory and available is not None and old_availability != new_availability:
                        self._record_change(
                            db, run_id, "variant", variant_id, "supplier_availability",
                            {"available": old_availability[0], "status": old_availability[1]},
                            {"available": available, "status": status},
                            observed_at,
                        )
                        inventory_changes += 1
                        changed_product_ids.add(product_id)

                    chosen_sku = sku if ("catalog" in scopes or is_new_variant) and sku is not None else (
                        previous["sku"] if previous else None
                    )
                    chosen_presentation = (
                        presentation
                        if ("catalog" in scopes or is_new_variant) and presentation is not None
                        else (previous["presentation"] if previous else None)
                    )
                    chosen_options = (
                        json_text(options)
                        if "catalog" in scopes or is_new_variant
                        else (previous["options_json"] if previous else "[]")
                    )
                    if previous and previous["options_json"] != chosen_options:
                        self._record_change(
                            db,
                            run_id,
                            "variant",
                            variant_id,
                            "options",
                            _decode_json(previous["options_json"]),
                            _decode_json(chosen_options),
                            observed_at,
                        )
                        changed_product_ids.add(product_id)
                    for field, old_value, new_value in (
                        ("sku", previous["sku"] if previous else None, chosen_sku),
                        ("presentation", previous["presentation"] if previous else None, chosen_presentation),
                    ):
                        if previous and old_value != new_value:
                            self._record_change(
                                db, run_id, "variant", variant_id, field, old_value, new_value, observed_at
                            )
                            changed_product_ids.add(product_id)
                    db.execute(
                        """INSERT INTO supplier_variants
                           (variant_id, product_id, sku, presentation, options_json,
                            provider_price_amount, provider_price_currency, supplier_available,
                            availability_status, supplier_quantity, last_checked_at,
                            absent_from_complete_scan)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0)
                           ON CONFLICT(variant_id) DO UPDATE SET
                             product_id=excluded.product_id, sku=excluded.sku,
                             presentation=excluded.presentation, options_json=excluded.options_json,
                             provider_price_amount=excluded.provider_price_amount,
                             provider_price_currency=excluded.provider_price_currency,
                             supplier_available=excluded.supplier_available,
                             availability_status=excluded.availability_status,
                             last_checked_at=excluded.last_checked_at,
                             absent_from_complete_scan=0""",
                        (
                            variant_id,
                            product_id,
                            chosen_sku,
                            chosen_presentation,
                            chosen_options,
                            chosen_price[0],
                            chosen_price[1],
                            chosen_availability[0],
                            chosen_status,
                            observed_at,
                        ),
                    )

            if complete_scan and "catalog" in scopes and seen_product_ids:
                known = db.execute(
                    "SELECT product_id, title FROM supplier_products WHERE absent_from_complete_scan=0"
                ).fetchall()
                for row in known:
                    if row["product_id"] in seen_product_ids:
                        continue
                    db.execute(
                        "UPDATE supplier_products SET absent_from_complete_scan=1 WHERE product_id=?",
                        (row["product_id"],),
                    )
                    changed_product_ids.add(row["product_id"])
                    self._record_change(
                        db, run_id, "product", row["product_id"], "not_returned_by_complete_scan",
                        False, True, observed_at,
                    )
                known_variants = db.execute(
                    """SELECT v.variant_id, v.product_id, v.presentation
                       FROM supplier_variants v JOIN supplier_products p USING(product_id)
                       WHERE p.absent_from_complete_scan=0 AND v.absent_from_complete_scan=0"""
                ).fetchall()
                for row in known_variants:
                    if row["product_id"] not in seen_product_ids or row["variant_id"] in seen_variant_ids:
                        continue
                    db.execute(
                        "UPDATE supplier_variants SET absent_from_complete_scan=1 WHERE variant_id=?",
                        (row["variant_id"],),
                    )
                    changed_product_ids.add(row["product_id"])
                    self._record_change(
                        db, run_id, "variant", row["variant_id"], "not_returned_by_complete_scan",
                        False, True, observed_at,
                    )

            return {
                "products_consulted": len(seen_product_ids),
                "products_updated": len(changed_product_ids),
                "inventory_changes": inventory_changes,
                "price_changes": price_changes,
                "new_products": new_products,
            }

    @staticmethod
    def _record_change(
        db: sqlite3.Connection,
        run_id: str,
        entity_type: str,
        entity_id: str,
        field: str,
        old_value: object,
        new_value: object,
        observed_at: str,
    ) -> None:
        db.execute(
            """INSERT INTO change_history
               (run_id, entity_type, entity_id, field, old_value_json, new_value_json, observed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                entity_type,
                entity_id,
                field,
                json_text(old_value) if old_value is not None else None,
                json_text(new_value) if new_value is not None else None,
                observed_at,
            ),
        )

    def update_run_stats(self, run_id: str, stats: dict[str, int]) -> None:
        with self.connection() as db:
            db.execute(
                """UPDATE sync_runs SET products_consulted=?, products_updated=?,
                   inventory_changes=?, price_changes=?, new_products=? WHERE id=?""",
                (
                    stats["products_consulted"],
                    stats["products_updated"],
                    stats["inventory_changes"],
                    stats["price_changes"],
                    stats["new_products"],
                    run_id,
                ),
            )

    def due_scopes(self, now: float | None = None) -> set[str]:
        now = now or time.time()
        with self.connection() as db:
            rows = db.execute(
                "SELECT name FROM schedules WHERE next_due_at<=? AND retry_after<=?",
                (now, now),
            ).fetchall()
        return {row["name"] for row in rows}

    def schedule_success(self, scopes: set[str], now: float | None = None) -> None:
        now = now or time.time()
        stamp = utc_now()
        with self.connection() as db:
            for scope in scopes:
                interval = SCHEDULES[scope]
                db.execute(
                    """UPDATE schedules SET last_success_at=?, next_due_at=?, retry_after=0,
                       retry_count=0 WHERE name=?""",
                    (stamp, now + interval, scope),
                )

    def schedule_failure(self, scopes: set[str], now: float | None = None) -> None:
        now = now or time.time()
        with self.connection() as db:
            for scope in scopes:
                row = db.execute(
                    "SELECT interval_seconds, retry_count FROM schedules WHERE name=?", (scope,)
                ).fetchone()
                retries = row["retry_count"] + 1
                if retries >= 3:
                    retry_after = now + row["interval_seconds"]
                    retries = 0
                else:
                    retry_after = now + (60 * (2 ** (retries - 1)))
                db.execute(
                    "UPDATE schedules SET retry_count=?, retry_after=?, next_due_at=? WHERE name=?",
                    (retries, retry_after, retry_after, scope),
                )

    def dashboard(self) -> dict:
        with self.connection() as db:
            runs = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM sync_runs ORDER BY started_at DESC, rowid DESC LIMIT 20"
                ).fetchall()
            ]
            for run in runs:
                run["scopes"] = _decode_json(run.pop("scopes_json"))
            products = [
                dict(row)
                for row in db.execute(
                    """SELECT p.product_id, p.title, p.brand, p.source_url, p.primary_image,
                              p.approval_status, p.nexor_match, p.absent_from_complete_scan,
                              p.last_checked_at, v.variant_id, v.sku, v.presentation,
                              v.provider_price_amount, v.provider_price_currency,
                              v.supplier_available, v.availability_status, v.supplier_quantity,
                              v.absent_from_complete_scan AS variant_absent_from_complete_scan
                       FROM supplier_products p LEFT JOIN supplier_variants v USING(product_id)
                       ORDER BY p.title COLLATE NOCASE LIMIT 500"""
                ).fetchall()
            ]
            changes = [
                dict(row)
                for row in db.execute(
                    """SELECT c.*, p.title, v.sku FROM change_history c
                       LEFT JOIN supplier_products p ON c.entity_type='product' AND p.product_id=c.entity_id
                       LEFT JOIN supplier_variants v ON c.entity_type='variant' AND v.variant_id=c.entity_id
                       ORDER BY c.id DESC LIMIT 100"""
                ).fetchall()
            ]
            schedule = [
                dict(row)
                for row in db.execute("SELECT * FROM schedules ORDER BY interval_seconds").fetchall()
            ]
            counts = {
                "products": db.execute("SELECT COUNT(*) FROM supplier_products").fetchone()[0],
                "pending": db.execute(
                    "SELECT COUNT(*) FROM supplier_products WHERE approval_status='pending_review'"
                ).fetchone()[0],
                "missing": db.execute(
                    "SELECT COUNT(*) FROM supplier_products WHERE absent_from_complete_scan=1"
                ).fetchone()[0],
                "errors": db.execute(
                    "SELECT COUNT(*) FROM sync_runs WHERE status IN ('failed','interrupted')"
                ).fetchone()[0],
            }
            successful = db.execute(
                "SELECT MAX(finished_at) FROM sync_runs WHERE status='succeeded'"
            ).fetchone()[0]
        for change in changes:
            change["old_value"] = _decode_json(change.pop("old_value_json"))
            change["new_value"] = _decode_json(change.pop("new_value_json"))
        return {
            "latest_success": successful,
            "latest_run": runs[0] if runs else None,
            "runs": runs,
            "products": products,
            "changes": changes,
            "schedule": schedule,
            "counts": counts,
        }


def _decode_json(value: str | None) -> object:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
