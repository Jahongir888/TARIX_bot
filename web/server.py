import os
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, update

# Loyihaning ma'lumotlar bazasi va Aiogram bot importlari
from database.db import async_session
from database.models import News, NewsComment
from data.config import BOT_TOKEN
from aiogram import Bot

# 1. Avval FastAPI obyektini yaratamiz
app = FastAPI()

# Guruhga post va izohlarni reply qilish uchun Aiogram bot obyekti
tg_bot = Bot(token=BOT_TOKEN)

# 2. Statik fayllar (home.js va boshqalar) uchun papkani ulaymiz
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# index.html fayliga aniq manzil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "index.html")

# 3. Sinov uchun savollar to'plami
SAMPLE_QUIZ = {
    "topic": "7-sinf Tarix: Amir Temur davlati",
    "duration_minutes": 15,
    "questions": [
        {
            "id": 1,
            "text": "Amir Temur nechanchi yilda tavallud topgan?",
            "options": ["1336-yil", "1342-yil", "1350-yil", "1370-yil"],
            "correct": 0
        },
        {
            "id": 2,
            "text": "Sohibqiron Amir Temurning otasi kim bo'lgan?",
            "options": ["Amir Qazag'on", "Amir Tarag'ay", "Hoji Barlos", "Mirzo Ulug'bek"],
            "correct": 1
        },
        {
            "id": 3,
            "text": "Amir Temur davlatining dastlabki poytaxti qaysi shahar bo'lgan?",
            "options": ["Buxoro", "Hirot", "Kesh (Shahrisabz)", "Samarqand"],
            "correct": 3
        },
        {
            "id": 4,
            "text": "Amir Temur qachon Movarounnahrning yagona hukmdori deb e'lon qilindi?",
            "options": ["1360-yil", "1370-yil", "1380-yil", "1395-yil"],
            "correct": 1
        },
        {
            "id": 5,
            "text": "Loy jangi qaysi yilda bo'lib o'tgan?",
            "options": ["1365-yil", "1368-yil", "1372-yil", "1390-yil"],
            "correct": 0
        }
    ]
}

# 4. Darslar ro'yxati
SAMPLE_LESSONS = {
    "6": [
        {"id": 601, "title": "1-dars. Qadimgi tosh davri (Paleolit)", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Eng qadimgi odamlar, ilk mehnat qurollari va olovning kashf etilishi haqida umumiy tushuncha."},
        {"id": 602, "title": "2-dars. O'rta tosh davri (Mezolit)", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Kamon va o'qning ixtiro qilinishi, hayvonlarni xonakilashtirishning boshlanishi."}
    ],
    "7": [
        {"id": 701, "title": "1-dars. Amir Temur davlatining tashkil topishi", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Movarounnahr XIV asr o'rtalarida, Amir Temurning hokimiyat tepasiga kelishi."},
        {"id": 702, "title": "2-dars. Amir Temurning harbiy yurishlari", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "desc": "Amir Temurning davlat chegaralarini mustahkamlashga qaratilgan harbiy yurishlari."}
    ],
    "8": [], "9": [], "10": [], "11": []
}

# 5. Asosiy sahifa (index.html)
@app.get("/", response_class=HTMLResponse)
async def read_root(response: Response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h3>Shablon fayli topilmadi: {TEMPLATE_PATH}</h3>"

# 6. Dinamik Yangiliklar API (Bazadan barcha yangiliklarni va teglarni o'qiydi)
@app.get("/api/news")
async def get_news_list(tag: str = None):
    async with async_session() as session:
        query = select(News).order_by(News.created_at.desc())
        res = await session.execute(query)
        items = res.scalars().all()

        result = []
        for n in items:
            tags = [t.strip() for t in n.hashtags.split() if t.strip()]
            if tag and tag not in tags:
                continue
            result.append({
                "id": n.id,
                "title": n.title,
                "hashtags": tags,
                "category": n.category,
                "summary": n.summary,
                "image_url": n.image_url,
                "views_count": n.views_count,
                "date": n.created_at.strftime("%d-%b, %H:%M")
            })
        return result

# 7. Bitta yangilik tafsiloti API (Ko'rishlar soni +1 oshadi)
@app.get("/api/news/{news_id}")
async def get_news_detail(news_id: int):
    async with async_session() as session:
        await session.execute(
            update(News).where(News.id == news_id).values(views_count=News.views_count + 1)
        )
        await session.commit()

        news = await session.get(News, news_id)
        if not news:
            return {"error": "Not found"}

        # O'xshash yangiliklar (shu kategoriya bo'yicha 3 ta)
        rel_q = select(News).where(News.category == news.category, News.id != news.id).limit(3)
        rel_res = await session.execute(rel_q)
        related = [{"id": r.id, "title": r.title, "image_url": r.image_url} for r in rel_res.scalars().all()]

        # Izohlar ro'yxati
        com_q = select(NewsComment).where(NewsComment.news_id == news_id).order_by(NewsComment.created_at.desc())
        com_res = await session.execute(com_q)
        comments = [{"user": c.user_name, "text": c.text, "time": c.created_at.strftime("%H:%M")} for c in com_res.scalars().all()]

        return {
            "id": news.id,
            "title": news.title,
            "hashtags": [t.strip() for t in news.hashtags.split() if t.strip()],
            "content": news.content,
            "image_url": news.image_url,
            "source_url": news.source_url,
            "source_name": news.source_name,
            "views_count": news.views_count,
            "date": news.created_at.strftime("%d-%b %Y, %H:%M"),
            "related": related,
            "comments": comments
        }

# 8. Komment yozish sxemasi va API (Community guruhiga reply qilish bilan)
class CommentSchema(BaseModel):
    news_id: int
    user_id: int
    user_name: str
    text: str

@app.post("/api/news/comment")
async def add_comment(data: CommentSchema):
    async with async_session() as session:
        news = await session.get(News, data.news_id)
        if not news:
            return {"status": "error"}

        comment = NewsComment(
            news_id=data.news_id,
            user_id=data.user_id,
            user_name=data.user_name,
            text=data.text
        )
        session.add(comment)
        await session.commit()

        # Bog'langan guruh bo'lsa, o'sha postga reply qilamiz
        if news.discussion_chat_id:
            try:
                await tg_bot.send_message(
                    chat_id=news.discussion_chat_id,
                    text=f"💬 <b>{data.user_name}</b> dan izoh:\n\n{data.text}",
                    reply_to_message_id=news.telegram_post_msg_id,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Guruhga reply yuborishda xatolik: {e}")

        return {"status": "success"}

# 9. Test API
@app.get("/api/test-data")
async def get_test_data():
    return SAMPLE_QUIZ

# 10. Darslar API
@app.get("/api/lessons/{class_id}")
async def get_lessons_by_class(class_id: str):
    return SAMPLE_LESSONS.get(class_id, [])

# 11. Ishga tushirish bloki (har doim eng oxirida turadi)
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)