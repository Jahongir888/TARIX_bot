import ssl
from pyngrok import ngrok, conf

# SSL xatosini to'g'irlash
ssl._create_default_https_context = ssl._create_unverified_context
conf.get_default().ssl_context = ssl._create_unverified_context()

# Ngrok saytidan nusxalagan shaxsiy authtokeningizni mana bu qo'shtirnoq ichiga qo'ying:
NGROK_AUTH_TOKEN = "3KCLvonOLBrlOQ8VkN5D1mlNNOg_3ESrVvWJAUnpawz9oDk1h"

try:
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    tunnel = ngrok.connect(8000)
    print("\n" + "=" * 55)
    print(f"SIZNING MINI APP HAVOLANGIZ:\n{tunnel.public_url}")
    print("=" * 55 + "\n")
    input("Tunnelni to'xtatish uchun Enter bosing...")
except Exception as e:
    print(f"\nXatolik yuz berdi: {e}")