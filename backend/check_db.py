import sqlite3

db_path = "app/db/storage.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("\nDatabase tables:")
for table in tables:
    print("-", table[0])

conn.close()