from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# 1. Telefon raqamni yuborish tugmasi
phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# 2. Viloyatlarni tanlash tugmalari
regions_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Toshkent sh."), KeyboardButton(text="Toshkent vil.")],
[KeyboardButton(text="Jizzax"), KeyboardButton(text="Sirdaryo")],
        [KeyboardButton(text="Andijon"), KeyboardButton(text="Farg'ona"), KeyboardButton(text="Namangan")],
        [KeyboardButton(text="Samarqand"), KeyboardButton(text="Buxoro"), KeyboardButton(text="Navoiy")],
        [KeyboardButton(text="Qashqadaryo"), KeyboardButton(text="Surxondaryo")],
        [KeyboardButton(text="Xorazm"), KeyboardButton(text="Qoraqalpog'iston R.")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# 3. O'qish maqsadini tanlash tugmalari (TZ bo'yicha)
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

# Navigatsiya (Orqaga / Bosh menyuga) tugmalari
nav_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Boshiga qaytish")]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# 1. Yangilangan Bosh menyu (Namunaviy testlar va Kitoblar qo'shildi)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📚 Darslar"),
            KeyboardButton(text="📝 Namunaviy testlar")
        ],
        [
            KeyboardButton(text="📖 Kitoblar"),
            KeyboardButton(text="👤 Profilim")
        ],
        [
            KeyboardButton(text="ℹ️ Bot haqida")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# 2. Universal navigatsiya tugmalari (Ichki bo'limlar uchun)
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

# Sizning jonli Ngrok havolangiz:
MINI_APP_URL = "https://christine-places-horses-planned.trycloudflare.com"

# Bosh menyu tugmalari
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📚 Darslar"),
            KeyboardButton(text="📝 Namunaviy testlar", web_app=WebAppInfo(url=MINI_APP_URL))
        ],
        [
            KeyboardButton(text="📖 Kitoblar"),
            KeyboardButton(text="👤 Profilim")
        ],
        [
            KeyboardButton(text="💰 Balansni to'ldirish"),
            KeyboardButton(text="ℹ️ Bot haqida")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# Chek yuborishni bekor qilish tugmasi
cancel_payment = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)