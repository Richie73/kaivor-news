"""FP125: shopping hub — a watchlist card in the Hub, backed by the
public.shopping_items table in Postgres (same database as tasks).
Current price, target price and a tap-to-buy link per item; the
first read of an empty table seeds Richie's live watchlist.
Automatic price checks only touch items flagged checkable, and a
failed check never invents a price."""

import re
import shutil
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import main
from price_check import check_price, extract_price_from_html
from shopping_store import (
    SEED_ITEMS,
    PostgresShoppingStore,
    ShoppingNotSetupError,
    is_missing_table_error,
    shopping_store_or_none,
)

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"

PIN = "test-pin-1234"
SECRET = "test-session-secret-32-chars-long!"
URL = "postgresql://user:pass@db.example.com:5432/postgres"


class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def fetchone(self):
        return self._conn.fetchone_result

    def fetchall(self):
        return self._conn.fetchall_result


class _FakeConnection:
    def __init__(self):
        self.executed = []
        self.closed = False
        self.fetchone_result = None
        self.fetchall_result = []
        self.raise_on_execute = None

    def execute(self, sql, params=()):
        if self.raise_on_execute is not None:
            raise self.raise_on_execute
        self.executed.append((sql, params))
        return _FakeCursor(self)

    @contextmanager
    def transaction(self):
        yield self

    def close(self):
        self.closed = True


class _FakeStore:
    """In-memory stand-in for the Postgres shopping store."""

    def __init__(self, items=None):
        self.items = {item["id"]: dict(item) for item in (items or [])}
        self.next_id = (max(self.items) + 1) if self.items else 1
        self.seeded = False

    def list_items(self):
        return sorted(self.items.values(), key=lambda i: (i["bought"], i["id"]))

    def ensure_seed(self):
        if self.items:
            return 0
        for item in SEED_ITEMS:
            self.add_item(**item)
        self.seeded = True
        return len(SEED_ITEMS)

    def repair_seed_urls(self):
        return 0

    def add_item(self, name, store="", url="", price=None,
                 target_price=None, price_note="", notes="",
                 checkable=True):
        item_id = self.next_id
        self.next_id += 1
        if not url:
            checkable = False
        self.items[item_id] = {
            "id": item_id, "name": name, "store": store, "url": url,
            "price": price, "target_price": target_price,
            "price_note": price_note, "notes": notes,
            "checkable": checkable, "bought": False,
            "last_checked": None,
            "created_at": "2026-11-18 07:45:00",
            "updated_at": "2026-11-18 07:45:00",
        }
        return item_id

    def update_item(self, item_id, **fields):
        item = self.items.get(item_id)
        if item is None:
            return None
        item.update(fields)
        return item

    def delete_item(self, item_id):
        return self.items.pop(item_id, None) is not None


@pytest.fixture
def fake_psycopg(monkeypatch):
    module = types.ModuleType("psycopg")
    connections = []

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        connections.append(conn)
        return conn

    module.connect = connect
    module.connections = connections
    monkeypatch.setitem(sys.modules, "psycopg", module)
    return module


def _authed_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    client = main.app.test_client()
    with client.session_transaction() as sess:
        sess["reading_authenticated"] = True
    return client


def _locked_client(monkeypatch):
    monkeypatch.setenv("KAIVOR_READING_PIN", PIN)
    monkeypatch.setenv("KAIVOR_SESSION_SECRET", SECRET)
    return main.app.test_client()


def _template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def _row(item_id=1, price=Decimal("46.99"), target=Decimal("99.99"),
         bought=False, checkable=True):
    return (
        item_id, "Fire TV Stick 4K Max (2025)", "Currys",
        "https://www.currys.co.uk/products/fire-tv-stick",
        price, target, "", "Was £99.99.", checkable, bought,
        None, datetime(2026, 11, 18, 7, 45, 0),
        datetime(2026, 11, 18, 7, 45, 0),
    )


def _item(item_id=1, price=46.99, target=99.99, bought=False,
          checkable=True, url="https://example.com/fire-stick"):
    return {
        "id": item_id, "name": "Fire TV Stick 4K Max (2025)",
        "store": "Currys", "url": url, "price": price,
        "target_price": target, "price_note": "", "notes": "",
        "checkable": checkable, "bought": bought,
        "last_checked": None,
        "created_at": "2026-11-18 07:45:00",
        "updated_at": "2026-11-18 07:45:00",
    }


# --- store ---


def test_store_requires_a_url():
    with pytest.raises(ValueError, match="KAIVOR_READING_DATABASE_URL"):
        PostgresShoppingStore("")


def test_store_requires_postgresql_scheme():
    with pytest.raises(ValueError, match="postgresql://"):
        PostgresShoppingStore("sqlite:///shopping.db")


def test_store_or_none_without_url(monkeypatch):
    monkeypatch.delenv("KAIVOR_READING_DATABASE_URL", raising=False)
    assert shopping_store_or_none() is None


def test_seed_items_cover_the_watchlist():
    assert len(SEED_ITEMS) == 5
    names = [item["name"] for item in SEED_ITEMS]
    assert any("TC85" in name for name in names)
    assert any("SC33" in name for name in names)
    assert any("Zeit" in name for name in names)
    assert any("Pixel 11 Pro" in name for name in names)
    assert any("Fire TV Stick" in name for name in names)
    for item in SEED_ITEMS:
        assert item["url"].startswith("https://")
        assert item["price"] is not None
        assert item["target_price"] is not None
    by_name = {item["name"]: item for item in SEED_ITEMS}
    # The Tapo triple and the Pixel deal are manual: their stored
    # prices are not the page's headline price.
    assert by_name["Tapo TC85 x 3 (triple pack)"]["checkable"] is False
    assert by_name["Pixel 11 Pro 256GB, EE 100GB"]["checkable"] is False
    assert by_name["Fire TV Stick 4K Max (2025)"]["checkable"] is True
    # FP125.1: the Fire Stick seed points at Argos, not Currys —
    # Currys returns 403 to an automated fetch, Argos serves the
    # same £46.99 page.
    assert by_name["Fire TV Stick 4K Max (2025)"]["store"] == "Argos"
    assert by_name["Fire TV Stick 4K Max (2025)"]["url"] == "https://www.argos.co.uk/product/4583420"


def test_list_items_normalises_decimals_and_dates(fake_psycopg):
    store = PostgresShoppingStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = [_row(1), _row(2, bought=True)]
        return conn

    fake_psycopg.connect = connect
    items = store.list_items()
    assert [i["id"] for i in items] == [1, 2]
    assert items[0]["price"] == 46.99
    assert items[0]["target_price"] == 99.99
    assert items[0]["created_at"] == "2026-11-18 07:45:00"
    assert items[0]["bought"] is False


def test_list_items_sql_orders_open_first(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchall_result = []
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.list_items()
    sql, _params = conn_holder["conn"].executed[0]
    assert "FROM public.shopping_items" in sql
    assert "ORDER BY bought ASC" in sql


def test_ensure_seed_inserts_when_empty(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (0,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    assert store.ensure_seed() == 5
    inserts = [s for s, _p in conn_holder["conn"].executed if "INSERT INTO" in s]
    assert len(inserts) == 5
    assert "Fire TV Stick 4K Max (2025)" in str(conn_holder["conn"].executed)


def test_ensure_seed_skips_when_items_exist(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (3,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    assert store.ensure_seed() == 0
    assert not [s for s, _p in conn_holder["conn"].executed if "INSERT INTO" in s]


def test_add_item_inserts_and_returns_id(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (7,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    assert store.add_item("Test item", "Shop", "https://example.com", 10.0, 8.0) == 7
    sql, params = conn_holder["conn"].executed[0]
    assert "INSERT INTO public.shopping_items" in sql
    assert params[0] == "Test item"
    assert params[7] is True


def test_add_item_forces_manual_without_url(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (7,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    store.add_item("In-store only", checkable=True)
    _sql, params = conn_holder["conn"].executed[0]
    assert params[7] is False


def test_update_item_bought(fake_psycopg):
    store = PostgresShoppingStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = _row(1, bought=True)
        return conn

    fake_psycopg.connect = connect
    updated = store.update_item(1, bought=True)
    assert updated["bought"] is True


def test_delete_item(fake_psycopg):
    store = PostgresShoppingStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (1,)
        return conn

    fake_psycopg.connect = connect
    assert store.delete_item(1) is True


def test_repair_seed_urls_updates_currys_row(fake_psycopg):
    store = PostgresShoppingStore(URL)
    conn_holder = {}

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = (5,)
        conn_holder["conn"] = conn
        return conn

    fake_psycopg.connect = connect
    assert store.repair_seed_urls() == 1
    sql, params = conn_holder["conn"].executed[0]
    assert "UPDATE public.shopping_items" in sql
    assert params[0] == "https://www.argos.co.uk/product/4583420"
    assert params[1] == "Argos"
    assert "currys.co.uk" in params[2]


def test_repair_seed_urls_noop_when_nothing_to_fix(fake_psycopg):
    store = PostgresShoppingStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.fetchone_result = None
        return conn

    fake_psycopg.connect = connect
    assert store.repair_seed_urls() == 0


def test_missing_table_raises_setup_error(fake_psycopg):
    store = PostgresShoppingStore(URL)

    class _MissingTable(Exception):
        sqlstate = "42P01"

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.raise_on_execute = _MissingTable('relation "public.shopping_items" does not exist')
        return conn

    fake_psycopg.connect = connect
    with pytest.raises(ShoppingNotSetupError, match="migration 004"):
        store.list_items()
    assert is_missing_table_error(_MissingTable("x")) is True
    assert is_missing_table_error(ValueError("boom")) is False


def test_other_db_errors_pass_through(fake_psycopg):
    store = PostgresShoppingStore(URL)

    def connect(database_url, **kwargs):
        conn = _FakeConnection()
        conn.raise_on_execute = RuntimeError("connection refused")
        return conn

    fake_psycopg.connect = connect
    with pytest.raises(RuntimeError, match="connection refused"):
        store.list_items()


# --- price extraction ---


def test_extract_price_from_json_ld():
    html = """<html><head><script type="application/ld+json">
    {"@type": "Product", "name": "Stick",
     "offers": {"price": "46.99", "priceCurrency": "GBP"}}
    </script></head></html>"""
    assert extract_price_from_html(html) == 46.99


def test_extract_price_from_json_ld_graph_and_list_offers():
    html = """<script type="application/ld+json">
    {"@graph": [{"@type": "WebPage"}, {"@type": "Product",
     "offers": [{"price": "99.99", "priceCurrency": "USD"},
                {"lowPrice": "46.99", "priceCurrency": "GBP"}]}]}
    </script>"""
    assert extract_price_from_html(html) == 46.99


def test_extract_price_ignores_non_gbp():
    html = """<script type="application/ld+json">
    {"@type": "Product", "offers": {"price": "55.00", "priceCurrency": "USD"}}
    </script>"""
    assert extract_price_from_html(html) is None


def test_extract_price_from_meta_tag():
    html = """<meta property="og:price:amount" content="46.99">"""
    assert extract_price_from_html(html) == 46.99
    html2 = """<meta content="32.50" property="product:price:amount">"""
    assert extract_price_from_html(html2) == 32.50


def test_extract_price_returns_none_without_price():
    assert extract_price_from_html("<html><body>No offers here</body></html>") is None
    assert extract_price_from_html("") is None


class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


def test_check_price_ok():
    html = """<script type="application/ld+json">
    {"@type": "Product", "offers": {"price": "46.99", "priceCurrency": "GBP"}}
    </script>"""
    with patch("price_check.requests.get", return_value=_FakeResponse(200, html)):
        assert check_price("https://example.com/item") == {"status": "ok", "price": 46.99}


def test_check_price_unavailable_on_404():
    with patch("price_check.requests.get", return_value=_FakeResponse(404, "")):
        result = check_price("https://example.com/item")
        assert result["status"] == "unavailable"


def test_check_price_unavailable_without_price_on_page():
    with patch("price_check.requests.get", return_value=_FakeResponse(200, "<html></html>")):
        result = check_price("https://example.com/item")
        assert result["status"] == "unavailable"


def test_check_price_error_on_timeout():
    with patch("price_check.requests.get", side_effect=requests.Timeout("slow")):
        result = check_price("https://example.com/item")
        assert result["status"] == "error"


def test_check_price_rejects_non_http_url():
    assert check_price("ftp://example.com/item")["status"] == "error"
    assert check_price("")["status"] == "error"


# --- routes ---


def test_get_shopping_seeds_and_lists(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore()
    with patch("main.shopping_store_or_none", return_value=fake):
        response = client.get("/api/shopping")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["items"]) == 5
    assert fake.seeded is True


def test_get_shopping_setup_needed(monkeypatch):
    client = _authed_client(monkeypatch)

    class _UnsetStore(_FakeStore):
        def ensure_seed(self):
            raise ShoppingNotSetupError("run migration 004")

    with patch("main.shopping_store_or_none", return_value=_UnsetStore()):
        response = client.get("/api/shopping")
    assert response.status_code == 503
    assert response.get_json()["setup_needed"] is True


def test_get_shopping_not_configured(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=None):
        response = client.get("/api/shopping")
    assert response.status_code == 503
    assert response.get_json()["success"] is False


def test_add_shopping_item_requires_name(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=_FakeStore()):
        response = client.post("/api/shopping", json={"store": "Shop"})
    assert response.status_code == 400


def test_add_shopping_item_rejects_bad_url(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=_FakeStore()):
        response = client.post(
            "/api/shopping",
            json={"name": "Item", "url": "example.com/no-scheme"},
        )
    assert response.status_code == 400


def test_add_shopping_item_ok(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore()
    with patch("main.shopping_store_or_none", return_value=fake):
        response = client.post(
            "/api/shopping",
            json={"name": "New torch", "store": "Shop",
                  "url": "https://example.com/torch",
                  "price": 19.99, "target_price": 15.0},
        )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert fake.items[1]["name"] == "New torch"
    assert fake.items[1]["price"] == 19.99


def test_update_shopping_item_bought(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore([_item(1)])
    with patch("main.shopping_store_or_none", return_value=fake):
        response = client.put("/api/shopping/1", json={"bought": True})
    assert response.status_code == 200
    assert response.get_json()["item"]["bought"] is True


def test_update_shopping_item_404(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=_FakeStore()):
        response = client.put("/api/shopping/99", json={"bought": True})
    assert response.status_code == 404


def test_delete_shopping_item_ok(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore([_item(1)])
    with patch("main.shopping_store_or_none", return_value=fake):
        response = client.delete("/api/shopping/1")
    assert response.status_code == 200
    assert 1 not in fake.items


def test_delete_shopping_item_404(monkeypatch):
    client = _authed_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=_FakeStore()):
        response = client.delete("/api/shopping/99")
    assert response.status_code == 404


def test_check_prices_updates_checkable_only(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore([
        _item(1, price=46.99, checkable=True),
        _item(2, price=165.72, checkable=False),
        _item(3, price=27.99, bought=True, checkable=True),
    ])
    with (
        patch("main.shopping_store_or_none", return_value=fake),
        patch("main.check_price", return_value={"status": "ok", "price": 39.99}),
    ):
        response = client.post("/api/shopping/check")
    assert response.status_code == 200
    data = response.get_json()
    assert data["checked"] == 1
    assert data["updated"] == 1
    assert fake.items[1]["price"] == 39.99
    assert fake.items[1]["last_checked"] is not None
    assert fake.items[2]["price"] == 165.72
    assert fake.items[3]["price"] == 27.99
    statuses = {r["id"]: r["status"] for r in data["results"]}
    assert statuses == {1: "ok", 2: "manual", 3: "manual"}


def test_check_prices_leaves_price_on_failed_check(monkeypatch):
    client = _authed_client(monkeypatch)
    fake = _FakeStore([_item(1, price=46.99, checkable=True)])
    with (
        patch("main.shopping_store_or_none", return_value=fake),
        patch("main.check_price",
              return_value={"status": "unavailable", "reason": "no price found"}),
    ):
        response = client.post("/api/shopping/check")
    assert response.status_code == 200
    data = response.get_json()
    assert data["checked"] == 1
    assert data["updated"] == 0
    assert fake.items[1]["price"] == 46.99
    assert fake.items[1]["last_checked"] is None


def test_mutation_routes_locked_without_pin(monkeypatch):
    client = _locked_client(monkeypatch)
    with patch("main.shopping_store_or_none", return_value=_FakeStore()):
        add = client.post("/api/shopping", json={"name": "Item"})
        check = client.post("/api/shopping/check")
        update = client.put("/api/shopping/1", json={"bought": True})
        remove = client.delete("/api/shopping/1")
    assert add.status_code == 401
    assert check.status_code == 401
    assert update.status_code == 401
    assert remove.status_code == 401


# --- template ---


def test_shopping_hub_card_markup():
    html = _template_text()
    assert 'id="hub-shopping"' in html
    assert "🛒 Shopping" in html
    assert 'id="shopping-add"' in html
    assert 'id="shopping-add-name"' in html
    assert 'id="shopping-add-url"' in html
    assert 'id="shopping-add-price"' in html
    assert 'id="shopping-add-target"' in html
    assert 'id="shopping-status"' in html
    assert "async function loadMorningHubShopping()" in html
    assert "function shoppingRowHtml(item) {" in html
    assert "function formatShoppingPrice(item) {" in html
    assert "async function checkShoppingPrices(button)" in html
    assert "async function saveShoppingItem(button)" in html
    assert "async function toggleShoppingBought(id, bought, checkbox)" in html
    assert "async function deleteShoppingItem(id, button)" in html
    assert ".shopping-at-target" in html
    assert ".shopping-link, .shopping-link:visited { color:var(--blue); }" in html


def test_shopping_loader_wired():
    html = _template_text()
    start = html.index("function renderMorningHub() {")
    window = html[start:start + 2000]
    assert "loadMorningHubShopping();" in window


def test_shopping_row_html_node():
    if shutil.which("node") is None:
        pytest.skip("node is not available")
    html = _template_text()
    price_match = re.search(r"function formatShoppingPrice\(item\) \{(.*?)\n\}", html, re.S)
    row_match = re.search(r"function shoppingRowHtml\(item\) \{(.*?)\n\}", html, re.S)
    escape_match = re.search(r"function escapeHtml\(value\) \{(.*?)\n\}", html, re.S)
    assert price_match is not None
    assert row_match is not None
    assert escape_match is not None
    script = (
        "import assert from 'node:assert/strict';\n"
        "const document = {createElement: () => ({textContent: '', get innerHTML() { return this.textContent; }})};\n"
        + escape_match.group(0)
        + "\n"
        + price_match.group(0)
        + "\n"
        + row_match.group(0)
        + "\nassert.strictEqual(formatShoppingPrice({price: 46.99, price_note: ''}), '£46.99');\n"
        + "assert.strictEqual(formatShoppingPrice({price: 39.79, price_note: '/mo + £149 upfront'}), '£39.79 /mo + £149 upfront');\n"
        + "assert.strictEqual(formatShoppingPrice({price: null}), '—');\n"
        + "const atTarget = shoppingRowHtml({id: 1, name: 'Stick', store: 'Currys', url: 'https://example.com/s', price: 46.99, target_price: 99.99, price_note: '', notes: '', checkable: true, bought: false});\n"
        + "assert.ok(atTarget.includes('shopping-at-target'));\n"
        + "assert.ok(atTarget.includes('✓ At target'));\n"
        + "assert.ok(atTarget.includes('£46.99'));\n"
        + "assert.ok(atTarget.includes('href=\"https://example.com/s\"'));\n"
        + "assert.ok(atTarget.includes('class=\"shopping-link\"'));\n"
        + "assert.ok(!atTarget.includes(' checked '));\n"
        + "const above = shoppingRowHtml({id: 2, name: 'Cameras', store: 'Tapo', url: 'https://example.com/t', price: 165.72, target_price: 155.72, price_note: '', notes: 'Code ends 30 Nov', checkable: false, bought: false});\n"
        + "assert.ok(above.includes('Target £155.72'));\n"
        + "assert.ok(!above.includes('shopping-at-target'));\n"
        + "assert.ok(above.includes('Tap the link to check'));\n"
        + "assert.ok(above.includes('Code ends 30 Nov'));\n"
        + "const bought = shoppingRowHtml({id: 3, name: 'Torch', store: '', url: '', price: 23.89, target_price: 23.89, price_note: '', notes: '', checkable: false, bought: true});\n"
        + "assert.ok(bought.includes(' checked '));\n"
        + "assert.ok(bought.includes('✓ Bought'));\n"
        + "assert.ok(bought.includes('toggleShoppingBought(3, this.checked, this)'));\n"
        + "assert.ok(bought.includes('deleteShoppingItem(3, this)'));\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        result = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        Path(path).unlink(missing_ok=True)
    assert result.returncode == 0, result.stderr
