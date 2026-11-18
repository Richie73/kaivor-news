"""
Kaivor Shopping Hub — PostgreSQL store (FP125).

Backed by the public.shopping_items table in the Supabase database
Reading already uses (KAIVOR_READING_DATABASE_URL). The schema comes
from the versioned migration
migrations/reading/004_shopping_items_fp125.sql — never created by
the app. Postgres-only, like tasks: without a database URL the
routes report not configured (503) instead of inventing a store.

The watchlist seeds itself: the first read of an empty table
inserts SEED_ITEMS, Richie's live watchlist as of 18 Nov 2026
(Tapo cameras, the Sofirn torch test, the Rammstein vinyl, the
Pixel deal and the Fire TV Stick). Prices in the seed are the
last verified figures; the notes say where each one came from.

checkable means "the stored price is the page's headline price,
so an automatic check may overwrite it". The Tapo triple and the
Pixel deal are NOT checkable: the Tapo page shows the single
price (£62.39) while the stored price is the triple (£165.72),
and the Pixel price is monthly plus an upfront sum. Amazon and
AliExpress block automated checks entirely, so those items are
manual too — the hub links out and Richie checks by hand.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Iterator

_COLUMNS = (
    "id, name, store, url, price, target_price, price_note, notes, "
    "checkable, bought, last_checked, created_at, updated_at"
)

SEED_ITEMS = [
    {
        "name": "Tapo TC85 x 3 (triple pack)",
        "store": "Tapo UK store",
        "url": "https://uk.store.tapo.com/products/magnetic-battery-security-camera-2k-qhd-no-subscription-fee-tapo-tc85",
        "price": "165.72",
        "target_price": "155.72",
        "price_note": "",
        "notes": "Triple with bundle discount (single £62.39). Code TAPOBF10_EG5QX5PP_1 takes it to £155.72, valid to 30 Nov 2026.",
        "checkable": False,
    },
    {
        "name": "Sofirn SC33 torch",
        "store": "AliExpress",
        "url": "https://www.aliexpress.com/wholesale?SearchText=sofirn+sc33",
        "price": "23.89",
        "target_price": "23.89",
        "price_note": "",
        "notes": "Testing one first. 5,200 lm turbo, 1,800 lm high. 11.11 sale price — sale ends 18 Nov 16:59.",
        "checkable": False,
    },
    {
        "name": "Rammstein — Zeit [VINYL]",
        "store": "Amazon",
        "url": "https://www.amazon.co.uk/s?k=rammstein+zeit+vinyl",
        "price": "27.99",
        "target_price": "35.59",
        "price_note": "",
        "notes": "Lowest yet £27.99 on 17 Nov. Amazon blocks automatic checks — tap to look.",
        "checkable": False,
    },
    {
        "name": "Pixel 11 Pro 256GB, EE 100GB",
        "store": "Mozillion",
        "url": "https://www.mozillion.com/bundle/google/pixel-11-pro",
        "price": "39.79",
        "target_price": "40.00",
        "price_note": "/mo + £149 upfront",
        "notes": "Under the £40/month cap. The daily phone watch tracks this too.",
        "checkable": False,
    },
    {
        "name": "Fire TV Stick 4K Max (2025)",
        "store": "Argos",
        "url": "https://www.argos.co.uk/product/4583420",
        "price": "46.99",
        "target_price": "99.99",
        "price_note": "",
        "notes": "Was £99.99; dropped to £46.99 on 16 Nov at Currys and Argos.",
        "checkable": True,
    },
]

# FP125.1: the Fire Stick seed first pointed at Currys, whose
# page returns 403 to an automated fetch — the check could never
# work. Argos serves the same £46.99 page to a plain fetch, so
# the seed moved there. repair_seed_urls() fixes rows seeded
# before the switch (matched on the old URL, not the name).
# Map: old URL -> (new URL, new store name).
_SEED_URL_REPAIRS = {
    "https://www.currys.co.uk/products/amazon-fire-tv-stick-4k-max-2025-with-alexa-voice-remote-10275955.html":
        ("https://www.argos.co.uk/product/4583420", "Argos"),
}


class ShoppingNotSetupError(RuntimeError):
    """The shopping_items table does not exist yet (migration 004)."""


def is_missing_table_error(exc):
    """True when a psycopg error means the table is missing."""
    if getattr(exc, "sqlstate", None) == "42P01":
        return True
    message = str(exc).lower()
    return "shopping_items" in message and "does not exist" in message


class PostgresShoppingStore:
    """PostgreSQL shopping watchlist storage."""

    def __init__(self, database_url):
        self.database_url = database_url
        if not self.database_url:
            raise ValueError("KAIVOR_READING_DATABASE_URL is required.")
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("Shopping database URL must use postgresql://.")
        # Require TLS even if a manually copied URI omitted the query option.
        if "sslmode=" not in self.database_url.lower():
            separator = "&" if "?" in self.database_url else "?"
            self.database_url += separator + "sslmode=require"

    @contextmanager
    def _connection(self) -> Iterator[object]:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL shopping storage requires psycopg. "
                "Install requirements-postgres.txt."
            ) from exc

        conn = psycopg.connect(
            self.database_url,
            connect_timeout=10,
            prepare_threshold=None,  # Required for PgBouncer transaction pooling.
        )
        try:
            with conn.transaction():
                yield conn
        finally:
            conn.close()

    @staticmethod
    @contextmanager
    def _setup_errors():
        """Turn a missing-table error into ShoppingNotSetupError."""
        try:
            yield
        except ShoppingNotSetupError:
            raise
        except Exception as exc:
            if is_missing_table_error(exc):
                raise ShoppingNotSetupError(
                    "Shopping is not set up yet — run migration 004."
                ) from exc
            raise

    @staticmethod
    def _item(row):
        # Rows come back as tuples in _COLUMNS order. Prices are
        # Decimal from Postgres; timestamps are datetimes. Turn them
        # into plain JSON-safe values.
        values = list(row)
        for index in (4, 5):
            if isinstance(values[index], Decimal):
                values[index] = float(values[index])
        for index in (10, 11, 12):
            if isinstance(values[index], datetime):
                values[index] = values[index].strftime("%Y-%m-%d %H:%M:%S")
        keys = (
            "id", "name", "store", "url", "price", "target_price",
            "price_note", "notes", "checkable", "bought",
            "last_checked", "created_at", "updated_at",
        )
        return dict(zip(keys, values))

    def list_items(self):
        with self._setup_errors():
            with self._connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT {_COLUMNS}
                    FROM public.shopping_items
                    ORDER BY bought ASC, created_at ASC, id ASC
                    """
                ).fetchall()
                return [self._item(row) for row in rows]

    def ensure_seed(self):
        """Insert the seed watchlist when the table is empty."""
        with self._setup_errors():
            with self._connection() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM public.shopping_items"
                ).fetchone()[0]
                if count:
                    return 0
                for item in SEED_ITEMS:
                    conn.execute(
                        """
                        INSERT INTO public.shopping_items
                            (name, store, url, price, target_price,
                             price_note, notes, checkable)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            item["name"], item["store"], item["url"],
                            item["price"], item["target_price"],
                            item["price_note"], item["notes"],
                            item["checkable"],
                        ),
                    )
                return len(SEED_ITEMS)

    def repair_seed_urls(self):
        """Fix seed URLs that turned out not to work (FP125.1).

        Returns the number of rows updated. Only touches rows
        whose URL exactly matches a known-bad seed URL.
        """
        repaired = 0
        with self._setup_errors():
            with self._connection() as conn:
                for old_url, (new_url, new_store) in _SEED_URL_REPAIRS.items():
                    row = conn.execute(
                        """
                        UPDATE public.shopping_items
                        SET url = %s, store = %s, updated_at = now()
                        WHERE url = %s
                        RETURNING id
                        """,
                        (new_url, new_store, old_url),
                    ).fetchone()
                    if row is not None:
                        repaired += 1
        return repaired

    def add_item(self, name, store="", url="", price=None,
                 target_price=None, price_note="", notes="",
                 checkable=True):
        if not url:
            checkable = False
        with self._setup_errors(), self._connection() as conn:
            row = conn.execute(
                """
                INSERT INTO public.shopping_items
                    (name, store, url, price, target_price,
                     price_note, notes, checkable)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name, store, url, price, target_price,
                    price_note, notes, checkable,
                ),
            ).fetchone()
            return row[0]

    def update_item(self, item_id, **fields):
        allowed = {
            "name", "store", "url", "price", "target_price",
            "price_note", "notes", "checkable", "bought",
            "last_checked",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return self.get_item(item_id)
        assignments = ", ".join(f"{key} = %s" for key in updates)
        with self._setup_errors(), self._connection() as conn:
            row = conn.execute(
                f"""
                UPDATE public.shopping_items
                SET {assignments}, updated_at = now()
                WHERE id = %s
                RETURNING {_COLUMNS}
                """,
                (*updates.values(), item_id),
            ).fetchone()
            return self._item(row) if row else None

    def get_item(self, item_id):
        with self._setup_errors(), self._connection() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM public.shopping_items WHERE id = %s",
                (item_id,),
            ).fetchone()
            return self._item(row) if row else None

    def delete_item(self, item_id):
        with self._setup_errors(), self._connection() as conn:
            row = conn.execute(
                "DELETE FROM public.shopping_items WHERE id = %s RETURNING id",
                (item_id,),
            ).fetchone()
            return row is not None


def shopping_store_or_none():
    """The shopping store, or None when no database URL is configured."""
    database_url = os.environ.get("KAIVOR_READING_DATABASE_URL")
    if not database_url:
        return None
    return PostgresShoppingStore(database_url)
