"""FP086: full Markets view + price history (template side).

Tapping the Market Watch strip opens a full Markets view — one row
per asset with the current price, today's change, a five-trading-day
sparkline and today's range (Yahoo assets) or the five-day range (FX
pairs). Like the weather view it hides the news cards without
destroying them, so tapping a news category brings the stories
straight back.
"""
import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "index.html"


def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def function_body(html, opener, next_opener):
    start = html.index(opener)
    end = html.index(next_opener, start)
    return html[start:end]


def markets_js_block():
    html = template_text()
    start = html.index("// FP086 MARKETS VIEW: BEGIN")
    end = html.index("// FP086 MARKETS VIEW: END", start)
    return html[start:end]


def test_market_bar_opens_the_markets_view():
    html = template_text()
    assert 'onclick="showMarkets()"' in html
    assert 'aria-label="Live market prices — tap to open the full markets view"' in html
    assert ".market-bar { display:block; overflow:hidden; padding:12px 0; margin-bottom:16px; font-size:13px; background:#161618; border-radius:12px; border:1px solid #26262a; white-space:nowrap; cursor:pointer; }" in html


def test_markets_section_hidden_by_default():
    html = template_text()
    assert '<section id="markets-section" class="weather-card" aria-label="Markets" style="display:none">' in html
    assert 'id="markets-list"' in html
    assert 'id="markets-updated"' in html
    assert 'onclick="refreshMarketsFromView()"' in html


def test_show_markets_hides_without_destroying():
    html = template_text()
    body = function_body(html, "function showMarkets() {", "function hideMarketsView() {")
    assert "hideWeatherView();" in body
    assert "querySelectorAll('.card').forEach(card => { card.style.display = 'none'; });" in body
    assert "container.innerHTML" not in body
    assert "getElementById('markets-section')" in body
    assert "section.style.display = 'block';" in body
    assert "loadMarketsHistory();" in body
    assert "fetch('/api/finance/history'" in html


def test_other_views_hide_the_markets_view():
    html = template_text()
    for opener in [
        "function filterCategory(category, element) {",
        "async function showSaved(element) {",
        "function showChat(element) {",
        "function showSettings(element){",
        "function showWeather(element) {",
    ]:
        start = html.index(opener)
        window = html[start:start + len(opener) + 60]
        assert "hideMarketsView();" in window, opener
    assert html.count("hideMarketsView();") == 5  # one call site per other view


def test_markets_rows_show_price_change_range_and_sparkline():
    html = template_text()
    body = function_body(html, "function marketsRowHtml(key, entry) {",
                         "async function loadMarketsHistory() {")
    assert "formatMarketPrice(key, entry.current)" in body
    assert "formatMarketChange(key, entry.change, entry.change_pct)" in body
    assert "sparklineSvg(entry.series)" in body
    assert "'Today '" in body
    assert "'5-day '" in body
    assert "entry.day_high" in body
    assert "entry.day_low" in body


def test_markets_view_orders_eleven_rows():
    html = template_text()
    assert "const order = ['Gold', 'Silver', 'Bitcoin', 'Ethereum', 'SP500', 'FTSE100', 'Brent_Oil', 'GBP_USD', 'GBP_EUR', 'GBP_JPY', 'EUR_USD'];" in html


def test_history_fill_updates_the_ticker():
    html = template_text()
    body = function_body(html, "async function loadMarketsHistory() {",
                         "async function refreshMarketsFromView() {")
    assert "fillTickerFromHistory(history);" in body
    fill = function_body(html, "function fillTickerFromHistory(history) {",
                         "// FP086 MARKETS VIEW: END")
    assert "updateMarketValue(key, entry.current);" in fill
    assert "marketHistoryFill = Date.now() / 1000;" in fill
    assert "setMarketStatus('Prices from the Markets view · ' + formatMarketAge(0), 'stale');" in fill
    ticker = function_body(html, "async function updateFinanceTicker() {",
                           "async function refreshMarkets() {")
    assert "if (result.age_seconds !== null) marketHistoryFill = null;" in ticker
    assert "if (marketHistoryFill) {" in ticker
    assert "Prices from the Markets view" in ticker


def test_markets_deep_link():
    html = template_text()
    assert "else if (initialHash === '#markets') { showMarkets(); }" in html


def test_markets_history_helpers_node():
    script = markets_js_block() + """
const out = {
    fx: formatMarketPrice('GBP_USD', 1.3227),
    fxJpy: formatMarketPrice('GBP_JPY', 211.62),
    usd: formatMarketPrice('Gold', 3886.3),
    missing: formatMarketPrice('Gold', null),
    up: formatMarketChange('Gold', 10, 0.38),
    down: formatMarketChange('GBP_USD', -0.0029, -0.22),
    none: formatMarketChange('Gold', null, null),
    sparkUp: sparklineSvg([{close: 1}, {close: 2}, {close: 3}]),
    sparkDown: sparklineSvg([{close: 3}, {close: 2}, {close: 1}]),
    sparkShort: sparklineSvg([{close: 1}]),
};
console.log(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["fx"] == "1.3227"
    assert out["fxJpy"] == "211.6200"
    assert out["usd"] == "$3,886.30"
    assert out["missing"] == "—"
    assert out["up"] == {"text": "▲ +$10.00 (+0.38%)", "cls": "markets-up"}
    assert out["down"] == {"text": "▼ 0.0029 (-0.22%)", "cls": "markets-down"}
    assert out["none"] == {"text": "—", "cls": ""}
    assert 'stroke="#35FA33"' in out["sparkUp"]
    assert 'stroke="#f87171"' in out["sparkDown"]
    assert "<polyline" in out["sparkUp"]
    assert out["sparkShort"] == ""


def test_ticker_fill_from_history_node():
    script = """
const filled = {};
let statusText = '';
function updateMarketValue(k, v) { filled[k] = v; }
function setMarketStatus(text) { statusText = text; }
function formatMarketAge(s) { return 'Updated ' + s + 's ago'; }
""" + markets_js_block() + """
fillTickerFromHistory({
    Gold: {current: 3886.3},
    Silver: {current: 49.12},
    GBP_USD: {current: null},
    GBP_JPY: {current: 211.62},
});
console.log(JSON.stringify({filled, hasFill: typeof marketHistoryFill === 'number', statusText}));
"""
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["filled"] == {"Gold": 3886.3, "Silver": 49.12, "GBP_JPY": 211.62}
    assert out["hasFill"] is True
    assert out["statusText"] == "Prices from the Markets view · Updated 0s ago"
