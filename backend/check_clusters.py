import sqlite3

db_path = "app/db/storage.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n=== CLUSTERS TABLE ===")

columns = cursor.execute(
    "PRAGMA table_info(clusters)"
).fetchall()

for column in columns:
    print(f"- {column[1]} ({column[2]})")

print("\n=== ADDRESS_CLUSTERS TABLE ===")

columns = cursor.execute(
    "PRAGMA table_info(address_clusters)"
).fetchall()

for column in columns:
    print(f"- {column[1]} ({column[2]})")

print("\n=== COUNTS ===")

cluster_count = cursor.execute(
    "SELECT COUNT(*) FROM clusters"
).fetchone()[0]

address_count = cursor.execute(
    "SELECT COUNT(*) FROM address_clusters"
).fetchone()[0]

print(f"Total clusters: {cluster_count}")
print(f"Total address-cluster mappings: {address_count}")

conn.close()