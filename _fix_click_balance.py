"""One-off: inspect + fix Click balance for telegram_id 1206236612."""
import sqlite3
from datetime import datetime

TG_ID = 1206236612
TARGET = 2000

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute(
    "SELECT telegram_id, balance, coins, is_paid FROM users WHERE telegram_id=?",
    (TG_ID,),
)
user = cur.fetchone()
print("BEFORE user:", user)

cur.execute(
    "SELECT id, user_id, amount, tx_type, description, created_at "
    "FROM coin_transactions WHERE user_id=? ORDER BY id DESC LIMIT 15",
    (TG_ID,),
)
print("coin_transactions:", cur.fetchall())

try:
    cur.execute(
        "SELECT id, telegram_id, amount, transaction_type, title, created_at "
        "FROM balance_transactions WHERE telegram_id=? ORDER BY id DESC LIMIT 15",
        (TG_ID,),
    )
    print("balance_transactions:", cur.fetchall())
except Exception as e:
    print("balance_transactions skip:", e)

try:
    cur.execute(
        "SELECT id, telegram_id, amount, status, click_trans_id, created_at, completed_at "
        "FROM payment_history WHERE telegram_id=? ORDER BY id DESC LIMIT 15",
        (TG_ID,),
    )
    print("payment_history:", cur.fetchall())
except Exception as e:
    print("payment_history skip:", e)

if not user:
    print("USER NOT FOUND")
    raise SystemExit(1)

bal = int(user[1] or 0)
coins = int(user[2] or 0)
print(f"current balance={bal}, coins={coins}, target={TARGET}")

if bal != TARGET or coins != TARGET:
    cur.execute(
        "UPDATE users SET balance=?, coins=?, is_paid=1 WHERE telegram_id=?",
        (TARGET, TARGET, TG_ID),
    )
    # Missing top-up row if only one 1000 payment was recorded
    cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM coin_transactions "
        "WHERE user_id=? AND tx_type='topup'",
        (TG_ID,),
    )
    topup_sum = int(cur.fetchone()[0] or 0)
    print("topup_sum in coin_transactions:", topup_sum)
    if topup_sum < TARGET:
        missing = TARGET - topup_sum
        now = datetime.utcnow().isoformat(sep=" ")
        cur.execute(
            "INSERT INTO coin_transactions (user_id, amount, tx_type, description, created_at) "
            "VALUES (?, ?, 'topup', ?, ?)",
            (
                TG_ID,
                missing,
                f"Manual fix: Click 500 xatosidan keyin yetishmagan +{missing} UZS",
                now,
            ),
        )
        cur.execute(
            "INSERT INTO balance_transactions "
            "(telegram_id, amount, transaction_type, title, item_category, created_at) "
            "VALUES (?, ?, 'income', ?, 'hisob', ?)",
            (
                TG_ID,
                missing,
                "Click to'lov (manual balans tuzatish)",
                now,
            ),
        )
        print(f"added missing transaction amount={missing}")
    conn.commit()
    cur.execute(
        "SELECT telegram_id, balance, coins, is_paid FROM users WHERE telegram_id=?",
        (TG_ID,),
    )
    print("AFTER user:", cur.fetchone())
else:
    print("Already at target; no update needed")

conn.close()
