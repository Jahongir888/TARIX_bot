from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
            KeyboardButton(text="💰 Balansni to'ldirish"),
            KeyboardButton(text="ℹ️ Bot haqida")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# 6. Chek yuborishni bekor qilish tugmasi
cancel_payment = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)