from future import annotations

import asyncio
import datetime as dt
import logging
from contextlib import suppress
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import BOT_TOKEN
from app.db import ENGINE, SessionLocal
from app.models import Base, User, Invoice
from app.middleware import ChannelGateMiddleware
from app.handlers.menu_router import get_router

from app.services.cryptomus import verify_webhook
from app.scheduler import ensure_resets
from app.utils import utcnow, in_30_days
from app.constants import PLANS, REF_BONUS_USD, REF_FREE_PLUS_DAYS, REF_FREE_PLUS_MIN_PAID_USD


# =========================================================
# Logging
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("tilek_ai")


# =========================================================
# FastAPI app
# =========================================================
app = FastAPI(title="Tilek AI", version="1.0.0")


@app.get("/health")
async def health():
    return {"ok": True, "service": "tilek_ai", "ts": utcnow().isoformat()}


# =========================================================
# Aiogram bot + dispatcher
# =========================================================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

dp = Dispatcher()
dp.message.middleware(ChannelGateMiddleware())
dp.callback_query.middleware(ChannelGateMiddleware())
dp.include_router(get_router())


# Background task handles
_polling_task: Optional[asyncio.Task] = None
_cron_task: Optional[asyncio.Task] = None


# =========================================================
# DB init
# =========================================================
async def _db_init():
    """
    Create tables if they don't exist.
    (Алгачкы MVP үчүн ушундай. Кийин Alembic миграция кошобуз.)
    """
    log.info("DB init: creating tables (if not exist)...")
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("DB init: done ✅")


# =========================================================
# Cron loop (scheduler)
# =========================================================
async def _cron_loop():
    """
    Every 60 seconds:
    - free daily reset
    - unblock users
    - monthly refill
    """
    log.info("Cron loop started ✅")
    while True:
        try:
            await ensure_resets()
        except Exception as e:
            log.warning("Cron loop error: %s", e)
        await asyncio.sleep(60)


# =========================================================
# Polling loop
# =========================================================
async def _polling_loop():
    """
    Aiogram long polling in background.
    """
    log.info("Polling started ✅")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.exception("Polling crashed: %s", e)
    finally:
        log.info("Polling stopped.")


# =========================================================
# Startup / Shutdown
# =========================================================
@app.on_event("startup")
async def on_startup():
    await _db_init()

    global _polling_task, _cron_task
    _cron_task = asyncio.create_task(_cron_loop())
    _polling_task = asyncio.create_task(_polling_loop())

    log.info("Tilek AI started 🎉")


@app.on_event("shutdown")
async def on_shutdown():
    global _polling_task, _cron_task

    # stop polling
    if _polling_task:
        _polling_task.cancel()
        with suppress(Exception):
            await _polling_task

# stop cron
    if _cron_task:
        _cron_task.cancel()
        with suppress(Exception):
            await _cron_task

    # close bot session
    with suppress(Exception):
        await bot.session.close()

    # dispose engine
    with suppress(Exception):
        await ENGINE.dispose()

    log.info("Tilek AI shutdown ✅")


# =========================================================
# Helpers: referral reward
# =========================================================
async def _ref_reward(session, buyer: User, paid_amount: float):
    """
    Referral rules:
    - buyer has referrer_tg_id
    - PLUS purchase => referrer +$3
    - if paid_amount >= $5 => 7 days PLUS for referrer (NOT PRO)
    """
    if not buyer.referrer_tg_id:
        return

    ref_res = await session.execute(select(User).where(User.tg_id == buyer.referrer_tg_id))
    ref_user = ref_res.scalar_one_or_none()
    if not ref_user:
        return

    ref_user.ref_balance_usd += float(REF_BONUS_USD)

    if paid_amount >= float(REF_FREE_PLUS_MIN_PAID_USD):
        # grant 7 days PLUS
        p = PLANS["PLUS"]
        ref_user.plan = "PLUS"
        ref_user.plan_until = utcnow() + dt.timedelta(days=int(REF_FREE_PLUS_DAYS))

        # If user had no limits, give initial bundle
        if (ref_user.chat_left or 0) <= 0 and (ref_user.video_left or 0) <= 0:
            ref_user.chat_left = p.monthly_chat
            ref_user.video_left = p.monthly_video
            ref_user.music_left = p.monthly_music
            ref_user.image_left = p.monthly_image
            ref_user.voice_left = p.monthly_voice
            ref_user.doc_left = p.monthly_doc
            ref_user.last_monthly_reset = utcnow()

        with suppress(Exception):
            await bot.send_message(ref_user.tg_id, "🎁 Досум! Реферал иштеди: 7 күн PLUS ачылды 😎💎")


# =========================================================
# Cryptomus Webhook
# =========================================================
@app.post("/cryptomus/webhook")
async def cryptomus_webhook(req: Request):
    """
    Cryptomus sends:
    - headers: sign
    - body: json
    """
    body = await req.body()
    header_sign = req.headers.get("sign", "")

    if not verify_webhook(body, header_sign):
        raise HTTPException(status_code=401, detail="bad sign")

    data = await req.json()

    order_id = data.get("order_id") or data.get("orderId") or data.get("orderid")
    status = (data.get("status") or data.get("payment_status") or data.get("paymentStatus") or "").lower()
    paid = status in ("paid", "paid_over", "paid_partial", "success")

    if not order_id:
        return {"ok": True}

    try:
        async with SessionLocal() as s:
            inv_res = await s.execute(select(Invoice).where(Invoice.order_id == str(order_id)))
            inv = inv_res.scalar_one_or_none()
            if not inv:
                # unknown order, ignore
                return {"ok": True}

            # Already paid? ignore duplicates
            if inv.status == "paid":
                return {"ok": True}

            if not paid:
                # you can store failed status too
                inv.status = status or "failed"
                await s.commit()
                return {"ok": True}

            # Mark invoice paid
            inv.status = "paid"
            inv.paid_at = utcnow()

            # Load user
            u_res = await s.execute(select(User).where(User.tg_id == inv.tg_id))
            u = u_res.scalar_one_or_none()
            if not u:
                # user may be missing if purchased before /start
                u = User(tg_id=inv.tg_id)
                s.add(u)
                await s.flush()

            # Apply purchase
            if inv.kind == "PLAN_PLUS":
                p = PLANS["PLUS"]
                u.plan = "PLUS"
                u.plan_until = in_30_days()
                u.chat_left = p.monthly_chat
                u.video_left = p.monthly_video
                u.music_left = p.monthly_music
                u.image_left = p.monthly_image
                u.voice_left = p.monthly_voice
                u.doc_left = p.monthly_doc
                u.last_monthly_reset = utcnow()

                with suppress(Exception):
                    await bot.send_message(u.tg_id, "✅ PLUS актив болду! 😎💎")

                # referral reward only for PLUS
                paid_amount = float(data.get("amount") or inv.amount_usd or 0.0)
                await _ref_reward(s, u, paid_amount=paid_amount)

            elif inv.kind == "PLAN_PRO":
                p = PLANS["PRO"]
                u.plan = "PRO"
                u.plan_until = in_30_days()
                u.chat_left = p.monthly_chat
                u.video_left = p.monthly_video
                u.music_left = p.monthly_music
                u.image_left = p.monthly_image
                u.voice_left = p.monthly_voice
                u.doc_left = p.monthly_doc
                u.last_monthly_reset = utcnow()

                with suppress(Exception):
                    await bot.send_message(u.tg_id, "✅ PRO актив болду! 😈🔴")

            elif inv.kind.startswith("VIP_VIDEO_"):
                # kind example: VIP_VIDEO_3
                try:
                    n = int(inv.kind.split("_")[-1])
                except Exception:
                    n = 0
                u.vip_video_credits += max(0, n)

                with suppress(Exception):
                    await bot.send_message(u.tg_id, f"✅ VIP VIDEO кредит кошулду: +{n} 🎥")

            elif inv.kind.startswith("VIP_MUSIC_"):
                # kind example: VIP_MUSIC_5
                try:
                    minutes = int(inv.kind.split("_")[-1])
                except Exception:
                    minutes = 0
                u.vip_music_minutes += max(0, minutes)

                with suppress(Exception):
                    await bot.send_message(u.tg_id, f"✅ VIP MUSIC минут кошулду: +{minutes} мин 🪉")

            else:
                # unknown kind - just save paid invoice
                log.warning("Paid invoice with unknown kind=%s", inv.kind)

            await s.commit()

    except SQLAlchemyError as e:
        log.exception("DB error in webhook: %s", e)
        # Return ok to avoid Cryptomus retry storm (or choose 500 if you want retries)
        return JSONResponse({"ok": True}, status_code=200)
    except Exception as e:
        log.exception("Webhook crash: %s", e)
        return JSONResponse({"ok": True}, status_code=200)

    return {"ok": True}


# =========================================================
# Global error handler (optional but nice)
# =========================================================
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"ok": False, "error": "server_error"})

