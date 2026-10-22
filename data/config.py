import os
from pathlib import Path
from dotenv import load_dotenv

# Loyihaning ildiz papkasidagi .env ni aniq topib yuklash
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Adminlar ID raqamini ro'yxatga olish
admins_raw = os.getenv("ADMINS", "")
ADMINS = [int(admin_id.strip()) for admin_id in admins_raw.split(",") if admin_id.strip()]

# Mini App / admin panel asosiy URL
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://pharos-talim.uz").rstrip("/")

# Brauzer admin kirishi: oddiy token (hash yo'q). Default: admin123
ADMIN_PANEL_TOKEN = (os.getenv("ADMIN_PANEL_TOKEN") or "admin123").strip()