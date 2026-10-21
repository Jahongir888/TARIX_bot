import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# 1. users jadvalida birth_date va created_at ustunlaridagi noto'g'ri qiymatlarni tozalash
cur.execute("UPDATE users SET birth_date = 'Tanlanmagan' WHERE birth_date IS NULL OR birth_date = ''")
cur.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL OR created_at = ''")

conn.commit()
conn.close()

print("Baza xatoliklari muvaffaqiyatli tozalandi!")