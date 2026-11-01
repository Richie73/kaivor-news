# Kaivor Reading Foundation (FP041)

Provider-independent reading domain for the Kaivor engine. This milestone provides a local SQLite library, progress tracking, personal notes, reading lists, and a service layer suitable for future CLI/API/Android interfaces.

BorrowBox is represented only by a safe official-site launcher and a provider boundary. There is **no login automation, scraping, undocumented endpoint use, credential capture, or synchronization**. Add synchronization only after Bolinda confirms an authorized integration method.

## Quick start

From the Kaivor project root:

```bash
python - <<'PY'
from reading import ReadingRepository, ReadingService
repo = ReadingRepository("data/reading.db")
reading = ReadingService(repo)
book = reading.add_book("Example title", "Example author", format="ebook")
reading.start_reading(book.id)
reading.record_progress(book.id, 25, 300)
reading.add_note(book.id, "An important idea", page_or_position="25")
print(reading.dashboard()["library"])
PY
```

The database is created on first use at `data/reading.db` by default. Pass another path to `ReadingRepository` for tests or alternate storage.

## Test

```bash
python -m unittest discover -s tests -p 'test_reading_fp041.py' -v
```

## Public API

- `ReadingRepository`: persistence and query operations.
- `ReadingService`: application use cases.
- `Book`, `ReadingNote`, `ReadingList`, `ReadingStatus`: domain models.
- `BorrowBoxProvider`: official-site launcher and explicit disabled-sync boundary.

## Design constraints

- Reading data is stored separately from conversation memory and news data.
- SQLite foreign keys enforce note/list relationships.
- User text is stored as text; no copyrighted book content is fetched or copied.
- Provider identity is explicit so other library providers can be added later.
- Database files are runtime data and should not be committed to source control.
