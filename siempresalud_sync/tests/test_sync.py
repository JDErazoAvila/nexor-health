from __future__ import annotations

from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from siempresalud_sync.store import SyncStore


def product(price: int = 109900, available: bool = True) -> dict:
    return {
        "id": "gid://shopify/Product/40017",
        "handle": "kit-repuesto-gris",
        "title": "Kit de repuesto Gris para fonendoscopio Littmann",
        "description": {"plain": "Descripción pública del producto."},
        "url": "https://siempresalud.co/products/kit-repuesto-gris",
        "categories": [{"value": "Littmann", "taxonomy": "merchant"}],
        "media": [{"type": "image", "url": "https://cdn.shopify.com/40017.jpg"}],
        "variants": [
            {
                "id": "gid://shopify/ProductVariant/40017",
                "sku": "40017",
                "title": "Gris",
                "price": {"amount": price, "currency": "COP"},
                "availability": {"available": available, "status": "in_stock" if available else "out_of_stock"},
                "options": [{"name": "Color", "label": "Gris"}],
            }
        ],
    }


class SyncStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = SyncStore(Path(self.temp.name) / "sync.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(
        self, payload: dict, scopes: set[str], references: set[str] | None = None
    ) -> tuple[str, dict]:
        run_id = self.store.start_run(scopes)
        stats = self.store.apply_catalog(
            run_id, [payload], scopes, True, {"40017"} if references is None else references
        )
        self.store.update_run_stats(run_id, stats)
        self.store.finish_run(run_id, "succeeded")
        return run_id, stats

    def test_detects_provider_changes_without_touching_retail_price(self) -> None:
        _, initial = self._run(product(), {"inventory", "price", "catalog"})
        self.assertEqual(initial["new_products"], 1)

        _, changed = self._run(product(price=119900, available=False), {"inventory", "price"})
        self.assertEqual(changed["price_changes"], 1)
        self.assertEqual(changed["inventory_changes"], 1)

        dashboard = self.store.dashboard()
        variant = dashboard["products"][0]
        self.assertEqual(variant["provider_price_amount"], 119900)
        self.assertEqual(variant["supplier_available"], 0)
        self.assertIsNone(variant["supplier_quantity"])
        self.assertEqual(
            {change["field"] for change in dashboard["changes"]},
            {"product_added", "variant_added", "provider_reference_price", "supplier_availability"},
        )

    def test_new_products_remain_pending_and_absence_is_not_deletion(self) -> None:
        first = product()
        second = product()
        second["id"] = "gid://shopify/Product/40018"
        second["variants"][0]["id"] = "gid://shopify/ProductVariant/40018"
        second["variants"][0]["sku"] = "40018"
        run_id = self.store.start_run({"inventory", "price", "catalog"})
        self.store.apply_catalog(run_id, [first, second], {"inventory", "price", "catalog"}, True, set())
        self.store.finish_run(run_id, "succeeded")
        run_id = self.store.start_run({"catalog"})
        self.store.apply_catalog(run_id, [second], {"catalog"}, True, set())
        self.store.finish_run(run_id, "succeeded")

        dashboard = self.store.dashboard()
        self.assertEqual(dashboard["counts"]["products"], 2)
        self.assertEqual(dashboard["counts"]["pending"], 2)
        self.assertEqual(dashboard["counts"]["missing"], 1)

    def test_scheduler_intervals_are_persisted(self) -> None:
        schedule = {item["name"]: item["interval_seconds"] for item in self.store.dashboard()["schedule"]}
        self.assertEqual(schedule, {"inventory": 21600, "price": 43200, "catalog": 86400})
        self.store.schedule_success({"inventory", "price", "catalog"}, now=1000)
        restarted_store = SyncStore(self.store.path)
        self.assertEqual(restarted_store.due_scopes(now=1001), set())

    def test_inventory_runs_do_not_discover_new_products_before_catalog_schedule(self) -> None:
        run_id = self.store.start_run({"inventory"})
        stats = self.store.apply_catalog(run_id, [product()], {"inventory"}, True, set())
        self.store.finish_run(run_id, "succeeded")

        self.assertEqual(stats["products_consulted"], 1)
        self.assertEqual(self.store.dashboard()["counts"]["products"], 0)

    def test_scoped_updates_do_not_overwrite_other_supplier_fields(self) -> None:
        self._run(product(), {"inventory", "price", "catalog"})
        price_only = product(price=120000, available=False)
        self._run(price_only, {"price"})
        dashboard = self.store.dashboard()
        variant = dashboard["products"][0]
        self.assertEqual(variant["provider_price_amount"], 120000)
        self.assertEqual(variant["supplier_available"], 1)

    def test_catalog_run_tracks_reference_presentation_description_and_image_changes(self) -> None:
        self._run(product(), {"inventory", "price", "catalog"})
        changed = product()
        changed["description"] = {"plain": "Descripción actualizada."}
        changed["categories"] = [{"value": "Repuestos", "taxonomy": "merchant"}]
        changed["media"] = [{"type": "image", "url": "https://cdn.shopify.com/40017-new.jpg"}]
        changed["variants"][0]["sku"] = "40017-B"
        changed["variants"][0]["title"] = "Gris nuevo"
        changed["variants"][0]["options"] = [{"name": "Color", "label": "Gris nuevo"}]
        _, stats = self._run(changed, {"catalog"})

        self.assertEqual(stats["products_updated"], 1)
        fields = {change["field"] for change in self.store.dashboard()["changes"]}
        self.assertTrue({"categories", "description", "images", "sku", "presentation", "options"} <= fields)

    def test_interrupted_run_is_recovered_after_restart(self) -> None:
        run_id = self.store.start_run({"inventory"})
        stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        with self.store.connection() as db:
            db.execute(
                "UPDATE sync_runs SET owner_host='previous-host', heartbeat_at=? WHERE id=?",
                (stale, run_id),
            )

        self.store.reconcile_interrupted_runs()
        dashboard = self.store.dashboard()
        self.assertEqual(dashboard["runs"][0]["status"], "interrupted")
        self.assertIn("inventory", self.store.due_scopes())

    def test_only_one_run_can_hold_the_database_lock(self) -> None:
        run_id = self.store.start_run({"inventory"})
        with self.assertRaises(RuntimeError):
            self.store.start_run({"price"})
        self.store.finish_run(run_id, "succeeded")

    def test_scheduler_uses_three_retries_then_waits_for_next_interval(self) -> None:
        self.store.schedule_failure({"inventory"}, now=100)
        self.assertNotIn("inventory", self.store.due_scopes(now=159))
        self.assertIn("inventory", self.store.due_scopes(now=160))
        self.store.schedule_failure({"inventory"}, now=160)
        self.store.schedule_failure({"inventory"}, now=280)
        self.assertNotIn("inventory", self.store.due_scopes(now=280 + 21600 - 1))
        self.assertIn("inventory", self.store.due_scopes(now=280 + 21600))

    def test_price_run_preserves_product_details_when_source_omits_them(self) -> None:
        self._run(product(), {"inventory", "price", "catalog"})
        changed = product(price=120000)
        changed.pop("description")
        changed.pop("media")
        changed.pop("categories")
        changed["title"] = "Temporary result title"
        self._run(changed, {"price"})

        with self.store.connection() as db:
            row = db.execute(
                "SELECT title, description_json, images_json FROM supplier_products"
            ).fetchone()
        self.assertEqual(row["title"], product()["title"])
        self.assertIn("Descripción pública", row["description_json"])
        self.assertIn("40017.jpg", row["images_json"])


if __name__ == "__main__":
    unittest.main()
