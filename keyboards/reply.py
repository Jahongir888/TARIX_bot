from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from data.config import ADMINS, WEBAPP_URL
from database.regions_data import REGIONS_DATA

_ADMIN_IDS = set(ADMINS or []) | {1206236612}

# 1. Telefon raqamni yuborish tugmasi
phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# 14 ta hudud tugmalari (2 tadan qator qilib joylanadi)
def get_regions_keyboard():
    buttons = []
    region_names = list(REGIONS_DATA.keys())
    for i in range(0, len(region_names), 2):
        row = [KeyboardButton(text=region_names[i])]
        if i + 1 < len(region_names):
            row.append(KeyboardButton(text=region_names[i+1]))
        buttons.append(row)
    buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# Tanlangan hududga mos tuman/shaharlar tugmalari
def get_districts_keyboard(region_name: str):
    districts = REGIONS_DATA.get(region_name, [])
    buttons = []
    for i in range(0, len(districts), 2):
        row = [KeyboardButton(text=districts[i])]
        if i + 1 < len(districts):
            row.append(KeyboardButton(text=districts[i+1]))
        buttons.append(row)
    buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
# ==========================================================

# 3. O'qish maqsadini tanlash tugmalari
targets_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Abituriyent (OTMga kirish)")],
        [KeyboardButton(text="📜 Milliy sertifikat")],
        [KeyboardButton(text="👨‍🏫 Ustozlar uchun attestatsiya")],
        [KeyboardButton(text="🏆 Fan olimpiadasi")],
        [KeyboardButton(text="📚 Boshqa maqsadda")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# 4. Universal navigatsiya tugmalari (Ichki bo'limlar uchun)
nav_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Boshiga qaytish")]
    ],
    resize_keyboard=True,
    is_persistent=True
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⬅️ Orqaga"),
            KeyboardButton(text="🏠 Bosh menyu")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# 5. ASOSIY BOSH MENYU (Ssilkasiz, toza Reply tugmalar)
def get_main_menu(telegram_id: int | None = None) -> ReplyKeyboardMarkup:
    """Oddiy foydalanuvchi menyusi; adminlarga WebApp boshqaruv tugmasi qo'shiladi."""
    rows = [
        [
            KeyboardButton(text="📚 Darslar"),
            KeyboardButton(text="📝 Namunaviy testlar"),
        ],
        [
            KeyboardButton(text="📖 Kitoblar"),
            KeyboardButton(text="👤 Profilim"),
        ],
        [
            KeyboardButton(text="💰 Balansni to'ldirish"),
            KeyboardButton(text="ℹ️ Bot haqida"),
        ],
    ]
    if telegram_id and int(telegram_id) in _ADMIN_IDS:
        rows.append([
            KeyboardButton(
                text="⚙️ Admin Boshqaruv Paneli",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"),
            )
        ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


# Orqaga moslik: eski importlar `main_menu` deb kutadi
main_menu = get_main_menu()

# 6. Chek yuborishni bekor qilish tugmasi
cancel_payment = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)