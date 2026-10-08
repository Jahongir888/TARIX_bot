from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from keyboards.reply import phone_keyboard, regions_keyboard, targets_keyboard, main_menu
from states.register import RegisterState
from keyboards.reply import phone_keyboard, regions_keyboard, targets_keyboard, main_menu, back_keyboard
from database.db import async_session
from database.models import User
from sqlalchemy import select

router = Router()


# 1. Start bosilganda Ism-familiya so'raladi
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n"
        f"<b>PHAROS</b> ta'lim platformasiga xush kelibsiz! 🏛✨\n\n"
        f"Ro'yxatdan o'tish uchun to'liq ism va familiyangizni kiriting:\n"
        f"(Masalan: Ali Valiyev)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.set_state(RegisterState.full_name)


# 2. Ism va familiyani qabul qilish hamda tekshirish
@router.message(RegisterState.full_name, F.text)
async def get_name(message: Message, state: FSMContext):
    # Matnni probellar bo'yicha so'zlarga ajratamiz
    name_parts = message.text.strip().split()

    # Agar so'zlar soni 2 tadan kam bo'lsa (faqat ism yoki familiya kiritilgan bo'lsa)
    if len(name_parts) < 2:
        await message.answer(
            "⚠️ Iltimos, ism va familiyangizni to'liq kiriting!\n"
            "(Masalan: Ali Valiyev)"
        )
        return  # Funksiyani shu yerda to'xtatadi va keyingi holatga o'tkazmaydi

    # Agar 2 yoki undan ortiq so'z bo'lsa, qabul qilib saqlaymiz
    await state.update_data(full_name=message.text.strip())

    await message.answer(
        "Rahmat! Endi pastdagi tugma orqali shaxsiy telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard
    )
    await state.set_state(RegisterState.contact)


# 3. Faqat telegram kontakt yuborilganda qabul qilinadi
@router.message(RegisterState.contact, F.contact)
async def get_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)

    await message.answer(
        "Qaysi viloyatdansiz? Quyidagi variantlardan birini tanlang:",
        reply_markup=regions_keyboard
    )
    await state.set_state(RegisterState.region)


# Kontakt o'rniga boshqa narsa (oddiy matn, rasm va h.k.) yuborilsa
@router.message(RegisterState.contact, ~F.contact)
async def invalid_contact(message: Message):
    await message.answer(
        "Iltimos, telefon raqamingizni yuborish uchun pastdagi «📱 Telefon raqamni yuborish» tugmasini bosing!",
        reply_markup=phone_keyboard
    )


# 4. Viloyat qabul qilinib, maqsad so'raladi
@router.message(RegisterState.region, F.text)
async def get_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text)

    await message.answer(
        "Platformadan foydalanishdan asosiy maqsadingiz nima?",
        reply_markup=targets_keyboard
    )
    await state.set_state(RegisterState.target)


# 5. Maqsad tanlangach, barcha ma'lumotlar jamlanadi
@router.message(RegisterState.target, F.text)
async def get_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text)

    data = await state.get_data()
    # === MA'LUMOTLAR BAZASIGA YOZISH ===
    async with async_session() as session:
        # 1. Foydalanuvchi bazada bor-yo'qligini tekshiramiz
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if not user:
            # Yangi o'quvchi bo'lsa, bazaga qo'shamiz
            user = User(
                telegram_id=message.from_user.id,
                full_name=data.get('full_name'),
                phone_number=data.get('phone'),
                region=data.get('region'),
                target=data.get('target'),
                balance=0,
                is_paid=False
            )
            session.add(user)
        else:
            # Agar mavjud bo'lsa, ma'lumotlarini yangilaymiz
            user.full_name = data.get('full_name')
            user.phone_number = data.get('phone')
            user.region = data.get('region')
            user.target = data.get('target')

        await session.commit()
    # ====================================
    await message.answer(
        f"✅ <b>Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!</b>\n\n"
        f"👤 <b>Ism:</b> {data.get('full_name')}\n"
        f"📱 <b>Tel:</b> {data.get('phone')}\n"
        f"📍 <b>Viloyat:</b> {data.get('region')}\n"
        f"🎯 <b>Maqsad:</b> {data.get('target')}\n\n"
        f"Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=main_menu,
        parse_mode="HTML"
    )
    await state.clear()


# 1. "Boshiga qaytish" bosilganda barcha holatlarni tozalab, startga qaytaradi
@router.message(F.text == "🏠 Boshiga qaytish")
async def reset_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Barcha amallar bekor qilindi. Boshlash uchun /start buyrug'ini yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )


# 2. "Orqaga" bosilganda bitta oldingi holatga qaytarish mexanizmi
@router.message(F.text == "⬅️ Orqaga")
async def go_back(message: Message, state: FSMContext):
    current_state = await state.get_state()

    # Agar foydalanuvchi viloyat tanlashda bo'lsa -> telefon so'rashga qaytaradi
    if current_state == RegisterState.region:
        await state.set_state(RegisterState.contact)
        await message.answer(
            "Telefon raqamingizni qayta yuboring:",
            reply_markup=phone_keyboard
        )
    # Agar maqsad tanlashda bo'lsa -> viloyat tanlashga qaytaradi
    elif current_state == RegisterState.target:
        await state.set_state(RegisterState.region)
        await message.answer(
            "Viloyatingizni qayta tanlang:",
            reply_markup=regions_keyboard
        )
    else:
        await message.answer("Oldingi bosqich mavjud emas.")

# "Bosh menyu" bosilganda holatni tozalab, asosiy menyuni chiqaradi
@router.message(F.text == "🏠 Bosh menyu")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Siz asosiy bosh menyudasiz:", reply_markup=main_menu)

# "Orqaga" bosilganda (agar biror bo'limda bo'lsa ham) bosh menyuga qaytaradi
@router.message(F.text == "⬅️ Orqaga")
async def go_back_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyuga qaytdingiz:", reply_markup=main_menu)