"""Click Shop API (YaTT) — Prepare / Complete to'lov endpointlari."""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, Optional

from aiogram import Bot
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

# .env yuklanishi uchun
from data.config import BOT_TOKEN
from database.db import async_session
from database.models import BalanceTransaction, CoinTransaction, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments/click", tags=["Click Payment"])

CLICK_SERVICE_ID = (os.getenv("CLICK_SERVICE_ID") or "").strip()
CLICK_MERCHANT_ID = (os.getenv("CLICK_MERCHANT_ID") or "").strip()
CLICK_SECRET_KEY = (os.getenv("CLICK_SECRET_KEY") or "").strip()
CLICK_MERCHANT_USER_ID = (os.getenv("CLICK_MERCHANT_USER_ID") or "").strip()

tg_bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None


def _generate_sign_string(
    click_trans_id: str,
    service_id: str,
    secret_key: str,
    merchant_trans_id: str,
    amount: str,
    action: str,
    sign_time: str,
    merchant_prepare_id: Optional[str] = None,
) -> str:
    """
    Click Shop API rasmiy MD5 imzo.
    Prepare:  click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time
    Complete: ... + merchant_prepare_id + amount + action + sign_time  (prepare_id merchant_trans_id dan keyin)
    """
    parts = [
        str(click_trans_id),
        str(service_id),
        str(secret_key),
        str(merchant_trans_id),
    ]
    if merchant_prepare_id is not None and str(merchant_prepare_id) != "":
        parts.append(str(merchant_prepare_id))
    parts.extend([str(amount), str(action), str(sign_time)])
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


def _click_json(error: int, error_note: str, **extra) -> JSONResponse:
    return JSONResponse(content={"error": error, "error_note": error_note, **extra})


async def _notify_payment_success(telegram_id: int, amount: int, new_balance: int) -> None:
    """To'lov tasdiqlangach foydalanuvchiga Telegram xabar. Xato bo'lsa Click javobiga ta'sir qilmaydi."""
    if tg_bot is None:
        return
    try:
        await tg_bot.send_message(
            chat_id=telegram_id,
            text=(
                "To'lovingiz muvaffaqiyatli qabul qilindi! ✅\n"
                f"Hisobingizga +{amount} so'm qo'shildi.\n"
                f"Hozirgi balansingiz: {new_balance} so'm."
            ),
        )
    except Exception:
        logger.exception(
            "Click complete: Telegram xabar yuborilmadi (tg_id=%s)", telegram_id
        )


async def _parse_click_body(request: Request) -> Dict[str, Any]:
    """Click form-urlencoded yoki JSON body ni o'qiydi (500 bermaslik uchun xavfsiz)."""
    import json
    from urllib.parse import parse_qs

    raw = await request.body()
    text = raw.decode("utf-8", errors="ignore") if raw else ""
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            body = json.loads(text or "{}")
            return body if isinstance(body, dict) else {}
        except Exception:
            return {}

    # Click odatda x-www-form-urlencoded yuboradi
    try:
        parsed = parse_qs(text, keep_blank_values=True)
        return {k: (v[0] if isinstance(v, list) and v else "") for k, v in parsed.items()}
    except Exception:
        logger.exception("Click body parse xatosi")
        return {}


def _verify_sign(data: Dict[str, Any], action: int) -> bool:
    if not CLICK_SECRET_KEY:
        return False

    click_trans_id = str(data.get("click_trans_id") or "")
    service_id = str(data.get("service_id") or CLICK_SERVICE_ID or "")
    merchant_trans_id = str(data.get("merchant_trans_id") or "")
    amount = str(data.get("amount") or "")
    sign_time = str(data.get("sign_time") or "")
    sign_string = str(data.get("sign_string") or "").lower()

    prepare_id: Optional[str] = None
    if action == 1:
        raw = data.get("merchant_prepare_id")
        if raw is not None and str(raw) != "":
            prepare_id = str(raw)

    expected = _generate_sign_string(
        click_trans_id=click_trans_id,
        service_id=service_id,
        secret_key=CLICK_SECRET_KEY,
        merchant_trans_id=merchant_trans_id,
        amount=amount,
        action=str(action),
        sign_time=sign_time,
        merchant_prepare_id=prepare_id,
    )
    return expected == sign_string


@router.post("/prepare")
async def click_prepare(request: Request):
    """
    Click Shop API — Prepare (action=0).
    merchant_trans_id = foydalanuvchi telegram_id.
    """
    try:
        data = await _parse_click_body(request)
        logger.info("Click prepare payload keys=%s", list(data.keys()))

        if not _verify_sign(data, action=0):
            logger.warning(
                "Click prepare SIGN FAIL (secret_set=%s, service=%s)",
                bool(CLICK_SECRET_KEY),
                data.get("service_id"),
            )
            return _click_json(-1, "SIGN CHECK FAILED")

        click_trans_id = str(data.get("click_trans_id") or "")
        merchant_trans_id = str(data.get("merchant_trans_id") or "").strip()

        try:
            telegram_id = int(merchant_trans_id)
        except (TypeError, ValueError):
            return _click_json(
                -5,
                "User not found",
                click_trans_id=click_trans_id,
                merchant_trans_id=merchant_trans_id,
            )

        async with async_session() as session:
            user = (
                await session.execute(select(User).where(User.telegram_id == telegram_id))
            ).scalar_one_or_none()

            if not user:
                return _click_json(
                    -5,
                    "User not found",
                    click_trans_id=int(click_trans_id) if str(click_trans_id).isdigit() else click_trans_id,
                    merchant_trans_id=merchant_trans_id,
                )

        click_id_out: Any = int(click_trans_id) if str(click_trans_id).isdigit() else click_trans_id
        return JSONResponse(
            content={
                "click_trans_id": click_id_out,
                "merchant_trans_id": merchant_trans_id,
                "merchant_prepare_id": click_id_out,
                "error": 0,
                "error_note": "Success",
            }
        )
    except Exception:
        logger.exception("Click prepare: unhandled error")
        return _click_json(-8, "Error in request from click")


@router.post("/complete")
async def click_complete(request: Request):
    """
    Click Shop API — Complete (action=1).
    Muvaffaqiyatda balansni oshiradi, CoinTransaction yozadi va Telegram xabar yuboradi.
    """
    try:
        return await _click_complete_impl(request)
    except Exception:
        logger.exception("Click complete: unhandled error")
        return _click_json(-8, "Error in request from click")


async def _click_complete_impl(request: Request):
    data = await _parse_click_body(request)

    if not _verify_sign(data, action=1):
        return _click_json(-1, "SIGN CHECK FAILED")

    click_trans_id = str(data.get("click_trans_id") or "")
    merchant_trans_id = str(data.get("merchant_trans_id") or "").strip()
    click_paydoc_id = str(data.get("click_paydoc_id") or "")
    amount_raw = str(data.get("amount") or "0")

    click_id_out: Any = int(click_trans_id) if str(click_trans_id).isdigit() else click_trans_id

    # Click tomonidan bekor / xato
    try:
        click_error = int(data.get("error") if data.get("error") is not None else 0)
    except (TypeError, ValueError):
        click_error = 0

    if click_error < 0:
        return _click_json(
            click_error,
            str(data.get("error_note") or "Transaction cancelled"),
            click_trans_id=click_id_out,
            merchant_trans_id=merchant_trans_id,
            merchant_confirm_id=click_id_out,
        )

    try:
        amount_val = int(float(amount_raw))
    except (TypeError, ValueError):
        return _click_json(-2, "Incorrect parameter amount")

    if amount_val <= 0:
        return _click_json(-2, "Incorrect parameter amount")

    try:
        telegram_id = int(merchant_trans_id)
    except (TypeError, ValueError):
        return _click_json(-5, "User not found")

    new_balance = 0
    async with async_session() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()

        if not user:
            return _click_json(
                -5,
                "User not found",
                click_trans_id=click_id_out,
                merchant_trans_id=merchant_trans_id,
            )

        try:
            # Qat'iy increment: overwrite emas (har bir muvaffaqiyatli to'lov qo'shiladi)
            user.balance = int(user.balance or 0) + amount_val
            user.coins = int(user.balance or 0)
            user.is_paid = True
            new_balance = int(user.balance or 0)

            session.add(
                CoinTransaction(
                    user_id=telegram_id,
                    amount=amount_val,
                    tx_type="topup",
                    description=(
                        f"Click to'lov cheki: {click_paydoc_id}, "
                        f"summa: {amount_val} UZS"
                    ),
                )
            )
            session.add(
                BalanceTransaction(
                    telegram_id=telegram_id,
                    amount=amount_val,
                    transaction_type="income",
                    title="Click orqali to'lov",
                    item_category="hisob",
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Click complete: balans yangilanmadi")
            return _click_json(-7, "Failed to update user")

    # action==1 (Complete) muvaffaqiyat: balans yangilandi — foydalanuvchiga xabar.
    # Xabar xatosi Click'ga 500/error bermasligi uchun silent ushlanadi.
    await _notify_payment_success(telegram_id, amount_val, new_balance)

    return JSONResponse(
        content={
            "click_trans_id": click_id_out,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": click_id_out,
            "error": 0,
            "error_note": "Success",
        }
    )
