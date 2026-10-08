from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from states.register import PaymentState
from keyboards.reply import main_menu, cancel_payment
from database.db import async_session
from database.models import User
from data.config import ADMINS

router = Router()

# 1. "Balansni to'ldirish" bosilganda karta raqami chiqadi
@router.message(F.text == "💰 Balansni to'ldirish")
async def start_payment(message: Message, state: FSMContext):
    await message.answer(
        "💳 <b>Balansni to'ldirish uchun to'lov rekvizitlari:</b>\n\n"
        "🔹 Karta raqam: <code>8600 0000 0000 0000</code>\n"
        "🔹 Karta egasi: PHAROS TA'LIM\n\n"
        "⚠️ <b>Ko'rsatma:</b>\n"
        "Kerakli summani o'tkazgach, to'lov cheki (skrinshot yoki rasm)ni ushbu botga yuboring.",
        reply_markup=cancel_payment,
        parse_mode="HTML"
    )
    await state.set_state(PaymentState.receipt)

# To'lovni bekor qilish
@router.message(PaymentState.receipt, F.text == "❌ Bekor qilish")
async def cancel_receipt(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("To'lov jarayoni bekor qilindi.", reply_markup=main_menu)

# 2. O'quvchi chek rasmini yuborganda adminga tasdiqlash uchun yo'naltirish
@router.message(PaymentState.receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    # Adminga boradigan tasdiqlash tugmalari
    admin_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ 50,000 UZS qo'shish", callback_data=f"pay_add_{user_id}_50000"),
                InlineKeyboardButton(text="✅ 100,000 UZS qo'shish", callback_data=f"pay_add_{user_id}_100000")
            ],
            [
                InlineKeyboardButton(text="❌ Chekni rad etish", callback_data=f"pay_reject_{user_id}")
            ]
        ]
    )

    # Birinchi adminga yuboramiz
    admin_id = ADMINS[0]
    await message.bot.send_photo(
        chat_id=admin_id,
        photo=photo_id,
        caption=(
            f"📥 <b>Yangi to'lov cheki keldi!</b>\n\n"
            f"👤 O'quvchi: <b>{user_name}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            f"Chekni tekshirib, quyidagi tugmalar orqali tasdiqlang:"
        ),
        reply_markup=admin_markup,
        parse_mode="HTML"
    )

    await message.answer(
        "✅ To'lov chekingiz adminga yuborildi!\n"
        "Administrator chekni tekshirib, hisobingizni to'ldirishi bilan sizga bildirishnoma keladi.",
        reply_markup=main_menu
    )
    await state.clear()

# 3. Admin tugmani bosganda o'quvchi balansini oshirish va bazaga yozish
@router.callback_query(F.data.startswith("pay_add_"))
async def admin_approve_payment(callback: CallbackQuery):
    _, _, target_user_id, amount = callback.data.split("_")
    target_user_id = int(target_user_id)
    amount = int(amount)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == target_user_id))
        user = result.scalar_one_or_none()

        if user:
            user.balance += amount
            user.is_paid = True
            await session.commit()
            new_balance = user.balance
        else:
            await callback.answer("Foydalanuvchi bazadan topilmadi!", show_alert=True)
            return

    # O'quvchiga xabar jo'natish
    await callback.bot.send_message(
        chat_id=target_user_id,
        text=(
            f"🎉 <b>Hisobingiz to'ldirildi!</b>\n\n"
            f"💰 Qo'shildi: +{amount:,} UZS\n"
            f"💳 Joriy balansingiz: <b>{new_balance:,} UZS</b>\n\n"
            f"Endi ta'lim xizmatlaridan to'liq foydalanishingiz mumkin!"
        ),
        parse_mode="HTML"
    )

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n✅ <b>TASDIQLANDI (+{amount:,} UZS)</b>",
        reply_markup=None
    )
    await callback.answer("To'lov muvaffaqiyatli tasdiqlandi!")

# 4. Admin rad etganda
@router.callback_query(F.data.startswith("pay_reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[2])

    await callback.bot.send_message(
        chat_id=target_user_id,
        text="❌ <b>To'lovingiz tasdiqlanmadi.</b>\nChek noaniq yoki to'lov hisobga kelib tushmagan. Iltimos, ma'lumotlarni qayta tekshirib yuboring.",
        parse_mode="HTML"
    )

    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n❌ <b>RAD ETILDI</b>",
        reply_markup=None
    )
    await callback.answer("Chek rad etildi.")