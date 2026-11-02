"""FP048 regressions: local UI updates and duplicate-submit protection."""
from pathlib import Path


def template():
    return (Path(__file__).resolve().parents[1] / "templates" / "reading.html").read_text()

def test_book_mutations_do_not_reload_entire_dashboard():
    source = template()
    assert "allBooksCache.unshift({...result.book,latest_progress:null,notes_count:0})" in source
    assert "removeCachedBook(id)" in source
    assert "updateCachedBook(id, result.book)" in source
    assert "await loadDashboard()" not in source[source.index("$('add-book-form')"):source.index("$('search-books')")]

def test_progress_uses_optimistic_update_and_rolls_back_on_failure():
    source = template()
    assert "updateCachedBook(id, {latest_progress:optimisticProgress, status:optimisticStatus})" in source
    assert "updateCachedBook(id, {latest_progress:previousProgress, status:previousStatus})" in source

def test_mutating_controls_have_busy_state():
    source = template()
    assert "function setBusy(button, busy" in source
    assert "setBusy(submitButton, true, 'Adding…')" in source
    assert "setBusy(document.querySelector(`.book-card[data-id=\"${id}\"] .save-status`), true, 'Saving…')" in source
    assert "setBusy(document.querySelector(`.book-card[data-id=\"${id}\"] .record-progress`), true, 'Saving…')" in source

def test_dashboard_reload_is_initial_load_only():
    source = template()
    assert "loadDashboard().catch(error=>showMessage(error.message,true))" in source
    assert "await loadDashboard()" not in source
