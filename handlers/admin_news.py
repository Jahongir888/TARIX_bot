import os
import pandas as pd
from aiogram import Router, F, Bot
from aiogram.types import Message
from database.db import async_session
from database.models import News

admin_news_router = Router()

# O'zingizning Telegram ID'ingizni kiriting (masalan: [1206236612])
ADMIN_IDS = [1206236612]


@admin_news_router.message(F.document, F.from_user.id.in_(ADMIN_IDS))
async def import_news_excel(message: Message, bot: Bot):
    # Faqat excel fayllarni tekshiramiz
    if not message.document.file_name.endswith(('.xlsx', '.xls')):
        return

    status_msg = await message.answer("📥 Excel fayl qabul qilindi, yangiliklar import qilinmoqda...")

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{message.document.file_name}"

    # Faylni yuklab olamiz
    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, file_path)

    try:
        df = pd.read_excel(file_path)
        count = 0

        async with async_session() as session:
            for _, row in df.iterrows():
                # Ustunlar bo'sh emasligini tekshiramiz
                if pd.isna(row.get('title')) or pd.isna(row.get('content')):
                    continue

                new_item = News(
                    title=str(row['title']).strip(),
                    hashtags=str(row.get('hashtags', '')).strip(),
                    category=str(row.get('category', 'umumiy')).strip(),
                    summary=str(row.get('summary', '')).strip() if pd.notna(row.get('summary')) else None,
                    content=str(row['content']).strip(),
                    image_url=str(row.get('image_url', '')).strip(),
                    source_url=str(row.get('source_url', '')).strip() if pd.notna(row.get('source_url')) else None,
                    source_name=str(row.get('source_name', 'Manba')).strip(),
                    discussion_chat_id=int(row['discussion_chat_id']) if pd.notna(
                        row.get('discussion_chat_id')) else None
                )
                session.add(new_item)
                await session.flush()

                # Agar yo'nalish guruhi ID'si berilgan bo'lsa, o'sha yerga avtomatik post tashlaymiz
                if new_item.discussion_chat_id:
                    try:
                        sent = await bot.send_photo(
                            chat_id=new_item.discussion_chat_id,
                            photo=new_item.image_url,
                            caption=f"📢 <b>{new_item.title}</b>\n\n{new_item.summary or ''}\n\n{new_item.hashtags}",
                            parse_mode="HTML"
                        )
                        new_item.telegram_post_msg_id = sent.message_id
                    except Exception as err:
                        print(f"Guruhga post chiqarishda xatolik: {err}")

                count += 1

            await session.commit()

        await status_msg.edit_text(f"✅ Muvaffaqiyatli <b>{count}</b> ta yangilik bazaga kiritildi!", parse_mode="HTML")

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)