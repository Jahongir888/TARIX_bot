import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# 1. users jadvalida created_at ustuniga to'g'ri ISO matnli sana yozamiz
cur.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL OR typeof(created_at) != 'text'")

# 2. Agar birth_date ustuni bo'lsa, uni ham tekshirib matnga keltiramiz
try:
    cur.execute("UPDATE users SET birth_date = 'Tanlanmagan' WHERE birth_date IS NULL OR typeof(birth_date) != 'text'")
except Exception:
    pass

# 3. 84920194 idli foydalanuvchining sanalarini kafolatli to'g'rilaymiz
cur.execute("UPDATE users SET created_at = datetime('now') WHERE telegram_id = 84920194")

conn.commit()
conn.close()

print("Baza ichidagi barcha sana formatlari to'liq to'g'rilandi!")