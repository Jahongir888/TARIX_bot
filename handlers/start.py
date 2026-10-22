from datetime import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from states.register import RegisterState
from keyboards.reply import (
    phone_keyboard,
    get_regions_keyboard,
    get_districts_keyboard,
    targets_keyboard,
    get_main_menu,
)
from database.regions_data import REGIONS_DATA
from database.db import async_session
from database.models import User, OctagonBattle
from data.config import ADMINS, WEBAPP_URL

router = Router()

_ADMIN_IDS = set(ADMINS or []) | {1206236612}


def _menu_for(user_id: int):
    return get_main_menu(user_id)


async def _send_admin_panel_hint(message: Message):
    """Adminlarga WebApp panel va brauzer token eslatmasi."""
    if message.from_user.id not in _ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="⚙️ Admin Boshqaruv Paneli",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"),
        )
    ]])
    await message.answer(
        "🛡 <b>Admin rejim</b>\n"
        "Tezkor tahrirlash va statistika uchun panelni oching.\n"
        "Katta Excel import: <code>/import_quiz</code>, <code>/add_news</code>\n\n"
        f"Brauzer: <code>{WEBAPP_URL}/admin?token=…</code>",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def _handle_octagon_start(message: Message, room_code: str) -> bool:
    """oct_ROOMCODE deep-link: taklif holatini tekshirib xabar yuboradi."""
    code = (room_code or "").strip().upper()
    if code.startswith("OCT_"):
        code = code[4:]
    if not code:
        return False

    async with async_session() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

        battle = (
            await session.execute(
                select(OctagonBattle).where(OctagonBattle.room_code == code)
            )
        ).scalar_one_or_none()

        if not battle:
            await message.answer(
                "❌ Oktagon jang xonasi topilmadi yoki havola noto'g'ri.",
                reply_markup=_menu_for(message.from_user.id) if user else ReplyKeyboardRemove(),
            )
            return True

        now = datetime.utcnow()
        if battle.status == "waiting" and battle.expires_at < now:
            battle.status = "expired"
            await session.commit()

        if battle.status != "waiting":
            status_msg = {
                "expired": "⏱ Bu duel havolasining 60 soniyalik muddati tugagan.",
                "cancelled": "🚫 Taklif bekor qilingan (raqib boshqa jangni boshlagan).",
                "active": "⚔️ Jang allaqachon boshlangan.",
                "finished": "✅ Bu jang yakunlangan.",
            }.get(battle.status, "Havola endi faol emas.")
            await message.answer(
                status_msg,
                reply_markup=_menu_for(message.from_user.id) if user else ReplyKeyboardRemove(),
            )
            return True

        seconds_left = max(0, int((battle.expires_at - now).total_seconds()))
        creator = (
            await session.execute(select(User).where(User.telegram_id == battle.creator_id))
        ).scalar_one_or_none()
        creator_name = (creator.full_name if creator else None) or "Raqib"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⚔️ Oktagonda jangni qabul qilish",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?startapp=oct_{code}")
            )]
        ])

        text = (
            f"⚔️ <b>Oktagon jang chaqiruvi!</b>\n\n"
            f"Chaqiruvchi: <b>{creator_name}</b>\n"
            f"Fan: <b>{battle.subject}</b>\n"
            f"Daraja: <b>{battle.level}</b>\n"
            + (f"Mavzu: <b>{battle.topic}</b>\n" if battle.topic else "")
            + f"\n⏱ Qolgan vaqt: <b>{seconds_left}</b> soniya\n"
            + ("Platformaga kiring va jangni qabul qiling." if user
               else "Avval /start orqali ro'yxatdan o'ting, so'ng havolani qayta bosing.")
        )
        if user:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
            await message.answer("Asosiy menyu:", reply_markup=_menu_for(message.from_user.id))
        else:
            await message.answer(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return True


# 1. Start bosilganda — deep-link yoki ro'yxatdan o'tish
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject = None):
    payload = (command.args if command else None) or ""

    # Oktagon duel havolasi: start=oct_ROOMCODE
    if payload.startswith("oct_"):
        handled = await _handle_octagon_start(message, payload)
        if handled:
            # Agar foydalanuvchi allaqachon a'zo bo'lsa — ro'yxatdan o'tkazmaymiz
            async with async_session() as session:
                existing = (
                    await session.execute(
                        select(User).where(User.telegram_id == message.from_user.id)
                    )
                ).scalar_one_or_none()
            if existing:
                await state.clear()
                return

    # Mavjud foydalanuvchi oddiy /start
    async with async_session() as session:
        existing = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()

    if existing and not payload.startswith("oct_"):
        await state.clear()
        await message.answer(
            f"Assalomu alaykum, <b>{existing.full_name or message.from_user.full_name}</b>!\n"
            f"PHAROS platformasiga xush kelibsiz.",
            reply_markup=_menu_for(message.from_user.id),
            parse_mode="HTML",
        )
        await _send_admin_panel_hint(message)
        return

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
    name_parts = message.text.strip().split()

    if len(name_parts) < 2:
        await message.answer(
            "⚠️ Iltimos, ism va familiyangizni to'liq kiriting!\n"
            "(Masalan: Ali Valiyev)"
        )
        return

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
        reply_markup=get_regions_keyboard()
    )
    await state.set_state(RegisterState.region)


# Kontakt o'rniga boshqa narsa yuborilsa
@router.message(RegisterState.contact, ~F.contact)
async def invalid_contact(message: Message):
    await message.answer(
        "Iltimos, telefon raqamingizni yuborish uchun pastdagi «📱 Telefon raqamni yuborish» tugmasini bosing!",
        reply_markup=phone_keyboard
    )


# 4. Viloyat tanlanganda -> Tuman/Shaharlar ro'yxati chiqadi
@router.message(RegisterState.region, F.text.in_(REGIONS_DATA.keys()))
async def get_region(message: Message, state: FSMContext):
    selected_region = message.text
    await state.update_data(region=selected_region)

    await message.answer(
        f"📍 <b>{selected_region}</b> tanlandi.\nEndi tuman yoki shahringizni tanlang:",
        reply_markup=get_districts_keyboard(selected_region),
        parse_mode="HTML"
    )
    await state.set_state(RegisterState.district)


# Agar viloyat tugmasi bosilmay, boshqa narsa yozilsa
@router.message(RegisterState.region)
async def invalid_region(message: Message):
    await message.answer(
        "Iltimos, pastdagi tugmalardan viloyatingizni tanlang:",
        reply_markup=get_regions_keyboard()
    )


# 5. Tuman/shahar tanlanganda -> Maqsad so'raladi
@router.message(RegisterState.district, F.text)
async def get_district(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_region = data.get("region")
    districts = REGIONS_DATA.get(selected_region, [])

    if message.text not in districts:
        await message.answer(
            "Iltimos, pastdagi tugmalardan tuman yoki shahringizni tanlang:",
            reply_markup=get_districts_keyboard(selected_region)
        )
        return

    full_district = f"{selected_region}, {message.text}"
    await state.update_data(district=full_district)

    await message.answer(
        "Platformadan foydalanishdan asosiy maqsadingiz nima?",
        reply_markup=targets_keyboard
    )
    await state.set_state(RegisterState.target)


# 6. Maqsad tanlangach -> Bazaga yozish va ro'yxatdan o'tishni yakunlash
@router.message(RegisterState.target, F.text)
async def get_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text)
    data = await state.get_data()

    # === MA'LUMOTLAR BAZASIGA YOZISH ===
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=message.from_user.id,
                full_name=data.get('full_name'),
                phone_number=data.get('phone'),
                region=data.get('region'),
                district=data.get('district'),
                target=data.get('target'),
                balance=0,
                is_paid=False
            )
            session.add(user)
        else:
            user.full_name = data.get('full_name')
            user.phone_number = data.get('phone')
            user.region = data.get('region')
            user.district = data.get('district')
            user.target = data.get('target')

        await session.commit()
    # ====================================

    await message.answer(
        f"✅ <b>Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!</b>\n\n"
        f"👤 <b>Ism:</b> {data.get('full_name')}\n"
        f"📱 <b>Tel:</b> {data.get('phone')}\n"
        f"📍 <b>Manzil:</b> {data.get('district')}\n"
        f"🎯 <b>Maqsad:</b> {data.get('target')}\n\n"
        f"Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=_menu_for(message.from_user.id),
        parse_mode="HTML"
    )
    await _send_admin_panel_hint(message)
    await state.clear()


# ==========================================================
# NAVIGATSIYA BOSHQARUVI (Orqaga va Boshiga qaytish)
# ==========================================================

@router.message(F.text == "🏠 Boshiga qaytish")
async def reset_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Barcha amallar bekor qilindi. Boshlash uchun /start buyrug'ini yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text == "⬅️ Orqaga")
async def go_back(message: Message, state: FSMContext):
    current_state = await state.get_state()

    # 1. Viloyatda tursa -> telefonga qaytaradi
    if current_state == RegisterState.region:
        await state.set_state(RegisterState.contact)
        await message.answer(
            "Telefon raqamingizni qayta yuboring:",
            reply_markup=phone_keyboard
        )
    # 2. Tumanda tursa -> viloyatga qaytaradi
    elif current_state == RegisterState.district:
        await state.set_state(RegisterState.region)
        await message.answer(
            "Viloyatingizni qayta tanlang:",
            reply_markup=get_regions_keyboard()
        )
    # 3. Maqsadda tursa -> o'sha viloyatning tumanlariga qaytaradi
    elif current_state == RegisterState.target:
        data = await state.get_data()
        selected_region = data.get("region")
        await state.set_state(RegisterState.district)
        await message.answer(
            "Tumaningizni qayta tanlang:",
            reply_markup=get_districts_keyboard(selected_region)
        )
    else:
        await state.clear()
        await message.answer(
            "Siz asosiy bosh menyudasiz:",
            reply_markup=_menu_for(message.from_user.id),
        )


@router.message(F.text == "🏠 Bosh menyu")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Siz asosiy bosh menyudasiz:",
        reply_markup=_menu_for(message.from_user.id),
    )


@router.message(F.text.in_({"/admin", "⚙️ Admin Boshqaruv Paneli"}))
async def open_admin_panel(message: Message):
    if message.from_user.id not in _ADMIN_IDS:
        await message.answer("⛔ Bu bo'lim faqat adminlar uchun.")
        return
    await _send_admin_panel_hint(message)