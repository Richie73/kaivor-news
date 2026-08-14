import sqlite3, os
from sqlalchemy import create_engine, text

def run_migration():
    # Try every possible name we used for the local DB
    possible_dbs = ['kaivor_permanent.db', 'kaivor_vault.db', 'kaivor_local_safe.db', 'kaivor_emergency.db']
    old_db = next((db for db in possible_dbs if os.path.exists(db)), None)
    
    pg_url = os.environ.get('DATABASE_URL')

    if not pg_url:
        print("Error: DATABASE_URL not set in Termux.")
        return
    if not old_db:
        print(f"Error: Could not find any local .db file. Tried: {possible_dbs}")
        return

    print(f"Found local data in: {old_db}")
    print(f"Transferring to Neon Cloud...")
    
    sl_conn = sqlite3.connect(old_db)
    sl_cur = sl_conn.cursor()
    pg_engine = create_engine(pg_url.replace("postgres://", "postgresql://"))

    report = {"src": 0, "art": 0, "lib": 0}

    # 1. Migrate Sources (Feeds)
    try:
        # Check if table is 'Feed' or 'sources' in the old DB
        sl_cur.execute("SELECT name, url FROM Feed")
        rows = sl_cur.fetchall()
        with pg_engine.connect() as pg:
            for r in rows:
                pg.execute(text("INSERT INTO sources (name, feed_url) VALUES (:n, :u) ON CONFLICT DO NOTHING"), {"n": r[0], "u": r[1]})
            pg.commit()
        report["src"] = len(rows)
    except Exception as e:
        print(f"Source migration skipped or failed: {e}")

    # 2. Migrate Articles and Bookmarks
    try:
        sl_cur.execute("SELECT title, link, img, source, is_saved, created_at FROM Article WHERE is_saved=1")
        rows = sl_cur.fetchall()
        with pg_engine.connect() as pg:
            for r in rows:
                # Insert Article into Postgres
                pg.execute(text("""INSERT INTO articles (title, article_url, image_url, source_name, imported_at) 
                                VALUES (:t, :u, :i, :s, :d) ON CONFLICT DO NOTHING"""),
                                {"t":r[0], "u":r[1], "i":r[2], "s":r[3], "d":r[5]})
                
                # Get the new ID to create the Library entry
                res = pg.execute(text("SELECT id FROM articles WHERE article_url = :u"), {"u":r[1]}).fetchone()
                if res:
                    pg.execute(text("INSERT INTO library (article_id, saved_at) VALUES (:id, :at) ON CONFLICT DO NOTHING"), {"id":res[0], "at":r[5]})
                report["lib"] += 1
            pg.commit()
    except Exception as e:
        print(f"Article migration skipped or failed: {e}")

    print("\n--- MIGRATION REPORT ---")
    print(f"Sources Migrated: {report['src']}")
    print(f"Library Bookmarks Migrated: {report['lib']}")
    print("Stage 1 Migration Complete.")

if __name__ == "__main__":
    run_migration()
