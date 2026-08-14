import sqlite3, os
from sqlalchemy import create_engine, text

def run_migration():
    # Detect old DB path
    old_db = 'kaivor_permanent.db' if os.path.exists('kaivor_permanent.db') else 'kaivor_vault.db'
    pg_url = os.environ.get('DATABASE_URL')

    if not pg_url or not os.path.exists(old_db):
        print(f"Error: Missing requirements. DB: {old_db}, PG_ENV: {'Set' if pg_url else 'None'}")
        return

    print(f"Inspecting {old_db}...")
    sl_conn = sqlite3.connect(old_db)
    sl_cur = sl_conn.cursor()
    pg_engine = create_engine(pg_url.replace("postgres://", "postgresql://"))

    report = {"src": [0,0,0,0], "art": [0,0,0,0], "lib": [0,0,0,0]} # [existing, migrated, skipped, failed]

    # 1. MIGRATE SOURCES
    try:
        sl_cur.execute("SELECT name, url, cat FROM Feed")
        rows = sl_cur.fetchall()
        report["src"][0] = len(rows)
        with pg_engine.connect() as pg:
            for r in rows:
                try:
                    pg.execute(text("INSERT INTO sources (name, feed_url, categories) VALUES (:n, :u, :c) ON CONFLICT DO NOTHING"), {"n": r[0], "u": r[1], "c": r[2]})
                    report["src"][1] += 1
                except: report["src"][3] += 1
            pg.commit()
    except Exception as e: print(f"Source migration skipped: {e}")

    # 2. MIGRATE ARTICLES & LIBRARY
    try:
        sl_cur.execute("SELECT title, link, img, source, cat, is_saved, created_at FROM Article")
        rows = sl_cur.fetchall()
        report["art"][0] = len(rows)
        with pg_engine.connect() as pg:
            for r in rows:
                try:
                    # Insert Article
                    pg.execute(text("""INSERT INTO articles (title, article_url, image_url, source_name, category, imported_at) 
                                    VALUES (:t, :u, :i, :s, :c, :d) ON CONFLICT DO NOTHING"""),
                                    {"t":r[0], "u":r[1], "i":r[2], "s":r[3], "c":r[4], "d":r[6]})
                    report["art"][1] += 1
                    
                    # If is_saved, create library entry
                    if r[5] == 1:
                        report["lib"][0] += 1
                        aid = pg.execute(text("SELECT id FROM articles WHERE article_url = :u"), {"u":r[1]}).fetchone()[0]
                        pg.execute(text("INSERT INTO library (article_id, saved_at) VALUES (:id, :at) ON CONFLICT DO NOTHING"), {"id":aid, "at":r[6]})
                        report["lib"][1] += 1
                except: report["art"][3] += 1
            pg.commit()
    except Exception as e: print(f"Article migration skipped: {e}")

    print("\n--- MIGRATION REPORT ---")
    print(f"Sources: Existing {report['src'][0]}, Migrated {report['src'][1]}, Failed {report['src'][3]}")
    print(f"Articles: Existing {report['art'][0]}, Migrated {report['art'][1]}, Failed {report['art'][3]}")
    print(f"Library: Existing {report['lib'][0]}, Migrated {report['lib'][1]}, Failed {report['lib'][3]}")

if __name__ == "__main__":
    run_migration()
