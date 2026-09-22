import sqlite3
import os

db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    print("Database file not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Total tables: {len(tables)}")
    print("\nTable names:")
    for t in tables:
        print(f"- {t[0]}")
    conn.close()
