import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

# BotFather bergan tokenni qo'ying
BOT_TOKEN = "8870408083:AAFYvNySTkP8DA6EaKiP2_xXUX6Nqh1l15Q"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}! Bot muvaffaqiyatli ishga tushdi.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Botdan foydalanish bo'yicha qo'llanma:\n"
        "• /start — Botni qayta ishga tushirish\n"
        "• /help — Mavjud buyruqlar ro'yxati"
    )

@dp.message()
async def echo_handler(message: types.Message):
    await message.send_copy(chat_id=message.chat.id)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())