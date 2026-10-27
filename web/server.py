import os
import sys
import math
import random
from datetime import datetime, date, timedelta
from typing import Optional, List

# Tizim Pythonida uvicorn yo'q: avtomatik loyiha .venv ga o'tamiz
_VENV_PY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"))
_IN_VENV = hasattr(sys, "base_prefix") and sys.prefix != sys.base_prefix
if not _IN_VENV and os.path.isfile(_VENV_PY):
    os.execv(_VENV_PY, [_VENV_PY, "-m", "web.server", *sys.argv[1:]])

import uvicorn
from fastapi import FastAPI, Response, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, or_, update, func
from urllib.parse import urlparse, unquote

# Loyihaning ma'lumotlar bazasi va Aiogram bot importlari
from database.db import async_session, init_db
from database.models import (
    User, UserDevice, UserProgress, News, NewsComment, NewsReaction,
    CoinTransaction, UserDailyActivity, UserFeedback, ExamEvent,
    Notification, UserCoursePace, UserOctagonProfile, Promotion,
    PlatformStats, UserCabinetItem, UserFeedback,
    TargetInstitution, TargetDirection,
    UserSupervisor, SupervisorInvoice,
    OctagonBattle, OctagonBattleAnalysis, OctagonBattleReaction,
    SubjectCatalog, SubjectModule, SubjectWiki, SubjectSchedule,
    SubjectMistakeBank, SubjectCommunityPost, SubjectDiagnosticReport,
    SubjectBook, SubjectQuizLink, UserSubjectEnrollment,
    ExamQuiz, ExamQuestion, ExamRating, ExamSubmission,
    ReferralEarning, UserCourseAccess,
    MasterFactQuestion,
)
import json
from database.regions_data import REGIONS_DATA

import uuid
import secrets

from data.config import BOT_TOKEN, GEMINI_API_KEY, GEMINI_ESSAY_MODEL
from aiogram import Bot
from web.routes.admin_routes import router as admin_router
import asyncio
import re
import base64
import urllib.error
import urllib.request

try:
    import httpx as _httpx
except ImportError:  # serverda paket bo'lmasa ham Mini App ishlashi uchun
    _httpx = None

# 1. FastAPI ilovasini yaratamiz
app = FastAPI(title="PHAROS Education Platform")

# Aiogram bot obyekti (Telegram guruhiga sharhlarni yo'naltirish uchun)
tg_bot = Bot(token=BOT_TOKEN)

# 2. Statik fayllar (JS, CSS, Media) ulanishi
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Admin panel marshrutlari (GET /admin + /api/admin/*)
app.include_router(admin_router)

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


class OctagonInviteSchema(BaseModel):
    telegram_id: int
    subject: str = "tarix"
    level: str = "orta"
    topic: Optional[str] = None
    opponent_id: Optional[int] = None  # Revansh / tanlangan raqib


class OctagonCancelSchema(BaseModel):
    telegram_id: int


class OctagonBotBattleSchema(BaseModel):
    telegram_id: int
    subject: str = "tarix"
    level: str = "orta"
    topic: Optional[str] = None


class OctagonFindOpponentSchema(BaseModel):
    telegram_id: int
    subject: str = "tarix"
    level: str = "orta"
    topic: Optional[str] = None


class OctagonAcceptSchema(BaseModel):
    telegram_id: int
    room_code: str


class OctagonPresenceSchema(BaseModel):
    telegram_id: int
    subject: Optional[str] = None


class OctagonReactionSchema(BaseModel):
    telegram_id: int
    battle_id: int
    emoji: str


class OctagonRematchSchema(BaseModel):
    telegram_id: int
    battle_id: int


class SubjectAskSchema(BaseModel):
    telegram_id: int
    subject_id: int
    content: str
    hashtags: Optional[str] = "#savol"
    user_name: Optional[str] = None


class SubjectResolveMistakeSchema(BaseModel):
    telegram_id: int
    mistake_id: int
    is_correct: bool = True


class SubjectBattleChallengeSchema(BaseModel):
    telegram_id: int
    subject_id: int
    module_id: Optional[int] = None
    level: str = "orta"
    topic: Optional[str] = None


# ==========================================================
# ASOSIY YO'NALISHLAR (ENDPOINTS)
# ==========================================================

OCTAGON_INVITE_TTL_SECONDS = 60
OCTAGON_ONLINE_WINDOW_SECONDS = 120
OCTAGON_BASIC_STICKERS = ["🔥", "😤", "😮", "💪"]
OCTAGON_PRO_STICKERS = ["🏆", "⚡"]
OCTAGON_PREMIUM_STICKERS = ["👑", "💎"]

OCTAGON_TOPIC_COURSE_MAP = {
    "Amir Temur": {"title": "7-sinf: Amir Temur davlati", "link": "lessons", "course_id": 701},
    "Temuriylar": {"title": "7-sinf: Temuriylar saltanati", "link": "lessons", "course_id": 702},
    "Qadimgi dunyo": {"title": "6-sinf: Qadimgi tosh davri", "link": "lessons", "course_id": 601},
    "Milliy uyg'onish": {"title": "9-sinf: Milliy uyg'onish", "link": "lessons", "course_id": 901},
    "Umumiy": {"title": "Tarix: Milliy Sertifikat Ensiklopediyasi", "link": "books", "course_id": 1},
}

def _coerce_telegram_id(telegram_id: Optional[str]) -> Optional[int]:
    """Bo'sh yoki noto'g'ri telegram_id ni 422 o'rniga None ga aylantiradi."""
    if telegram_id is None:
        return None
    value = str(telegram_id).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


# 5. Asosiy sahifa (index.html)
@app.get("/", response_class=HTMLResponse)
async def read_root(response: Response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h3>Shablon fayli topilmadi: {TEMPLATE_PATH}</h3>"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


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
            "balance": int(user.balance if user.balance is not None else (user.coins or 0) or 0),
            "coins": int(user.balance if user.balance is not None else (user.coins or 0) or 0),
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
            bal = int(user.balance if user.balance is not None else (user.coins or 0) or 0)
            return {"status": "warning", "message": "Oferta bonusi allaqachon berilgan!", "balance": bal, "coins": bal}

        user.oferta_accepted = True
        bonus = 20000
        user.balance = int(user.balance or 0) + bonus
        user.coins = int(user.balance or 0)

        tx = CoinTransaction(
            user_id=telegram_id,
            amount=bonus,
            tx_type="oferta",
            description="Oferta shartnomasini imzolaganlik uchun bonus (so'm)"
        )
        session.add(tx)
        await session.commit()

        return {
            "status": "success",
            "message": "Oferta qabul qilindi! +20 000 so'm hisobingizga qo'shildi",
            "balance": int(user.balance or 0),
            "coins": int(user.balance or 0),
        }


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
def _sample_notifications():
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
                "message": "Hisobingizga muvaffaqiyatli +20 000 so'm qo'shildi.",
                "target_tab": "profile",
                "is_read": False,
                "created_at": "Kecha"
            }
        ]
    }


def _sample_course_pace():
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


def _sample_octagon_rank():
    return {
        "course_title": "7-sinf O'zbekiston tarixi",
        "rank": 14,
        "rating": 1250,
        "battles": 8
    }


@app.get("/api/notifications")
async def get_notifications(telegram_id: Optional[str] = None):
    tg_id = _coerce_telegram_id(telegram_id)
    if tg_id is None:
        return _sample_notifications()

    async with async_session() as session:
        query = select(Notification).where(
            or_(Notification.user_id == tg_id, Notification.user_id == None)
        ).order_by(Notification.created_at.desc())

        res = await session.execute(query)
        notifs = res.scalars().all()

        if not notifs:
            return _sample_notifications()

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
async def get_user_course_pace(telegram_id: Optional[str] = None):
    tg_id = _coerce_telegram_id(telegram_id)
    if tg_id is None:
        return _sample_course_pace()

    async with async_session() as session:
        query = select(UserCoursePace).where(
            UserCoursePace.is_active == True,
            UserCoursePace.user_id == tg_id
        )

        res = await session.execute(query)
        paces = res.scalars().all()

        if not paces:
            return _sample_course_pace()

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
async def get_octagon_user_rank(telegram_id: Optional[str] = None):
    tg_id = _coerce_telegram_id(telegram_id)
    if tg_id is None:
        return _sample_octagon_rank()

    async with async_session() as session:
        res = await session.execute(
            select(UserOctagonProfile).where(UserOctagonProfile.user_id == tg_id)
        )
        stat = res.scalar_one_or_none()

        if not stat:
            return _sample_octagon_rank()

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
            "price_coin": 150000,
            "old_price_coin": 250000,
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
            "price_coin": 180000,
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
            "price_coin": 45000,
            "old_price_coin": 70000,
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
            "price_coin": 130000,
            "old_price_coin": 190000,
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
            "price_coin": 100000,
            "old_price_coin": 160000,
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
    user_mock_balance = 50000
    product_price = 150000

    if user_mock_balance < product_price:
        needed = product_price - user_mock_balance
        return {
            "success": False,
            "status": "insufficient_funds",
            "needed_coins": needed,
            "needed_amount": needed,
            "current_balance": user_mock_balance,
            "message": f"Balansingizda mablag' yetarli emas! Yana {needed:,} so'm kerak.".replace(",", " "),
        }

    return {
        "success": True,
        "status": "success",
        "new_balance": user_mock_balance - product_price,
        "message": "Xarid muvaffaqiyatli amalga oshirildi! Kurs 'Kabinet' bo'limiga qo'shildi."
    }


# ==========================================================
# MAQSAD BO'LIMI API
# ==========================================================
_TARGET_TYPES = {"otm", "otm_harbiy", "litsey", "litsey_harbiy"}
_ALL_DIRECTION = "Barcha yo'nalishlar"
_ALL_BLOCK = "Barcha fanlar majmuasi"
_ALL_REGION = "Barcha viloyatlar"
_TARGET_BADGES = {
    "otm": "🏛 Fuqarolik OTM",
    "otm_harbiy": "🎖 Harbiy OTM",
    "litsey": "🏫 Fuqarolik Litsey",
    "litsey_harbiy": "🛡 Harbiy Litsey",
}

# Namunaviy savollar: (matn, variantlar, to'g'ri indeks)
_MOCK_BANKS = {
    "tarix": [
        ("Amir Temur qaysi yilda tavallud topgan?", ["1336-yil", "1342-yil", "1370-yil", "1405-yil"], 0),
        ("Temuriylar davlatining asosiy poytaxti qaysi shahar bo'lgan?", ["Buxoro", "Samarqand", "Hirot", "Xiva"], 1),
        ("Alisher Navoiyning mashhur xamsasi qaysi tilda yozilgan?", ["Arab", "Fors", "Eski o'zbek (turkiy)", "Urdu"], 2),
        ("Jadidchilik harakati namoyandalaridan biri kim?", ["Amir Temur", "Mahmudxo'ja Behbudiy", "Jaloliddin Manguberdi", "Spitamen"], 1),
        ("Buyuk Ipak yo'li asosan nima uchun xizmat qilgan?", ["Harbiy yurish", "Xalqaro savdo va madaniyat", "Diniy marosim", "Suv ta'minoti"], 1),
        ("Amir Temur davlatining dastlabki markazi qaysi shahar?", ["Kesh (Shahrisabz)", "Parij", "Dehli", "Istanbul"], 0),
    ],
    "uzb_tarix": [
        ("O'zbekiston davlat mustaqilligi qachon e'lon qilingan?", ["31-avgust 1991", "1-sentabr 1991", "8-dekabr 1992", "1-iyul 1994"], 1),
        ("O'zbekiston Respublikasining Birinchi Prezidenti kim?", ["Sharof Rashidov", "Islom Karimov", "Abdulla Qodiriy", "Fitrat"], 1),
        ("Davlat tili haqidagi qonun qaysi yilda qabul qilingan?", ["1989", "1991", "1992", "1995"], 0),
        ("Amaldagi Konstitutsiya qachon qabul qilingan?", ["1-sentabr 1991", "8-dekabr 1992", "21-oktabr 1989", "1-yanvar 2000"], 1),
        ("Milliy valyuta — so'm muomalaga qaysi yilda kiritilgan?", ["1991", "1992", "1994", "1998"], 2),
        ("O'zbekiston poytaxti qaysi shahar?", ["Samarqand", "Buxoro", "Toshkent", "Nukus"], 2),
    ],
    "geografiya": [
        ("O'zbekiston poytaxti qaysi shahar?", ["Samarqand", "Toshkent", "Buxoro", "Andijon"], 1),
        ("Qoraqalpog'iston Respublikasi markazi qaysi shahar?", ["Nukus", "Urganch", "Termiz", "Guliston"], 0),
        ("O'zbekiston iqlimi qanday tavsiflanadi?", ["Dengiz iqlimi", "Ekvatorial", "Keskin kontinental", "Musson"], 2),
        ("Mamlakatdagi eng baland nuqta qaysi cho'qqi?", ["Hazrati Sulton", "Chimyon", "Bobotog'", "Nurota"], 0),
        ("Orol dengizi qaysi havzada joylashgan?", ["Kaspiy", "Amudaryo va Sirdaryo", "Zarafshon", "Qashqadaryo"], 1),
        ("Farg'ona vodiysi qaysi davlatlar bilan chegaradosh?", ["Qozog'iston va Turkmaniston", "Qirg'iziston va Tojikiston", "Eron va Afg'oniston", "Rossiya va Xitoy"], 1),
    ],
    "matematika": [
        ("2 + 2 × 2 ifodasining qiymati nechaga teng?", ["6", "8", "4", "10"], 0),
        ("200 sonining 15 foizi nechaga teng?", ["20", "30", "15", "45"], 1),
        ("√144 ning qiymati nechaga teng?", ["11", "12", "14", "16"], 1),
        ("Uchburchak ichki burchaklari yig'indisi necha gradus?", ["90", "120", "180", "360"], 2),
        ("7 ning kvadrati nechaga teng?", ["42", "47", "49", "56"], 2),
        ("2x + 4 = 10 tenglamaning yechimi qaysi?", ["x = 2", "x = 3", "x = 4", "x = 7"], 1),
    ],
    "ona_tili": [
        ("Ot so'z turkumi nimani bildiradi?", ["Harakat", "Narsa va shaxs", "Belgi", "Miqdor"], 1),
        ("O'zbek tilida nechta kelishik bor?", ["4", "5", "6", "8"], 2),
        ("«Kitob» so'zi qaysi so'z turkumi?", ["Ot", "Fe'l", "Sifat", "Ravish"], 0),
        ("Gap boshidagi harf qanday yoziladi?", ["Kichik", "Bosh harf", "Faqat lotin", "Faqat kirill"], 1),
        ("«va» so'zi qanday vazifa bajaradi?", ["Kelishik", "Bog'lovchi", "Yuklama", "Modal so'z"], 1),
        ("Quyidagilardan qaysi biri unli harf?", ["b", "a", "t", "s"], 1),
    ],
    "huquq": [
        ("Davlatning oliy normativ-huquqiy hujjati nima?", ["Farmon", "Konstitutsiya", "Nizom", "Yo'riqnoma"], 1),
        ("O'zbekistonda voyaga yetish yoshi necha?", ["16", "18", "21", "25"], 1),
        ("Sud hokimiyati qanday bo'lishi kerak?", ["Ijro organiga bo'ysunadi", "Mustaqil", "Faqat mahalliy", "Harbiy"], 1),
        ("Davlat tili qaysi?", ["Rus tili", "O'zbek tili", "Ingliz tili", "Fors tili"], 1),
        ("Huquqiy davlatning asosiy belgisi nima?", ["Qonun ustuvorligi", "Faqat kuch", "Yopiq sud", "Tsenzura"], 0),
        ("Fuqaroning asosiy burchaklaridan biri nima?", ["Konstitutsiyaga rioya qilish", "Soliq to'lamaslik", "Sudni rad etish", "Qonunni e'tiborsiz qoldirish"], 0),
    ],
    "chet_tili": [
        ("«Book» so'zining o'zbekcha tarjimasi qaysi?", ["Daftar", "Kitob", "Qalam", "Parta"], 1),
        ("I ___ a student. Bo'sh joyga qaysi so'z tushadi?", ["is", "are", "am", "be"], 2),
        ("«Child» so'zining ko'pligi qanday?", ["childs", "childes", "children", "childrens"], 2),
        ("«Hello» so'zi nima degani?", ["Xayr", "Salom", "Rahmat", "Kechirasiz"], 1),
        ("She ___ English every day.", ["speak", "speaks", "speaking", "spoke"], 1),
        ("Yesterday uchun qaysi zamon ishlatiladi?", ["Present Simple", "Past Simple", "Future Simple", "Present Continuous"], 1),
    ],
    "biologiya": [
        ("Fotosintez qaysi organizmlarga xos?", ["Zamburug'", "O'simlik", "Virus", "Bakteriya spora"], 1),
        ("Irsiy axborot qayerda saqlanadi?", ["DNK", "Suv", "Glyukoza", "Yog'"], 0),
        ("Odam somatik hujayrasida nechta xromosoma bor?", ["23", "44", "46", "48"], 2),
        ("Yurak qaysi tizimga kiradi?", ["Hazm", "Qon aylanish", "Nafas", "Tayanch"], 1),
        ("Mitoxondriya vazifasi nima?", ["Energiya hosil qilish", "Fotosintez", "Hujayra devori", "Rang berish"], 0),
        ("Qizil qon tanachalari nima deb ataladi?", ["Leykotsit", "Trombotsit", "Eritrotsit", "Plazma"], 2),
    ],
    "kimyo": [
        ("Suvning kimyoviy formulasi qaysi?", ["CO2", "H2O", "NaCl", "O2"], 1),
        ("Oltinning kimyoviy belgisi qaysi?", ["Ag", "Fe", "Au", "Cu"], 2),
        ("pH = 7 qanday muhitni bildiradi?", ["Kislotali", "Neytral", "Ishqoriy", "Tuz"], 1),
        ("Kislorodning kimyoviy belgisi qaysi?", ["K", "O", "N", "C"], 1),
        ("NaCl qanday modda?", ["Suv", "Osh tuzi", "Shakar", "Sirka"], 1),
        ("Atom raqami nimani bildiradi?", ["Protonlar soni", "Neytron massasi", "Hajm", "Harorat"], 0),
    ],
    "fizika": [
        ("Tezlik qanday topiladi?", ["massa / vaqt", "masofa / vaqt", "kuch × vaqt", "tok × qarshilik"], 1),
        ("Nyutonning ikkinchi qonuni qaysi?", ["F = ma", "U = IR", "E = mc²", "PV = nRT"], 0),
        ("Elektr toki kuchi birligi nima?", ["Volt", "Om", "Amper", "Joul"], 2),
        ("Om qonuni qaysi ifoda?", ["F = ma", "U = IR", "s = vt", "p = mv"], 1),
        ("Og'irlik kuchi qaysi o'zaro ta'sir?", ["Ishqalanish", "Gravitatsiya", "Magnit", "Yorug'lik"], 1),
        ("Yorug'lik tezligi taxminan qancha?", ["300 km/s", "3 000 km/s", "300 000 km/s", "30 km/s"], 2),
    ],
    "kasbiy": [
        ("Kasbiy (ijodiy) imtihon nimani baholaydi?", ["Faqat yoshni", "Ijodiy qobiliyat va ko'nikmani", "Faqat bo'yni", "Til sertifikatini"], 1),
        ("Portfolio nima?", ["Ishlar to'plami", "Pasport", "Diplom ilovasi", "Tibbiy ma'lumotnoma"], 0),
        ("Eskiz nima?", ["Yakuniy hisobot", "Dastlabki chizma", "Moliyaviy reja", "Imtihon varaqasi"], 1),
        ("Kompozitsiya nimani anglatadi?", ["Elementlarning joylashuvi", "Faqat rang", "Faqat matn", "Hisob-kitob"], 0),
        ("Dizayn loyihasining birinchi bosqichi odatda nima?", ["Chop etish", "G'oya va eskiz", "Sotish", "Arxivlash"], 1),
        ("Ijodiy ishda rang nimaga xizmat qiladi?", ["Kayfiyat va urg'u", "Faqat qog'oz og'irligi", "Imzo", "Shifr"], 0),
    ],
    "generic": [
        ("Ushbu fan bo'yicha testning asosiy maqsadi nima?", ["Yodlash tezligi", "Bilim va ko'nikmani baholash", "Imlo tekshiruvi", "Jismoniy tayyorgarlik"], 1),
        ("To'g'ri javobni tanlashda nimalarga tayaniladi?", ["Taxmin", "Mavzu bo'yicha bilim", "Variant tartibi", "Vaqt"], 1),
        ("Nazorat testida birinchi navbatda nima o'qiladi?", ["Savol sharti", "Oxirgi variant", "Sarlavha osti", "Imzo"], 0),
        ("Agar ikkita variant o'xshash bo'lsa, nima qilish kerak?", ["Birinchisini belgilash", "Shartni qayta o'qib farqni topish", "Bo'sh qoldirish", "Tasodifiy tanlash"], 1),
        ("Test yakunida ball qanday hisoblanadi?", ["Faqat vaqt bo'yicha", "To'g'ri javoblar va koeffitsient bo'yicha", "Sahifa soni bo'yicha", "Tasodifiy"], 1),
        ("Namunaviy sinov nima uchun kerak?", ["Tayyorgarlikni sinash", "Hujjat topshirish", "To'lov qilish", "Kontrakt imzolash"], 0),
    ],
}


def _clean_target_filter(value: Optional[str], sentinel: str) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if not text or text == sentinel:
        return None
    return text


def _safe_inst_type(inst_type: Optional[str]) -> str:
    value = (inst_type or "otm").strip()
    return value if value in _TARGET_TYPES else "otm"


def _canon_subject(name: Optional[str]) -> str:
    raw = (name or "").lower().replace("ʻ", "'").replace("’", "'").replace("`", "'")
    raw = raw.replace("o‘", "o'").replace("g‘", "g'")
    if "huquq" in raw:
        return "huquq"
    if "geograf" in raw:
        return "geografiya"
    if "biolog" in raw:
        return "biologiya"
    if "kimyo" in raw:
        return "kimyo"
    if "fizika" in raw:
        return "fizika"
    if "matemat" in raw:
        return "matematika"
    if "chet til" in raw:
        return "chet_tili"
    if "kasbiy" in raw or "ijodiy" in raw:
        return "kasbiy"
    if "zbekiston tarix" in raw:
        return "uzb_tarix"
    if "ona tili" in raw or "zbek tili" in raw or "adabiyot" in raw:
        return "ona_tili"
    if "tarix" in raw:
        return "tarix"
    return "generic"


def _split_subject_block(block: str):
    parts = [p.strip() for p in (block or "").split(" - ") if p.strip()]
    if parts and parts[-1].upper() == "MB":
        parts = parts[:-1]
    main = parts[0] if parts else "Asosiy fan"
    second = parts[1] if len(parts) > 1 else "2-fan"
    return main, second


def _expand_questions(subject: str, count: int, start_id: int):
    bank = _MOCK_BANKS.get(_canon_subject(subject)) or _MOCK_BANKS["generic"]
    questions = []
    for i in range(count):
        text, options, correct = bank[i % len(bank)]
        cycle = i // len(bank)
        qtext = text if cycle == 0 else f"{text} (variant {cycle + 1})"
        questions.append({
            "id": start_id + i,
            "text": qtext,
            "options": list(options),
            "correct": correct,
        })
    return questions


def _build_mock_payload(ctx: dict):
    main = ctx["subject_main"]
    second = ctx["subject_second"] or "2-fan"
    specs = [
        {"key": "main", "title": main, "kind": "1-asosiy fan", "count": 30, "coeff": 3.1},
        {"key": "second", "title": second, "kind": "2-asosiy fan", "count": 30, "coeff": 2.1},
        {"key": "ona_tili", "title": "Ona tili", "kind": "Majburiy fan", "count": 10, "coeff": 1.1},
        {"key": "matematika", "title": "Matematika", "kind": "Majburiy fan", "count": 10, "coeff": 1.1},
        {"key": "uzb_tarix", "title": "O'zbekiston tarixi", "kind": "Majburiy fan", "count": 10, "coeff": 1.1},
    ]
    blocks = []
    next_id = 1
    total = 0
    max_score = 0.0
    for spec in specs:
        questions = _expand_questions(spec["title"], spec["count"], next_id)
        next_id += len(questions)
        total += spec["count"]
        max_score += spec["count"] * spec["coeff"]
        blocks.append({
            "key": spec["key"],
            "title": spec["title"],
            "kind": spec["kind"],
            "coeff": spec["coeff"],
            "count": spec["count"],
            "questions": questions,
        })
    return {
        "direction_id": ctx.get("direction_id"),
        "title": ctx.get("title") or ctx.get("subject_block"),
        "inst_name": ctx.get("inst_name"),
        "cipher": ctx.get("cipher"),
        "subject_block": ctx.get("subject_block"),
        "subject_main": main,
        "subject_second": second,
        "duration_minutes": 180,
        "question_count": total,
        "max_score": round(max_score, 1),
        "blocks": blocks,
    }


def _split_media_urls(raw: Optional[str]) -> list:
    if not raw:
        return []
    parts = re.split(r"[\n|,;]+", str(raw))
    return [p.strip() for p in parts if p and p.strip()]


def _parse_json_list(raw) -> Optional[list]:
    if not raw:
        return None
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw) if isinstance(raw, str) else None
        return data if isinstance(data, list) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _build_practical_exams(direction: TargetDirection) -> list:
    cached = _parse_json_list(getattr(direction, "practical_exams_json", None))
    if cached is not None:
        return cached
    exams = []
    for n in range(1, 6):
        name = getattr(direction, f"exam{n}_name", None)
        date_raw = getattr(direction, f"exam{n}_date", None)
        criteria = getattr(direction, f"exam{n}_criteria", None)
        mock_url = getattr(direction, f"exam{n}_mock_url", None)
        course_url = getattr(direction, f"exam{n}_course_url", None)
        if not any([name, date_raw, criteria, mock_url, course_url]):
            continue
        exams.append({
            "index": n,
            "name": name or f"{n}-amaliy sinov",
            "date": date_raw or "",
            "criteria": criteria or "",
            "practical_mock_id": getattr(direction, "practical_mock_id", None) or None,
            "practical_mock_url": mock_url or None,
            "practical_course_url": course_url or getattr(direction, "practical_course_url", None) or None,
        })
    return exams


def _build_dates_timeline(inst: TargetInstitution, direction: TargetDirection) -> list:
    cached = _parse_json_list(getattr(direction, "dates_timeline_json", None))
    if cached is not None:
        return cached
    items = []
    if getattr(inst, "admission_date", None):
        items.append({
            "key": "admission",
            "label": "Hujjat topshirish",
            "date": inst.admission_date,
        })
    for n in range(1, 6):
        date_raw = getattr(direction, f"exam{n}_date", None)
        name = getattr(direction, f"exam{n}_name", None)
        if date_raw:
            items.append({
                "key": f"exam{n}",
                "label": name or f"{n}-amaliy imtihon",
                "date": date_raw,
            })
    if getattr(direction, "test_exam_date", None):
        items.append({
            "key": "test_exam",
            "label": "Test sinovi",
            "date": direction.test_exam_date,
        })
    return items


def _direction_card(direction: TargetDirection, inst: TargetInstitution) -> dict:
    grant = direction.grant_ball if direction.grant_ball is not None else direction.grant_score
    contract = direction.contract_ball if direction.contract_ball is not None else direction.contract_score
    second = direction.subject_second or direction.subject_secondary or ""
    third = getattr(direction, "subject_third", None) or ""
    edu_lang = direction.edu_lang or direction.education_lang or ""
    is_litsey = inst.inst_type in {"litsey", "litsey_harbiy"}
    is_military = inst.inst_type in {"litsey_harbiy", "otm_harbiy"}
    gallery_images = _split_media_urls(getattr(inst, "gallery", None))
    practical_exams = _build_practical_exams(direction)
    dates_timeline = _build_dates_timeline(inst, direction)
    catalog_url = getattr(direction, "catalog_courses_url", None) or None
    bundle_url = getattr(direction, "bundle_package_url", None) or catalog_url
    subject_block = direction.subject_block or ""
    if not subject_block:
        bits = [direction.subject_main, second, third if is_litsey else None]
        subject_block = " - ".join(b for b in bits if b)
    return {
        "id": direction.id,
        "inst_name": inst.name,
        "short_name": inst.short_name,
        "inst_type": inst.inst_type,
        "region": inst.region,
        "logo_url": inst.logo_url or "",
        "direction_title": direction.title,
        "cipher": direction.cipher or "",
        "edu_form": direction.edu_form or "",
        "edu_lang": edu_lang,
        "subject_main": direction.subject_main,
        "subject_second": second,
        "subject_third": third,
        "subject_secondary": second,
        "mandatory_subjects": (
            None if is_litsey
            else (direction.mandatory_subjects or "Ona tili, Matematika, O'zbekiston tarixi")
        ),
        "subject_block": subject_block,
        "grant_score": grant or 0,
        "contract_score": contract or 0,
        "grant_ball": grant or 0,
        "contract_ball": contract or 0,
        "badge": _TARGET_BADGES.get(inst.inst_type, "🏛 OTM"),
        "is_litsey": is_litsey,
        "is_military": is_military,
        "gallery_images": gallery_images,
        "gallery": gallery_images,
        "review_video_url": getattr(inst, "video_review_url", None) or None,
        "video_review_url": getattr(inst, "video_review_url", None) or None,
        "overview_text": getattr(inst, "overview_text", None) or None,
        "eligibility_criteria": getattr(inst, "eligibility_criteria", None) or None,
        "career_opportunities": getattr(inst, "opportunities", None) or None,
        "opportunities": getattr(inst, "opportunities", None) or None,
        "admission_info": getattr(inst, "admission_info", None) or None,
        "admission_date": getattr(inst, "admission_date", None) or None,
        "admission_requirements": getattr(inst, "admission_requirements", None) or None,
        "dates_timeline": dates_timeline,
        "practical_exams": practical_exams,
        "subjects_table_image": getattr(direction, "subjects_table_image", None) or None,
        "mock_test_url": getattr(direction, "mock_test_url", None) or None,
        "catalog_courses_url": catalog_url,
        "bundle_package_url": bundle_url,
        "practical_mock_id": getattr(direction, "practical_mock_id", None) or None,
        "practical_course_url": getattr(direction, "practical_course_url", None) or None,
        "test_exam_date": getattr(direction, "test_exam_date", None) or None,
        "exams": {
            f"exam{n}": {
                "date": getattr(direction, f"exam{n}_date", None),
                "name": getattr(direction, f"exam{n}_name", None),
                "criteria": getattr(direction, f"exam{n}_criteria", None),
                "mock_url": getattr(direction, f"exam{n}_mock_url", None),
                "course_url": getattr(direction, f"exam{n}_course_url", None),
            }
            for n in range(1, 6)
        },
    }


def _direction_query(inst_type: str, direction: Optional[str], subject_block: Optional[str], region: Optional[str]):
    stmt = (
        select(TargetDirection, TargetInstitution)
        .join(TargetInstitution, TargetDirection.institution_id == TargetInstitution.id)
        .where(
            TargetInstitution.inst_type == inst_type,
            TargetInstitution.is_active.is_(True),
        )
    )
    direction = _clean_target_filter(direction, _ALL_DIRECTION)
    subject_block = _clean_target_filter(subject_block, _ALL_BLOCK)
    region = _clean_target_filter(region, _ALL_REGION)
    if direction:
        stmt = stmt.where(TargetDirection.title == direction)
    if subject_block:
        stmt = stmt.where(TargetDirection.subject_block == subject_block)
    if region:
        stmt = stmt.where(TargetInstitution.region == region)
    return stmt


# --- Telegram post → real image proxy (lightweight in-memory cache) ---
_TG_IMAGE_CACHE: dict = {}
_TG_IMAGE_CACHE_TTL = 3600  # seconds
_TG_POST_RE = re.compile(
    r"^https?://(?:t\.me|telegram\.me)/(?:s/)?([A-Za-z0-9_]+)/(\d+)/?(?:\?.*)?$",
    re.IGNORECASE,
)
_TG_CDN_HOST_RE = re.compile(
    r"^(?:cdn\d*\.(?:telesco\.pe|telegram-cdn\.org)|(?:www\.)?telegram\.org)$",
    re.IGNORECASE,
)
_TG_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _tg_cache_get(key: str):
    entry = _TG_IMAGE_CACHE.get(key)
    if not entry:
        return None
    if entry["expires"] < datetime.utcnow().timestamp():
        _TG_IMAGE_CACHE.pop(key, None)
        return None
    return entry["value"]


def _tg_cache_set(key: str, value):
    _TG_IMAGE_CACHE[key] = {
        "value": value,
        "expires": datetime.utcnow().timestamp() + _TG_IMAGE_CACHE_TTL,
    }
    # Soft cap — drop oldest half if too large
    if len(_TG_IMAGE_CACHE) > 256:
        ordered = sorted(_TG_IMAGE_CACHE.items(), key=lambda kv: kv[1]["expires"])
        for old_key, _ in ordered[: len(ordered) // 2]:
            _TG_IMAGE_CACHE.pop(old_key, None)


def _parse_telegram_post_url(url: str):
    raw = unquote(str(url or "").strip())
    m = _TG_POST_RE.match(raw)
    if not m:
        return None
    return m.group(1), m.group(2)


def _is_allowed_tg_cdn(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return bool(_TG_CDN_HOST_RE.match(host))


def _pick_tg_cdn_url(candidate: str) -> Optional[str]:
    found = (candidate or "").strip().replace("&amp;", "&")
    if found.startswith("http") and _is_allowed_tg_cdn(found):
        return found
    return None


def _extract_tg_image_from_html(html: str, channel: str = "", post_id: str = "") -> Optional[str]:
    """t.me/s/... sahifasidan aniq postga tegishli rasm URL ni ajratib oladi."""
    if not html:
        return None

    # 1) Aniq post havolasiga bog'langan photo wrap (sahifada bir nechta post bo'ladi)
    if channel and post_id:
        ch = re.escape(channel)
        pid = re.escape(str(post_id))
        post_patterns = [
            rf'<a[^>]+href=["\']https?://t\.me/{ch}/{pid}["\'][^>]*style=["\'][^"\']*background-image:\s*url\([\'"]?([^\'")\s]+)',
            rf'<a[^>]+style=["\'][^"\']*background-image:\s*url\([\'"]?([^\'")\s]+)[^>]*href=["\']https?://t\.me/{ch}/{pid}["\']',
            rf'data-post=["\']{ch}/{pid}["\'][\s\S]{{0,2500}}?background-image:\s*url\([\'"]?([^\'")\s]+)',
        ]
        for pat in post_patterns:
            m = re.search(pat, html, flags=re.IGNORECASE)
            if m:
                picked = _pick_tg_cdn_url(m.group(1))
                if picked:
                    return picked

    # 2) og:image (ba'zan bo'sh bo'ladi)
    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ):
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            picked = _pick_tg_cdn_url(m.group(1))
            if picked:
                return picked

    # 3) Fallback — birinchi CDN rasm
    for pat in (
        r'tgme_widget_message_photo_wrap[^>]+style=["\'][^"\']*background-image:\s*url\([\'"]?([^\'")\s]+)',
        r'<img[^>]+src=["\'](https://cdn\d*\.(?:telesco\.pe|telegram-cdn\.org)/[^"\']+)["\']',
    ):
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            picked = _pick_tg_cdn_url(m.group(1))
            if picked:
                return picked
    return None


async def _http_get_bytes(url: str, timeout: float = 25.0) -> tuple:
    """(status, content_bytes, content_type). httpx yoki urllib."""
    if _httpx is not None:
        async with _httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=_TG_FETCH_HEADERS)
            ctype = resp.headers.get("content-type", "application/octet-stream")
            return resp.status_code, resp.content, ctype

    def _sync_get():
        req = urllib.request.Request(url, headers=_TG_FETCH_HEADERS, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "application/octet-stream")
                return resp.status, data, ctype
        except urllib.error.HTTPError as err:
            try:
                data = err.read()
            except Exception:
                data = b""
            ctype = err.headers.get("Content-Type", "application/octet-stream") if err.headers else "application/octet-stream"
            return err.code, data, ctype

    return await asyncio.to_thread(_sync_get)


async def _resolve_telegram_image_url(post_url: str) -> Optional[str]:
    parsed = _parse_telegram_post_url(post_url)
    if not parsed:
        return None
    channel, post_id = parsed
    cache_key = f"tgimg:{channel}:{post_id}"
    cached = _tg_cache_get(cache_key)
    if cached:
        return cached
    preview_url = f"https://t.me/s/{channel}/{post_id}"
    status, body, _ctype = await _http_get_bytes(preview_url)
    if status >= 400 or not body:
        return None
    try:
        html = body.decode("utf-8", errors="ignore")
    except Exception:
        return None
    image_url = _extract_tg_image_from_html(html, channel=channel, post_id=post_id)
    if image_url:
        _tg_cache_set(cache_key, image_url)
    return image_url


@app.get("/api/media/tg-image")
async def proxy_telegram_image(url: str = Query(..., min_length=8, max_length=512)):
    """
    Telegram ommaviy post (t.me/channel/N) sahifasidan haqiqiy rasmni
    topib, image/jpeg (yoki asl content-type) oqimi sifatida qaytaradi.
    Frontend <img src="/api/media/tg-image?url=..."> orqali ishlatadi.
    """
    post = _parse_telegram_post_url(url)
    if not post:
        raise HTTPException(status_code=400, detail="Faqat t.me / telegram.me post URL qabul qilinadi")

    channel, post_id = post
    bytes_key = f"tgbytes:{channel}:{post_id}"
    cached_bytes = _tg_cache_get(bytes_key)
    if cached_bytes:
        data, ctype = cached_bytes
        return Response(
            content=data,
            media_type=ctype or "image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-TG-Proxy": "cache-hit",
            },
        )

    image_url = await _resolve_telegram_image_url(url)
    if not image_url:
        raise HTTPException(status_code=404, detail="Postdan rasm topilmadi")

    status, data, ctype = await _http_get_bytes(image_url)
    if status >= 400 or not data:
        raise HTTPException(status_code=502, detail="Rasmni yuklab bo'lmadi")

    if not ctype or "text/html" in ctype.lower():
        ctype = "image/jpeg"
    _tg_cache_set(bytes_key, (data, ctype))
    return Response(
        content=data,
        media_type=ctype,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-TG-Proxy": "miss",
        },
    )


@app.get("/api/target/filter-options")
async def get_target_filter_options(inst_type: str = Query("otm")):
    inst_type = _safe_inst_type(inst_type)
    async with async_session() as session:
        directions = (await session.execute(
            select(TargetDirection.title)
            .join(TargetInstitution, TargetDirection.institution_id == TargetInstitution.id)
            .where(TargetInstitution.inst_type == inst_type, TargetInstitution.is_active.is_(True))
            .distinct()
            .order_by(TargetDirection.title)
        )).scalars().all()
        blocks = (await session.execute(
            select(TargetDirection.subject_block)
            .join(TargetInstitution, TargetDirection.institution_id == TargetInstitution.id)
            .where(
                TargetInstitution.inst_type == inst_type,
                TargetInstitution.is_active.is_(True),
                TargetDirection.subject_block.isnot(None),
                TargetDirection.subject_block != "",
            )
            .distinct()
            .order_by(TargetDirection.subject_block)
        )).scalars().all()
        regions = (await session.execute(
            select(TargetInstitution.region)
            .where(TargetInstitution.inst_type == inst_type, TargetInstitution.is_active.is_(True))
            .distinct()
            .order_by(TargetInstitution.region)
        )).scalars().all()
    return {
        "inst_type": inst_type,
        "directions": [d for d in directions if d],
        "subject_blocks": [b for b in blocks if b],
        "regions": [r for r in regions if r],
    }


@app.get("/api/target/directions")
async def get_target_directions(
    inst_type: str = Query("otm"),
    direction: Optional[str] = None,
    subject_block: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    inst_type = _safe_inst_type(inst_type)
    stmt = _direction_query(inst_type, direction, subject_block, region)
    async with async_session() as session:
        total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await session.execute(
            stmt.order_by(TargetInstitution.name, TargetDirection.title, TargetDirection.cipher)
            .offset(offset)
            .limit(limit)
        )).all()
    items = [_direction_card(d, inst) for d, inst in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


@app.get("/api/target/start-mock")
async def start_target_mock(
    inst_type: str = Query("otm"),
    direction_id: Optional[int] = None,
    direction: Optional[str] = None,
    subject_block: Optional[str] = None,
):
    inst_type = _safe_inst_type(inst_type)
    block = _clean_target_filter(subject_block, _ALL_BLOCK)
    title = _clean_target_filter(direction, _ALL_DIRECTION)
    async with async_session() as session:
        if direction_id:
            row = (await session.execute(
                select(TargetDirection, TargetInstitution)
                .join(TargetInstitution, TargetDirection.institution_id == TargetInstitution.id)
                .where(TargetDirection.id == direction_id)
            )).first()
            if not row:
                raise HTTPException(status_code=404, detail="Yo'nalish topilmadi.")
            d, inst = row
            ctx = {
                "direction_id": d.id,
                "title": d.title,
                "inst_name": inst.name,
                "cipher": d.cipher,
                "subject_block": d.subject_block,
                "subject_main": d.subject_main,
                "subject_second": d.subject_second or d.subject_secondary,
            }
            return _build_mock_payload(ctx)

        if block:
            main, second = _split_subject_block(block)
            pretty = title or block
            return _build_mock_payload({
                "direction_id": None,
                "title": pretty,
                "inst_name": None,
                "cipher": None,
                "subject_block": block,
                "subject_main": main,
                "subject_second": second,
            })

        if title:
            found = (await session.execute(
                select(TargetDirection.subject_block, TargetDirection.subject_main, TargetDirection.subject_second)
                .join(TargetInstitution, TargetDirection.institution_id == TargetInstitution.id)
                .where(TargetInstitution.inst_type == inst_type, TargetDirection.title == title)
                .distinct()
            )).all()
            unique_blocks = []
            for item in found:
                if item[0] and item[0] not in unique_blocks:
                    unique_blocks.append(item[0])
            if len(unique_blocks) == 1:
                main, second = _split_subject_block(unique_blocks[0])
                return _build_mock_payload({
                    "direction_id": None,
                    "title": title,
                    "inst_name": None,
                    "cipher": None,
                    "subject_block": unique_blocks[0],
                    "subject_main": found[0][1] or main,
                    "subject_second": found[0][2] or second,
                })

    raise HTTPException(status_code=400, detail="Iltimos, avval Fanlar majmuasini tanlang!")


@app.get("/api/targets/filter-data")
async def get_target_filter_metadata(inst_type: str = Query("otm")):
    data = await get_target_filter_options(inst_type)
    return {
        "directions": [_ALL_DIRECTION, *data["directions"]],
        "subjects": [_ALL_BLOCK, *data["subject_blocks"]],
        "subject_blocks": [_ALL_BLOCK, *data["subject_blocks"]],
        "regions": [_ALL_REGION, *data["regions"]],
    }


@app.get("/api/targets/cards")
async def get_target_cards(
    inst_type: str = Query("otm"),
    direction: Optional[str] = None,
    subject: Optional[str] = None,
    subject_block: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await get_target_directions(
        inst_type=inst_type,
        direction=direction,
        subject_block=subject_block or subject,
        region=region,
        limit=limit,
        offset=offset,
    )


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
# OKTAGON (PVP JANG ZALI) — YORDAMCHI FUNKSIYALAR
# ==========================================================
def _normalize_level(level: Optional[str]) -> str:
    raw = (level or "orta").strip().lower()
    mapping = {
        "oson": "oson",
        "easy": "oson",
        "orta": "orta",
        "o'rta": "orta",
        "oʻrta": "orta",
        "medium": "orta",
        "qiyin": "qiyin",
        "hard": "qiyin",
    }
    return mapping.get(raw, "orta")


def _normalize_subject(subject: Optional[str]) -> str:
    return (subject or "tarix").strip().lower() or "tarix"


def _strip_oct_prefix(room_code: str) -> str:
    code = (room_code or "").strip().upper()
    if code.startswith("OCT_"):
        return code[4:]
    return code


def _generate_room_code() -> str:
    return secrets.token_hex(3).upper()


async def _resolve_bot_username() -> str:
    bot_username = "pharos_talim_bot"
    try:
        me = await tg_bot.get_me()
        if me and me.username:
            bot_username = me.username
    except Exception:
        pass
    return bot_username


def _is_user_online(profile: Optional[UserOctagonProfile], now: Optional[datetime] = None) -> bool:
    if not profile or not profile.last_seen_at:
        return False
    now = now or datetime.utcnow()
    return (now - profile.last_seen_at).total_seconds() <= OCTAGON_ONLINE_WINDOW_SECONDS


async def _get_or_create_octagon_profile(session, user: User) -> UserOctagonProfile:
    res = await session.execute(
        select(UserOctagonProfile).where(UserOctagonProfile.user_id == user.telegram_id)
    )
    profile = res.scalar_one_or_none()
    if profile:
        if not profile.region and user.region:
            profile.region = user.region
        if user.is_subscribed or user.is_paid:
            if profile.subscription_tier == "free":
                profile.subscription_tier = "pro"
        return profile

    tier = "free"
    if user.is_subscribed and user.is_paid:
        tier = "premium"
    elif user.is_subscribed or user.is_paid:
        tier = "pro"

    profile = UserOctagonProfile(
        user_id=user.telegram_id,
        current_course=f"{user.selected_subject or 'tarix'} kursi",
        subject_focus=_normalize_subject(user.selected_subject),
        region=user.region,
        rank_position=99,
        total_battles=0,
        victories=0,
        rating_points=1000,
        subscription_tier=tier,
        last_seen_at=datetime.utcnow(),
    )
    session.add(profile)
    await session.flush()
    return profile


async def _expire_stale_invites(session, now: Optional[datetime] = None):
    now = now or datetime.utcnow()
    res = await session.execute(
        select(OctagonBattle).where(
            OctagonBattle.status == "waiting",
            OctagonBattle.expires_at < now,
        )
    )
    for battle in res.scalars().all():
        battle.status = "expired"


async def _cancel_waiting_invites(session, creator_id: int) -> int:
    res = await session.execute(
        select(OctagonBattle).where(
            OctagonBattle.creator_id == creator_id,
            OctagonBattle.status == "waiting",
        )
    )
    count = 0
    for battle in res.scalars().all():
        battle.status = "cancelled"
        count += 1
    return count


def _stickers_for_tier(tier: str) -> dict:
    basic = list(OCTAGON_BASIC_STICKERS)
    pro = list(OCTAGON_PRO_STICKERS)
    premium = list(OCTAGON_PREMIUM_STICKERS)
    unlocked = list(basic)
    if tier in ("pro", "premium"):
        unlocked.extend(pro)
    if tier == "premium":
        unlocked.extend(premium)
    return {
        "tier": tier or "free",
        "basic": basic,
        "pro": pro,
        "premium": premium,
        "unlocked": unlocked,
    }


def _topic_course_meta(topic_name: str) -> dict:
    meta = OCTAGON_TOPIC_COURSE_MAP.get(topic_name) or OCTAGON_TOPIC_COURSE_MAP["Umumiy"]
    return {
        "recommended_course_id": meta["course_id"],
        "recommended_course_title": meta["title"],
        "recommended_course_link": meta["link"],
    }


async def _build_battle_analyses(session, battle: OctagonBattle, user_id: int, wrong_topics: list):
    for item in wrong_topics:
        topic_name = item["topic"]
        mistakes = int(item.get("mistakes", 1))
        total = max(int(item.get("total", mistakes + 1)), mistakes)
        mastery = round(max(0.0, 100.0 * (total - mistakes) / total), 1)
        course = _topic_course_meta(topic_name)
        session.add(OctagonBattleAnalysis(
            battle_id=battle.id,
            user_id=user_id,
            topic_name=topic_name,
            questions_total=total,
            mistakes_count=mistakes,
            mastery_percent=mastery,
            recommended_course_id=course["recommended_course_id"],
            recommended_course_title=course["recommended_course_title"],
            recommended_course_link=course["recommended_course_link"],
        ))


async def _simulate_and_finish_battle(
    session,
    battle: OctagonBattle,
    creator_profile: UserOctagonProfile,
    opponent_profile: Optional[UserOctagonProfile] = None,
):
    """Demo jang natijasini hisoblab, diagnostika yozuvlarini yaratadi."""
    level_bias = {"oson": 2, "orta": 0, "qiyin": -2}.get(battle.level, 0)
    creator_correct = max(3, min(10, random.randint(5, 9) + level_bias))
    opponent_correct = max(2, min(10, random.randint(4, 9) + (0 if battle.is_bot else level_bias)))
    creator_wrong = 10 - creator_correct
    opponent_wrong = 10 - opponent_correct

    battle.creator_correct = creator_correct
    battle.creator_wrong = creator_wrong
    battle.opponent_correct = opponent_correct
    battle.opponent_wrong = opponent_wrong
    battle.creator_score = creator_correct * 10
    battle.opponent_score = opponent_correct * 10
    battle.status = "finished"
    battle.started_at = battle.started_at or datetime.utcnow()
    battle.finished_at = datetime.utcnow()

    if battle.creator_score > battle.opponent_score:
        battle.winner_id = battle.creator_id
    elif battle.opponent_score > battle.creator_score:
        battle.winner_id = 0 if battle.is_bot else battle.opponent_id
    else:
        battle.winner_id = None

    topic_seed = (battle.topic or "Umumiy").strip() or "Umumiy"
    creator_gaps = [
        {"topic": topic_seed, "mistakes": max(1, creator_wrong // 2 or 1), "total": 4},
        {"topic": "Temuriylar", "mistakes": max(1, creator_wrong // 3 or 1), "total": 3},
    ]
    await _build_battle_analyses(session, battle, battle.creator_id, creator_gaps)

    if battle.opponent_id and not battle.is_bot:
        opp_gaps = [
            {"topic": topic_seed, "mistakes": max(1, opponent_wrong // 2 or 1), "total": 4},
            {"topic": "Qadimgi dunyo", "mistakes": max(1, opponent_wrong // 3 or 1), "total": 3},
        ]
        await _build_battle_analyses(session, battle, battle.opponent_id, opp_gaps)

    creator_profile.total_battles = (creator_profile.total_battles or 0) + 1
    if battle.winner_id == battle.creator_id:
        creator_profile.victories = (creator_profile.victories or 0) + 1
        creator_profile.rating_points = (creator_profile.rating_points or 1000) + 25
    elif battle.winner_id is not None:
        creator_profile.rating_points = max(0, (creator_profile.rating_points or 1000) - 15)

    if opponent_profile and battle.opponent_id:
        opponent_profile.total_battles = (opponent_profile.total_battles or 0) + 1
        if battle.winner_id == battle.opponent_id:
            opponent_profile.victories = (opponent_profile.victories or 0) + 1
            opponent_profile.rating_points = (opponent_profile.rating_points or 1000) + 25
        elif battle.winner_id == battle.creator_id:
            opponent_profile.rating_points = max(0, (opponent_profile.rating_points or 1000) - 15)

    creator_profile.updated_at = datetime.utcnow()
    if opponent_profile:
        opponent_profile.updated_at = datetime.utcnow()


async def _user_brief(session, telegram_id: Optional[int], now: Optional[datetime] = None) -> dict:
    if not telegram_id:
        return {
            "telegram_id": None,
            "full_name": "PHAROS Bot",
            "region": "—",
            "rating": 1200,
            "is_online": True,
            "is_member": False,
            "is_bot": True,
        }

    now = now or datetime.utcnow()
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    profile = (
        await session.execute(
            select(UserOctagonProfile).where(UserOctagonProfile.user_id == telegram_id)
        )
    ).scalar_one_or_none()

    return {
        "telegram_id": telegram_id,
        "full_name": (user.full_name if user else None) or f"O'quvchi {telegram_id}",
        "region": (user.region if user else None) or (profile.region if profile else None) or "Noma'lum",
        "rating": (profile.rating_points if profile else 1000) or 1000,
        "is_online": _is_user_online(profile, now),
        "is_member": user is not None,
        "is_bot": False,
        "subscription_tier": (profile.subscription_tier if profile else "free") or "free",
    }


# ==========================================================
# OKTAGON API ENDPOINTLARI
# ==========================================================
@app.on_event("startup")
async def _octagon_startup():
    try:
        await init_db()
    except Exception as e:
        print(f"Octagon schema init ogohlantirish: {e}")


@app.post("/api/octagon/presence")
async def octagon_presence(payload: OctagonPresenceSchema):
    """Mini App ochiq bo'lganda onlayn heartbeat."""
    async with async_session() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        profile = await _get_or_create_octagon_profile(session, user)
        profile.last_seen_at = datetime.utcnow()
        if payload.subject:
            profile.subject_focus = _normalize_subject(payload.subject)
        profile.updated_at = datetime.utcnow()
        await session.commit()

        stickers = _stickers_for_tier(profile.subscription_tier or "free")
        return {"status": "ok", "is_online": True, "stickers": stickers}


@app.post("/api/octagon/create-invite")
async def octagon_create_invite(payload: OctagonInviteSchema):
    """60 sekundlik duel taklifi va Telegram start havolasini yaratadi."""
    subject = _normalize_subject(payload.subject)
    level = _normalize_level(payload.level)
    topic = (payload.topic or "").strip() or None
    now = datetime.utcnow()

    async with async_session() as session:
        await _expire_stale_invites(session, now)

        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        profile = await _get_or_create_octagon_profile(session, user)
        profile.subject_focus = subject
        profile.last_seen_at = now

        # Yangi taklifdan oldin eski waiting havolalarni bekor qilmaymiz —
        # faqat muddati o'tganlarni expire qilamiz. Bot/jonli jangda cancel-invites chaqiriladi.
        room_code = _generate_room_code()
        while True:
            exists = (
                await session.execute(
                    select(OctagonBattle.id).where(OctagonBattle.room_code == room_code)
                )
            ).scalar_one_or_none()
            if not exists:
                break
            room_code = _generate_room_code()

        battle = OctagonBattle(
            room_code=room_code,
            creator_id=payload.telegram_id,
            opponent_id=payload.opponent_id,
            is_bot=False,
            subject=subject,
            level=level,
            topic=topic,
            status="waiting",
            expires_at=now + timedelta(seconds=OCTAGON_INVITE_TTL_SECONDS),
        )
        session.add(battle)
        await session.commit()
        await session.refresh(battle)

        opponent_info = None
        if payload.opponent_id:
            opponent_info = await _user_brief(session, payload.opponent_id, now)

    bot_username = await _resolve_bot_username()
    invite_link = f"https://t.me/{bot_username}?start=oct_{room_code}"

    return {
        "status": "ok",
        "battle_id": battle.id,
        "room_code": room_code,
        "invite_link": invite_link,
        "expires_in": OCTAGON_INVITE_TTL_SECONDS,
        "expires_at": battle.expires_at.isoformat() + "Z",
        "subject": subject,
        "level": level,
        "topic": topic,
        "opponent": opponent_info,
    }


@app.get("/api/octagon/check-invite/{room_code}")
async def octagon_check_invite(room_code: str, telegram_id: Optional[str] = None):
    """Havola faolligi, 60s muddat va bekor qilinmaganligini tekshiradi."""
    code = _strip_oct_prefix(room_code)
    now = datetime.utcnow()
    viewer_id = _coerce_telegram_id(telegram_id)

    async with async_session() as session:
        await _expire_stale_invites(session, now)
        await session.commit()

        battle = (
            await session.execute(
                select(OctagonBattle).where(OctagonBattle.room_code == code)
            )
        ).scalar_one_or_none()

        if not battle:
            return {
                "valid": False,
                "status": "not_found",
                "message": "Jang xonasi topilmadi",
            }

        if battle.status == "waiting" and battle.expires_at < now:
            battle.status = "expired"
            await session.commit()

        seconds_left = max(0, int((battle.expires_at - now).total_seconds()))
        is_active = battle.status == "waiting" and seconds_left > 0

        creator = await _user_brief(session, battle.creator_id, now)
        opponent = None
        if battle.opponent_id:
            opponent = await _user_brief(session, battle.opponent_id, now)

        return {
            "valid": is_active,
            "status": battle.status if is_active or battle.status != "waiting" else "expired",
            "battle_id": battle.id,
            "room_code": battle.room_code,
            "subject": battle.subject,
            "level": battle.level,
            "topic": battle.topic,
            "expires_at": battle.expires_at.isoformat() + "Z",
            "seconds_left": seconds_left if is_active else 0,
            "creator": creator,
            "opponent": opponent,
            "viewer_is_creator": viewer_id == battle.creator_id if viewer_id else False,
            "message": (
                "Taklif faol" if is_active
                else "Taklif muddati tugagan yoki bekor qilingan"
            ),
        }


@app.post("/api/octagon/accept-invite")
async def octagon_accept_invite(payload: OctagonAcceptSchema):
    """Telegram havolasi orqali jangni qabul qilish."""
    code = _strip_oct_prefix(payload.room_code)
    now = datetime.utcnow()

    async with async_session() as session:
        await _expire_stale_invites(session, now)

        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Avval platformaga ro'yxatdan o'ting")

        battle = (
            await session.execute(
                select(OctagonBattle).where(OctagonBattle.room_code == code)
            )
        ).scalar_one_or_none()
        if not battle:
            raise HTTPException(status_code=404, detail="Jang xonasi topilmadi")

        if battle.creator_id == payload.telegram_id:
            raise HTTPException(status_code=400, detail="O'zingizning taklifingizni qabul qila olmaysiz")

        if battle.status != "waiting" or battle.expires_at < now:
            battle.status = "expired" if battle.status == "waiting" else battle.status
            await session.commit()
            raise HTTPException(status_code=410, detail="Taklif muddati tugagan yoki bekor qilingan")

        profile = await _get_or_create_octagon_profile(session, user)
        creator_user = (
            await session.execute(select(User).where(User.telegram_id == battle.creator_id))
        ).scalar_one_or_none()
        creator_profile = None
        if creator_user:
            creator_profile = await _get_or_create_octagon_profile(session, creator_user)

        battle.opponent_id = payload.telegram_id
        battle.status = "active"
        battle.started_at = now
        profile.last_seen_at = now

        await _simulate_and_finish_battle(session, battle, creator_profile or profile, profile)
        await session.commit()

        try:
            await tg_bot.send_message(
                battle.creator_id,
                f"⚔️ <b>Oktagon:</b> {user.full_name or 'Raqib'} jang chaqirig'ingizni qabul qildi!\n"
                f"Fan: <b>{battle.subject}</b> · Daraja: <b>{battle.level}</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "battle_id": battle.id,
            "result_ready": True,
        }


@app.post("/api/octagon/cancel-invites")
async def octagon_cancel_invites(payload: OctagonCancelSchema):
    """Bot yoki boshqa raqib bilan jang boshlanganda kutishdagi barcha havolalarni bekor qiladi."""
    async with async_session() as session:
        await _expire_stale_invites(session)
        cancelled = await _cancel_waiting_invites(session, payload.telegram_id)
        await session.commit()
    return {"status": "ok", "cancelled_count": cancelled}


@app.get("/api/octagon/history")
async def octagon_history(
    telegram_id: Optional[str] = None,
    subject: Optional[str] = None,
    level: Optional[str] = None,
    region: Optional[str] = None,
):
    """Foydalanuvchi janglar tarixi — fan, daraja va viloyat filtrlari bilan."""
    tg_id = _coerce_telegram_id(telegram_id)
    if tg_id is None:
        return {"items": [], "filters": {"subjects": [], "levels": [], "regions": list(REGIONS_DATA.keys())}}

    now = datetime.utcnow()
    async with async_session() as session:
        await _expire_stale_invites(session, now)
        await session.commit()

        query = select(OctagonBattle).where(
            OctagonBattle.status == "finished",
            or_(
                OctagonBattle.creator_id == tg_id,
                OctagonBattle.opponent_id == tg_id,
            ),
        ).order_by(OctagonBattle.finished_at.desc(), OctagonBattle.id.desc())

        if subject:
            query = query.where(OctagonBattle.subject == _normalize_subject(subject))
        if level:
            query = query.where(OctagonBattle.level == _normalize_level(level))

        battles = (await session.execute(query)).scalars().all()
        items = []

        for b in battles:
            i_am_creator = b.creator_id == tg_id
            my_score = b.creator_score if i_am_creator else b.opponent_score
            opp_score = b.opponent_score if i_am_creator else b.creator_score
            opp_id = b.opponent_id if i_am_creator else b.creator_id

            if b.is_bot and i_am_creator:
                opponent = {
                    "telegram_id": None,
                    "full_name": "PHAROS Bot",
                    "region": "Tizim",
                    "rating": 1200,
                    "is_online": True,
                    "is_member": False,
                    "is_bot": True,
                }
            else:
                opponent = await _user_brief(session, opp_id, now)

            if region and region != "all":
                opp_region = (opponent.get("region") or "").lower()
                if region.lower() not in opp_region and opp_region not in region.lower():
                    continue

            if b.winner_id is None:
                outcome = "draw"
            elif b.winner_id == tg_id:
                outcome = "win"
            else:
                outcome = "loss"

            items.append({
                "battle_id": b.id,
                "subject": b.subject,
                "level": b.level,
                "topic": b.topic,
                "outcome": outcome,
                "my_score": my_score,
                "opponent_score": opp_score,
                "my_correct": b.creator_correct if i_am_creator else b.opponent_correct,
                "my_wrong": b.creator_wrong if i_am_creator else b.opponent_wrong,
                "opponent": opponent,
                "is_bot": b.is_bot,
                "finished_at": b.finished_at.strftime("%d.%m.%Y %H:%M") if b.finished_at else "",
                "can_rematch": not b.is_bot and bool(opp_id),
            })

        return {
            "items": items,
            "filters": {
                "subjects": ["tarix", "huquq", "psixologiya", "ona tili"],
                "levels": ["oson", "orta", "qiyin"],
                "regions": ["all"] + list(REGIONS_DATA.keys()),
            },
        }


@app.get("/api/octagon/leaderboard")
async def octagon_leaderboard(
    subject: Optional[str] = None,
    level: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Viloyat / fan / umumiy reyting peshqadamlari."""
    async with async_session() as session:
        query = select(UserOctagonProfile).order_by(
            UserOctagonProfile.rating_points.desc(),
            UserOctagonProfile.victories.desc(),
        )

        if subject:
            query = query.where(UserOctagonProfile.subject_focus == _normalize_subject(subject))
        if region and region != "all":
            query = query.where(UserOctagonProfile.region == region)

        profiles = (await session.execute(query.limit(limit))).scalars().all()
        leaders = []

        if not profiles:
            # Demo peshqadamlar (bo'sh bazada UI sinovi uchun)
            sample = [
                {"full_name": "Sardor Karimov", "region": "Toshkent shahri", "rating": 1480, "victories": 24, "subject": "tarix"},
                {"full_name": "Dilnoza Rahimova", "region": "Samarqand viloyati", "rating": 1410, "victories": 19, "subject": "tarix"},
                {"full_name": "Javohir Aliyev", "region": "Farg'ona viloyati", "rating": 1365, "victories": 17, "subject": "huquq"},
                {"full_name": "Madina Yusupova", "region": "Buxoro viloyati", "rating": 1320, "victories": 15, "subject": "tarix"},
                {"full_name": "Bekzod Toshpulatov", "region": "Andijon viloyati", "rating": 1288, "victories": 14, "subject": "psixologiya"},
            ]
            for idx, row in enumerate(sample, start=1):
                if subject and row["subject"] != _normalize_subject(subject):
                    continue
                if region and region != "all" and row["region"] != region:
                    continue
                leaders.append({
                    "rank": idx,
                    "full_name": row["full_name"],
                    "region": row["region"],
                    "rating": row["rating"],
                    "victories": row["victories"],
                    "subject": row["subject"],
                    "is_online": idx <= 2,
                })
            return {"items": leaders[:limit], "mode": "sample"}

        for idx, p in enumerate(profiles, start=1):
            user = (
                await session.execute(select(User).where(User.telegram_id == p.user_id))
            ).scalar_one_or_none()
            leaders.append({
                "rank": idx,
                "telegram_id": p.user_id,
                "full_name": (user.full_name if user else None) or f"O'quvchi {p.user_id}",
                "region": p.region or (user.region if user else None) or "Noma'lum",
                "rating": p.rating_points or 1000,
                "victories": p.victories or 0,
                "subject": p.subject_focus or "tarix",
                "is_online": _is_user_online(p),
            })

        return {"items": leaders, "mode": "live"}


@app.post("/api/octagon/start-bot")
async def octagon_start_bot(payload: OctagonBotBattleSchema):
    """Bot bilan bellashuv — avvalgi takliflarni bekor qiladi va jangni yakunlaydi."""
    subject = _normalize_subject(payload.subject)
    level = _normalize_level(payload.level)
    topic = (payload.topic or "").strip() or "Umumiy mashq"
    now = datetime.utcnow()

    async with async_session() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        profile = await _get_or_create_octagon_profile(session, user)
        cancelled = await _cancel_waiting_invites(session, payload.telegram_id)

        battle = OctagonBattle(
            room_code=_generate_room_code(),
            creator_id=payload.telegram_id,
            opponent_id=None,
            is_bot=True,
            subject=subject,
            level=level,
            topic=topic,
            status="active",
            expires_at=now,
            started_at=now,
        )
        session.add(battle)
        await session.flush()

        await _simulate_and_finish_battle(session, battle, profile, None)
        profile.last_seen_at = now
        profile.subject_focus = subject
        await session.commit()

        return {
            "status": "ok",
            "battle_id": battle.id,
            "cancelled_invites": cancelled,
            "result_ready": True,
        }


@app.post("/api/octagon/find-opponent")
async def octagon_find_opponent(payload: OctagonFindOpponentSchema):
    """Jonli PvP: shu fanni o'rganayotgan onlayn o'quvchini topadi."""
    subject = _normalize_subject(payload.subject)
    level = _normalize_level(payload.level)
    topic = (payload.topic or "").strip() or None
    now = datetime.utcnow()
    online_since = now - timedelta(seconds=OCTAGON_ONLINE_WINDOW_SECONDS)

    async with async_session() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        my_profile = await _get_or_create_octagon_profile(session, user)
        my_profile.last_seen_at = now
        my_profile.subject_focus = subject

        cancelled = await _cancel_waiting_invites(session, payload.telegram_id)

        candidates = (
            await session.execute(
                select(UserOctagonProfile).where(
                    UserOctagonProfile.user_id != payload.telegram_id,
                    UserOctagonProfile.subject_focus == subject,
                    UserOctagonProfile.last_seen_at >= online_since,
                ).order_by(UserOctagonProfile.rating_points.desc()).limit(20)
            )
        ).scalars().all()

        if not candidates:
            await session.commit()
            return {
                "status": "not_found",
                "message": "Hozircha onlayn raqib topilmadi. Bot bilan o'ynang yoki do'stga havola yuboring.",
                "cancelled_invites": cancelled,
            }

        # Reytingga eng yaqin raqib
        candidates = sorted(
            candidates,
            key=lambda p: abs((p.rating_points or 1000) - (my_profile.rating_points or 1000)),
        )
        opp_profile = candidates[0]
        opp_user = (
            await session.execute(select(User).where(User.telegram_id == opp_profile.user_id))
        ).scalar_one_or_none()

        battle = OctagonBattle(
            room_code=_generate_room_code(),
            creator_id=payload.telegram_id,
            opponent_id=opp_profile.user_id,
            is_bot=False,
            subject=subject,
            level=level,
            topic=topic,
            status="active",
            expires_at=now,
            started_at=now,
        )
        session.add(battle)
        await session.flush()

        await _simulate_and_finish_battle(session, battle, my_profile, opp_profile)
        await session.commit()

        # Raqibga bot xabarnomasi
        try:
            await tg_bot.send_message(
                opp_profile.user_id,
                f"⚔️ <b>Oktagon chaqiruvi!</b>\n"
                f"{user.full_name or 'Raqib'} siz bilan jonli jang boshladi.\n"
                f"Fan: <b>{subject}</b> · Daraja: <b>{level}</b>"
                + (f"\nMavzu: <b>{topic}</b>" if topic else ""),
                parse_mode="HTML",
            )
        except Exception:
            pass

        session.add(Notification(
            user_id=opp_profile.user_id,
            source="oktagon",
            title="Oktagon: Jonli jang!",
            message=f"{user.full_name or 'Raqib'} sizni jangga chaqirdi ({subject}, {level}).",
            target_tab="octagon",
            is_read=False,
        ))
        await session.commit()

        return {
            "status": "ok",
            "battle_id": battle.id,
            "cancelled_invites": cancelled,
            "opponent": await _user_brief(session, opp_profile.user_id, now),
            "result_ready": True,
        }


@app.get("/api/octagon/battle-result/{battle_id}")
async def octagon_battle_result(battle_id: int, telegram_id: Optional[str] = None):
    """G'olib/mag'lub, ochkolar va kamchiliklar diagnostikasi + kurs havolalari."""
    tg_id = _coerce_telegram_id(telegram_id)
    now = datetime.utcnow()

    async with async_session() as session:
        battle = await session.get(OctagonBattle, battle_id)
        if not battle:
            raise HTTPException(status_code=404, detail="Jang topilmadi")

        analyses_q = select(OctagonBattleAnalysis).where(OctagonBattleAnalysis.battle_id == battle_id)
        if tg_id:
            analyses_q = analyses_q.where(OctagonBattleAnalysis.user_id == tg_id)
        analyses = (await session.execute(analyses_q)).scalars().all()

        i_am_creator = tg_id == battle.creator_id if tg_id else True
        my_score = battle.creator_score if i_am_creator else battle.opponent_score
        opp_score = battle.opponent_score if i_am_creator else battle.creator_score
        my_correct = battle.creator_correct if i_am_creator else battle.opponent_correct
        my_wrong = battle.creator_wrong if i_am_creator else battle.opponent_wrong

        if battle.winner_id is None:
            outcome = "draw"
            winner_label = "Durang"
        elif tg_id and battle.winner_id == tg_id:
            outcome = "win"
            winner_label = "Siz g'alaba qozondingiz!"
        elif battle.is_bot and battle.winner_id == 0:
            outcome = "loss"
            winner_label = "PHAROS Bot g'olib"
        elif tg_id and battle.winner_id != tg_id:
            outcome = "loss"
            winner_label = "Raqib g'olib"
        else:
            outcome = "finished"
            winner_label = "Jang yakunlandi"

        if battle.is_bot:
            opponent = {
                "full_name": "PHAROS Bot",
                "region": "Tizim",
                "rating": 1200,
                "is_bot": True,
                "is_online": True,
            }
        else:
            opp_id = battle.opponent_id if i_am_creator else battle.creator_id
            opponent = await _user_brief(session, opp_id, now)

        gaps = [
            {
                "topic": a.topic_name,
                "questions_total": a.questions_total,
                "mistakes_count": a.mistakes_count,
                "mastery_percent": a.mastery_percent,
                "course_id": a.recommended_course_id,
                "course_title": a.recommended_course_title,
                "course_link": a.recommended_course_link or "lessons",
            }
            for a in analyses
        ]

        return {
            "battle_id": battle.id,
            "subject": battle.subject,
            "level": battle.level,
            "topic": battle.topic,
            "outcome": outcome,
            "winner_label": winner_label,
            "my_score": my_score,
            "opponent_score": opp_score,
            "my_correct": my_correct,
            "my_wrong": my_wrong,
            "opponent": opponent,
            "gaps": gaps,
            "finished_at": battle.finished_at.strftime("%d.%m.%Y %H:%M") if battle.finished_at else "",
        }


@app.post("/api/octagon/send-reaction")
async def octagon_send_reaction(payload: OctagonReactionSchema):
    """Jang ichidagi stiker/reaksiya — tarifga qarab cheklanadi."""
    emoji = (payload.emoji or "").strip()
    if not emoji:
        raise HTTPException(status_code=400, detail="Stiker tanlanmagan")

    async with async_session() as session:
        battle = await session.get(OctagonBattle, payload.battle_id)
        if not battle:
            raise HTTPException(status_code=404, detail="Jang topilmadi")

        if payload.telegram_id not in (battle.creator_id, battle.opponent_id or -1):
            raise HTTPException(status_code=403, detail="Bu jangga tegishli emassiz")

        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        profile = await _get_or_create_octagon_profile(session, user)
        stickers = _stickers_for_tier(profile.subscription_tier or "free")

        if emoji not in stickers["unlocked"]:
            raise HTTPException(
                status_code=403,
                detail="Bu stiker faqat Pro/Premium obunachilar uchun",
            )

        is_premium = emoji in (OCTAGON_PRO_STICKERS + OCTAGON_PREMIUM_STICKERS)
        session.add(OctagonBattleReaction(
            battle_id=battle.id,
            user_id=payload.telegram_id,
            emoji=emoji,
            is_premium=is_premium,
        ))
        await session.commit()

        # Raqibga real-time xabar (agar odam bo'lsa)
        target_id = battle.opponent_id if payload.telegram_id == battle.creator_id else battle.creator_id
        if target_id and not battle.is_bot:
            try:
                await tg_bot.send_message(
                    target_id,
                    f"Oktagon reaksiya: {emoji}",
                )
            except Exception:
                pass

        return {"status": "ok", "emoji": emoji, "is_premium": is_premium}


@app.post("/api/octagon/rematch")
async def octagon_rematch(payload: OctagonRematchSchema):
    """Yutqazilgan jang uchun revansh: onlayn bo'lsa xabar, aks holda ulashish havolasi."""
    now = datetime.utcnow()

    async with async_session() as session:
        battle = await session.get(OctagonBattle, payload.battle_id)
        if not battle or battle.status != "finished":
            raise HTTPException(status_code=404, detail="Jang topilmadi")

        if payload.telegram_id not in (battle.creator_id, battle.opponent_id or -1):
            raise HTTPException(status_code=403, detail="Bu jangga tegishli emassiz")

        if battle.is_bot:
            raise HTTPException(status_code=400, detail="Bot bilan revansh uchun yangi bot jangini boshlang")

        opp_id = battle.opponent_id if payload.telegram_id == battle.creator_id else battle.creator_id
        if not opp_id:
            raise HTTPException(status_code=400, detail="Raqib topilmadi")

        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        await _get_or_create_octagon_profile(session, user)
        opp_brief = await _user_brief(session, opp_id, now)

        room_code = _generate_room_code()
        invite = OctagonBattle(
            room_code=room_code,
            creator_id=payload.telegram_id,
            opponent_id=opp_id,
            is_bot=False,
            subject=battle.subject,
            level=battle.level,
            topic=battle.topic,
            status="waiting",
            expires_at=now + timedelta(seconds=OCTAGON_INVITE_TTL_SECONDS),
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)

        bot_username = await _resolve_bot_username()
        invite_link = f"https://t.me/{bot_username}?start=oct_{room_code}"
        notified = False

        if opp_brief.get("is_online") and opp_brief.get("is_member"):
            try:
                await tg_bot.send_message(
                    opp_id,
                    f"🔁 <b>Revansh chaqiruvi!</b>\n"
                    f"{user.full_name or 'Raqib'} qayta bellashuvga chaqiryapti.\n"
                    f"Fan: <b>{battle.subject}</b> · Daraja: <b>{battle.level}</b>\n"
                    f"Havola (60 soniya): {invite_link}",
                    parse_mode="HTML",
                )
                notified = True
            except Exception:
                notified = False

            session.add(Notification(
                user_id=opp_id,
                source="oktagon",
                title="Oktagon: Revansh!",
                message=f"{user.full_name or 'Raqib'} sizni qayta jangga chaqirdi.",
                target_tab="octagon",
                is_read=False,
            ))
            await session.commit()

        return {
            "status": "ok",
            "battle_id": invite.id,
            "room_code": room_code,
            "invite_link": invite_link,
            "expires_in": OCTAGON_INVITE_TTL_SECONDS,
            "opponent_online": bool(opp_brief.get("is_online")),
            "notified": notified,
            "opponent": opp_brief,
        }


# ==========================================================
# FAN TIZIMI VA O'QUV PANELI (SUBJECT DASHBOARD)
# ==========================================================
SUBJECT_RANK_THRESHOLDS = (
    (90, "Grossmeyster"),
    (70, "Ustoz"),
    (40, "Bilimdon"),
    (0, "Shogird"),
)


def _subject_rank_from_progress(actual: int) -> str:
    for threshold, label in SUBJECT_RANK_THRESHOLDS:
        if actual >= threshold:
            return label
    return "Shogird"


def _pace_status(actual: int, expected: int) -> str:
    """ahead | on_track | slightly_behind | behind"""
    diff = actual - expected
    if diff >= 5:
        return "ahead"
    if diff >= -5:
        return "on_track"
    if diff >= -15:
        return "slightly_behind"
    return "behind"


def _pace_color(status: str) -> str:
    return {
        "ahead": "#10B981",
        "on_track": "#10B981",
        "slightly_behind": "#F59E0B",
        "behind": "#EF4444",
    }.get(status, "#10B981")


async def _ensure_subject_seed(session) -> SubjectCatalog:
    """Demo fan + bog'liq ma'lumotlarni bir marta seed qiladi."""
    existing = (
        await session.execute(select(SubjectCatalog).where(SubjectCatalog.code == "tarix"))
    ).scalar_one_or_none()
    if existing:
        return existing

    subject = SubjectCatalog(
        code="tarix",
        title="O'zbekiston tarixi",
        description="Tematik-taqvimiy dastur, wiki, battle va diagnostika bilan to'liq fan paneli.",
        image_url="https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=600",
        is_active=True,
    )
    session.add(subject)
    await session.flush()

    modules = [
        SubjectModule(
            subject_id=subject.id, title="6-sinf O'zbekiston tarixi",
            description="Qadimgi davrdan ilk o'rta asrlargacha", grade_level="6-sinf",
            order_num=1, price_coin=80, old_price_coin=120, is_standalone=True,
            image_url="https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=400",
        ),
        SubjectModule(
            subject_id=subject.id, title="7-sinf O'zbekiston tarixi",
            description="Amir Temur va Temuriylar davri", grade_level="7-sinf",
            order_num=2, price_coin=90, old_price_coin=140, is_standalone=True,
            image_url="https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400",
        ),
        SubjectModule(
            subject_id=subject.id, title="Milliy sertifikat: Tarix",
            description="MS uchun to'liq modul", grade_level="MS",
            order_num=3, price_coin=150, old_price_coin=220, is_standalone=True,
            image_url="https://images.unsplash.com/photo-1456513080080-7e9c7c9f6e0a?w=400",
        ),
    ]
    session.add_all(modules)
    await session.flush()

    wiki_rows = [
        SubjectWiki(
            subject_id=subject.id, term="Amir Temur", concept_type="shaxs",
            definition="Sohibqiron Amir Temur (1336–1405) — Movarounnahr hukmdori, Temuriylar saltanati asoschisi.",
            source_book="7-sinf O'zbekiston tarixi", grade_level="7-sinf",
            topic_title="Amir Temur davlati",
        ),
        SubjectWiki(
            subject_id=subject.id, term="1370-yil", concept_type="sana",
            definition="Amir Temur Movarounnahrning yagona hukmdori deb e'lon qilingan yil.",
            source_book="7-sinf O'zbekiston tarixi", grade_level="7-sinf",
            topic_title="Davlatning shakllanishi",
        ),
        SubjectWiki(
            subject_id=subject.id, term="Tuzukot", concept_type="qoida",
            definition="Amir Temur davlat boshqaruvi qoidalari to'plami — Tuzukot (Temur tuzuklari).",
            source_book="Ma'lumotnoma: Temuriylar", grade_level="7-sinf",
            topic_title="Davlat boshqaruvi",
        ),
        SubjectWiki(
            subject_id=subject.id, term="Movarounnahr", concept_type="atama",
            definition="Amudaryo va Sirdaryo oralig'idagi tarixiy geografik mintaqa.",
            source_book="6-sinf O'zbekiston tarixi", grade_level="6-sinf",
            topic_title="Geografik tushunchalar",
        ),
        SubjectWiki(
            subject_id=subject.id, term="Markazlashgan davlat", concept_type="nazariya",
            definition="Yagona hukmronlik ostida birlashtirilgan, markaziy boshqaruvga ega davlat shakli.",
            source_book="Tarix nazariyasi qo'llanmasi", grade_level="MS",
            topic_title="Davlatshunoslik",
        ),
    ]
    session.add_all(wiki_rows)

    schedule_rows = [
        SubjectSchedule(
            subject_id=subject.id, module_id=modules[1].id, order_num=1,
            topic_title="Amir Temurning kelib chiqishi",
            planned_date=date.today() - timedelta(days=21),
            video_url="https://www.w3schools.com/html/mov_bbb.mp4", test_score_avg=78.0,
        ),
        SubjectSchedule(
            subject_id=subject.id, module_id=modules[1].id, order_num=2,
            topic_title="1370-yil: yagona hukmdorlik",
            planned_date=date.today() - timedelta(days=14),
            video_url="https://www.w3schools.com/html/mov_bbb.mp4", test_score_avg=65.0,
        ),
        SubjectSchedule(
            subject_id=subject.id, module_id=modules[1].id, order_num=3,
            topic_title="Loy jangi (1365)",
            planned_date=date.today() - timedelta(days=7),
            video_url="https://www.w3schools.com/html/mov_bbb.mp4", test_score_avg=None,
        ),
        SubjectSchedule(
            subject_id=subject.id, module_id=modules[1].id, order_num=4,
            topic_title="Temur tuzuklari",
            planned_date=date.today() + timedelta(days=3),
            video_url="https://www.w3schools.com/html/mov_bbb.mp4", test_score_avg=None,
        ),
        SubjectSchedule(
            subject_id=subject.id, module_id=modules[1].id, order_num=5,
            topic_title="Temuriylar me'morchiligi",
            planned_date=date.today() + timedelta(days=10),
            video_url="https://www.w3schools.com/html/mov_bbb.mp4", test_score_avg=None,
        ),
    ]
    session.add_all(schedule_rows)

    session.add_all([
        SubjectBook(
            subject_id=subject.id, module_id=modules[1].id,
            title="7-sinf O'zbekiston tarixi (elektron)",
            book_type="darslik",
            cover_url="https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=300",
            viewer_url="https://www.w3schools.com/html/mov_bbb.mp4",
            is_downloadable=False,
        ),
        SubjectBook(
            subject_id=subject.id, module_id=modules[1].id,
            title="Temuriylar ma'lumotnomasi",
            book_type="malumotnoma",
            cover_url="https://images.unsplash.com/photo-1512820790803-83ca734da794?w=300",
            viewer_url="https://www.w3schools.com/html/mov_bbb.mp4",
            is_downloadable=False,
        ),
        SubjectBook(
            subject_id=subject.id,
            title="Tarix savolnomasi (MS)",
            book_type="savolnoma",
            cover_url="https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=300",
            viewer_url="https://www.w3schools.com/html/mov_bbb.mp4",
            is_downloadable=False,
        ),
    ])

    session.add_all([
        SubjectQuizLink(
            subject_id=subject.id, module_id=modules[1].id,
            title="Bob 1: Amir Temur davlati", scope="bob", quiz_id=1,
            is_paid=False, price_coin=0,
        ),
        SubjectQuizLink(
            subject_id=subject.id, module_id=modules[1].id,
            title="7-sinf yakuniy test", scope="modul", quiz_id=2,
            is_paid=True, price_coin=25,
        ),
        SubjectQuizLink(
            subject_id=subject.id, title="Fan bo'yicha umumiy test",
            scope="fan", quiz_id=3, is_paid=True, price_coin=40,
        ),
    ])

    session.add(SubjectDiagnosticReport(
        user_id=12345678, subject_id=subject.id, quiz_id=1,
        quiz_title="Bob 1: Amir Temur davlati",
        video_review_url="https://www.w3schools.com/html/mov_bbb.mp4",
        analysis_text="Umumiy natija o'rtacha. Asosiy tushunchalar o'zlashtirilgan, ammo sanalar va janglar xronologiyasida bo'shliqlar bor.",
        strengths_text="• Amir Temur shaxsiyati va davlat tuzumi yaxshi bilingan.\n• Tuzukot tushunchasi aniq javoblangan.",
        weaknesses_text="• 1365-yil Loy jangi sanasi chalkashtirilgan.\n• Poytaxt shaharlari ketma-ketligi zaif.",
        sources_json=json.dumps([
            {"title": "7-sinf O'zbekiston tarixi, Bob 2", "url": "https://edu.uz"},
            {"title": "Temur tuzuklari (tarjima)", "url": "https://ziyouz.com"},
        ], ensure_ascii=False),
    ))

    await session.commit()
    return subject


async def _get_or_create_enrollment(session, telegram_id: int, subject: SubjectCatalog) -> UserSubjectEnrollment:
    row = (
        await session.execute(
            select(UserSubjectEnrollment).where(
                UserSubjectEnrollment.user_id == telegram_id,
                UserSubjectEnrollment.subject_id == subject.id,
            )
        )
    ).scalar_one_or_none()
    if row:
        return row

    enrollment = UserSubjectEnrollment(
        user_id=telegram_id,
        subject_id=subject.id,
        status="active",
        rank_label="Bilimdon",
        actual_progress=45,
        expected_progress=65,
        current_schedule_id=None,
    )
    session.add(enrollment)
    await session.flush()
    return enrollment


@app.get("/api/subject-dashboard/my-subjects")
async def subject_dashboard_my_subjects(telegram_id: int = 12345678):
    """O'quvchining faol/yakunlangan fanlari, status va reja liniyasi."""
    async with async_session() as session:
        subject = await _ensure_subject_seed(session)
        enrollment = await _get_or_create_enrollment(session, telegram_id, subject)

        # Kabinetdan qo'shimcha kurslarni ham fan sifatida ko'rsatish
        cab_items = (
            await session.execute(
                select(UserCabinetItem).where(
                    UserCabinetItem.telegram_id == telegram_id,
                    UserCabinetItem.status.in_(["active", "archive"]),
                )
            )
        ).scalars().all()

        subjects_out = []
        pace = _pace_status(enrollment.actual_progress, enrollment.expected_progress)
        subjects_out.append({
            "subject_id": subject.id,
            "code": subject.code,
            "title": subject.title,
            "image_url": subject.image_url,
            "enrollment_status": enrollment.status,
            "rank_label": enrollment.rank_label or _subject_rank_from_progress(enrollment.actual_progress),
            "actual_progress": enrollment.actual_progress,
            "expected_progress": enrollment.expected_progress,
            "pace_status": pace,
            "pace_color": _pace_color(pace),
            "is_primary": True,
        })

        for item in cab_items:
            # Takrorlanmasligi uchun faqat boshqa nomlarni qo'shamiz
            if item.title and subject.title.lower() in (item.title or "").lower():
                continue
            item_pace = _pace_status(item.actual_progress or 0, item.expected_progress or 0)
            subjects_out.append({
                "subject_id": subject.id,
                "cabinet_item_id": item.id,
                "code": subject.code,
                "title": item.title,
                "image_url": item.image_url or subject.image_url,
                "enrollment_status": "completed" if item.status == "archive" else "active",
                "rank_label": item.user_rank or "Shogird",
                "actual_progress": item.actual_progress or 0,
                "expected_progress": item.expected_progress or 0,
                "pace_status": item_pace,
                "pace_color": _pace_color(item_pace),
                "is_primary": False,
            })

        await session.commit()
        return {"subjects": subjects_out, "count": len(subjects_out)}


@app.get("/api/subject-dashboard/overview")
async def subject_dashboard_overview(subject_id: int, telegram_id: int = 12345678):
    """Tanlangan fan uchun sarlavha, status, progress va navigatsiya meta."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        subject = (
            await session.execute(select(SubjectCatalog).where(SubjectCatalog.id == subject_id))
        ).scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=404, detail="Fan topilmadi")

        enrollment = await _get_or_create_enrollment(session, telegram_id, subject)
        pace = _pace_status(enrollment.actual_progress, enrollment.expected_progress)
        modules_count = (
            await session.execute(
                select(func.count()).select_from(SubjectModule).where(
                    SubjectModule.subject_id == subject_id, SubjectModule.is_active == True
                )
            )
        ).scalar() or 0

        await session.commit()
        return {
            "subject_id": subject.id,
            "code": subject.code,
            "title": subject.title,
            "description": subject.description,
            "image_url": subject.image_url,
            "rank_label": enrollment.rank_label or _subject_rank_from_progress(enrollment.actual_progress),
            "actual_progress": enrollment.actual_progress,
            "expected_progress": enrollment.expected_progress,
            "pace_status": pace,
            "pace_color": _pace_color(pace),
            "enrollment_status": enrollment.status,
            "modules_count": modules_count,
            "current_schedule_id": enrollment.current_schedule_id,
        }


@app.get("/api/subject-dashboard/wiki")
async def subject_dashboard_wiki(
    subject_id: int,
    q: Optional[str] = None,
    concept_type: Optional[str] = None,
):
    """Tushuncha qidiruvi va concept_type filtri."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        query = select(SubjectWiki).where(SubjectWiki.subject_id == subject_id)
        if concept_type and concept_type.strip() and concept_type != "all":
            query = query.where(SubjectWiki.concept_type == concept_type.strip().lower())
        if q and q.strip():
            like = f"%{q.strip()}%"
            query = query.where(
                or_(
                    SubjectWiki.term.ilike(like),
                    SubjectWiki.definition.ilike(like),
                    SubjectWiki.topic_title.ilike(like),
                    SubjectWiki.source_book.ilike(like),
                )
            )
        query = query.order_by(SubjectWiki.term.asc())
        rows = (await session.execute(query)).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "term": r.term,
                    "definition": r.definition,
                    "source_book": r.source_book,
                    "grade_level": r.grade_level,
                    "topic_title": r.topic_title,
                    "concept_type": r.concept_type,
                }
                for r in rows
            ],
            "concept_types": ["atama", "shaxs", "sana", "qoida", "nazariya"],
        }


@app.get("/api/subject-dashboard/schedule")
async def subject_dashboard_schedule(subject_id: int, telegram_id: int = 12345678):
    """Dars jadvali va o'quvchining joriy nuqtasi."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        subject = (
            await session.execute(select(SubjectCatalog).where(SubjectCatalog.id == subject_id))
        ).scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=404, detail="Fan topilmadi")
        enrollment = await _get_or_create_enrollment(session, telegram_id, subject)

        rows = (
            await session.execute(
                select(SubjectSchedule)
                .where(SubjectSchedule.subject_id == subject_id)
                .order_by(SubjectSchedule.order_num.asc())
            )
        ).scalars().all()

        total = len(rows) or 1
        current_idx = max(0, min(total - 1, int(round(enrollment.actual_progress / 100 * (total - 1)))))
        if enrollment.current_schedule_id is None and rows:
            enrollment.current_schedule_id = rows[current_idx].id
            await session.commit()

        items = []
        for i, r in enumerate(rows):
            is_current = (enrollment.current_schedule_id == r.id) or (i == current_idx)
            is_done = i < current_idx
            items.append({
                "id": r.id,
                "module_id": r.module_id,
                "order_num": r.order_num,
                "topic_title": r.topic_title,
                "planned_date": r.planned_date.isoformat() if r.planned_date else None,
                "video_url": r.video_url,
                "test_score_avg": r.test_score_avg,
                "is_current": is_current,
                "is_done": is_done,
                "status": "current" if is_current else ("done" if is_done else "upcoming"),
            })

        return {
            "items": items,
            "current_schedule_id": enrollment.current_schedule_id,
            "actual_progress": enrollment.actual_progress,
            "expected_progress": enrollment.expected_progress,
            "pace_status": _pace_status(enrollment.actual_progress, enrollment.expected_progress),
        }


@app.get("/api/subject-dashboard/mistakes")
async def subject_dashboard_mistakes(subject_id: int, telegram_id: int = 12345678):
    """Xatolar banki (faqat is_resolved=False)."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        rows = (
            await session.execute(
                select(SubjectMistakeBank).where(
                    SubjectMistakeBank.subject_id == subject_id,
                    SubjectMistakeBank.user_id == telegram_id,
                    SubjectMistakeBank.is_resolved == False,
                ).order_by(SubjectMistakeBank.created_at.desc())
            )
        ).scalars().all()

        # Demo seed — bo'sh bo'lsa
        if not rows:
            demo = [
                SubjectMistakeBank(
                    user_id=telegram_id, subject_id=subject_id, question_id=101,
                    question_text="Amir Temur nechanchi yilda tavallud topgan?",
                    options_json=json.dumps(["1336-yil", "1342-yil", "1350-yil", "1370-yil"]),
                    correct_answer="1336-yil", user_wrong_answer="1342-yil",
                    explanation="Amir Temur 1336-yilda Kesh (Shahrisabz) yaqinida tug'ilgan.",
                    mistake_count=2,
                ),
                SubjectMistakeBank(
                    user_id=telegram_id, subject_id=subject_id, question_id=102,
                    question_text="Loy jangi qaysi yilda bo'lib o'tgan?",
                    options_json=json.dumps(["1365-yil", "1368-yil", "1372-yil", "1390-yil"]),
                    correct_answer="1365-yil", user_wrong_answer="1368-yil",
                    explanation="Loy jangi 1365-yilda bo'lib o'tgan.",
                    mistake_count=1,
                ),
                SubjectMistakeBank(
                    user_id=telegram_id, subject_id=subject_id, question_id=103,
                    question_text="Amir Temur davlatining dastlabki poytaxti?",
                    options_json=json.dumps(["Buxoro", "Hirot", "Kesh (Shahrisabz)", "Samarqand"]),
                    correct_answer="Kesh (Shahrisabz)", user_wrong_answer="Samarqand",
                    explanation="Dastlabki poytaxt Kesh (Shahrisabz) bo'lgan.",
                    mistake_count=3,
                ),
            ]
            session.add_all(demo)
            await session.commit()
            rows = (
                await session.execute(
                    select(SubjectMistakeBank).where(
                        SubjectMistakeBank.subject_id == subject_id,
                        SubjectMistakeBank.user_id == telegram_id,
                        SubjectMistakeBank.is_resolved == False,
                    ).order_by(SubjectMistakeBank.created_at.desc())
                )
            ).scalars().all()

        items = []
        for r in rows:
            opts = []
            try:
                opts = json.loads(r.options_json) if r.options_json else []
            except Exception:
                opts = []
            items.append({
                "id": r.id,
                "question_id": r.question_id,
                "question_text": r.question_text,
                "options": opts,
                "correct_answer": r.correct_answer,
                "user_wrong_answer": r.user_wrong_answer,
                "explanation": r.explanation,
                "mistake_count": r.mistake_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return {"items": items, "count": len(items)}


@app.post("/api/subject-dashboard/resolve-mistake")
async def subject_dashboard_resolve_mistake(payload: SubjectResolveMistakeSchema):
    """To'g'ri yechilgan savolni xatolar bankidan chiqarish (is_resolved=True)."""
    async with async_session() as session:
        row = (
            await session.execute(
                select(SubjectMistakeBank).where(
                    SubjectMistakeBank.id == payload.mistake_id,
                    SubjectMistakeBank.user_id == payload.telegram_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Xato topilmadi")

        if payload.is_correct:
            row.is_resolved = True
            await session.commit()
            return {"status": "resolved", "mistake_id": row.id, "is_resolved": True}

        row.mistake_count = (row.mistake_count or 0) + 1
        await session.commit()
        return {"status": "kept", "mistake_id": row.id, "mistake_count": row.mistake_count, "is_resolved": False}


@app.get("/api/subject-dashboard/community")
async def subject_dashboard_community(
    subject_id: int,
    hashtag: Optional[str] = None,
    limit: int = 50,
):
    """Hashtaglar bo'yicha jamoa xabarlari."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        query = select(SubjectCommunityPost).where(SubjectCommunityPost.subject_id == subject_id)
        if hashtag and hashtag.strip() and hashtag != "all":
            tag = hashtag.strip()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            query = query.where(SubjectCommunityPost.hashtags.ilike(f"%{tag}%"))
        query = query.order_by(SubjectCommunityPost.created_at.desc()).limit(min(limit, 100))
        rows = (await session.execute(query)).scalars().all()

        if not rows and (not hashtag or hashtag in (None, "", "all")):
            demo = [
                SubjectCommunityPost(
                    subject_id=subject_id, user_id=111, user_name="Dilshod",
                    hashtags="#savol", content="Amir Temur va Chingizxon o'rtasidagi eng muhim farq nima? #savol",
                ),
                SubjectCommunityPost(
                    subject_id=subject_id, user_id=222, user_name="Madina",
                    hashtags="#manba", content="Temur tuzuklarining ishonchli tarjimasi qayerda? #manba",
                ),
                SubjectCommunityPost(
                    subject_id=subject_id, user_id=333, user_name="Jasur",
                    hashtags="#tushunmadim", content="Loy jangi sabablari chalkash — #tushunmadim",
                ),
            ]
            session.add_all(demo)
            await session.commit()
            rows = demo

        return {
            "items": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "user_name": r.user_name or "O'quvchi",
                    "hashtags": r.hashtags or "",
                    "content": r.content,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "filters": ["#savol", "#manba", "#tushunmadim", "#javob"],
        }


@app.post("/api/subject-dashboard/ask-question")
async def subject_dashboard_ask_question(payload: SubjectAskSchema):
    """Hamjamiyatga yangi savol / post qoldirish."""
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Xabar matni bo'sh")

    hashtags = (payload.hashtags or "#savol").strip()
    # Matndan hashtag ajratib olish
    for token in content.split():
        if token.startswith("#") and token.lower() not in hashtags.lower():
            hashtags = f"{hashtags} {token}".strip()

    async with async_session() as session:
        await _ensure_subject_seed(session)
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        name = payload.user_name or (user.full_name if user else None) or "O'quvchi"

        post = SubjectCommunityPost(
            subject_id=payload.subject_id,
            user_id=payload.telegram_id,
            user_name=name,
            hashtags=hashtags,
            content=content,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return {
            "status": "ok",
            "post": {
                "id": post.id,
                "user_id": post.user_id,
                "user_name": post.user_name,
                "hashtags": post.hashtags,
                "content": post.content,
                "created_at": post.created_at.isoformat() if post.created_at else None,
            },
        }


@app.get("/api/subject-dashboard/diagnostics/{quiz_id}")
async def subject_dashboard_diagnostics(quiz_id: int, subject_id: Optional[int] = None, telegram_id: int = 12345678):
    """Test videosharhi, manbalar va matnli tahlil."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        query = select(SubjectDiagnosticReport).where(
            SubjectDiagnosticReport.quiz_id == quiz_id,
        )
        if subject_id:
            query = query.where(SubjectDiagnosticReport.subject_id == subject_id)
        # Avval foydalanuvchining o'z hisoboti, keyin umumiy seed
        user_row = (
            await session.execute(query.where(SubjectDiagnosticReport.user_id == telegram_id))
        ).scalar_one_or_none()
        row = user_row or (await session.execute(query)).scalars().first()

        if not row:
            return {
                "quiz_id": quiz_id,
                "quiz_title": f"Test #{quiz_id}",
                "video_review_url": None,
                "analysis_text": "Ushbu test uchun diagnostika hali tayyor emas.",
                "strengths_text": "",
                "weaknesses_text": "",
                "sources": [],
            }

        sources = []
        try:
            sources = json.loads(row.sources_json) if row.sources_json else []
        except Exception:
            sources = []

        return {
            "id": row.id,
            "quiz_id": row.quiz_id,
            "quiz_title": row.quiz_title,
            "subject_id": row.subject_id,
            "video_review_url": row.video_review_url,
            "analysis_text": row.analysis_text,
            "strengths_text": row.strengths_text,
            "weaknesses_text": row.weaknesses_text,
            "sources": sources,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


@app.get("/api/subject-dashboard/modules")
async def subject_dashboard_modules(subject_id: int, telegram_id: int = 12345678):
    """Alohida sotib olinadigan modullar."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        rows = (
            await session.execute(
                select(SubjectModule).where(
                    SubjectModule.subject_id == subject_id,
                    SubjectModule.is_active == True,
                ).order_by(SubjectModule.order_num.asc())
            )
        ).scalars().all()

        cab = (
            await session.execute(
                select(UserCabinetItem.product_id).where(
                    UserCabinetItem.telegram_id == telegram_id,
                    UserCabinetItem.status == "active",
                )
            )
        ).scalars().all()
        owned_product_ids = set(cab or [])

        return {
            "items": [
                {
                    "id": m.id,
                    "title": m.title,
                    "description": m.description,
                    "grade_level": m.grade_level,
                    "price_coin": m.price_coin,
                    "old_price_coin": m.old_price_coin,
                    "image_url": m.image_url,
                    "is_standalone": m.is_standalone,
                    "product_id": m.product_id,
                    "owned": bool(m.product_id and m.product_id in owned_product_ids),
                }
                for m in rows
            ]
        }


@app.get("/api/subject-dashboard/books")
async def subject_dashboard_books(subject_id: int):
    """In-app kitoblar (download bloklangan)."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        rows = (
            await session.execute(
                select(SubjectBook).where(
                    SubjectBook.subject_id == subject_id,
                    SubjectBook.is_active == True,
                )
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": b.id,
                    "title": b.title,
                    "book_type": b.book_type,
                    "cover_url": b.cover_url,
                    "viewer_url": b.viewer_url,
                    "is_downloadable": False,  # Har doim bloklangan
                    "module_id": b.module_id,
                }
                for b in rows
            ]
        }


@app.get("/api/subject-dashboard/quizzes")
async def subject_dashboard_quizzes(subject_id: int, paid: Optional[str] = None):
    """Bob/kitob/fan testlari — Testlar bo'limiga yo'naltiradi."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        query = select(SubjectQuizLink).where(
            SubjectQuizLink.subject_id == subject_id,
            SubjectQuizLink.is_active == True,
        )
        if paid == "1" or paid == "true":
            query = query.where(SubjectQuizLink.is_paid == True)
        elif paid == "0" or paid == "false":
            query = query.where(SubjectQuizLink.is_paid == False)
        rows = (await session.execute(query)).scalars().all()
        return {
            "items": [
                {
                    "id": q.id,
                    "title": q.title,
                    "scope": q.scope,
                    "quiz_id": q.quiz_id,
                    "is_paid": q.is_paid,
                    "price_coin": q.price_coin,
                    "target_tab": "tests",
                }
                for q in rows
            ]
        }


@app.get("/api/subject-dashboard/battle-modules")
async def subject_dashboard_battle_modules(subject_id: int):
    """Battle uchun fan ichidagi modul/mavzu doirasi."""
    async with async_session() as session:
        await _ensure_subject_seed(session)
        modules = (
            await session.execute(
                select(SubjectModule).where(
                    SubjectModule.subject_id == subject_id,
                    SubjectModule.is_active == True,
                ).order_by(SubjectModule.order_num.asc())
            )
        ).scalars().all()
        return {
            "subject_id": subject_id,
            "modules": [
                {"id": m.id, "title": m.title, "grade_level": m.grade_level}
                for m in modules
            ],
            "game_types": [
                {"id": "octagon", "title": "Oktagon duel", "available": True},
                {"id": "quiz_race", "title": "Tezkor viktorina", "available": False},
                {"id": "memory_match", "title": "Xotira o'yini", "available": False},
            ],
        }


@app.post("/api/subject-dashboard/battle-challenge")
async def subject_dashboard_battle_challenge(payload: SubjectBattleChallengeSchema):
    """Chaqiriqni fan Community guruhiga (duel ssilkasi) yo'llash."""
    subject_id = payload.subject_id
    level = _normalize_level(payload.level)
    topic = (payload.topic or "").strip() or None

    async with async_session() as session:
        subject = (
            await session.execute(select(SubjectCatalog).where(SubjectCatalog.id == subject_id))
        ).scalar_one_or_none()
        if not subject:
            subject = await _ensure_subject_seed(session)

        if payload.module_id and not topic:
            mod = (
                await session.execute(
                    select(SubjectModule).where(SubjectModule.id == payload.module_id)
                )
            ).scalar_one_or_none()
            if mod:
                topic = mod.title

        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            # Dev fallback
            pass

        now = datetime.utcnow()
        room_code = _generate_room_code()
        battle = OctagonBattle(
            room_code=room_code,
            creator_id=payload.telegram_id,
            subject=subject.code or "tarix",
            level=level,
            topic=topic,
            status="waiting",
            expires_at=now + timedelta(seconds=OCTAGON_INVITE_TTL_SECONDS),
        )
        session.add(battle)
        await session.commit()

        bot_username = await _resolve_bot_username()
        invite_link = f"https://t.me/{bot_username}?start=oct_{room_code}"

        community_sent = False
        if subject.community_chat_id:
            try:
                text = (
                    f"⚔️ <b>{subject.title}</b> Community chaqirig'i!\n"
                    f"Mavzu: {topic or 'Umumiy'}\n"
                    f"Daraja: {level}\n"
                    f"Havola: {invite_link}"
                )
                await tg_bot.send_message(subject.community_chat_id, text, parse_mode="HTML")
                community_sent = True
            except Exception as e:
                print(f"Community challenge yuborish xatosi: {e}")

        return {
            "status": "ok",
            "room_code": room_code,
            "invite_link": invite_link,
            "subject": subject.title,
            "topic": topic,
            "level": level,
            "community_sent": community_sent,
            "expires_in": OCTAGON_INVITE_TTL_SECONDS,
            "share_text": f"PHAROS {subject.title} duel: {invite_link}",
        }


# ==========================================================
# TESTLAR BO'LIMI API
# ==========================================================
EXAM_SUBJECTS = {
    "tarix": "Tarix",
    "huquq": "Huquqshunoslik",
    "psixologiya": "Psixologiya",
    "ona_tili": "Ona tili",
}
EXAM_TYPES = {
    "milliy_sertifikat": "Milliy sertifikat",
    "namunaviy": "Namunaviy testlar",
    "imtihon": "Imtihon",
    "bmba_asosiy": "BMBA (Asosiy blok)",
    "bmba_majburiy": "BMBA (Majburiy blok)",
    "akademik_litsey": "Akademik litsey imtihoni",
    "olimpiada": "Olimpiada",
    "attestatsiya": "Attestatsiya",
}
EXAM_OPTION_KEYS = ("A", "B", "C", "D")
EXAM_DIFFICULTY_LABELS = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}


class ExamRateSchema(BaseModel):
    quiz_id: int
    telegram_id: int
    stars: int


class ExamSubmitSchema(BaseModel):
    quiz_id: int
    telegram_id: int
    mode: str = "elektron"
    answers: dict = {}
    image_base64: Optional[str] = None


class ExamEssaySubmitSchema(BaseModel):
    quiz_id: int
    telegram_id: int
    images: List[str] = []
    images_base64: Optional[List[str]] = None


ONA_TILI_ESSAY_TITLE = "Ona tili: Milliy sertifikat — 2026 kuz, 1-variant (To'y-hasham)"
ONA_TILI_ESSAY_PATH = "/ms/ona_tili/essay/toy-hasham"
ONA_TILI_ESSAY_ANALYSIS = (
    "Ushbu imtihon 'To'y-hasham' mavzusidagi dolzarb ijtimoiy muammoni yoritishga "
    "qaratilgan bo'lib, Rasch modeli bo'yicha 75 ballik shkalada baholanadi."
)
ESSAY_CRITERIA_SPEC = [
    {"name": "Mavzu yoritilishi", "max": 5},
    {"name": "Matn kompozitsiyasi", "max": 3},
    {"name": "Lug'at boyligi", "max": 3},
    {"name": "Orfografiya", "max": 3},
    {"name": "Punktuatsiya", "max": 3},
    {"name": "Grammatika va uslub", "max": 3},
]
ESSAY_RAW_MAX = 20.0
ESSAY_RASH_MAX = 75.0


def _exam_level(percent: float) -> str:
    if percent >= 86:
        return "Ustoz"
    if percent >= 51:
        return "Bilimdon"
    return "Boshlang'ich"


def _exam_links(raw) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _exam_now() -> datetime:
    """Exceldagi e'lon va start vaqtlari serverning mahalliy soati bilan solishtiriladi."""
    return datetime.now()


def _quiz_window(quiz: ExamQuiz, now: Optional[datetime] = None) -> str:
    now = now or _exam_now()
    if quiz.visible_at and now < quiz.visible_at:
        return "hidden"
    if quiz.starts_at and now < quiz.starts_at:
        return "scheduled"
    return "open"


def _starts_countdown(starts_at: Optional[datetime], now: datetime) -> tuple:
    if not starts_at or now >= starts_at:
        return 0, ""
    seconds = max(0, int((starts_at - now).total_seconds()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _secs = divmod(rem, 60)
    if days > 0:
        label = f"{days} kun {hours} soat"
    elif hours > 0:
        label = f"{hours} soat {minutes} daqiqa"
    else:
        label = f"{max(minutes, 1)} daqiqa"
    return seconds, label


def _ensure_quiz_open(quiz: ExamQuiz):
    window = _quiz_window(quiz)
    if window == "hidden":
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if window == "scheduled":
        _seconds, label = _starts_countdown(quiz.starts_at, _exam_now())
        raise HTTPException(status_code=403, detail=f"Test hali ochilmagan. Boshlanishiga: {label} qoldi")


def _quiz_base_amount(quiz: ExamQuiz) -> int:
    base = int(quiz.base_price or 0)
    if base > 0:
        return base
    return int(quiz.price or 0)


def _course_tokens(raw: Optional[str]) -> set:
    tokens = set()
    for part in str(raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part:
            tokens.add(part)
    return tokens


def _price_for_user(quiz: ExamQuiz, owned: set, shared: bool) -> dict:
    base = _quiz_base_amount(quiz)
    if base <= 0:
        return {"price": 0, "base_price": 0, "discount_percent": 0, "free_reason": None}
    if _course_tokens(quiz.free_for_courses) & owned:
        return {"price": 0, "base_price": base, "discount_percent": 100, "free_reason": "course"}
    percent = max(0, min(100, int(quiz.share_discount_percent or 0)))
    if shared and percent > 0:
        price = int(round(base * (100 - percent) / 100.0))
        return {
            "price": max(0, price),
            "base_price": base,
            "discount_percent": percent,
            "free_reason": "share",
        }
    return {"price": base, "base_price": base, "discount_percent": 0, "free_reason": None}


async def _owned_course_ids(session, telegram_id: Optional[int]) -> set:
    owned = set()
    if not telegram_id:
        return owned
    cabinet_ids = (
        await session.execute(
            select(UserCabinetItem.product_id).where(
                UserCabinetItem.telegram_id == telegram_id,
                UserCabinetItem.status == "active",
            )
        )
    ).scalars().all()
    owned.update(str(int(item_id)) for item_id in cabinet_ids if item_id is not None)

    subject_ids = (
        await session.execute(
            select(UserSubjectEnrollment.subject_id).where(
                UserSubjectEnrollment.user_id == telegram_id,
                UserSubjectEnrollment.status == "active",
            )
        )
    ).scalars().all()
    owned.update(str(int(item_id)) for item_id in subject_ids if item_id is not None)

    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if not user:
        return owned
    access_rows = (
        await session.execute(
            select(UserCourseAccess).where(
                UserCourseAccess.user_id == user.id,
                UserCourseAccess.is_active == True,
            )
        )
    ).scalars().all()
    now = _exam_now()
    for row in access_rows:
        if row.expires_at and row.expires_at < now:
            continue
        if row.product_id is not None:
            owned.add(str(int(row.product_id)))
    return owned


async def _user_has_shared(session, telegram_id: Optional[int]) -> bool:
    if not telegram_id:
        return False
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if user and (user.invited_friends_count or 0) > 0:
        return True
    invites = (
        await session.execute(
            select(func.count(ReferralEarning.id)).where(ReferralEarning.inviter_id == telegram_id)
        )
    ).scalar()
    return int(invites or 0) > 0


def _question_beta(question: ExamQuestion) -> float:
    try:
        beta = float(question.difficulty_beta) if question.difficulty_beta is not None else 2.0
    except (TypeError, ValueError):
        beta = 2.0
    if beta <= 0:
        return 2.0
    return beta


def _rasch_theta(pairs: list) -> float:
    """Rasch MLE: P(to'g'ri) = 1 / (1 + exp(-(theta - beta)))."""
    if not pairs:
        return 2.0
    scores = [int(score) for score, _beta in pairs]
    betas = [float(beta) for _score, beta in pairs]
    if all(score == 1 for score in scores):
        return round(max(betas) + 0.8, 3)
    if all(score == 0 for score in scores):
        return round(min(betas) - 0.8, 3)
    theta = sum(betas) / len(betas)
    for _step in range(40):
        gradient = 0.0
        hessian = 0.0
        for score, beta in zip(scores, betas):
            gap = theta - beta
            if gap > 20:
                probability = 1.0 - 1e-9
            elif gap < -20:
                probability = 1e-9
            else:
                probability = 1.0 / (1.0 + math.exp(-gap))
            probability = min(max(probability, 1e-9), 1.0 - 1e-9)
            gradient += score - probability
            hessian -= probability * (1.0 - probability)
        if abs(hessian) < 1e-12:
            break
        nxt = theta - (gradient / hessian)
        nxt = max(-1.0, min(5.5, nxt))
        if abs(nxt - theta) < 1e-5:
            theta = nxt
            break
        theta = nxt
    return round(theta, 3)


def _rasch_grade(theta: float) -> str:
    if theta >= 2.7:
        return "A"
    if theta >= 2.2:
        return "B+"
    if theta >= 1.7:
        return "B"
    return "C"


def _is_essay_quiz(quiz: ExamQuiz) -> bool:
    path = (quiz.command_path or "").lower()
    if "essay" in path or "esse" in path:
        return True
    title = (quiz.title or "").lower().replace("ʻ", "'").replace("ʼ", "'")
    return "to'y-hasham" in title or "toy-hasham" in title.replace("'", "")


def _essay_certificate_level(rash_score: float) -> str:
    if rash_score >= 65.0:
        return "A"
    if rash_score >= 55.0:
        return "B+"
    if rash_score >= 45.0:
        return "B"
    if rash_score >= 35.0:
        return "C+"
    return "C"


def _essay_rasch_from_raw(raw_score: float) -> dict:
    """Ona tili esse: xom ball (0..20) → Rasch 75 ballik shkala."""
    R = max(0.0, min(ESSAY_RAW_MAX, float(raw_score)))
    theta = math.log((R + 0.5) / (ESSAY_RAW_MAX + 0.5 - R))
    rash = round(((theta + 3.7) / 7.4) * ESSAY_RASH_MAX, 1)
    rash = max(0.0, min(ESSAY_RASH_MAX, rash))
    return {
        "raw_score": round(R, 1),
        "theta": round(theta, 4),
        "rash_score": rash,
        "level": _essay_certificate_level(rash),
        "certificate": rash >= 35.0,
    }


def _essay_system_prompt() -> str:
    return (
        "Siz Ona tili fanidan Milliy sertifikat imtihoni bo'yicha oliy toifali ekspert-tekshiruvchisiz. "
        "Mavzu: 'To'y-hasham'.\n"
        "Qo'lyozma rasm(lar)ni diqqat bilan o'rganib chiqing:\n"
        "- Kirish, to'y-hashamlardagi isrofgarchilik, kimo'zarga musobaqa, jamiyatdagi ijtimoiy asoratlar "
        "va xulosa fikrlarining mavjudligini baholang.\n"
        "- Matndagi barcha imlo, tinish belgisi va uslubiy xatolarni ajratib bering.\n"
        "Baholash mezonlari (xom ball, jami max 20):\n"
        "1) Mavzuning yoritilishi va g'oyaviy pishiqligi — max 5\n"
        "2) Matn kompozitsiyasi va mantiqiy yaxlitlik — max 3\n"
        "3) Lug'at boyligi va uslubiy rang-baranglik — max 3\n"
        "4) Orfografiya (imlo) — max 3\n"
        "5) Punktuatsiya (tinish belgilari) — max 3\n"
        "6) Grammatika va uslubiy me'yorlar — max 3\n"
        "Natijani faqat JSON formatida qaytaring (markdown yo'q):\n"
        "{\n"
        "  \"raw_score\": 16.0,\n"
        "  \"rash_score\": 61.5,\n"
        "  \"level\": \"B+\",\n"
        "  \"criteria\": [\n"
        "     {\"name\": \"Mavzu yoritilishi\", \"score\": 4, \"max\": 5, "
        "\"comment\": \"Mavzu yaxshi ochilgan, lekin isrofgarchilik oqibatlari yetarli asoslanmagan.\"},\n"
        "     {\"name\": \"Matn kompozitsiyasi\", \"score\": 2, \"max\": 3, \"comment\": \"...\"},\n"
        "     {\"name\": \"Lug'at boyligi\", \"score\": 2, \"max\": 3, \"comment\": \"...\"},\n"
        "     {\"name\": \"Orfografiya\", \"score\": 3, \"max\": 3, \"comment\": \"...\"},\n"
        "     {\"name\": \"Punktuatsiya\", \"score\": 2, \"max\": 3, \"comment\": \"...\"},\n"
        "     {\"name\": \"Grammatika va uslub\", \"score\": 3, \"max\": 3, \"comment\": \"...\"}\n"
        "  ],\n"
        "  \"spelling_errors\": [\n"
        "     {\"wrong\": \"tuy\", \"correct\": \"to'y\", \"explanation\": \"Tutux belgisi tushirib qoldirilgan\"}\n"
        "  ],\n"
        "  \"feedback\": \"Umumiy xulosa matni\"\n"
        "}"
    )


def _parse_data_url(image_b64: str) -> tuple:
    raw = (image_b64 or "").strip()
    if not raw:
        return "", "image/jpeg"
    mime = "image/jpeg"
    if raw.startswith("data:"):
        match = re.match(r"^data:([^;,]+);base64,(.+)$", raw, re.DOTALL)
        if match:
            mime = match.group(1).strip() or mime
            raw = match.group(2).strip()
        else:
            raw = raw.split(",", 1)[-1].strip()
    raw = re.sub(r"\s+", "", raw)
    return raw, mime


def _extract_json_object(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
    return {}


def _normalize_essay_ai_result(payload: dict) -> dict:
    criteria = []
    raw_from_criteria = 0.0
    source_criteria = payload.get("criteria") if isinstance(payload.get("criteria"), list) else []
    for index, spec in enumerate(ESSAY_CRITERIA_SPEC):
        item = source_criteria[index] if index < len(source_criteria) and isinstance(source_criteria[index], dict) else {}
        try:
            score = float(item.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0.0
        max_score = float(spec["max"])
        score = max(0.0, min(max_score, score))
        raw_from_criteria += score
        criteria.append({
            "name": item.get("name") or spec["name"],
            "score": round(score, 1),
            "max": int(max_score) if max_score == int(max_score) else max_score,
            "comment": str(item.get("comment") or "").strip(),
            "passed": score >= max_score * 0.6,
        })
    try:
        raw_declared = float(payload.get("raw_score")) if payload.get("raw_score") is not None else raw_from_criteria
    except (TypeError, ValueError):
        raw_declared = raw_from_criteria
    raw_score = raw_from_criteria if raw_from_criteria > 0 else raw_declared
    scaled = _essay_rasch_from_raw(raw_score)
    errors = []
    for err in payload.get("spelling_errors") or []:
        if not isinstance(err, dict):
            continue
        wrong = str(err.get("wrong") or "").strip()
        correct = str(err.get("correct") or "").strip()
        if not wrong and not correct:
            continue
        errors.append({
            "wrong": wrong,
            "correct": correct,
            "explanation": str(err.get("explanation") or "").strip(),
        })
    feedback = str(payload.get("feedback") or "").strip()
    return {
        "kind": "essay_rasch",
        "raw_score": scaled["raw_score"],
        "rash_score": scaled["rash_score"],
        "theta": scaled["theta"],
        "level": scaled["level"],
        "certificate": scaled["certificate"],
        "criteria": criteria,
        "spelling_errors": errors,
        "feedback": feedback or ONA_TILI_ESSAY_ANALYSIS,
        "max_raw": ESSAY_RAW_MAX,
        "max_rash": ESSAY_RASH_MAX,
    }


def _fallback_essay_result(reason: str = "") -> dict:
    """Gemini ishlamasa ham Rasch pipeline sinovdan o'tishi uchun namuna natija."""
    mock = {
        "raw_score": 16.0,
        "criteria": [
            {"name": "Mavzu yoritilishi", "score": 4, "max": 5, "comment": "Mavzu ochilgan, isrofgarchilik oqibatlari biroz yuzaki."},
            {"name": "Matn kompozitsiyasi", "score": 2, "max": 3, "comment": "Kirish va xulosa bor, bog'lovchi o'tishlar zaif."},
            {"name": "Lug'at boyligi", "score": 2, "max": 3, "comment": "Lug'at o'rtacha, takrorlar uchraydi."},
            {"name": "Orfografiya", "score": 3, "max": 3, "comment": "Imlo asosan to'g'ri."},
            {"name": "Punktuatsiya", "score": 2, "max": 3, "comment": "Vergul va tireda xatolar bor."},
            {"name": "Grammatika va uslub", "score": 3, "max": 3, "comment": "Uslub me'yorida."},
        ],
        "spelling_errors": [
            {"wrong": "tuy", "correct": "to'y", "explanation": "Tutux belgisi tushirib qoldirilgan"},
            {"wrong": "hasham", "correct": "hasham", "explanation": "Kontekstga qarab 'to'y-hasham' birikmasi tavsiya etiladi"},
        ],
        "feedback": (
            "Esse 'To'y-hasham' mavzusiga mos yozilgan. Isrofgarchilik va kimo'zarga musobaqa g'oyalari bor. "
            + (f" (AI: {reason})" if reason else " (sinov/fallback baholash)")
        ),
    }
    return _normalize_essay_ai_result(mock)


async def _gemini_grade_essay_images(images: list) -> dict:
    if not images:
        raise HTTPException(status_code=400, detail="Kamida bitta esse rasmi kerak")
    if not GEMINI_API_KEY:
        return _fallback_essay_result("GEMINI_API_KEY yo'q")

    parts = [{"text": _essay_system_prompt() + "\n\nQuyidagi qo'lyozma sahifa(lar)ni baholang."}]
    for image in images[:8]:
        data, mime = _parse_data_url(image)
        if not data:
            continue
        try:
            base64.b64decode(data, validate=False)
        except Exception:
            continue
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Rasm formatini o'qib bo'lmadi")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_ESSAY_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    try:
        status_code, payload = await _gemini_http_post_json(url, body)
        if status_code >= 400:
            return _fallback_essay_result(f"HTTP {status_code}")
        text = ""
        for candidate in payload.get("candidates") or []:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                if part.get("text"):
                    text += part["text"]
        parsed = _extract_json_object(text)
        if not parsed:
            return _fallback_essay_result("JSON parse xatosi")
        return _normalize_essay_ai_result(parsed)
    except HTTPException:
        raise
    except Exception as exc:
        return _fallback_essay_result(str(exc)[:120])


async def _gemini_http_post_json(url: str, body: dict) -> tuple:
    """httpx bo'lsa undan, bo'lmasa stdlib urllib orqali Gemini ga POST."""
    if _httpx is not None:
        async with _httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
            )
            try:
                payload = response.json()
            except Exception:
                payload = {}
            return response.status_code, payload if isinstance(payload, dict) else {}

    def _sync_post():
        raw = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8") or "{}")
                return resp.status, data if isinstance(data, dict) else {}
        except urllib.error.HTTPError as err:
            try:
                data = json.loads(err.read().decode("utf-8") or "{}")
            except Exception:
                data = {}
            return err.code, data if isinstance(data, dict) else {}

    return await asyncio.to_thread(_sync_post)


def _chosen_option(question: ExamQuestion, answers: dict):
    chosen = answers.get(question.id)
    if chosen is None:
        chosen = answers.get(str(question.id))
    try:
        return int(chosen) if chosen is not None else None
    except (TypeError, ValueError):
        return None


def _evaluate_exam(questions: list, answers: dict) -> tuple:
    score, total, percent = _score_answers(questions, answers)
    pairs = []
    for question in questions:
        chosen = _chosen_option(question, answers)
        pairs.append((1 if chosen is not None and chosen == question.correct_option else 0, _question_beta(question)))
    theta = _rasch_theta(pairs)
    return score, total, percent, theta, _rasch_grade(theta)


def _pdf_text(value: str) -> str:
    text = value or ""
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´", "ʹ", "“", "”"):
        text = text.replace(ch, "'")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1", "replace").decode("latin-1")


def _wrap_pdf_line(text: str, width: int = 88) -> list:
    words = (text or "").split()
    if not words:
        return [""]
    lines, current = [], ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _build_simple_pdf(title: str, body_lines: list, watermark: Optional[str] = None) -> bytes:
    commands = ["BT", "/F1 14 Tf", "40 800 Td", f"({_pdf_text(title)}) Tj", "ET"]
    y = 776
    commands.append("BT")
    commands.append("/F1 10 Tf")
    for line in body_lines:
        if y < 48:
            break
        commands.append(f"1 0 0 1 40 {y} Tm")
        commands.append(f"({_pdf_text(line)}) Tj")
        y -= 14
    commands.append("ET")
    if watermark:
        commands.extend([
            "0.75 0.84 0.78 rg",
            "BT",
            "/F1 22 Tf",
            "0.92 0.28 -0.22 0.94 70 460 Tm",
            f"({_pdf_text(watermark)}) Tj",
            "ET",
            "0 0 0 rg",
        ])
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    header = b"%PDF-1.4\n"
    chunks = [header]
    offsets = []
    cursor = len(header)
    for index, obj in enumerate(objects, start=1):
        offsets.append(cursor)
        piece = f"{index} 0 obj\n".encode("latin-1") + obj + b"\nendobj\n"
        chunks.append(piece)
        cursor += len(piece)
    xref_lines = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    xref_lines.extend(f"{off:010d} 00000 n \n" for off in offsets)
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{cursor}\n%%EOF"
    )
    return b"".join(chunks) + "".join(xref_lines).encode("latin-1") + trailer.encode("latin-1")


def _quiz_pdf_lines(quiz: ExamQuiz, questions: list, kind: str) -> list:
    lines = [
        f"Fan: {EXAM_SUBJECTS.get(quiz.subject, quiz.subject)}",
        f"Tur: {EXAM_TYPES.get(quiz.exam_type, quiz.exam_type)}",
        f"Sana: {quiz.announced_at.strftime('%d.%m.%Y') if quiz.announced_at else ''}",
        "",
    ]
    if _is_essay_quiz(quiz):
        if kind == "answers":
            lines.extend([
                "Esse javoblar / yuklash sahifasi",
                "1) Titul varag'ini rasmga oling",
                "2) 'To'y-hasham' mavzusidagi esse sahifalarini ketma-ket yuklang",
                "3) Mini App skanerida 'Tekshirishga yuborish' tugmasini bosing",
                "",
                "Baholash: Rasch (IRT/Logit) — maksimal 75 ball",
            ])
        else:
            lines.extend([
                "ESSE IMTIHONI — mavzu: To'y-hasham",
                "",
                "Yozma ishingizda quyidagilarni yoriting:",
                "- Kirish",
                "- To'y-hashamlardagi isrofgarchilik",
                "- Kimo'zarga musobaqa",
                "- Jamiyatdagi ijtimoiy asoratlar",
                "- Xulosa",
                "",
                "Mezonlar (xom ball max 20): mavzu 5, kompozitsiya 3,",
                "lug'at 3, orfografiya 3, punktuatsiya 3, grammatika 3.",
                "Yakuniy ball Rasch modeli orqali 75 ballik shkalaga o'tkaziladi.",
            ])
        return lines
    if kind == "answers":
        lines.extend([
            "JAVOBLAR VARAQASI (TITUL)",
            "Familiya: ____________________",
            "Ism: ____________________",
            "ID: ____________________",
            "",
            "To'g'ri javobni bo'sh doira ichida belgilang.",
            "",
        ])
        for question in questions:
            lines.append(f"{question.order_num}.    ( A )   ( B )   ( C )   ( D )")
        return lines

    lines.append("Rasmiy DTM formatidagi test varaqasi")
    lines.append("")
    for question in questions:
        lines.extend(_wrap_pdf_line(f"{question.order_num}. {question.question_text}"))
        lines.append(f"    A) {question.option_a}")
        lines.append(f"    B) {question.option_b}")
        lines.append(f"    C) {question.option_c}")
        lines.append(f"    D) {question.option_d}")
        lines.append("")
    return lines


async def _ensure_named_user(session, telegram_id: int, full_name: str, region: str, district: str):
    user = (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if user:
        return user
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        region=region,
        district=district,
        selected_subject="tarix",
    )
    session.add(user)
    await session.flush()
    return user


def _answers_payload(questions: list, wrong_orders: set) -> dict:
    payload = {}
    for question in questions:
        if question.order_num in wrong_orders:
            payload[str(question.id)] = (question.correct_option + 1) % 4
        else:
            payload[str(question.id)] = question.correct_option
    return payload


def _score_answers(questions: list, answers: dict) -> tuple:
    correct = 0
    for question in questions:
        chosen = answers.get(question.id)
        if chosen is None:
            chosen = answers.get(str(question.id))
        try:
            chosen = int(chosen) if chosen is not None else None
        except (TypeError, ValueError):
            chosen = None
        if chosen is not None and chosen == question.correct_option:
            correct += 1
    total = len(questions)
    percent = round((correct / total) * 100, 1) if total else 0.0
    return correct, total, percent


async def _ensure_ona_tili_essay_seed(session):
    """Ona tili Milliy sertifikat — To'y-hasham esse imtihonini (agar yo'q bo'lsa) qo'shadi."""
    existing = (
        await session.execute(
            select(ExamQuiz).where(
                or_(
                    ExamQuiz.command_path == ONA_TILI_ESSAY_PATH,
                    ExamQuiz.title == ONA_TILI_ESSAY_TITLE,
                )
            ).order_by(ExamQuiz.id.desc())
        )
    ).scalars().first()
    if existing:
        existing.title = ONA_TILI_ESSAY_TITLE
        existing.subject = "ona_tili"
        existing.exam_type = "milliy_sertifikat"
        existing.price = 0
        existing.base_price = 0
        existing.link = "https://t.me/pharos_talim_bot"
        existing.analysis_text = ONA_TILI_ESSAY_ANALYSIS
        existing.command_path = ONA_TILI_ESSAY_PATH
        existing.duration_minutes = existing.duration_minutes or 90
        existing.is_active = True
        if not existing.announced_at:
            existing.announced_at = datetime(2026, 10, 20, 9, 0, 0)
        await session.commit()
        return existing

    quiz = ExamQuiz(
        title=ONA_TILI_ESSAY_TITLE,
        subject="ona_tili",
        exam_type="milliy_sertifikat",
        price=0,
        base_price=0,
        link="https://t.me/pharos_talim_bot",
        analysis_text=ONA_TILI_ESSAY_ANALYSIS,
        duration_minutes=90,
        announced_at=datetime(2026, 10, 20, 9, 0, 0),
        is_active=True,
        command_path=ONA_TILI_ESSAY_PATH,
    )
    session.add(quiz)
    await session.flush()
    quiz.pdf_url = f"/api/exams/paper/{quiz.id}?kind=test"
    quiz.answer_sheet_url = f"/api/exams/paper/{quiz.id}?kind=answers"
    await session.commit()
    return quiz


async def _ensure_exam_seed(session):
    existing = (await session.execute(select(func.count(ExamQuiz.id)))).scalar() or 0
    if existing:
        await _ensure_ona_tili_essay_seed(session)
        return

    def links(a, b, c, d):
        return json.dumps({"A": a, "B": b, "C": c, "D": d}, ensure_ascii=False)

    quiz_milliy = ExamQuiz(
        title="Tarix: Milliy sertifikat — 2026 kuz, 1-variant",
        subject="tarix",
        exam_type="milliy_sertifikat",
        price=35000,
        link="https://pharos.uz/exams/tarix/milliy-sertifikat/2026-kuz-1-variant/rasmiy-dtm-format",
        analysis_text="Umumiy tahlil: siyosiy tarix va Temuriylar madaniyati bo'yicha xatolar ko'proq 1370-yildan keyingi davlat tuzumi hamda poytaxt masalasida uchraydi. Har bir xato variant yonidagi darslik betini qayta o'qing.",
        duration_minutes=20,
        announced_at=datetime(2026, 10, 2, 9, 0, 0),
        is_active=True,
    )
    quiz_bmba = ExamQuiz(
        title="Tarix: BMBA asosiy blok — namunaviy to'plam",
        subject="tarix",
        exam_type="bmba_asosiy",
        price=0,
        link="https://pharos.uz/exams/tarix/bmba-asosiy-blok/2026-namuna/bepul-variant",
        analysis_text="BMBA asosiy blok tahlili: madaniy meros va adabiy manbalar bo'yicha izohlar variantlar tagida berilgan.",
        duration_minutes=15,
        announced_at=datetime(2026, 9, 18, 8, 0, 0),
        is_active=True,
    )
    quiz_huquq = ExamQuiz(
        title="Huquqshunoslik: semestr imtihoni — 1-nazorat",
        subject="huquq",
        exam_type="imtihon",
        price=15000,
        link="https://pharos.uz/exams/huquqshunoslik/imtihon/2026-semestr-1-nazorat/tolik-havola",
        analysis_text="Huquq bo'yicha umumiy izoh: Konstitutsiya moddalari va fuqarolik layoqati chegarasini adashtirmang.",
        duration_minutes=15,
        announced_at=datetime(2026, 10, 15, 10, 0, 0),
        is_active=True,
    )
    session.add_all([quiz_milliy, quiz_bmba, quiz_huquq])
    await session.flush()
    for quiz in (quiz_milliy, quiz_bmba, quiz_huquq):
        quiz.pdf_url = f"/api/exams/paper/{quiz.id}?kind=test"
        quiz.answer_sheet_url = f"/api/exams/paper/{quiz.id}?kind=answers"

    milliy_specs = [
        dict(order_num=1, question_text="Amir Temur nechanchi yilda tavallud topgan?",
             option_a="1336-yil", option_b="1342-yil", option_c="1350-yil", option_d="1370-yil",
             correct_option=0, topic="Amir Temur davlati", direction="Siyosiy tarix", difficulty="oson",
             book_links_json=links("7-sinf O'zbekiston tarixi, 86-bet", "7-sinf O'zbekiston tarixi, 88-bet", "Temuriylar davri, 12-bet", "Milliy ensiklopediya, 40-bet"),
             analysis_text="Amir Temur 1336-yil 9-aprelda Kesh yaqinidagi Xo'ja Ilg'or qishlog'ida tug'ilgan."),
        dict(order_num=2, question_text="Sohibqiron Amir Temurning otasi kim bo'lgan?",
             option_a="Amir Qazag'on", option_b="Amir Tarag'ay", option_c="Hoji Barlos", option_d="Mirzo Ulug'bek",
             correct_option=1, topic="Amir Temur davlati", direction="Siyosiy tarix", difficulty="oson",
             book_links_json=links("7-sinf O'zbekiston tarixi, 87-bet", "7-sinf O'zbekiston tarixi, 86-bet", "Barlos qabilasi, 19-bet", "Temuriylar, 140-bet"),
             analysis_text="Amir Tarag'ay barlos beklaridan bo'lib, Amir Temurning otasidir."),
        dict(order_num=3, question_text="Amir Temur davlatining dastlabki poytaxti qaysi shahar bo'lgan?",
             option_a="Buxoro", option_b="Hirot", option_c="Kesh (Shahrisabz)", option_d="Samarqand",
             correct_option=2, topic="Davlat markazi", direction="Siyosiy tarix", difficulty="qiyin",
             book_links_json=links("7-sinf O'zbekiston tarixi, 92-bet", "Xuroson yurishlari, 30-bet", "7-sinf O'zbekiston tarixi, 90-bet", "Samarqand obidalar, 8-bet"),
             analysis_text="1370-yildan keyin dastlabki poytaxt Kesh bo'lgan, keyinroq Samarqand poytaxtga aylangan."),
        dict(order_num=4, question_text="Amir Temur qachon Movarounnahrning yagona hukmdori deb e'lon qilindi?",
             option_a="1360-yil", option_b="1370-yil", option_c="1380-yil", option_d="1395-yil",
             correct_option=1, topic="Amir Temur davlati", direction="Siyosiy tarix", difficulty="orta",
             book_links_json=links("7-sinf O'zbekiston tarixi, 84-bet", "7-sinf O'zbekiston tarixi, 91-bet", "Harbiy yurishlar, 22-bet", "Anqara jangi, 4-bet"),
             analysis_text="1370-yilda Balx yaqinidagi qurultoyda u Movarounnahr hukmdori deb e'lon qilingan."),
        dict(order_num=5, question_text="Loy jangi qaysi yilda bo'lib o'tgan?",
             option_a="1365-yil", option_b="1368-yil", option_c="1372-yil", option_d="1390-yil",
             correct_option=0, topic="Loy jangi", direction="Harbiy tarix", difficulty="orta",
             book_links_json=links("7-sinf O'zbekiston tarixi, 89-bet", "Mo'g'ul yurishlari, 15-bet", "Temur tuzuklari, 44-bet", "Zafarnoma, 70-bet"),
             analysis_text="1365-yil bahoridagi Loy jangida yomg'ir tufayli otliq qo'shinlar loyga botgan."),
    ]
    bmba_specs = [
        dict(order_num=1, question_text="Registon ansambli qaysi shaharda joylashgan?",
             option_a="Buxoro", option_b="Samarqand", option_c="Xiva", option_d="Qo'qon",
             correct_option=1, topic="Temuriylar madaniyati", direction="Madaniy meros", difficulty="oson",
             book_links_json=links("8-sinf Tarix, 40-bet", "8-sinf Tarix, 41-bet", "Xiva me'morchiligi, 9-bet", "Qo'qon xonligi, 12-bet"),
             analysis_text="Ulug'bek, Sherdor va Tillakori madrasalari Samarqand Registonida turadi."),
        dict(order_num=2, question_text="Mirzo Ulug'bek rasadxonasi qaysi asrda barpo etilgan?",
             option_a="XII asr", option_b="XIII asr", option_c="XV asr", option_d="XVIII asr",
             correct_option=2, topic="Ulug'bek akademiyasi", direction="Madaniy meros", difficulty="orta",
             book_links_json=links("8-sinf Tarix, 20-bet", "8-sinf Tarix, 28-bet", "8-sinf Tarix, 48-bet", "Qo'qon, 3-bet"),
             analysis_text="Rasadxona 1420-yillarda, ya'ni XV asrda Samarqandda qurilgan."),
        dict(order_num=3, question_text="«Zafarnoma» asarining muallifi kim?",
             option_a="Alisher Navoiy", option_b="Zahiriddin Muhammad Bobur", option_c="Sharafiddin Ali Yazdiy", option_d="Nizomiddin Shomiy",
             correct_option=2, topic="Tarixiy manbalar", direction="Madaniy meros", difficulty="qiyin",
             book_links_json=links("Adabiyot 10-sinf, 60-bet", "Boburnoma, 1-bet", "8-sinf Tarix, 52-bet", "Zafarnoma (Shomiy), 6-bet"),
             analysis_text="Sharafiddin Ali Yazdiy «Zafarnoma»si Amir Temur yurishlarining keng manbasidir. Nizomiddin Shomiy ham shu nomdagi ilk asar muallifi, lekin maktab dasturidagi keng variant Yazdiynikidir."),
        dict(order_num=4, question_text="Amir Temur «Temur tuzuklari»da davlatni nechta tabaqaga bo'lib boshqarishni tavsiya qiladi?",
             option_a="12", option_b="4", option_c="7", option_d="3",
             correct_option=0, topic="Davlat boshqaruvi", direction="Davlat tuzumi", difficulty="qiyin",
             book_links_json=links("Temur tuzuklari, 18-bet", "7-sinf O'zbekiston tarixi, 96-bet", "8-sinf Tarix, 33-bet", "Huquq 10-sinf, 11-bet"),
             analysis_text="Tuzuklarda saltanat 12 tabaqa asosida tartibga solinadi."),
    ]
    huquq_specs = [
        dict(order_num=1, question_text="O'zbekiston Respublikasining amaldagi Konstitutsiyasi qachon qabul qilingan?",
             option_a="1991-yil 1-sentabr", option_b="1992-yil 8-dekabr", option_c="1993-yil 2-iyul", option_d="2000-yil 27-yanvar",
             correct_option=1, topic="Konstitutsiya", direction="Davlat huquqi", difficulty="oson",
             book_links_json=links("Huquq 11-sinf, 14-bet", "Konstitutsiya, muqaddima", "Huquq 11-sinf, 20-bet", "Saylov kodeksi, 3-bet"),
             analysis_text="Konstitutsiya 1992-yil 8-dekabrda qabul qilingan."),
        dict(order_num=2, question_text="Oliy Majlisning quyi palatasi qanday nomlanadi?",
             option_a="Senat", option_b="Vazirlar Mahkamasi", option_c="Qonunchilik palatasi", option_d="Oliy sud",
             correct_option=2, topic="Davlat hokimiyati", direction="Davlat huquqi", difficulty="orta",
             book_links_json=links("Konstitutsiya, 76-modda izohi", "Huquq 11-sinf, 41-bet", "Konstitutsiya, IX bo'lim", "Huquq 11-sinf, 55-bet"),
             analysis_text="Oliy Majlis Qonunchilik palatasi va Senatdan iborat."),
        dict(order_num=3, question_text="Fuqaro necha yoshdan to'liq muomala layoqatiga ega bo'ladi?",
             option_a="14", option_b="16", option_c="18", option_d="21",
             correct_option=2, topic="Fuqarolik layoqati", direction="Fuqarolik huquqi", difficulty="oson",
             book_links_json=links("Fuqarolik kodeksi, 22-modda", "Huquq 10-sinf, 30-bet", "Fuqarolik kodeksi, 27-modda", "Mehnat kodeksi, 77-modda"),
             analysis_text="To'liq muomala layoqati 18 yoshga to'lganda vujudga keladi."),
    ]

    def add_questions(quiz, specs):
        beta_by_label = {"oson": 1.4, "orta": 2.1, "qiyin": 2.9}
        rows = []
        for spec in specs:
            prepared = dict(spec)
            prepared.setdefault("difficulty_beta", beta_by_label.get(prepared.get("difficulty"), 2.0))
            if prepared.get("book_links_json") and not prepared.get("option_sources"):
                prepared["option_sources"] = prepared["book_links_json"]
            if prepared.get("analysis_text") and not prepared.get("solution_text"):
                prepared["solution_text"] = prepared["analysis_text"]
            row = ExamQuestion(quiz_id=quiz.id, **prepared)
            session.add(row)
            rows.append(row)
        return rows

    milliy_rows = add_questions(quiz_milliy, milliy_specs)
    add_questions(quiz_bmba, bmba_specs)
    add_questions(quiz_huquq, huquq_specs)
    await session.flush()

    def _region_key(fragment):
        for key in REGIONS_DATA:
            if fragment in key:
                return key
        return fragment

    def _district_name(region_key, fragment):
        for name in REGIONS_DATA.get(region_key, []):
            if fragment in name:
                return name
        return fragment

    xorazm = _region_key("Xorazm")
    fargona = _region_key("Farg")
    samarqand = _region_key("Samarqand")
    buxoro = _region_key("Buxoro")
    namangan = _region_key("Namangan")
    toshkent = _region_key("Toshkent shahri")
    andijon = _region_key("Andijon")
    people = [
        (9001006, "Sevara Yusupova", xorazm, _district_name(xorazm, "Urganch shahri"), set()),
        (9001003, "Nilufar Rahimova", fargona, _district_name(fargona, "qon shahri"), {3}),
        (9001002, "Jasur Toshpo'latov", samarqand, _district_name(samarqand, "Urgut"), {3, 5}),
        (9001005, "Dilshod Nurmatov", buxoro, _district_name(buxoro, "Buxoro shahri"), {2, 5}),
        (9001007, "Akmal Qodirov", namangan, _district_name(namangan, "Namangan shahri"), {1, 3, 5}),
        (9001001, "Madina Karimova", toshkent, _district_name(toshkent, "Chilonzor"), {2, 3, 4}),
        (9001004, "Bekzod Aliyev", andijon, _district_name(andijon, "Asaka"), {1, 2, 3, 4}),
    ]
    for tg_id, name, region, district, wrong in people:
        await _ensure_named_user(session, tg_id, name, region, district)
        answers = _answers_payload(milliy_rows, wrong)
        score, total, percent = _score_answers(milliy_rows, {int(k): v for k, v in answers.items()})
        session.add(ExamSubmission(
            quiz_id=quiz_milliy.id,
            user_id=tg_id,
            full_name=name,
            region=region,
            district=district,
            score=score,
            total_questions=total,
            percent=percent,
            answers_json=json.dumps(answers),
            mode="elektron",
            level_label=_exam_level(percent),
            created_at=datetime(2026, 10, 12, 9, tg_id % 50, 0),
        ))

    yunusobod = _district_name(toshkent, "Yunusobod")
    current = await _ensure_named_user(
        session, 84920194, "Jahongir", toshkent, yunusobod
    )
    current_region = current.region if current.region and current.region not in ("O'zbekiston", "Tanlanmagan") else toshkent
    current_district = current.district if current.district and current.district not in ("Tanlanmagan",) else yunusobod
    current_name = current.full_name or "Jahongir"
    current_answers = _answers_payload(milliy_rows, {3, 5})
    score, total, percent = _score_answers(milliy_rows, {int(k): v for k, v in current_answers.items()})
    session.add(ExamSubmission(
        quiz_id=quiz_milliy.id,
        user_id=current.telegram_id,
        full_name=current_name,
        region=current_region,
        district=current_district,
        score=score,
        total_questions=total,
        percent=percent,
        answers_json=json.dumps(current_answers),
        mode="elektron",
        level_label=_exam_level(percent),
        created_at=datetime(2026, 10, 16, 18, 0, 0),
    ))

    for tg_id, stars in ((9001006, 5), (9001003, 5), (9001002, 4), (84920194, 4), (9001001, 3), (9001004, 5)):
        session.add(ExamRating(quiz_id=quiz_milliy.id, user_id=tg_id, stars=stars))
    session.add(ExamRating(quiz_id=quiz_bmba.id, user_id=84920194, stars=5))
    session.add(ExamRating(quiz_id=quiz_huquq.id, user_id=9001002, stars=4))
    await session.commit()
    await _ensure_ona_tili_essay_seed(session)


async def _load_quiz(session, quiz_id: int) -> ExamQuiz:
    quiz = (
        await session.execute(select(ExamQuiz).where(ExamQuiz.id == quiz_id, ExamQuiz.is_active == True))
    ).scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return quiz


async def _load_questions(session, quiz_id: int) -> list:
    rows = (
        await session.execute(
            select(ExamQuestion).where(ExamQuestion.quiz_id == quiz_id).order_by(ExamQuestion.order_num.asc())
        )
    ).scalars().all()
    return list(rows)


async def _rating_stats(session, quiz_id: int, telegram_id: Optional[int] = None) -> dict:
    avg_value, votes = (
        await session.execute(
            select(func.avg(ExamRating.stars), func.count(ExamRating.id)).where(ExamRating.quiz_id == quiz_id)
        )
    ).one()
    my_stars = None
    if telegram_id:
        mine = (
            await session.execute(
                select(ExamRating.stars).where(
                    ExamRating.quiz_id == quiz_id,
                    ExamRating.user_id == telegram_id,
                )
            )
        ).scalar_one_or_none()
        my_stars = int(mine) if mine is not None else None
    return {
        "avg_rating": round(float(avg_value), 2) if avg_value is not None else 0.0,
        "votes": int(votes or 0),
        "my_stars": my_stars,
    }


async def _participant_count(session, quiz_id: int) -> int:
    value = (
        await session.execute(
            select(func.count(func.distinct(ExamSubmission.user_id))).where(ExamSubmission.quiz_id == quiz_id)
        )
    ).scalar()
    return int(value or 0)


def _best_submissions(rows: list) -> list:
    best = {}
    for row in rows:
        current = best.get(row.user_id)
        if current is None or (row.percent or 0, row.score or 0, row.id or 0) > (
            current.percent or 0, current.score or 0, current.id or 0
        ):
            best[row.user_id] = row
    ordered = list(best.values())
    ordered.sort(key=lambda item: (-(item.percent or 0), -(item.score or 0), item.created_at or datetime.min, item.id or 0))
    return ordered


def _place_label(region: Optional[str], district: Optional[str]) -> str:
    region_name = region or "—"
    district_name = district or "—"
    if district_name.startswith(region_name):
        return district_name
    return f"{region_name}, {district_name}"


def _public_rank_label(rank: Optional[int], has_submission: bool, filtered_out: bool) -> str:
    if not has_submission:
        return "Siz hali bu testda ishtirok etmadingiz"
    if filtered_out or not rank:
        return "Siz ushbu filtrda ishtirok etmagansiz"
    return f"Siz {rank}-o'rindasiz"


def _exam_rash_label(theta, level: Optional[str] = None) -> str:
    if theta is None:
        return "—"
    try:
        value = f"{float(theta):.2f}"
        grade = (level or "").strip()
        if not grade or grade in ("Boshlang'ich", "Bilimdon", "Ustoz"):
            grade = _rasch_grade(float(theta))
        return f"{value} ({grade})"
    except (TypeError, ValueError):
        return "—"


def _exam_rank_banner(
    *,
    has_submission: bool,
    mine,
    my_rank: Optional[int],
    region_name: str,
    district_name: str,
    user_region: str,
    user_district: str,
) -> dict:
    ball = int(mine.score or 0) if mine else None
    theta = mine.ability_theta if mine else None
    level = (mine.level_label if mine else None) or None
    if theta is not None and (not level or level in ("Boshlang'ich", "Bilimdon", "Ustoz")):
        try:
            level = _rasch_grade(float(theta))
        except Exception:
            pass
    rash = _exam_rash_label(theta, level)

    if not has_submission:
        return {
            "scope": "none",
            "belongs": False,
            "my_rank": None,
            "ball": None,
            "theta": None,
            "level": None,
            "rash": None,
            "my_label": "Siz hali bu testda ishtirok etmadingiz",
        }

    if district_name:
        belongs = bool(user_district) and (
            user_district == district_name
            or user_district.endswith(district_name)
            or district_name in user_district
        )
        if not belongs:
            return {
                "scope": "foreign",
                "belongs": False,
                "my_rank": None,
                "ball": ball,
                "theta": theta,
                "level": level,
                "rash": rash,
                "my_label": "Siz bu hududga tegishli emassiz",
            }
        return {
            "scope": "district",
            "belongs": True,
            "my_rank": my_rank,
            "ball": ball,
            "theta": theta,
            "level": level,
            "rash": rash,
            "my_label": (
                f"Siz tuman reytingida: {my_rank}-o'rindasiz · {ball} ball"
                + (f" · RASH {rash}" if theta is not None else "")
                if my_rank else "Siz ushbu tuman filtrida topilmadingiz"
            ),
        }

    if region_name:
        belongs = bool(user_region) and (
            user_region == region_name
            or user_region.startswith(region_name)
            or region_name in user_region
        )
        if not belongs:
            return {
                "scope": "foreign",
                "belongs": False,
                "my_rank": None,
                "ball": ball,
                "theta": theta,
                "level": level,
                "rash": rash,
                "my_label": "Siz bu hududga tegishli emassiz",
            }
        return {
            "scope": "region",
            "belongs": True,
            "my_rank": my_rank,
            "ball": ball,
            "theta": theta,
            "level": level,
            "rash": rash,
            "my_label": (
                f"Siz viloyat reytingida: {my_rank}-o'rindasiz · {ball} ball"
                + (f" · RASH {rash}" if theta is not None else "")
                if my_rank else "Siz ushbu viloyat filtrida topilmadingiz"
            ),
        }

    return {
        "scope": "global",
        "belongs": True,
        "my_rank": my_rank,
        "ball": ball,
        "theta": theta,
        "level": level,
        "rash": rash,
        "my_label": (
            f"Siz umumiy reytingda: {my_rank}-o'rindasiz · {ball} ball"
            + (f" · RASH {rash}" if theta is not None else "")
            if my_rank else "Siz hali bu testda ishtirok etmadingiz"
        ),
    }


@app.get("/api/exams/list")
async def exams_list(
    subject: str = "tarix",
    exam_type: str = "milliy_sertifikat",
    telegram_id: Optional[str] = None,
):
    tg_id = _coerce_telegram_id(telegram_id)
    async with async_session() as session:
        await _ensure_exam_seed(session)
        rows = (
            await session.execute(
                select(ExamQuiz).where(
                    ExamQuiz.is_active == True,
                    ExamQuiz.subject == subject,
                    ExamQuiz.exam_type == exam_type,
                ).order_by(ExamQuiz.announced_at.desc())
            )
        ).scalars().all()
        now = _exam_now()
        owned = await _owned_course_ids(session, tg_id)
        shared = await _user_has_shared(session, tg_id)
        items = []
        for quiz in rows:
            window = _quiz_window(quiz, now)
            if window == "hidden":
                continue
            seconds_left, starts_label = _starts_countdown(quiz.starts_at, now) if window == "scheduled" else (0, "")
            pricing = _price_for_user(quiz, owned, shared)
            stats = await _rating_stats(session, quiz.id, tg_id)
            q_count = (
                await session.execute(
                    select(func.count(ExamQuestion.id)).where(ExamQuestion.quiz_id == quiz.id)
                )
            ).scalar() or 0
            items.append({
                "id": quiz.id,
                "title": quiz.title,
                "subject": quiz.subject,
                "subject_label": EXAM_SUBJECTS.get(quiz.subject, quiz.subject),
                "exam_type": quiz.exam_type,
                "exam_type_label": EXAM_TYPES.get(quiz.exam_type, quiz.exam_type),
                "price": pricing["price"],
                "base_price": pricing["base_price"],
                "discount_percent": pricing["discount_percent"],
                "free_reason": pricing["free_reason"],
                "access": window,
                "starts_at": quiz.starts_at.isoformat() if quiz.starts_at else None,
                "visible_at": quiz.visible_at.isoformat() if quiz.visible_at else None,
                "starts_in_seconds": seconds_left,
                "starts_in_label": starts_label,
                "command_path": quiz.command_path,
                "link": quiz.link,
                "pdf_url": quiz.pdf_url,
                "answer_sheet_url": quiz.answer_sheet_url,
                "announced_at": quiz.announced_at.isoformat() if quiz.announced_at else None,
                "announced_label": quiz.announced_at.strftime("%d.%m.%Y") if quiz.announced_at else "",
                "participants": await _participant_count(session, quiz.id),
                "duration_minutes": quiz.duration_minutes or 20,
                "questions_count": q_count,
                "is_essay": _is_essay_quiz(quiz),
                "scoring_model": "rasch_75" if _is_essay_quiz(quiz) else "rasch_mcq",
                **stats,
            })
        return {"items": items, "subject": subject, "exam_type": exam_type}


@app.post("/api/exams/rate")
async def exams_rate(payload: ExamRateSchema):
    stars = int(payload.stars)
    if stars < 1 or stars > 5:
        raise HTTPException(status_code=400, detail="Baho 1 dan 5 gacha bo'lishi kerak")
    async with async_session() as session:
        await _ensure_exam_seed(session)
        await _load_quiz(session, payload.quiz_id)
        row = (
            await session.execute(
                select(ExamRating).where(
                    ExamRating.quiz_id == payload.quiz_id,
                    ExamRating.user_id == payload.telegram_id,
                )
            )
        ).scalar_one_or_none()
        if row:
            row.stars = stars
        else:
            session.add(ExamRating(quiz_id=payload.quiz_id, user_id=payload.telegram_id, stars=stars))
        await session.commit()
        stats = await _rating_stats(session, payload.quiz_id, payload.telegram_id)
        return {"status": "ok", **stats}


@app.get("/api/exams/questions/{quiz_id}")
async def exams_questions(quiz_id: int):
    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, quiz_id)
        _ensure_quiz_open(quiz)
        questions = await _load_questions(session, quiz_id)
        return {
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "duration_minutes": quiz.duration_minutes or 20,
                "price": _quiz_base_amount(quiz),
                "link": quiz.link,
                "pdf_url": quiz.pdf_url,
                "answer_sheet_url": quiz.answer_sheet_url,
                "subject_label": EXAM_SUBJECTS.get(quiz.subject, quiz.subject),
                "exam_type_label": EXAM_TYPES.get(quiz.exam_type, quiz.exam_type),
            },
            "questions": [
                {
                    "id": question.id,
                    "order_num": question.order_num,
                    "order": question.order_num,
                    "question_text": question.question_text,
                    "text": question.question_text,
                    "image_top": question.image_top,
                    "image_bottom": question.image_bottom,
                    "options": [question.option_a, question.option_b, question.option_c, question.option_d],
                }
                for question in questions
            ],
        }


def _normalize_answer_map(raw: dict) -> dict:
    parsed = {}
    if not isinstance(raw, dict):
        return parsed
    for key, value in raw.items():
        try:
            parsed[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return parsed


def _simulate_scan_answers(questions: list, image_base64: str) -> dict:
    seed = len(image_base64 or "") % 97
    answers = {}
    for index, question in enumerate(questions):
        if (index + seed) % 4 == 0:
            answers[question.id] = (question.correct_option + 1 + (seed % 3)) % 4
        else:
            answers[question.id] = question.correct_option
    return answers


@app.post("/api/exams/submit-multipage-essay")
async def exams_submit_multipage_essay(payload: ExamEssaySubmitSchema):
    """Ona tili Milliy sertifikat esse: ko'p sahifali qo'lyozma → Gemini Vision → Rasch 75."""
    images = []
    for item in (payload.images or []) + (payload.images_base64 or []):
        if isinstance(item, str) and item.strip():
            images.append(item.strip())
    if not images:
        raise HTTPException(status_code=400, detail="Kamida bitta rasm yuboring (titul yoki esse)")

    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, payload.quiz_id)
        _ensure_quiz_open(quiz)
        if not _is_essay_quiz(quiz):
            raise HTTPException(status_code=400, detail="Bu test esse (Rasch 75) formatida emas")

        essay = await _gemini_grade_essay_images(images)
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=payload.telegram_id,
                full_name=f"O'quvchi {payload.telegram_id}",
                region="Toshkent shahri",
                district="Yunusobod tumani",
                selected_subject=quiz.subject or "ona_tili",
            )
            session.add(user)
            await session.flush()
        region = user.region if user.region and user.region not in ("Tanlanmagan",) else "Toshkent shahri"
        district = user.district if user.district and user.district not in ("Tanlanmagan",) else "Yunusobod tumani"
        rash = float(essay["rash_score"])
        percent = round((rash / ESSAY_RASH_MAX) * 100, 1) if ESSAY_RASH_MAX else 0.0
        stored = {
            "kind": "essay_rasch",
            "pages": len(images),
            "raw_score": essay["raw_score"],
            "rash_score": essay["rash_score"],
            "theta": essay["theta"],
            "level": essay["level"],
            "certificate": essay["certificate"],
            "criteria": essay["criteria"],
            "spelling_errors": essay["spelling_errors"],
            "feedback": essay["feedback"],
            "max_raw": ESSAY_RAW_MAX,
            "max_rash": ESSAY_RASH_MAX,
        }
        submission = ExamSubmission(
            quiz_id=quiz.id,
            user_id=payload.telegram_id,
            full_name=user.full_name or f"O'quvchi {payload.telegram_id}",
            region=region,
            district=district,
            score=int(round(rash)),
            total_questions=int(ESSAY_RASH_MAX),
            percent=percent,
            ability_theta=float(essay["theta"]),
            answers_json=json.dumps(stored, ensure_ascii=False),
            mode="skaner",
            level_label=essay["level"],
        )
        session.add(submission)
        await session.commit()

        all_rows = (
            await session.execute(select(ExamSubmission).where(ExamSubmission.quiz_id == quiz.id))
        ).scalars().all()
        ranking = _best_submissions(list(all_rows))
        rank = next((index + 1 for index, row in enumerate(ranking) if row.user_id == payload.telegram_id), None)
        return {
            "status": "ok",
            "submission_id": submission.id,
            "kind": "essay_rasch",
            "raw_score": essay["raw_score"],
            "rash_score": essay["rash_score"],
            "theta": essay["theta"],
            "level": essay["level"],
            "grade": essay["level"],
            "certificate": essay["certificate"],
            "score": int(round(rash)),
            "total": int(ESSAY_RASH_MAX),
            "percent": percent,
            "criteria": essay["criteria"],
            "spelling_errors": essay["spelling_errors"],
            "feedback": essay["feedback"],
            "diagnostics": essay["criteria"],
            "mode": "skaner",
            "rank": rank,
            "rank_label": _public_rank_label(rank, True, False),
            "participants": len(ranking),
            "analysis_text": quiz.analysis_text or ONA_TILI_ESSAY_ANALYSIS,
        }


@app.post("/api/exams/submit")
async def exams_submit(payload: ExamSubmitSchema):
    mode = (payload.mode or "elektron").strip().lower()
    if mode not in ("elektron", "skaner", "qogoz"):
        raise HTTPException(status_code=400, detail="Noto'g'ri rejim")
    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, payload.quiz_id)
        _ensure_quiz_open(quiz)
        if _is_essay_quiz(quiz):
            raise HTTPException(
                status_code=400,
                detail="Esse imtihoni uchun /api/exams/submit-multipage-essay endpointidan foydalaning",
            )
        questions = await _load_questions(session, quiz.id)
        answers = _normalize_answer_map(payload.answers or {})
        simulated = False
        if mode == "skaner" and not answers:
            answers = _simulate_scan_answers(questions, payload.image_base64 or "")
            simulated = True
        score, total, percent, theta, level = _evaluate_exam(questions, answers)
        user = (
            await session.execute(select(User).where(User.telegram_id == payload.telegram_id))
        ).scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=payload.telegram_id,
                full_name=f"O'quvchi {payload.telegram_id}",
                region="Toshkent shahri",
                district="Yunusobod tumani",
                selected_subject=quiz.subject or "tarix",
            )
            session.add(user)
            await session.flush()
        region = user.region if user.region and user.region not in ("Tanlanmagan",) else "Toshkent shahri"
        district = user.district if user.district and user.district not in ("Tanlanmagan",) else "Yunusobod tumani"
        stored = {str(key): value for key, value in answers.items()}
        submission = ExamSubmission(
            quiz_id=quiz.id,
            user_id=payload.telegram_id,
            full_name=user.full_name or f"O'quvchi {payload.telegram_id}",
            region=region,
            district=district,
            score=score,
            total_questions=total,
            percent=percent,
            ability_theta=theta,
            answers_json=json.dumps(stored),
            mode=mode,
            level_label=level,
        )
        session.add(submission)
        await session.commit()

        all_rows = (
            await session.execute(select(ExamSubmission).where(ExamSubmission.quiz_id == quiz.id))
        ).scalars().all()
        ranking = _best_submissions(list(all_rows))
        rank = next((index + 1 for index, row in enumerate(ranking) if row.user_id == payload.telegram_id), None)
        return {
            "status": "ok",
            "submission_id": submission.id,
            "score": score,
            "total": total,
            "percent": percent,
            "theta": theta,
            "grade": level,
            "level": level,
            "mode": mode,
            "scan_simulated": simulated,
            "rank": rank,
            "rank_label": _public_rank_label(rank, True, False),
            "participants": len(ranking),
        }


@app.get("/api/exams/paper/{quiz_id}")
async def exams_paper(
    quiz_id: int,
    telegram_id: Optional[str] = None,
    kind: str = "test",
    download: int = 0,
):
    kind = "answers" if kind == "answers" else "test"
    tg_id = _coerce_telegram_id(telegram_id)
    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, quiz_id)
        _ensure_quiz_open(quiz)
        questions = await _load_questions(session, quiz_id)
        user = None
        if tg_id:
            user = (
                await session.execute(select(User).where(User.telegram_id == tg_id))
            ).scalar_one_or_none()
        watermark = None
        if kind == "test":
            name = (user.full_name if user and user.full_name else None) or (f"ID {tg_id}" if tg_id else "PHAROS o'quvchi")
            watermark = f"PHAROS | {name} | ID {tg_id or '-'}"
        title = quiz.title if kind == "test" else f"{quiz.title} — javoblar varaqasi"
        pdf_bytes = _build_simple_pdf(title, _quiz_pdf_lines(quiz, questions, kind), watermark)
        filename = f"pharos-{'javoblar' if kind == 'answers' else 'test'}-{quiz_id}.pdf"
        disposition = "attachment" if download else "inline"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"{disposition}; filename=\"{filename}\""},
        )


@app.get("/api/exams/leaderboard/{quiz_id}")
async def exams_leaderboard(
    quiz_id: int,
    telegram_id: Optional[str] = None,
    region: str = "",
    district: str = "",
):
    tg_id = _coerce_telegram_id(telegram_id)
    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, quiz_id)
        rows = (
            await session.execute(select(ExamSubmission).where(ExamSubmission.quiz_id == quiz.id))
        ).scalars().all()
        best = _best_submissions(list(rows))
        mine = next((row for row in best if tg_id and row.user_id == tg_id), None)
        user_region = (mine.region if mine else "") or ""
        user_district = (mine.district if mine else "") or ""
        if tg_id and (not user_region or not user_district):
            profile = (
                await session.execute(select(User).where(User.telegram_id == tg_id))
            ).scalar_one_or_none()
            if profile:
                user_region = user_region or (profile.region or "")
                user_district = user_district or (profile.district or "")
        region_name = (region or "").strip()
        district_name = (district or "").strip()
        filtered = best
        if region_name:
            filtered = [row for row in filtered if (row.region or "") == region_name]
        if district_name:
            filtered = [
                row for row in filtered
                if (row.district or "") == district_name
                or str(row.district or "").endswith(district_name)
            ]
        essay_mode = _is_essay_quiz(quiz)
        items = []
        my_rank = None
        for index, row in enumerate(filtered, start=1):
            if tg_id and row.user_id == tg_id:
                my_rank = index
            theta = row.ability_theta
            level = row.level_label or _exam_level(row.percent or 0)
            essay_rash = None
            if row.answers_json:
                try:
                    stored = json.loads(row.answers_json)
                    if isinstance(stored, dict) and stored.get("kind") == "essay_rasch":
                        essay_rash = stored.get("rash_score")
                        level = stored.get("level") or level
                        if stored.get("theta") is not None:
                            theta = stored.get("theta")
                except Exception:
                    pass
            if not essay_mode and theta is not None and level in ("Boshlang'ich", "Bilimdon", "Ustoz", None, ""):
                try:
                    level = _rasch_grade(float(theta))
                except Exception:
                    pass
            ball = int(row.score or 0)
            if essay_rash is not None:
                try:
                    ball = round(float(essay_rash), 1)
                except (TypeError, ValueError):
                    pass
                rash_label = f"{float(essay_rash):.1f} ({level})"
            elif essay_mode:
                rash_label = f"{ball} ({level})" if level else str(ball)
            else:
                rash_label = _exam_rash_label(theta, level)
            items.append({
                "rank": index,
                "telegram_id": row.user_id,
                "full_name": row.full_name or f"O'quvchi {row.user_id}",
                "region": row.region or "—",
                "district": row.district or "—",
                "place": _place_label(row.region, row.district),
                "ball": ball,
                "score": ball,
                "total": int(ESSAY_RASH_MAX) if essay_mode else (row.total_questions or 0),
                "percent": row.percent or 0,
                "theta": theta,
                "level": level,
                "rash": rash_label,
                "rash_score": essay_rash,
            })
        banner = _exam_rank_banner(
            has_submission=mine is not None,
            mine=mine,
            my_rank=my_rank,
            region_name=region_name,
            district_name=district_name,
            user_region=user_region,
            user_district=user_district,
        )
        return {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "my_rank": banner["my_rank"],
            "my_label": banner["my_label"],
            "my_ball": banner["ball"],
            "my_theta": banner["theta"],
            "my_level": banner["level"],
            "my_rash": banner["rash"],
            "my_scope": banner["scope"],
            "belongs_to_filter": banner["belongs"],
            "user_region": user_region or None,
            "user_district": user_district or None,
            "has_submission": mine is not None,
            "regions_map": REGIONS_DATA,
            "items": items,
        }


@app.get("/api/exams/analysis/{quiz_id}")
async def exams_analysis(quiz_id: int, telegram_id: Optional[str] = None):
    tg_id = _coerce_telegram_id(telegram_id)
    async with async_session() as session:
        await _ensure_exam_seed(session)
        quiz = await _load_quiz(session, quiz_id)
        if _quiz_window(quiz) == "hidden":
            raise HTTPException(status_code=404, detail="Test topilmadi")
        if _quiz_window(quiz) == "scheduled":
            _seconds, label = _starts_countdown(quiz.starts_at, _exam_now())
            return {
                "quiz_id": quiz.id,
                "title": quiz.title,
                "locked": True,
                "lock_message": f"Tahlil test boshlangach ochiladi. Boshlanishiga: {label} qoldi",
                "analysis_text": "",
                "full_analysis_video": None,
                "has_submission": False,
                "score": None,
                "total": 0,
                "percent": None,
                "theta": None,
                "level": None,
                "mode": None,
                "questions": [],
                "diagnostics": [],
            }
        questions = await _load_questions(session, quiz_id)
        submission = None
        if tg_id:
            rows = (
                await session.execute(
                    select(ExamSubmission).where(
                        ExamSubmission.quiz_id == quiz.id,
                        ExamSubmission.user_id == tg_id,
                    ).order_by(ExamSubmission.created_at.desc())
                )
            ).scalars().all()
            submission = rows[0] if rows else None

        essay_payload = None
        if submission and submission.answers_json:
            try:
                raw_payload = json.loads(submission.answers_json)
                if isinstance(raw_payload, dict) and raw_payload.get("kind") == "essay_rasch":
                    essay_payload = raw_payload
            except Exception:
                essay_payload = None

        if essay_payload or _is_essay_quiz(quiz):
            rash_score = None
            raw_score = None
            level = submission.level_label if submission else None
            theta = submission.ability_theta if submission else None
            criteria = []
            spelling_errors = []
            feedback = quiz.analysis_text or ONA_TILI_ESSAY_ANALYSIS
            if essay_payload:
                rash_score = essay_payload.get("rash_score")
                raw_score = essay_payload.get("raw_score")
                level = essay_payload.get("level") or level
                theta = essay_payload.get("theta", theta)
                criteria = essay_payload.get("criteria") or []
                spelling_errors = essay_payload.get("spelling_errors") or []
                feedback = essay_payload.get("feedback") or feedback
            elif submission:
                rash_score = float(submission.score or 0)
                raw_score = None
            return {
                "quiz_id": quiz.id,
                "title": quiz.title,
                "kind": "essay_rasch",
                "is_essay": True,
                "analysis_text": quiz.analysis_text or ONA_TILI_ESSAY_ANALYSIS,
                "full_analysis_video": quiz.full_analysis_video,
                "locked": False,
                "lock_message": "",
                "has_submission": submission is not None,
                "score": submission.score if submission else None,
                "total": int(ESSAY_RASH_MAX),
                "percent": submission.percent if submission else None,
                "theta": theta,
                "raw_score": raw_score,
                "rash_score": rash_score,
                "level": level,
                "certificate": bool(essay_payload.get("certificate")) if essay_payload else None,
                "mode": submission.mode if submission else None,
                "criteria": criteria,
                "spelling_errors": spelling_errors,
                "feedback": feedback,
                "questions": [],
                "diagnostics": criteria,
                "max_rash": ESSAY_RASH_MAX,
                "max_raw": ESSAY_RAW_MAX,
            }

        chosen_map = {}
        if submission and submission.answers_json:
            try:
                raw = json.loads(submission.answers_json)
                chosen_map = {int(key): int(value) for key, value in raw.items()}
            except Exception:
                chosen_map = {}

        question_items = []
        grouped = {}
        for question in questions:
            sources = _exam_links(question.option_sources) or _exam_links(question.book_links_json)
            solution = (question.solution_text or question.analysis_text or "").strip()
            options = [question.option_a, question.option_b, question.option_c, question.option_d]
            user_index = chosen_map.get(question.id)
            is_wrong = user_index is not None and user_index != question.correct_option
            is_blank = submission is not None and user_index is None
            missed = is_wrong or is_blank
            option_rows = []
            for index, text in enumerate(options):
                key = EXAM_OPTION_KEYS[index]
                option_rows.append({
                    "index": index,
                    "key": key,
                    "text": text,
                    "source": sources.get(key) or sources.get(key.lower()) or "",
                    "is_correct": index == question.correct_option,
                    "is_user_choice": user_index == index,
                })
            question_items.append({
                "id": question.id,
                "order": question.order_num,
                "text": question.question_text,
                "question_text": question.question_text,
                "image_top": question.image_top,
                "image_bottom": question.image_bottom,
                "solution_text": solution,
                "video_solution_url": question.video_solution_url,
                "options": option_rows,
                "correct_index": question.correct_option,
                "correct_key": EXAM_OPTION_KEYS[question.correct_option],
                "user_index": user_index,
                "user_key": EXAM_OPTION_KEYS[user_index] if user_index is not None and 0 <= user_index <= 3 else None,
                "is_correct": user_index is not None and user_index == question.correct_option,
                "answered": user_index is not None,
                "topic": question.topic or "Mavzu ko'rsatilmagan",
                "direction": question.direction or "Yo'nalish ko'rsatilmagan",
                "difficulty": question.difficulty or "orta",
                "difficulty_label": EXAM_DIFFICULTY_LABELS.get(question.difficulty or "orta", question.difficulty or "O'rta"),
                "analysis_text": solution,
            })
            bucket_key = (question.direction or "—", question.topic or "—", question.difficulty or "orta")
            bucket = grouped.setdefault(bucket_key, {"total": 0, "wrong": 0})
            bucket["total"] += 1
            if missed or (submission is None):
                if submission is not None and missed:
                    bucket["wrong"] += 1
        diagnostics = []
        for (direction, topic, difficulty), bucket in grouped.items():
            total = bucket["total"]
            wrong = bucket["wrong"] if submission is not None else 0
            mastery = round(((total - wrong) / total) * 100, 1) if total and submission is not None else None
            diagnostics.append({
                "direction": direction,
                "topic": topic,
                "difficulty": difficulty,
                "difficulty_label": EXAM_DIFFICULTY_LABELS.get(difficulty, difficulty),
                "total": total,
                "wrong": wrong,
                "mastery": mastery,
            })
        return {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "kind": "mcq",
            "is_essay": False,
            "analysis_text": quiz.analysis_text or "",
            "full_analysis_video": quiz.full_analysis_video,
            "locked": False,
            "lock_message": "",
            "has_submission": submission is not None,
            "score": submission.score if submission else None,
            "total": submission.total_questions if submission else len(questions),
            "percent": submission.percent if submission else None,
            "theta": submission.ability_theta if submission else None,
            "level": submission.level_label if submission else None,
            "mode": submission.mode if submission else None,
            "questions": question_items,
            "diagnostics": diagnostics,
        }


@app.get("/api/exams/student/{telegram_id}")
async def exams_student(telegram_id: int, quiz_id: Optional[int] = None):
    async with async_session() as session:
        await _ensure_exam_seed(session)
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        rows = (
            await session.execute(
                select(ExamSubmission).where(ExamSubmission.user_id == telegram_id).order_by(ExamSubmission.percent.desc())
            )
        ).scalars().all()
        best = rows[0] if rows else None
        quiz_row = None
        quiz_rank = None
        if quiz_id:
            quiz_rows = (
                await session.execute(select(ExamSubmission).where(ExamSubmission.quiz_id == quiz_id))
            ).scalars().all()
            ordered = _best_submissions(list(quiz_rows))
            for index, row in enumerate(ordered, start=1):
                if row.user_id == telegram_id:
                    quiz_row = row
                    quiz_rank = index
                    break
        source = quiz_row or best
        return {
            "telegram_id": telegram_id,
            "full_name": (user.full_name if user and user.full_name else None) or (source.full_name if source else None) or f"O'quvchi {telegram_id}",
            "region": (user.region if user and user.region else None) or (source.region if source else None) or "—",
            "district": (user.district if user and user.district else None) or (source.district if source else None) or "—",
            "avatar_url": user.avatar_url if user else None,
            "exams_taken": len({row.quiz_id for row in rows}),
            "attempts": len(rows),
            "best_percent": best.percent if best else None,
            "level": (quiz_row.level_label if quiz_row else None) or (best.level_label if best else "Boshlang'ich"),
            "quiz_rank": quiz_rank,
            "quiz_score": quiz_row.score if quiz_row else None,
            "quiz_total": quiz_row.total_questions if quiz_row else None,
            "quiz_percent": quiz_row.percent if quiz_row else None,
        }


# ==========================================================
# MASTER BAZA API (Ovozli savol-javob / Mini App)
# ==========================================================
def _master_fact_to_dict(row: MasterFactQuestion) -> dict:
    return {
        "id": row.id,
        "fakt_id": row.fakt_id,
        "test_id": row.test_id,
        "grade": row.grade,
        "topic_num": row.topic_num,
        "asl_gap": row.asl_gap,
        "fakt_kontekst": row.fakt_kontekst,
        "savol_matni": row.savol_matni,
        "test_matni": row.test_matni,
        "test_obyekt": row.test_obyekt,
        "etalon_javob": row.etalon_javob,
        "variant_b": row.variant_b,
        "variant_c": row.variant_c,
        "variant_d": row.variant_d,
        "kalit_soz": row.kalit_soz,
        "klass": row.klass,
        "yonalish": row.yonalish,
        "tarkibiy_faktlar": row.tarkibiy_faktlar,
        "tematik_teg": row.tematik_teg,
        "mavzu_reja": row.mavzu_reja,
    }


async def _master_grade_rows(session):
    return (
        await session.execute(
            select(
                MasterFactQuestion.grade,
                func.count(func.distinct(MasterFactQuestion.topic_num)).label("topics_count"),
                func.count(func.distinct(MasterFactQuestion.fakt_id)).label("facts_count"),
                func.count(MasterFactQuestion.id).label("questions_count"),
            )
            .group_by(MasterFactQuestion.grade)
            .order_by(MasterFactQuestion.grade)
        )
    ).all()


@app.get("/api/master/grades")
async def get_master_grades():
    """Master bazada mavjud sinflar ro'yxati."""
    try:
        await init_db()
        async with async_session() as session:
            rows = await _master_grade_rows(session)
            # Serverda import qilinmagan bo'lsa — bir marta avtomatik yuklaymiz
            if not rows:
                try:
                    from import_master_baza import import_master_baza
                    await import_master_baza(replace=False)
                    rows = await _master_grade_rows(session)
                except Exception as import_err:
                    print(f"[master/grades] avto-import xato: {import_err}")
                    return {"grades": [], "total": 0, "error": f"avto-import: {import_err}"}
    except Exception as e:
        print(f"[master/grades] xato: {e}")
        return {"grades": [], "total": 0, "error": str(e)}

    grades = [
        {
            "grade": grade,
            "title": f"{grade}-sinf",
            "topics_count": int(topics_count or 0),
            "facts_count": int(facts_count or 0),
            "questions_count": int(questions_count or 0),
        }
        for grade, topics_count, facts_count, questions_count in rows
    ]
    return {"grades": grades, "total": len(grades)}


@app.get("/api/master/topics/{grade}")
async def get_master_topics(grade: int):
    """Tanlangan sinf bo'yicha mavzular va ulardagi faktlar soni."""
    try:
        await init_db()
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(
                        MasterFactQuestion.topic_num,
                        func.count(func.distinct(MasterFactQuestion.fakt_id)).label("facts_count"),
                        func.count(MasterFactQuestion.id).label("questions_count"),
                    )
                    .where(MasterFactQuestion.grade == grade)
                    .group_by(MasterFactQuestion.topic_num)
                    .order_by(MasterFactQuestion.topic_num)
                )
            ).all()
    except Exception as e:
        print(f"[master/topics] xato: {e}")
        return {"grade": grade, "topics": [], "total_topics": 0, "error": str(e)}

    topics = [
        {
            "topic_num": topic_num,
            "title": f"Mavzu {topic_num}",
            "facts_count": int(facts_count or 0),
            "questions_count": int(questions_count or 0),
        }
        for topic_num, facts_count, questions_count in rows
    ]
    return {"grade": grade, "topics": topics, "total_topics": len(topics)}


@app.get("/api/master/facts/{grade}/{topic_num}")
async def get_master_facts(grade: int, topic_num: int):
    """Tanlangan mavzuga tegishli faktlar, asl gaplar va etalon javoblar."""
    try:
        await init_db()
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(MasterFactQuestion)
                    .where(
                        MasterFactQuestion.grade == grade,
                        MasterFactQuestion.topic_num == topic_num,
                    )
                    .order_by(MasterFactQuestion.id)
                )
            ).scalars().all()
    except Exception as e:
        print(f"[master/facts] xato: {e}")
        raise HTTPException(status_code=500, detail=f"Master baza o'qilmadi: {e}") from e

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{grade}-sinf, Mavzu {topic_num} uchun faktlar topilmadi",
        )

    return {
        "grade": grade,
        "topic_num": topic_num,
        "title": f"Mavzu {topic_num}",
        "count": len(rows),
        "facts": [_master_fact_to_dict(r) for r in rows],
    }


# ==========================================================
# SERVERNI ISHGA TUSHIRISH (HAR DOIM ENG OXIRIDA TURADI)
# ==========================================================
if __name__ == "__main__":
    uvicorn.run("web.server:app", host="127.0.0.1", port=8080, reload=True)