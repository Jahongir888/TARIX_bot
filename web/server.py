import os
from datetime import datetime, date, timedelta
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
    CoinTransaction, UserDailyActivity, UserFeedback, ExamEvent,
    Notification, UserCoursePace, UserOctagonProfile, Promotion,
    PlatformStats, UserCabinetItem, UserFeedback,
    UserSupervisor, SupervisorInvoice
)

import uuid
import secrets

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
    reaction_type: str

class ProfileUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    secondary_phone: Optional[str] = None
    birth_date: Optional[str] = None
    avatar_url: Optional[str] = None

class SupervisorAddSchema(BaseModel):
    student_tg_id: int
    supervisor_name: str  # Kontakt bo'yicha berilgan ism, masalan: "Otam"

class FeedbackSchema(BaseModel):
    telegram_id: int
    category: str = "taklif"
    message: str

class ActivityPingSchema(BaseModel):
    seconds: int = 30

class PurchaseRequest(BaseModel):
    telegram_id: int
    product_id: int


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


# 6. SHAXSIY KABINET / PROFIL MA'LUMOTLARINI OLISH (XATOLIKLARSIZ)
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

        if not user:
            display_title = first_name.strip() if first_name else f"Foydalanuvchi {telegram_id}"
            user = User(
                telegram_id=telegram_id,
                full_name=display_title,
                selected_subject="tarix",
                target="Attestatsiya",
                district="Tanlanmagan",
                balance=0,
                coins=0,
                is_paid=False,
                is_subscribed=False,
                birth_date="Tanlanmagan",
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
        transactions = []
        for t in tx_res.scalars().all():
            t_date = t.created_at.strftime("%d-%b, %H:%M") if t.created_at else "-"
            transactions.append({
                "amount": t.amount,
                "description": t.description,
                "date": t_date
            })

        # Qurilmalar ro'yxati
        devices_q = select(UserDevice).where(UserDevice.user_id == user.telegram_id).order_by(UserDevice.last_login.desc())
        dev_res = await session.execute(devices_q)
        device_rows = dev_res.scalars().all()

        devices = []
        for d in device_rows:
            l_login = d.last_login.strftime("%d-%b, %H:%M") if d.last_login else "Hozir faol"
            devices.append({
                "id": d.id,
                "device_name": d.device_name,
                "device_ip": d.device_ip or "Noma'lum IP",
                "last_login": l_login
            })

        if not devices:
            devices = [{"id": 0, "device_name": "Mobil qurilma", "device_ip": "127.0.0.1", "last_login": "Hozir faol"}]

        # Sana xatolarini oldini olish
        b_date = getattr(user, 'birth_date', None)
        b_date_str = str(b_date) if b_date else "Tanlanmagan"

        j_date = ""
        if getattr(user, 'created_at', None):
            try:
                j_date = user.created_at.strftime("%d-%b %Y")
            except Exception:
                j_date = str(user.created_at)

        cab_q = select(UserCabinetItem).where(
            UserCabinetItem.telegram_id == telegram_id,
            UserCabinetItem.status == "active"
        )
        cab_res = await session.execute(cab_q)
        cabinet_items = cab_res.scalars().all()
        user_courses = [
            {
                "id": str(c.id),
                "name": c.title,
                "score": c.actual_progress or 0,
                "level": c.user_rank or "Shogird"
            }
            for c in cabinet_items
        ]
        knowledge_level = user_courses[0]["level"] if user_courses else "Mehmon"

        supervisor_data = None
        try:
            sup_query = select(UserSupervisor).where(
                UserSupervisor.student_tg_id == user.telegram_id,
                UserSupervisor.is_active == True
            ).order_by(UserSupervisor.created_at.desc())
            sup_res = await session.execute(sup_query)
            supervisor = sup_res.scalars().first()
            if supervisor:
                supervisor_data = {
                    "id": supervisor.id,
                    "name": supervisor.supervisor_name or "Nazoratchi",
                    "is_connected": bool(supervisor.supervisor_tg_id),
                    "terms_accepted": bool(supervisor.terms_accepted)
                }
        except Exception:
            supervisor_data = None

        is_subscribed = bool(getattr(user, 'is_subscribed', False) or getattr(user, 'is_paid', False))

        return {
            "telegram_id": user.telegram_id,
            "full_name": user.full_name or first_name or "PHAROS o'quvchisi",
            "username": username or "",
            "phone_number": getattr(user, 'phone_number', None) or "Kiritilmagan",
            "secondary_phone": getattr(user, 'secondary_phone', None) or "",
            "region": getattr(user, 'region', None) or "O'zbekiston",
            "district": getattr(user, 'district', None) or "Tanlanmagan",
            "birth_date": b_date_str,
            "avatar_url": getattr(user, 'avatar_url', None) or "👤",
            "is_subscribed": is_subscribed,
            "knowledge_level": knowledge_level,
            "target": getattr(user, 'target', None) or "Abituriyent",
            "selected_subject": getattr(user, 'selected_subject', None) or "tarix",
            "balance": user.balance if user.balance is not None else 0,
            "coins": user.coins if user.coins is not None else 0,
            "is_paid": bool(getattr(user, 'is_paid', False)),
            "status_abc": getattr(user, 'status_abc', "CCC") or "CCC",
            "device_count": len(devices),
            "devices": devices,
            "supervisor": supervisor_data,
            "invited_friends": getattr(user, 'invited_friends_count', 0) or 0,
            "oferta_accepted": bool(getattr(user, 'oferta_accepted', False)),
            "total_hours": round((getattr(user, 'total_active_seconds', 0) or 0) / 3600, 1),
            "courses": user_courses,
            "transactions": transactions,
            "weekly_xp": [0, 0, 0, 0, 0, 0, round((getattr(user, 'total_active_seconds', 0) or 0) / 60)],
            "joined_date": j_date
        }


# 7. PROFIL MA'LUMOTLARINI TAHRIRLASH
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
        if payload.region is not None:
            user.region = payload.region.strip()
        if payload.district is not None:
            district_val = payload.district.strip()
            user.district = district_val
            if not payload.region and ", " in district_val:
                user.region = district_val.split(", ", 1)[0]
        if payload.secondary_phone is not None:
            user.secondary_phone = payload.secondary_phone.strip()
        if payload.birth_date is not None:
            user.birth_date = payload.birth_date.strip()
        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url

        await session.commit()
        return {"status": "success", "message": "Ma'lumotlar muvaffaqiyatli saqlandi"}


@app.post("/api/supervisor/invite-link")
async def create_supervisor_invite_link(payload: SupervisorAddSchema):
    student_tg_id = payload.student_tg_id
    supervisor_name = (payload.supervisor_name or "").strip()
    if not supervisor_name:
        raise HTTPException(status_code=400, detail="Nazoratchi ismini kiriting")

    invite_token = secrets.token_urlsafe(16)

    async with async_session() as session:
        student = (
            await session.execute(select(User).where(User.telegram_id == student_tg_id))
        ).scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        existing = (
            await session.execute(
                select(UserSupervisor)
                .where(
                    UserSupervisor.student_tg_id == student_tg_id,
                    UserSupervisor.is_active == True
                )
                .order_by(UserSupervisor.created_at.desc())
            )
        ).scalars().first()

        if existing:
            existing.supervisor_name = supervisor_name
            if not existing.supervisor_tg_id:
                existing.invite_token = invite_token
                existing.terms_accepted = False
            else:
                invite_token = existing.invite_token or invite_token
                if not existing.invite_token:
                    existing.invite_token = invite_token
        else:
            session.add(UserSupervisor(
                student_tg_id=student_tg_id,
                supervisor_name=supervisor_name,
                invite_token=invite_token,
                terms_accepted=False,
                is_active=True
            ))

        await session.commit()

    bot_username = "pharos_talim_bot"
    try:
        me = await tg_bot.get_me()
        if me and me.username:
            bot_username = me.username
    except Exception:
        pass

    invite_link = f"https://t.me/{bot_username}?start=sup_{invite_token}"
    return {
        "status": "ok",
        "invite_link": invite_link,
        "token": invite_token
    }


@app.post("/api/user/feedback")
async def submit_user_feedback(payload: FeedbackSchema):
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Xabar matni bo'sh")

    async with async_session() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        session.add(UserFeedback(
            user_id=payload.telegram_id,
            category=payload.category or "taklif",
            message=message
        ))
        await session.commit()

    return {"status": "ok", "message": "Murojaat qabul qilindi"}


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

        if getattr(user, 'oferta_accepted', False):
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


# 9. PLATFORMA FAOLLIGINI QAYD ETISH
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
            n_date = n.created_at.strftime("%d-%b, %H:%M") if n.created_at else "-"
            result.append({
                "id": n.id,
                "title": n.title,
                "hashtags": tags,
                "category": n.category,
                "summary": n.summary,
                "image_url": n.image_url,
                "views_count": n.views_count,
                "date": n_date
            })
        return result


# 11. Bitta yangilik tafsiloti API
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
        comments = [
            {
                "user": c.user_name,
                "text": c.text,
                "time": c.created_at.strftime("%H:%M") if c.created_at else ""
            }
            for c in com_res.scalars().all()
        ]

        n_full_date = news.created_at.strftime("%d-%b %Y, %H:%M") if news.created_at else "-"

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
            "date": n_full_date,
            "related": related,
            "comments": comments
        }


# 11.1 Reaksiya bosish API
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

        if existing and existing.reaction == data.reaction_type:
            await session.delete(existing)
            if data.reaction_type == "like" and (news.likes_count or 0) > 0: news.likes_count -= 1
            elif data.reaction_type == "heart" and (news.hearts_count or 0) > 0: news.hearts_count -= 1
            elif data.reaction_type == "fire" and (news.fires_count or 0) > 0: news.fires_count -= 1
            elif data.reaction_type == "idea" and (news.ideas_count or 0) > 0: news.ideas_count -= 1
            await session.commit()
            return {"status": "removed", "reaction": None}

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
                    "date": ev.target_date.strftime("%d-%m-%Y") if ev.target_date else "",
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

        if not notifs:
            return {
                "unread_count": 3,
                "items": [
                    {
                        "id": 1,
                        "source": "oktagon",
                        "title": "Jang chaqirig'i!",
                        "message": "Foydalanuvchi sizni Tarix fanidan tezkor jangga chaqirdi.",
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
                    "created_at": n.created_at.strftime("%d-%m %H:%M") if n.created_at else ""
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

        if not paces:
            return {
                "items": [
                    {
                        "id": 1,
                        "title": "7-sinf O'zbekiston tarixi",
                        "target_tab": "lessons",
                        "actual": 35,
                        "expected": 60,
                        "status": "Shogird"
                    },
                    {
                        "id": 2,
                        "title": "Tarix: Milliy Sertifikat Ensiklopediyasi",
                        "target_tab": "books",
                        "actual": 80,
                        "expected": 70,
                        "status": "Bilimdon"
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
        res = await session.execute(select(PlatformStats).order_by(PlatformStats.id.desc()))
        stat = res.scalar_one_or_none()

        if stat:
            return {
                "students": f"{stat.students_count:,}".replace(",", " "),
                "lessons": f"{stat.lessons_count}+",
                "questions": f"{stat.questions_count:,}".replace(",", " "),
                "books": f"{stat.books_count} ta"
            }

        return {
            "students": "1 280+",
            "lessons": "194+",
            "questions": "3 650+",
            "books": "12 ta"
        }


# ==========================================================
# KATALOG BO'LIMI API
# ==========================================================
@app.get("/api/catalog/products")
async def get_catalog_products(subject: Optional[str] = None, category: Optional[str] = None):
    sample_products = [
        {
            "id": 1,
            "title": "Tarix: Milliy Sertifikat A+ Intensiv",
            "short_desc": "Barcha davrlar xronologiyasi va qiyin testlar tahlili.",
            "subject": "tarix",
            "category": "ms",
            "price_coin": 150,
            "old_price_coin": 250,
            "rating": 4.9,
            "buyers_count": 420,
            "image_url": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=300&q=80"
        },
        {
            "id": 2,
            "title": "Attestatsiya 2026: Tarix Toifa",
            "short_desc": "Oliy va 1-toifa uchun rasmiy testlar va metodik qo'llanma.",
            "subject": "tarix",
            "category": "attestatsiya",
            "price_coin": 180,
            "old_price_coin": 0,
            "rating": 5.0,
            "buyers_count": 280,
            "image_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=300&q=80"
        },
        {
            "id": 3,
            "title": "Tarix: 6-11 Savol-Javob To'plami",
            "short_desc": "Darsliklardagi barcha atama va sanalar jamlangan bosma kitob.",
            "subject": "tarix",
            "category": "kitoblar",
            "price_coin": 45,
            "old_price_coin": 70,
            "rating": 4.8,
            "buyers_count": 510,
            "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300&q=80"
        },
        {
            "id": 4,
            "title": "Huquqshunoslik: BMBA Asosiy Blok",
            "short_desc": "Konstitutsiya va kodekslar asosidagi yangi testlar bazasi.",
            "subject": "huquq",
            "category": "bmba_asosiy",
            "price_coin": 130,
            "old_price_coin": 190,
            "rating": 4.9,
            "buyers_count": 310,
            "image_url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=300&q=80"
        },
        {
            "id": 5,
            "title": "Harbiy va OTM Psixologik Saralash",
            "short_desc": "Intellekt, barqarorlik va kasbiy yaroqlilik testlari tayyorgarligi.",
            "subject": "psixologiya",
            "category": "otm",
            "price_coin": 100,
            "old_price_coin": 160,
            "rating": 4.9,
            "buyers_count": 195,
            "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=300&q=80"
        }
    ]

    filtered = sample_products
    if subject and subject != "all":
        filtered = [p for p in filtered if p["subject"] == subject]
    if category and category != "all":
        filtered = [p for p in filtered if p["category"] == category]

    return filtered


@app.post("/api/catalog/buy")
async def buy_catalog_product(req: PurchaseRequest):
    user_mock_coins = 50
    product_price = 150

    if user_mock_coins < product_price:
        needed = product_price - user_mock_coins
        return {
            "success": False,
            "status": "insufficient_funds",
            "needed_coins": needed,
            "current_balance": user_mock_coins,
            "message": f"Balansingizda coin yetarli emas! Yana {needed} coin xarid qilishingiz kerak."
        }

    return {
        "success": True,
        "status": "success",
        "new_balance": user_mock_coins - product_price,
        "message": "Xarid muvaffaqiyatli amalga oshirildi! Kurs 'Kabinet' bo'limiga qo'shildi."
    }


# ==========================================================
# MAQSAD BO'LIMI API
# ==========================================================
@app.get("/api/targets/filter-data")
async def get_target_filter_metadata():
    return {
        "directions": [
            "Barcha yo'nalishlar",
            "Tarix (yo'nalishlar bo'yicha)",
            "Yurisprudensiya (Davlat-huquqiy faoliyat)",
            "Xalqaro munosabatlar va Diplomatiya",
            "Harbiy xizmat va qo'mondonlik",
            "Ijtimoiy-gumanitar fanlar"
        ],
        "subjects": [
            "Barcha fanlar",
            "Tarix",
            "Huquqshunoslik",
            "Matematika",
            "Psixologiya",
            "Ona tili va adabiyot"
        ],
        "regions": [
            "Barcha viloyatlar",
            "Toshkent shahri",
            "Toshkent viloyati",
            "Samarqand",
            "Farg'ona",
            "Andijon",
            "Namangan",
            "Buxoro",
            "Xorazm",
            "Qashqadaryo",
            "Surxondaryo",
            "Navoiy",
            "Jizzax",
            "Sirdaryo",
            "Qoraqalpog'iston"
        ]
    }


@app.get("/api/targets/cards")
async def get_target_cards(
    inst_type: str = Query("otm"),
    direction: Optional[str] = None,
    subject: Optional[str] = None,
    region: Optional[str] = None
):
    sample_data = [
        {
            "id": 1,
            "inst_name": "O'zbekiston Milliy Universiteti (O'zMU)",
            "short_name": "O'zMU",
            "inst_type": "otm",
            "region": "Toshkent shahri",
            "direction_title": "Tarix (yo'nalishlar bo'yicha)",
            "subject_main": "Tarix",
            "subject_secondary": "Geografiya",
            "grant_score": 172.5,
            "contract_score": 134.2,
            "quota": 65,
            "mock_quiz_id": 1,
            "badge": "🏛 Fuqarolik OTM"
        },
        {
            "id": 2,
            "inst_name": "Toshkent Davlat Yuridik Universiteti (TDYU)",
            "short_name": "TDYU",
            "inst_type": "otm",
            "region": "Toshkent shahri",
            "direction_title": "Yurisprudensiya (Davlat-huquqiy faoliyat)",
            "subject_main": "Huquqshunoslik",
            "subject_secondary": "Tarix",
            "grant_score": 184.8,
            "contract_score": 156.3,
            "quota": 250,
            "mock_quiz_id": 2,
            "badge": "🏛 Fuqarolik OTM"
        },
        {
            "id": 3,
            "inst_name": "Qurolli Kuchlar Akademiyasi",
            "short_name": "QKA",
            "inst_type": "otm_harbiy",
            "region": "Toshkent shahri",
            "direction_title": "Harbiy xizmat va qo'mondonlik",
            "subject_main": "Tarix",
            "subject_secondary": "Matematika",
            "grant_score": 165.0,
            "contract_score": 0.0,
            "quota": 120,
            "mock_quiz_id": 3,
            "badge": "🎖 Harbiy OTM"
        },
        {
            "id": 4,
            "inst_name": "Temurbeklar Maktabi Harbiy Akademik Litseyi",
            "short_name": "TM Litsey",
            "inst_type": "litsey_harbiy",
            "region": "Farg'ona",
            "direction_title": "Ijtimoiy-gumanitar fanlar",
            "subject_main": "Tarix",
            "subject_secondary": "Psixologiya",
            "grant_score": 162.0,
            "contract_score": 0.0,
            "quota": 100,
            "mock_quiz_id": 4,
            "badge": "🎖 Harbiy Litsey"
        },
        {
            "id": 5,
            "inst_name": "SamDU huzuridagi Akademik Litsey",
            "short_name": "SamDU Litsey",
            "inst_type": "litsey",
            "region": "Samarqand",
            "direction_title": "Ijtimoiy-gumanitar fanlar",
            "subject_main": "Tarix",
            "subject_secondary": "Ona tili va adabiyot",
            "grant_score": 145.5,
            "contract_score": 110.0,
            "quota": 80,
            "mock_quiz_id": 5,
            "badge": "🏫 Fuqarolik Litsey"
        }
    ]

    filtered = [item for item in sample_data if item["inst_type"] == inst_type]

    if direction and direction != "Barcha yo'nalishlar":
        filtered = [item for item in filtered if item["direction_title"] == direction]

    if subject and subject != "Barcha fanlar":
        filtered = [item for item in filtered if item["subject_main"] == subject or item["subject_secondary"] == subject]

    if region and region != "Barcha viloyatlar":
        filtered = [item for item in filtered if item["region"] == region]

    return filtered


# ==========================================================
# KABINET BO'LIMI API
# ==========================================================
@app.get("/api/cabinet/items")
async def get_cabinet_items(telegram_id: int = 12345678, filter_type: str = "active"):
    async with async_session() as session:
        query = select(UserCabinetItem).where(
            UserCabinetItem.telegram_id == telegram_id,
            UserCabinetItem.status == filter_type
        )
        res = await session.execute(query)
        items = res.scalars().all()

        if not items and filter_type == "active":
            return {
                "items": [
                    {
                        "id": 1,
                        "title": "7-sinf O'zbekiston tarixi",
                        "image_url": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=400",
                        "user_rank": "Bilimdon",
                        "days_left": 18,
                        "expire_date": "02.11.2026",
                        "actual_progress": 45,
                        "expected_progress": 65,
                        "course_rank": 8,
                        "last_lesson_id": "7"
                    }
                ]
            }

        now = datetime.utcnow()
        output = []
        for i in items:
            days_left = (i.expires_at - now).days if i.expires_at else 0
            expire_str = i.expires_at.strftime("%d.%m.%Y") if i.expires_at else "-"
            output.append({
                "id": i.id,
                "title": i.title,
                "image_url": i.image_url,
                "user_rank": i.user_rank,
                "days_left": max(0, days_left),
                "expire_date": expire_str,
                "actual_progress": i.actual_progress,
                "expected_progress": i.expected_progress,
                "course_rank": i.course_rank,
                "last_lesson_id": i.last_lesson_id
            })

        return {"items": output}


# ==========================================================
# SERVERNI ISHGA TUSHIRISH (HAR DOIM ENG OXIRIDA TURADI)
# ==========================================================
if __name__ == "__main__":
    uvicorn.run("web.server:app", host="127.0.0.1", port=8080, reload=True)