import asyncio
import os
from database.db import async_session, init_db
from database.models import News

async def main():
    # 1. Eski bazani xavfsiz tozalaymiz
    if os.path.exists('database.db'):
        try:
            os.remove('database.db')
            print("Eski database.db tozalandi.")
        except Exception as e:
            print("Faylni o'chirib bo'lmadi (server o'chiqligiga ishonch hosil qiling):", e)

    # 2. Yangi ustunlar bilan bazani ochamiz
    await init_db()
    print("Yangi baza ochildi.")

    # 3. Namunaviy yangilikni qo'shamiz
    async with async_session() as s:
        s.add(News(
            title="Tarix fanidan umumta'lim milliy sertifikat imtihoni muddatlari e'lon qilindi",
            hashtags="#tarix #MS #attestatsiya",
            summary="Bilimni baholash agentligi rasmiy imtihon sanalarini tasdiqladi.",
            content="2026-yilgi sinovlar uchun ro'yxatga olish boshlandi.\n\nSertifikat imtiyozlari va namunaviy testlar platformada e'lon qilindi.",
            image_url="https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=1000",
            source_name="BMBA rasmiy",
            source_url="https://uzbmb.uz",
            views_count=12
        ))
        await s.commit()
    print("Baza tayyor va yangilik muvaffaqiyatli qo'shildi!")

if __name__ == "__main__":
    asyncio.run(main())