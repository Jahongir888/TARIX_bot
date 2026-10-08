import sqlite3

# Bazaga ulanish
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Barcha foydalanuvchilarni o'qib olish
cursor.execute("SELECT id, telegram_id, full_name, phone_number, region, target, balance FROM users")
rows = cursor.fetchall()

print("\n" + "=" * 60)
print("📊 RO'YXATDAN O'TGAN FOYDALANUVCHILAR RO'YXATI:")
print("=" * 60)

for row in rows:
    print(f"🆔 ID: {row[0]}")
    print(f"🔹 Telegram ID: {row[1]}")
    print(f"👤 Ism: {row[2]}")
    print(f"📱 Tel: {row[3]}")
    print(f"📍 Viloyat: {row[4]}")
    print(f"🎯 Maqsad: {row[5]}")
    print(f"💰 Balans: {row[6]} UZS")
    print("-" * 60)

conn.close()