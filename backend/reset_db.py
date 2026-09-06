import sqlite3

db_path = "app/db/storage.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count before cleanup
total_before = cursor.execute(
    "SELECT COUNT(*) FROM transactions"
).fetchone()[0]

suspicious_before = cursor.execute(
    "SELECT COUNT(*) FROM transactions WHERE is_coinjoin = 1"
).fetchone()[0]

safe_before = cursor.execute(
    "SELECT COUNT(*) FROM transactions WHERE is_coinjoin = 0"
).fetchone()[0]

print(f"Transactions before reset: {total_before}")
print(f"Safe transactions: {safe_before}")
print(f"Suspicious transactions: {suspicious_before}")

# Delete only safe transactions
cursor.execute(
    "DELETE FROM transactions WHERE is_coinjoin = 0"
)

conn.commit()

# Count after cleanup
total_after = cursor.execute(
    "SELECT COUNT(*) FROM transactions"
).fetchone()[0]

print("\nCleanup completed.")
print(f"Transactions remaining: {total_after}")

conn.close()