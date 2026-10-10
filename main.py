import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from database.db import init_db
from handlers import payment
from handlers.admin_news import admin_news_router

# Sozlamalar va routerlar importi
from data.config import BOT_TOKEN, ADMINS
from handlers import start, payment


# 1. Bot komandalarini menyuda ko'rsatish
async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va qo'llanma")
    ]
    await bot.set_my_commands(commands)


# 2. Bot ishga tushganda adminga xabar yuborish
async def notify_admins(bot: Bot):
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, "Bot muvaffaqiyatli ishga tushdi! 🚀")
        except Exception:
            pass


# 3. Asosiy ishga tushirish funksiyasi
async def main():
    # 1. Ma'lumotlar bazasini ishga tushirish
    await init_db()
    print("Ma'lumotlar bazasi tayyor!")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Routerlarni ro'yxatdan o'tkazamiz
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(admin_news_router)
    # Boshlang'ich amallar
    await set_default_commands(bot)
    await notify_admins(bot)

    print("Bot muvaffaqiyatli ishga tushdi va xabarlarni eshitmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())