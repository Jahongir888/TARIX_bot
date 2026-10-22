import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from database.db import init_db
from data.config import BOT_TOKEN, ADMINS
from handlers import start, payment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("tg-bot")


def _load_optional_routers():
    """Admin routerlar import xatosida botning asosiy qismi ishlashda davom etadi."""
    routers = []

    try:
        from handlers.admin_quiz_import import admin_quiz_router
        routers.append(("admin_quiz", admin_quiz_router))
    except Exception as exc:
        logger.exception("admin_quiz_router yuklanmadi (bot ishlayveradi): %s", exc)

    try:
        from handlers.admin_news import admin_news_router
        routers.append(("admin_news", admin_news_router))
    except Exception as exc:
        logger.exception("admin_news_router yuklanmadi (bot ishlayveradi): %s", exc)

    return routers


async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va qo'llanma"),
        BotCommand(command="import_quiz", description="[Admin] Test Excel import"),
        BotCommand(command="add_news", description="[Admin] Yangilik Excel import"),
        BotCommand(command="admin", description="[Admin] Veb boshqaruv paneli"),
    ]
    await bot.set_my_commands(commands)


async def notify_admins(bot: Bot):
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, "Bot muvaffaqiyatli ishga tushdi! 🚀")
        except Exception:
            pass


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi. .env ni tekshiring.")
        sys.exit(1)

    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(payment.router)

    for name, router in _load_optional_routers():
        dp.include_router(router)
        logger.info("Router ulandi: %s", name)

    await set_default_commands(bot)
    await notify_admins(bot)

    # Eski webhook / boshqa polling qoldiqlarini tozalash
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as exc:
        logger.warning("Webhook o'chirishda ogohlantirish: %s", exc)

    logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni eshitmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (KeyboardInterrupt).")
