import asyncio
import datetime as dt
from fastapi import FastAPI, Request, HTTPException

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from sqlalchemy import select

from app.config import BOT_TOKEN
from app.db import ENGINE, SessionLocal
from app.models import Base, User, Invoice
from app.middleware import ChannelGateMiddleware
from app.handlers.menu_router import get_router
from app.services.cryptomus import verify_webhook
from app.constants import (
    PLANS,
    REF_BONUS_USD,
    REF_FREE_PLUS_DAYS,
    REF_FREE_PLUS_MIN_PAID_USD,
)
from app.utils import utcnow, in_30_days
from app.scheduler import ensure_resets

app = FastAPI()

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

dp.message.middleware(ChannelGateMiddleware())
dp.callback_query.middleware(ChannelGateMiddleware())
dp.include_router(get_router())

async def _db_init():
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def _background_loops():
    while True:
        try:
            await ensure_resets()
        except Exception:
            pass
        await asyncio.sleep(60)

async def _polling():
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    await _db_init()
    asyncio.create_task(_background_loops())
    asyncio.create_task(_polling())

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/cryptomus/webhook")
async def cryptomus_webhook(req: Request):
    body = await req.body()
    header_sign = req.headers.get("sign", "")

    if not verify_webhook(body, header_sign):
        raise HTTPException(status_code=401, detail="bad sign")

    data = await req.json()

    order_id = data.get("order_id") or data.get("orderId")
    status = (data.get("status") or data.get("payment_status") or "").lower()
    paid = status in ("paid", "paid_over", "paid_partial")

    if not order_id:
        return {"ok": True}

    paid_amount = None
    try:
        paid_amount = float(data.get("amount") or 0)
    except Exception:
        paid_amount = 0.0

    async with SessionLocal() as s:
        inv_res = await s.execute(select(Invoice).where(Invoice.order_id == order_id))
        inv = inv_res.scalar_one_or_none()
        if not inv:
            return {"ok": True}

        if paid and inv.status != "paid":
            inv.status = "paid"
            inv.paid_at = utcnow()

            u_res = await s.execute(select(User).where(User.tg_id == inv.tg_id))
            u = u_res.scalar_one_or_none()
            if not u:
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
                await bot.send_message(u.tg_id, "✅ PLUS актив болду! 😎💎")

                await _ref_reward(s, buyer=u, paid_amount=(paid_amount or inv.amount_usd))

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
                await bot.send_message(u.tg_id, "✅ PRO актив болду! 😈🔴")

            elif inv.kind.startswith("VIP_VIDEO_"):
                n = int(inv.kind.split("_")[-1])
                u.vip_video_credits += n
                await bot.send_message(u.tg_id, f"✅ VIP VIDEO кредит кошулду: +{n} 🎥")

            elif inv.kind.startswith("VIP_MUSIC_"):
                minutes = int(inv.kind.split("_")[-1])
                u.vip_music_minutes += minutes
                await bot.send_message(u.tg_id, f"✅ VIP MUSIC минут кошулду: +{minutes} мин 🪉")

            await s.commit()

    return {"ok": True}

async def _ref_reward(s, buyer: User, paid_amount: float):
    if not buyer.referrer_tg_id:
        return

    ref_res = await s.execute(select(User).where(User.tg_id == buyer.referrer_tg_id))
    ref_u = ref_res.scalar_one_or_none()
    if not ref_u:
        return

    # +$3 balance
    ref_u.ref_balance_usd += REF_BONUS_USD

    # 7 days PLUS if paid >= $5
    if paid_amount >= REF_FREE_PLUS_MIN_PAID_USD:
        p = PLANS["PLUS"]
        ref_u.plan = "PLUS"
        ref_u.plan_until = utcnow() + dt.timedelta(days=REF_FREE_PLUS_DAYS)

        # if empty limits, give at least once
        if ref_u.chat_left == 0 and ref_u.video_left == 0 and ref_u.music_left == 0:
            ref_u.chat_left = p.monthly_chat
            ref_u.video_left = p.monthly_video
            ref_u.music_left = p.monthly_music
            ref_u.image_left = p.monthly_image
            ref_u.voice_left = p.monthly_voice
            ref_u.doc_left = p.monthly_doc
            ref_u.last_monthly_reset = utcnow()

        await bot.send_message(ref_u.tg_id, "🎁 Досум! Реферал иштеди: 7 күн PLUS ачылды 😎💎")
              

