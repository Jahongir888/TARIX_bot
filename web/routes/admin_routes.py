"""PHAROS Admin Panel — statistika, test/yangilik CRUD va dinamik narxlar API."""
from __future__ import annotations

import json
from datetime import datetime, date
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from data.config import ADMINS, ADMIN_PANEL_TOKEN, BOT_TOKEN
from database.db import async_session
from database.models import (
    BookOrder,
    CoinTransaction,
    ExamQuestion,
    ExamQuiz,
    News,
    Product,
    User,
    UserDailyActivity,
)

router = APIRouter(tags=["admin"])

# Zaxira admin (eski handlerlar bilan moslik)
_FALLBACK_ADMINS = [1206236612]
ADMIN_ID_SET = set(ADMINS or []) | set(_FALLBACK_ADMINS)

# Brauzer uchun oddiy tokenlar (hash yo'q): admin123, ADMIN_PANEL_TOKEN, BOT_TOKEN
_SIMPLE_ADMIN_TOKENS = {"admin123", (ADMIN_PANEL_TOKEN or "").strip()}
if BOT_TOKEN:
    _SIMPLE_ADMIN_TOKENS.add(BOT_TOKEN.strip())
_SIMPLE_ADMIN_TOKENS.discard("")


# ==========================================================
# AUTH: oddiy token (admin123 / BOT_TOKEN) yoki Telegram user id
# ==========================================================
def _token_is_valid(candidate: str) -> bool:
    """Brauzer tokeni: faqat 'admin123' yoki BOT_TOKEN."""
    value = (candidate or "").strip()
    return bool(value) and value in _SIMPLE_ADMIN_TOKENS


def _parse_telegram_user_id(init_data: str) -> Optional[int]:
    """initData dan user.id ni o'qiydi (hash tekshiruvisiz)."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        user_raw = parsed.get("user")
        if not user_raw:
            return None
        user = json.loads(user_raw)
        return int(user.get("id") or 0) or None
    except Exception:
        return None


def _extract_admin_id(
    request: Request,
    token: Optional[str],
    x_telegram_init_data: Optional[str],
    authorization: Optional[str],
    x_admin_token: Optional[str],
) -> int:
    """Admin ID ni aniqlaydi yoki 401/403 qaytaradi."""
    # 1) Brauzer: ?token=admin123 yoki BOT_TOKEN / header
    candidate_token = (
        (token or "").strip()
        or (x_admin_token or "").strip()
        or ""
    )
    if authorization and authorization.lower().startswith("bearer "):
        candidate_token = candidate_token or authorization[7:].strip()

    if _token_is_valid(candidate_token):
        return next(iter(sorted(ADMIN_ID_SET)), 0)

    # 2) Telegram Mini App: initData dagi user id ADMINS da bo'lsa
    init_data = (x_telegram_init_data or "").strip()
    if not init_data:
        init_data = (request.headers.get("X-Telegram-Init-Data") or "").strip()
    if init_data:
        uid = _parse_telegram_user_id(init_data)
        if uid and uid in ADMIN_ID_SET:
            return uid
        if uid:
            raise HTTPException(status_code=403, detail="Siz admin emassiz")

    raise HTTPException(
        status_code=401,
        detail="Admin kirishi: token=admin123 yoki BOT_TOKEN",
    )


async def require_admin(
    request: Request,
    token: Optional[str] = Query(None),
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> int:
    return _extract_admin_id(
        request, token, x_telegram_init_data, authorization, x_admin_token
    )


# ==========================================================
# PYDANTIC SXEMALAR
# ==========================================================
class QuizUpdateSchema(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    exam_type: Optional[str] = None
    price: Optional[int] = None
    base_price: Optional[int] = None
    share_discount_percent: Optional[int] = None
    duration_minutes: Optional[int] = None
    command_path: Optional[str] = None
    visible_at: Optional[str] = None
    starts_at: Optional[str] = None
    full_analysis_video: Optional[str] = None
    analysis_text: Optional[str] = None
    is_active: Optional[bool] = None
    free_for_courses: Optional[str] = None


class QuizCreateSchema(BaseModel):
    title: str
    subject: str = "tarix"
    exam_type: str = "namunaviy"
    price: int = 0
    base_price: int = 0
    share_discount_percent: int = 0
    duration_minutes: int = 20
    command_path: Optional[str] = None
    is_active: bool = True


class QuestionUpdateSchema(BaseModel):
    order_num: Optional[int] = None
    question_text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_option: Optional[int] = Field(None, ge=0, le=3)
    difficulty_beta: Optional[float] = None
    video_solution_url: Optional[str] = None
    solution_text: Optional[str] = None
    topic: Optional[str] = None
    direction: Optional[str] = None
    difficulty: Optional[str] = None
    image_top: Optional[str] = None
    image_bottom: Optional[str] = None
    option_sources: Optional[str] = None


class QuestionCreateSchema(BaseModel):
    quiz_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: int = Field(0, ge=0, le=3)
    order_num: int = 1
    difficulty_beta: float = 2.0
    video_solution_url: Optional[str] = None
    solution_text: Optional[str] = None
    topic: Optional[str] = None


class NewsUpdateSchema(BaseModel):
    title: Optional[str] = None
    hashtags: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None


class NewsCreateSchema(BaseModel):
    title: str
    content: str
    hashtags: str = ""
    category: str = "umumiy"
    summary: Optional[str] = None
    image_url: str = ""
    source_url: Optional[str] = None
    source_name: str = "Manba"


class PricingItemSchema(BaseModel):
    entity: str  # "quiz" | "product"
    id: int
    price: Optional[int] = None
    base_price: Optional[int] = None
    share_discount_percent: Optional[int] = None
    price_coin: Optional[int] = None
    old_price_coin: Optional[int] = None
    is_active: Optional[bool] = None


class PricingUpdateSchema(BaseModel):
    items: list[PricingItemSchema]


def _parse_optional_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None or value == "":
        return None
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Noto'g'ri sana: {value}")


def _dt_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat(sep=" ", timespec="seconds") if value else None


def _quiz_dict(q: ExamQuiz, questions_count: int = 0) -> dict:
    return {
        "id": q.id,
        "title": q.title,
        "subject": q.subject,
        "exam_type": q.exam_type,
        "price": int(q.price or 0),
        "base_price": int(q.base_price or 0),
        "share_discount_percent": int(q.share_discount_percent or 0),
        "duration_minutes": q.duration_minutes,
        "command_path": q.command_path,
        "visible_at": _dt_iso(q.visible_at),
        "starts_at": _dt_iso(q.starts_at),
        "full_analysis_video": q.full_analysis_video,
        "analysis_text": q.analysis_text,
        "is_active": bool(q.is_active),
        "free_for_courses": q.free_for_courses or "",
        "questions_count": questions_count,
        "created_at": _dt_iso(q.created_at),
    }


def _question_dict(item: ExamQuestion) -> dict:
    return {
        "id": item.id,
        "quiz_id": item.quiz_id,
        "order_num": item.order_num,
        "question_text": item.question_text,
        "option_a": item.option_a,
        "option_b": item.option_b,
        "option_c": item.option_c,
        "option_d": item.option_d,
        "correct_option": item.correct_option,
        "difficulty_beta": float(item.difficulty_beta or 2.0),
        "video_solution_url": item.video_solution_url,
        "solution_text": item.solution_text,
        "topic": item.topic,
        "direction": item.direction,
        "difficulty": item.difficulty,
        "image_top": item.image_top,
        "image_bottom": item.image_bottom,
        "option_sources": item.option_sources,
    }


def _news_dict(n: News) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "hashtags": n.hashtags,
        "category": n.category,
        "summary": n.summary,
        "content": n.content,
        "image_url": n.image_url,
        "source_url": n.source_url,
        "source_name": n.source_name,
        "views_count": int(n.views_count or 0),
        "likes_count": int(n.likes_count or 0),
        "created_at": _dt_iso(n.created_at),
    }


# ==========================================================
# SAHIFA: GET /admin
# ==========================================================
@router.get("/admin", response_class=HTMLResponse)
async def admin_page(response: Response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "admin.html")
    if not os.path.exists(path):
        return HTMLResponse("<h3>admin.html topilmadi</h3>", status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@router.get("/api/admin/me")
async def admin_me(admin_id: int = Depends(require_admin)):
    return {"ok": True, "admin_id": admin_id, "is_admin": True}


# ==========================================================
# 1. DASHBOARD STATISTIKA
# ==========================================================
@router.get("/api/admin/stats")
async def admin_stats(admin_id: int = Depends(require_admin)):
    today = date.today()
    async with async_session() as session:
        students = (await session.execute(select(func.count(User.id)))).scalar() or 0
        today_active = (
            await session.execute(
                select(func.count(func.distinct(UserDailyActivity.user_id))).where(
                    UserDailyActivity.activity_date == today
                )
            )
        ).scalar() or 0
        products = (
            await session.execute(
                select(func.count(Product.id)).where(Product.is_active == True)
            )
        ).scalar() or 0
        quizzes = (
            await session.execute(
                select(func.count(ExamQuiz.id)).where(ExamQuiz.is_active == True)
            )
        ).scalar() or 0
        questions = (
            await session.execute(select(func.count(ExamQuestion.id)))
        ).scalar() or 0
        news_count = (await session.execute(select(func.count(News.id)))).scalar() or 0

        book_revenue = (
            await session.execute(select(func.coalesce(func.sum(BookOrder.price), 0)))
        ).scalar() or 0
        coin_spend = (
            await session.execute(
                select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                    CoinTransaction.amount < 0
                )
            )
        ).scalar() or 0
        total_balance = (
            await session.execute(select(func.coalesce(func.sum(User.balance), 0)))
        ).scalar() or 0

    return {
        "students_count": int(students),
        "today_active": int(today_active),
        "products_count": int(products),
        "quizzes_count": int(quizzes),
        "questions_count": int(questions),
        "news_count": int(news_count),
        "book_revenue": int(book_revenue),
        "coin_turnover": int(abs(coin_spend)),
        "users_balance_sum": int(total_balance),
        "turnover_balance": int(book_revenue) + int(abs(coin_spend)),
    }


# ==========================================================
# 2. TESTLAR (ExamQuiz)
# ==========================================================
@router.get("/api/admin/quizzes")
async def list_quizzes(
    admin_id: int = Depends(require_admin),
    q: Optional[str] = None,
    subject: Optional[str] = None,
    exam_type: Optional[str] = None,
    active_only: bool = False,
):
    async with async_session() as session:
        stmt = select(ExamQuiz).order_by(ExamQuiz.id.desc())
        if active_only:
            stmt = stmt.where(ExamQuiz.is_active == True)
        if subject:
            stmt = stmt.where(ExamQuiz.subject == subject)
        if exam_type:
            stmt = stmt.where(ExamQuiz.exam_type == exam_type)
        q_text = (q or "").strip()
        if q_text:
            like = f"%{q_text}%"
            stmt = stmt.where(
                or_(
                    ExamQuiz.title.ilike(like),
                    ExamQuiz.command_path.ilike(like),
                    ExamQuiz.subject.ilike(like),
                )
            )
        quizzes = (await session.execute(stmt)).scalars().all()
        counts = dict(
            (
                await session.execute(
                    select(ExamQuestion.quiz_id, func.count(ExamQuestion.id)).group_by(
                        ExamQuestion.quiz_id
                    )
                )
            ).all()
        )
        return [_quiz_dict(item, counts.get(item.id, 0)) for item in quizzes]


@router.post("/api/admin/quizzes")
async def create_quiz(body: QuizCreateSchema, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        quiz = ExamQuiz(
            title=body.title.strip(),
            subject=body.subject.strip() or "tarix",
            exam_type=body.exam_type.strip() or "namunaviy",
            price=max(0, body.price),
            base_price=max(0, body.base_price),
            share_discount_percent=max(0, min(100, body.share_discount_percent)),
            duration_minutes=max(1, body.duration_minutes),
            command_path=body.command_path,
            is_active=body.is_active,
            announced_at=datetime.utcnow(),
        )
        session.add(quiz)
        await session.commit()
        await session.refresh(quiz)
        return _quiz_dict(quiz, 0)


@router.put("/api/admin/quizzes/{quiz_id}")
async def update_quiz(
    quiz_id: int, body: QuizUpdateSchema, admin_id: int = Depends(require_admin)
):
    async with async_session() as session:
        quiz = (
            await session.execute(select(ExamQuiz).where(ExamQuiz.id == quiz_id))
        ).scalar_one_or_none()
        if not quiz:
            raise HTTPException(404, "Test topilmadi")
        data = body.model_dump(exclude_unset=True)
        if "visible_at" in data:
            data["visible_at"] = _parse_optional_dt(data["visible_at"])
        if "starts_at" in data:
            data["starts_at"] = _parse_optional_dt(data["starts_at"])
        if "share_discount_percent" in data and data["share_discount_percent"] is not None:
            data["share_discount_percent"] = max(0, min(100, int(data["share_discount_percent"])))
        for key, value in data.items():
            setattr(quiz, key, value)
        await session.commit()
        count = (
            await session.execute(
                select(func.count(ExamQuestion.id)).where(ExamQuestion.quiz_id == quiz_id)
            )
        ).scalar() or 0
        return _quiz_dict(quiz, int(count))


@router.delete("/api/admin/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: int, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        quiz = (
            await session.execute(select(ExamQuiz).where(ExamQuiz.id == quiz_id))
        ).scalar_one_or_none()
        if not quiz:
            raise HTTPException(404, "Test topilmadi")
        # Soft-delete: platforma bog'lanishlarini saqlash
        quiz.is_active = False
        await session.commit()
        return {"ok": True, "id": quiz_id}


# ==========================================================
# 3. SAVOLLAR (ExamQuestion)
# ==========================================================
@router.get("/api/admin/questions/{quiz_id}")
async def list_questions(quiz_id: int, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        quiz = (
            await session.execute(select(ExamQuiz).where(ExamQuiz.id == quiz_id))
        ).scalar_one_or_none()
        if not quiz:
            raise HTTPException(404, "Test topilmadi")
        rows = (
            await session.execute(
                select(ExamQuestion)
                .where(ExamQuestion.quiz_id == quiz_id)
                .order_by(ExamQuestion.order_num.asc(), ExamQuestion.id.asc())
            )
        ).scalars().all()
        return {
            "quiz": _quiz_dict(quiz, len(rows)),
            "questions": [_question_dict(item) for item in rows],
        }


@router.post("/api/admin/questions")
async def create_question(
    body: QuestionCreateSchema, admin_id: int = Depends(require_admin)
):
    async with async_session() as session:
        quiz = (
            await session.execute(select(ExamQuiz).where(ExamQuiz.id == body.quiz_id))
        ).scalar_one_or_none()
        if not quiz:
            raise HTTPException(404, "Test topilmadi")
        beta = float(body.difficulty_beta or 2.0)
        beta = max(1.1, min(3.2, beta))
        item = ExamQuestion(
            quiz_id=body.quiz_id,
            order_num=body.order_num,
            question_text=body.question_text.strip(),
            option_a=body.option_a.strip(),
            option_b=body.option_b.strip(),
            option_c=body.option_c.strip(),
            option_d=body.option_d.strip(),
            correct_option=body.correct_option,
            difficulty_beta=beta,
            video_solution_url=body.video_solution_url,
            solution_text=body.solution_text,
            topic=body.topic,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return _question_dict(item)


@router.put("/api/admin/questions/{question_id}")
async def update_question(
    question_id: int,
    body: QuestionUpdateSchema,
    admin_id: int = Depends(require_admin),
):
    async with async_session() as session:
        item = (
            await session.execute(
                select(ExamQuestion).where(ExamQuestion.id == question_id)
            )
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Savol topilmadi")
        data = body.model_dump(exclude_unset=True)
        if "difficulty_beta" in data and data["difficulty_beta"] is not None:
            data["difficulty_beta"] = max(1.1, min(3.2, float(data["difficulty_beta"])))
        for key, value in data.items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return _question_dict(item)


@router.delete("/api/admin/questions/{question_id}")
async def delete_question(question_id: int, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        item = (
            await session.execute(
                select(ExamQuestion).where(ExamQuestion.id == question_id)
            )
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Savol topilmadi")
        await session.delete(item)
        await session.commit()
        return {"ok": True, "id": question_id}


# ==========================================================
# 4. YANGILIKLAR
# ==========================================================
@router.get("/api/admin/news")
async def list_news(admin_id: int = Depends(require_admin), q: Optional[str] = None):
    async with async_session() as session:
        stmt = select(News).order_by(News.id.desc())
        q_text = (q or "").strip()
        if q_text:
            like = f"%{q_text}%"
            stmt = stmt.where(
                or_(News.title.ilike(like), News.hashtags.ilike(like), News.content.ilike(like))
            )
        rows = (await session.execute(stmt)).scalars().all()
        return [_news_dict(n) for n in rows]


@router.post("/api/admin/news")
async def create_news(body: NewsCreateSchema, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        item = News(
            title=body.title.strip(),
            content=body.content.strip(),
            hashtags=body.hashtags or "",
            category=body.category or "umumiy",
            summary=body.summary,
            image_url=body.image_url or "",
            source_url=body.source_url,
            source_name=body.source_name or "Manba",
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return _news_dict(item)


@router.put("/api/admin/news/{news_id}")
async def update_news(
    news_id: int, body: NewsUpdateSchema, admin_id: int = Depends(require_admin)
):
    async with async_session() as session:
        item = (
            await session.execute(select(News).where(News.id == news_id))
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Yangilik topilmadi")
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return _news_dict(item)


@router.delete("/api/admin/news/{news_id}")
async def delete_news(news_id: int, admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        item = (
            await session.execute(select(News).where(News.id == news_id))
        ).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Yangilik topilmadi")
        await session.delete(item)
        await session.commit()
        return {"ok": True, "id": news_id}


# ==========================================================
# 5. DINAMIK NARXLAR
# ==========================================================
@router.get("/api/admin/pricing")
async def list_pricing(admin_id: int = Depends(require_admin)):
    async with async_session() as session:
        quizzes = (
            await session.execute(
                select(ExamQuiz).where(ExamQuiz.is_active == True).order_by(ExamQuiz.id.desc())
            )
        ).scalars().all()
        products = (
            await session.execute(
                select(Product).where(Product.is_active == True).order_by(Product.id.desc())
            )
        ).scalars().all()
        return {
            "quizzes": [
                {
                    "id": q.id,
                    "title": q.title,
                    "subject": q.subject,
                    "exam_type": q.exam_type,
                    "price": int(q.price or 0),
                    "base_price": int(q.base_price or 0),
                    "share_discount_percent": int(q.share_discount_percent or 0),
                }
                for q in quizzes
            ],
            "products": [
                {
                    "id": p.id,
                    "title": p.title,
                    "subject": p.subject,
                    "category": p.category,
                    "item_type": p.item_type,
                    "price_coin": int(p.price_coin or 0),
                    "old_price_coin": int(p.old_price_coin or 0),
                }
                for p in products
            ],
        }


@router.post("/api/admin/update-pricing")
async def update_pricing(
    body: PricingUpdateSchema, admin_id: int = Depends(require_admin)
):
    if not body.items:
        raise HTTPException(400, "Bo'sh ro'yxat")
    updated = 0
    async with async_session() as session:
        for row in body.items:
            entity = (row.entity or "").strip().lower()
            if entity == "quiz":
                quiz = (
                    await session.execute(select(ExamQuiz).where(ExamQuiz.id == row.id))
                ).scalar_one_or_none()
                if not quiz:
                    continue
                if row.price is not None:
                    quiz.price = max(0, int(row.price))
                if row.base_price is not None:
                    quiz.base_price = max(0, int(row.base_price))
                if row.share_discount_percent is not None:
                    quiz.share_discount_percent = max(0, min(100, int(row.share_discount_percent)))
                if row.is_active is not None:
                    quiz.is_active = bool(row.is_active)
                updated += 1
            elif entity == "product":
                product = (
                    await session.execute(select(Product).where(Product.id == row.id))
                ).scalar_one_or_none()
                if not product:
                    continue
                if row.price_coin is not None:
                    product.price_coin = max(0, int(row.price_coin))
                if row.old_price_coin is not None:
                    product.old_price_coin = max(0, int(row.old_price_coin))
                if row.is_active is not None:
                    product.is_active = bool(row.is_active)
                updated += 1
        await session.commit()
    return {"ok": True, "updated": updated}
