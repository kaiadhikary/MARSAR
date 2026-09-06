import sqlite3

DB_PATH = "app/db/storage.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Count suspicious transactions
cursor.execute("""
    SELECT COUNT(*)
    FROM transactions
    WHERE is_coinjoin = 1
""")

count = cursor.fetchone()[0]

print(f"Suspicious transactions stored: {count}")
print("\nLast 10 suspicious transactions:\n")

# Get latest 10 suspicious transactions
cursor.execute("""
    SELECT
        txid,
        inputs_count,
        outputs_count,
        fee_rate,
        is_coinjoin,
        shannon_entropy,
        created_at
    FROM transactions
    WHERE is_coinjoin = 1
    ORDER BY created_at DESC
    LIMIT 10
""")

rows = cursor.fetchall()

if not rows:
    print("No suspicious transactions found.")
else:
    for i, row in enumerate(rows, start=1):
        txid, inputs, outputs, fee_rate, coinjoin, entropy, created_at = row

        tx_link = f"https://mempool.space/tx/{txid}"

        print(f"{i}. TXID: {txid}")
        print(f"   Inputs: {inputs}")
        print(f"   Outputs: {outputs}")
        print(f"   Fee Rate: {fee_rate}")
        print(f"   CoinJoin: {'YES' if coinjoin else 'NO'}")
        print(f"   Shannon Entropy: {entropy}")
        print(f"   Time: {created_at}")
        print(f"   Link: {tx_link}")
        print()

conn.close()