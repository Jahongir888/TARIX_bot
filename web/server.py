import os
from datetime import datetime, date
from typing import Optional

import uvicorn
from fastapi import FastAPI, Response, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, or_, update, func

# Loyihaning ma'lumotlar bazasi va Aiogram bot importlari
from database.db import async_session
from database.models import (
    User, UserDevice, UserProgress, News, NewsComment, NewsReaction,
    CoinTransaction, UserDailyActivity, UserFeedback, ExamEvent, Notification, UserCoursePace, UserOctagonProfile, Promotion, PlatformStats
)
from data.config import BOT_TOKEN
from aiogram import Bot

# 1. FastAPI ilovasini yaratamiz
app = FastAPI(title="PHAROS Education Platform")

# Aiogram bot obyekti (Telegram guruhiga sharhlarni yo'naltirish uchun)
tg_bot = Bot(token=BOT_TOKEN)

# 2. Statik fayllar (JS, CSS, Media) ulanishi
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# index.html shabloniga mutlaq manzil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "index.html")

# 3. Sinov namunaviy savollar to'plami
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

# 4. Sinflar bo'yicha darslar ro'yxati
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

# ==========================================================
# PYDANTIC SO'ROV SXEMALARI
# ==========================================================
class CommentSchema(BaseModel):
    news_id: int
    user_id: int
    user_name: str
    text: str

class ReactionSchema(BaseModel):
    news_id: int
    user_id: int
    reaction_type: str  # 'like', 'heart', 'fire', 'idea'

class ProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    district: Optional[str] = None
    secondary_phone: Optional[str] = None
    birth_date: Optional[str] = None
    avatar_url: Optional[str] = None

class ActivityPingSchema(BaseModel):
    seconds: int = 30


# ==========================================================
# ASOSIY YO'NALISHLAR (ENDPOINTS)
# ==========================================================

# 5. Asosiy sahifa (index.html)
@app.get("/", response_class=HTMLResponse)
async def read_root(response: Response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h3>Shablon fayli topilmadi: {TEMPLATE_PATH}</h3>"


# 6. SHAXSIY KABINET / PROFIL MA'LUMOTLARINI OLISH
@app.get("/api/profile")
async def get_user_profile(
    telegram_id: int = Query(..., description="Telegram foydalanuvchi ID raqami"),
    first_name: str = Query("", description="Telegram ism"),
    username: str = Query("", description="Telegram username")
):
    async with async_session() as session:
        query = select(User).where(User.telegram_id == telegram_id)
        res = await session.execute(query)
        user = res.scalar_one_or_none()

        # Yangi foydalanuvchi: sun'iy 120 coin va 100 soat EMAS, balki 0 Coin va 0 soatdan boshlanadi
        if not user:
            display_title = first_name.strip() if first_name else f"Foydalanuvchi {telegram_id}"
            user = User(
                telegram_id=telegram_id,
                full_name=display_title,
                selected_subject="tarix",
                target="Attestatsiya",
                balance=0,
                coins=0,
                is_paid=False,
                device_count=1,
                status_abc="CCC",
                total_active_seconds=0
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Tranzaksiyalar tarixi
        tx_query = select(CoinTransaction).where(CoinTransaction.user_id == telegram_id).order_by(CoinTransaction.created_at.desc())
        tx_res = await session.execute(tx_query)
        transactions = [
            {
                "amount": t.amount,
                "description": t.description,
                "date": t.created_at.strftime("%d-%b, %H:%M")
            }
            for t in tx_res.scalars().all()
        ]

        # Foydalanuvchining o'quv yo'nalishlari va statuslari (kurslar bo'yicha dinamik)
        user_courses = [
            {"id": "6_test", "name": "6-sinf mavzulashgan test", "score": 75, "level": "Bilimdon"},
            {"id": "7_tarix", "name": "7-sinf Tarix kursi", "score": 50, "level": "Shogird"},
            {"id": "attestatsiya", "name": "Attestatsiya Mock", "score": 92, "level": "Ustoz"}
        ]

        # Qurilmalar ro'yxati
        devices_q = select(UserDevice).where(UserDevice.user_id == user.telegram_id).order_by(UserDevice.last_login.desc())
        dev_res = await session.execute(devices_q)
        device_rows = dev_res.scalars().all()

        devices = [
            {
                "id": d.id,
                "device_name": d.device_name,
                "device_ip": d.device_ip or "Noma'lum IP",
                "last_login": d.last_login.strftime("%d-%b, %H:%M") if d.last_login else ""
            }
            for d in device_rows
        ]
        if not devices:
            devices = [{"id": 0, "device_name": "Mobil qurilma", "device_ip": "127.0.0.1", "last_login": "Hozir faol"}]

        return {
            "telegram_id": user.telegram_id,
            "full_name": user.full_name or first_name or "PHAROS o'quvchisi",
            "username": username or "",
            "phone_number": user.phone_number or "Kiritilmagan",
            "secondary_phone": user.secondary_phone or "",
            "region": user.region or "O'zbekiston",
            "district": user.district or "Tanlanmagan",
            "birth_date": user.birth_date or "Tanlanmagan",
            "avatar_url": user.avatar_url or "👤",
            "target": user.target or "Abituriyent",
            "selected_subject": user.selected_subject or "tarix",
            "balance": user.balance or 0,
            "coins": user.coins or 0,
            "is_paid": bool(user.is_paid),
            "status_abc": user.status_abc or "CCC",
            "device_count": len(devices),
            "devices": devices,
            "invited_friends": user.invited_friends_count or 0,
            "oferta_accepted": bool(user.oferta_accepted),
            "total_hours": round((user.total_active_seconds or 0) / 3600, 1),
            "courses": user_courses,
            "transactions": transactions,
            "weekly_xp": [0, 0, 0, 0, 0, 0, round((user.total_active_seconds or 0) / 60)],
            "joined_date": user.created_at.strftime("%d-%b %Y") if user.created_at else ""
        }


# 7. PROFIL MA'LUMOTLARINI TAHRIRLASH (✏️ TUGMASI UCHUN)
@app.patch("/api/user/profile/{telegram_id}")
async def update_user_profile(telegram_id: int, payload: ProfileUpdateSchema):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.district is not None:
            user.district = payload.district.strip()
        if payload.secondary_phone is not None:
            user.secondary_phone = payload.secondary_phone.strip()
        if payload.birth_date is not None:
            user.birth_date = payload.birth_date.strip()
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url

        await session.commit()
        return {"status": "success", "message": "Ma'lumotlar muvaffaqiyatli saqlandi"}


# 8. OFERTA IMZOLASH VA BIR MARTALIK +20 COIN BERISH
@app.post("/api/user/oferta/{telegram_id}")
async def accept_oferta(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        if user.oferta_accepted:
            return {"status": "warning", "message": "Oferta bonusi allaqachon berilgan!", "coins": user.coins}

        user.oferta_accepted = True
        user.coins = (user.coins or 0) + 20

        tx = CoinTransaction(
            user_id=telegram_id,
            amount=20,
            tx_type="oferta",
            description="Oferta shartnomasini imzolaganlik uchun bonus"
        )
        session.add(tx)
        await session.commit()

        return {"status": "success", "message": "Oferta qabul qilindi! +20 Coin hisobingizga qo'shildi", "coins": user.coins}


# 9. PLATFORMA FAOLLIGINI QAYD ETISH (TAYMER VA DIAGRAMMA UCHUN)
@app.post("/api/user/activity/{telegram_id}")
async def log_user_activity(telegram_id: int, payload: ActivityPingSchema):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return {"status": "ignored"}

        user.total_active_seconds = (user.total_active_seconds or 0) + payload.seconds

        today = date.today()
        act_res = await session.execute(
            select(UserDailyActivity).where(
                UserDailyActivity.user_id == telegram_id,
                UserDailyActivity.activity_date == today
            )
        )
        daily_act = act_res.scalar_one_or_none()

        if daily_act:
            daily_act.seconds_spent = (daily_act.seconds_spent or 0) + payload.seconds
        else:
            daily_act = UserDailyActivity(
                user_id=telegram_id,
                activity_date=today,
                seconds_spent=payload.seconds
            )
            session.add(daily_act)

        await session.commit()
        return {"status": "success", "total_seconds": user.total_active_seconds}


# 10. Dinamik Yangiliklar API
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


# 11. Bitta yangilik tafsiloti API (Reaksiyalar soni va foydalanuvchi holati bilan)
@app.get("/api/news/{news_id}")
async def get_news_detail(news_id: int, user_id: Optional[int] = Query(None)):
    async with async_session() as session:
        await session.execute(
            update(News).where(News.id == news_id).values(views_count=News.views_count + 1)
        )
        await session.commit()

        news = await session.get(News, news_id)
        if not news:
            return {"error": "Not found"}

        # Foydalanuvchi oldin shu yangilikka reaksiya bosganmi yoki yo'qligini aniqlash
        user_reaction = None
        if user_id:
            user_react_q = select(NewsReaction).where(
                NewsReaction.news_id == news_id,
                NewsReaction.user_id == user_id
            )
            react_res = await session.execute(user_react_q)
            user_react_row = react_res.scalar_one_or_none()
            if user_react_row:
                user_reaction = user_react_row.reaction

        rel_q = select(News).where(News.category == news.category, News.id != news.id).limit(3)
        rel_res = await session.execute(rel_q)
        related = [{"id": r.id, "title": r.title, "image_url": r.image_url} for r in rel_res.scalars().all()]

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
            "likes_count": news.likes_count or 0,
            "hearts_count": news.hearts_count or 0,
            "fires_count": news.fires_count or 0,
            "ideas_count": news.ideas_count or 0,
            "user_reaction": user_reaction,
            "date": news.created_at.strftime("%d-%b %Y, %H:%M"),
            "related": related,
            "comments": comments
        }


# 11.1 Reaksiya bosish va hisoblagichni yangilash API
@app.post("/api/news/react")
async def toggle_news_reaction(data: ReactionSchema):
    async with async_session() as session:
        news = await session.get(News, data.news_id)
        if not news:
            raise HTTPException(status_code=404, detail="Yangilik topilmadi")

        react_q = select(NewsReaction).where(
            NewsReaction.news_id == data.news_id,
            NewsReaction.user_id == data.user_id
        )
        res = await session.execute(react_q)
        existing = res.scalar_one_or_none()

        # Agar oldin bosilgan shu reaksiyaning o'zi qayta bosilsa -> uni bekor qiladi (-1)
        if existing and existing.reaction == data.reaction_type:
            await session.delete(existing)
            if data.reaction_type == "like" and (news.likes_count or 0) > 0: news.likes_count -= 1
            elif data.reaction_type == "heart" and (news.hearts_count or 0) > 0: news.hearts_count -= 1
            elif data.reaction_type == "fire" and (news.fires_count or 0) > 0: news.fires_count -= 1
            elif data.reaction_type == "idea" and (news.ideas_count or 0) > 0: news.ideas_count -= 1
            await session.commit()
            return {"status": "removed", "reaction": None}

        # Agar oldin boshqa reaksiya bosilgan bo'lsa -> eskisini kamaytirib, yangisini o'rnatadi
        if existing:
            old_r = existing.reaction
            if old_r == "like" and (news.likes_count or 0) > 0: news.likes_count -= 1
            elif old_r == "heart" and (news.hearts_count or 0) > 0: news.hearts_count -= 1
            elif old_r == "fire" and (news.fires_count or 0) > 0: news.fires_count -= 1
            elif old_r == "idea" and (news.ideas_count or 0) > 0: news.ideas_count -= 1
            existing.reaction = data.reaction_type
        else:
            new_r = NewsReaction(news_id=data.news_id, user_id=data.user_id, reaction=data.reaction_type)
            session.add(new_r)

        # Yangi reaksiyaga +1 qo'shish
        if data.reaction_type == "like": news.likes_count = (news.likes_count or 0) + 1
        elif data.reaction_type == "heart": news.hearts_count = (news.hearts_count or 0) + 1
        elif data.reaction_type == "fire": news.fires_count = (news.fires_count or 0) + 1
        elif data.reaction_type == "idea": news.ideas_count = (news.ideas_count or 0) + 1

        await session.commit()
        return {
            "status": "success",
            "reaction": data.reaction_type,
            "likes": news.likes_count,
            "hearts": news.hearts_count,
            "fires": news.fires_count,
            "ideas": news.ideas_count
        }


# 12. Izoh qoldirish API
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


# 13. Test API
@app.get("/api/test-data")
async def get_test_data():
    return SAMPLE_QUIZ


# 14. Darslar API
@app.get("/api/lessons/{class_id}")
async def get_lessons_by_class(class_id: str):
    return SAMPLE_LESSONS.get(class_id, [])


# ==========================================================
# IMTIHON TAYMERLARI (DEDLAYN) API
# ==========================================================
@app.get("/api/deadlines")
async def get_exam_deadlines():
    async with async_session() as session:
        now = datetime.utcnow()
        query = select(ExamEvent).where(
            ExamEvent.is_active == True,
            ExamEvent.target_date >= now
        ).order_by(ExamEvent.target_date.asc())

        res = await session.execute(query)
        events = res.scalars().all()

        if not events:
            return {
                "nearest": {
                    "title": "Tarix: Milliy Sertifikat (Bahorgi)",
                    "badge": "BMBA",
                    "target_iso": "2026-11-20T09:00:00",
                    "action_url": "https://my.uzbmb.uz"
                },
                "all": []
            }

        nearest = events[0]
        return {
            "nearest": {
                "title": nearest.title,
                "badge": nearest.badge_label,
                "target_iso": nearest.target_date.isoformat(),
                "action_url": nearest.action_url
            },
            "all": [
                {
                    "id": ev.id,
                    "title": ev.title,
                    "badge": ev.badge_label,
                    "date": ev.target_date.strftime("%d-%m-%Y"),
                    "action_url": ev.action_url
                } for ev in events
            ]
        }


# ==========================================================
# BILDIRISHNOMALAR (NOTIFICATIONS) API
# ==========================================================
@app.get("/api/notifications")
async def get_notifications(telegram_id: int = None):
    async with async_session() as session:
        query = select(Notification).where(
            or_(Notification.user_id == telegram_id, Notification.user_id == None)
        ).order_by(Notification.created_at.desc())

        res = await session.execute(query)
        notifs = res.scalars().all()

        # Agar bazada hali ma'lumot bo'lmasa, sinov uchun namuna qaytaramiz
        if not notifs:
            return {
                "unread_count": 3,
                "items": [
                    {
                        "id": 1,
                        "source": "oktagon",
                        "title": "Jang chaqirig'i!",
                        "message": "Foydalanuvchi sizni Tarix fanidan tezkori jangga chaqirdi.",
                        "target_tab": "home",
                        "is_read": False,
                        "created_at": "10 daqiqa oldin"
                    },
                    {
                        "id": 2,
                        "source": "testlar",
                        "title": "Namunaviy test yuklandi",
                        "message": "Attestatsiya-2026 uchun yangi 30 talik diagnostik test qo'shildi.",
                        "target_tab": "tests",
                        "is_read": False,
                        "created_at": "Bugun, 14:20"
                    },
                    {
                        "id": 3,
                        "source": "tolov",
                        "title": "Hisob to'ldirildi",
                        "message": "Hisobingizga muvaffaqiyatli +20 Coin qo'shildi.",
                        "target_tab": "profile",
                        "is_read": False,
                        "created_at": "Kecha"
                    },
                    {
                        "id": 4,
                        "source": "kurslar",
                        "title": "Dars eslatmasi",
                        "message": "7-sinf Tarix kursidagi 'Amir Temur' mavzusini davom ettirish vaqti bo'ldi.",
                        "target_tab": "lessons",
                        "is_read": True,
                        "created_at": "2 kun oldin"
                    },
                    {
                        "id": 5,
                        "source": "qurilmalar",
                        "title": "Yangi qurilmadan kirish",
                        "message": "Hisobingizga yangi qurilmadan kirish qayd etildi.",
                        "target_tab": "profile",
                        "is_read": True,
                        "created_at": "3 kun oldin"
                    }
                ]
            }

        unread = sum(1 for n in notifs if not n.is_read)
        return {
            "unread_count": unread,
            "items": [
                {
                    "id": n.id,
                    "source": n.source,
                    "title": n.title,
                    "message": n.message,
                    "target_tab": n.target_tab,
                    "is_read": n.is_read,
                    "created_at": n.created_at.strftime("%d-%m %H:%M")
                } for n in notifs
            ]
        }


@app.post("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: int):
    async with async_session() as session:
        n = await session.get(Notification, notif_id)
        if n:
            n.is_read = True
            await session.commit()
    return {"status": "ok"}


@app.get("/api/user/course-pace")
async def get_user_course_pace(telegram_id: int = None):
    async with async_session() as session:
        query = select(UserCoursePace).where(
            UserCoursePace.is_active == True
        )
        if telegram_id:
            query = query.where(UserCoursePace.user_id == telegram_id)

        res = await session.execute(query)
        paces = res.scalars().all()

        # Bazada hali yozuv bo'lmasa, sinov uchun namuna (mock) qaytariladi
        if not paces:
            return {
                "items": [
                    {
                        "id": 1,
                        "title": "7-sinf O'zbekiston tarixi",
                        "target_tab": "lessons",
                        "actual": 35,  # Yashil: 35% o'qigan
                        "expected": 60,  # Reja: 60% bo'lishi kerak (25% qizil kechikish)
                        "status": "Shogird"
                    },
                    {
                        "id": 2,
                        "title": "Tarix: Milliy Sertifikat Ensiklopediyasi",
                        "target_tab": "books",
                        "actual": 80,  # Yashil: 80% o'qigan
                        "expected": 70,  # Reja: 70% (o'z vaqtida, yashil qizilni bosib ketgan)
                        "status": "Bilimdon"
                    },
                    {
                        "id": 3,
                        "title": "Huquq asoslari (Attestatsiya)",
                        "target_tab": "lessons",
                        "actual": 90,
                        "expected": 90,
                        "status": "Ustoz"
                    }
                ]
            }

        return {
            "items": [
                {
                    "id": p.id,
                    "title": p.course_title,
                    "target_tab": p.target_tab,
                    "actual": p.actual_progress,
                    "expected": p.expected_progress,
                    "status": p.status_label
                } for p in paces
            ]
        }

@app.get("/api/octagon/user-rank")
async def get_octagon_user_rank(telegram_id: int = None):
    async with async_session() as session:
        stat = None
        if telegram_id:
            res = await session.execute(
                select(UserOctagonProfile).where(UserOctagonProfile.user_id == telegram_id)
            )
            stat = res.scalar_one_or_none()

        # Agar bazada hali ma'lumot bo'lmasa, sinov uchun namuna qaytariladi
        if not stat:
            return {
                "course_title": "7-sinf O'zbekiston tarixi",
                "rank": 14,
                "rating": 1250,
                "battles": 8
            }

        return {
            "course_title": stat.current_course,
            "rank": stat.rank_position,
            "rating": stat.rating_points,
            "battles": stat.total_battles
        }


@app.get("/api/promotions")
async def get_active_promotions():
    async with async_session() as session:
        now = datetime.utcnow()
        query = select(Promotion).where(
            Promotion.is_active == True,
            Promotion.end_date >= now
        ).order_by(Promotion.end_date.asc())

        res = await session.execute(query)
        promos = res.scalars().all()

        # Bazada hali aksiya kiritilmagan bo'lsa, sinov uchun namuna (mock) beramiz
        if not promos:
            return {
                "active": True,
                "promo": {
                    "id": 1,
                    "title": "SUPER AKSIYA: 2 tasi 1 da!",
                    "subtitle": "Tarix noldan + Harbiy psixologiya",
                    "badge": "CHEGIRMA 65%",
                    "original_price": "150 000",
                    "discount_price": "50 000",
                    "end_iso": "2026-10-18T23:59:59",
                    "target_tab": "books",
                    "action_text": "Xarid qilish"
                }
            }

        first = promos[0]
        return {
            "active": True,
            "promo": {
                "id": first.id,
                "title": first.title,
                "subtitle": first.subtitle,
                "badge": first.badge_label,
                "original_price": f"{first.original_price:,}".replace(",", " ") if first.original_price else None,
                "discount_price": f"{first.discount_price:,}".replace(",", " "),
                "end_iso": first.end_date.isoformat(),
                "target_tab": first.target_tab,
                "action_text": first.action_btn_text
            }
        }

@app.get("/api/platform-stats")
async def get_platform_stats():
    async with async_session() as session:
        # Avval maxsus kiritilgan statistika jadvalidan tekshiramiz
        res = await session.execute(select(PlatformStats).order_by(PlatformStats.id.desc()))
        stat = res.scalar_one_or_none()

        if stat:
            return {
                "students": f"{stat.students_count:,}".replace(",", " "),
                "lessons": f"{stat.lessons_count}+",
                "questions": f"{stat.questions_count:,}".replace(",", " "),
                "books": f"{stat.books_count} ta"
            }

        # Agar jadval bo'sh bo'lsa, haqiqiy jadvallardan yig'amiz yoki namuna beramiz
        return {
            "students": "1 280+",
            "lessons": "194+",
            "questions": "3 650+",
            "books": "12 ta"
        }

# Ishga tushirish bloki
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


