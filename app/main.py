import asyncio
import datetime as dt
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import BOT_TOKEN
from app.db import ENGINE, SessionLocal
from app.models import Base, User, Invoice
from app.middleware import ChannelGateMiddleware
from app.handlers.menu_router import get_router
from app.services.cryptomus import verify_webhook
from app.constants import PLANS, REF_BONUS_USD, REF_FREE_PLUS_DAYS, REF_FREE_PLUS_MIN_PAID_USD
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
    # tiny cron: every 60s resets
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

@app.post("/cryptomus/webhook")
async def cryptomus_webhook(req: Request):
    body = await req.body()
    header_sign = req.headers.get("sign", "")

    if not verify_webhook(body, header_sign):
        raise HTTPException(status_code=401, detail="bad sign")

    data = await req.json()

    order_id = data.get("order_id") or data.get("orderId")
    status = (data.get("status") or data.get("payment_status") or "").lower()
    paid = status in ("paid", "paid_over", "paid_partial")  # statuses vary; adjust if needed

    if not order_id:
        return {"ok": True}

    async with SessionLocal() as s:
        inv_res = await s.execute(select(Invoice).where(Invoice.order_id == order_id))
        inv = inv_res.scalar_one_or_none()
        if not inv:
            return {"ok": True}

        if paid and inv.status != "paid":
            inv.status = "paid"
            inv.paid_at = utcnow()

            u_res = await s.execute(select(User).where(User.tg_id == inv.tg_id))
            u = u_res.scalar_one()

            # Apply purchase
            if inv.kind == "PLAN_PLUS":
                p = PLANS["PLUS"]
                u.plan = "PLUS"
                u.plan_until = in_30_days()
                u.chat_left, u.video_left, u.music_left = p.monthly_chat, p.monthly_video, p.monthly_music
                u.image_left, u.voice_left, u.doc_left = p.monthly_image, p.monthly_voice, p.monthly_doc
                u.last_monthly_reset = utcnow()
                await bot.send_message(u.tg_id, "✅ PLUS актив болду! 😎💎")
                await _ref_reward(s, u, paid_amount=float(data.get("amount") or inv.amount_usd))

            elif inv.kind == "PLAN_PRO":
                p = PLANS["PRO"]
                u.plan = "PRO"
                u.plan_until = in_30_days()
                u.chat_left, u.video_left, u.music_left = p.monthly_chat, p.monthly_video, p.monthly_music
                u.image_left, u.voice_left, u.doc_left = p.monthly_image, p.monthly_voice, p.monthly_doc
                u.last_monthly_reset = utcnow()
                await bot.send_message(u.tg_id, "✅ PRO актив болду! 😈🔴")
                # PRO үчүн referral бонус жок

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

async def _ref_reward(s: AsyncSession, buyer: User, paid_amount: float):
    """
    Referral rules:
    - friend buys PLUS => referrer +$3
    - if paid_amount >= 5 => referrer gets 7 days PLUS
    - PRO => no bonus (handled outside)
    """
    if not buyer.referrer_tg_id:
        return

    ref_res = await s.execute(select(User).where(User.tg_id == buyer.referrer_tg_id))
    ref_u = ref_res.scalar_one_or_none()
    if not ref_u:
        return

    ref_u.ref_balance_usd += REF_BONUS_USD

    if paid_amount >= REF_FREE_PLUS_MIN_PAID_USD:
        # 7 күн PLUS (PRO эмес!)
        p = PLANS["PLUS"]
        ref_u.plan = "PLUS"
        ref_u.plan_until = utcnow() + dt.timedelta(days=REF_FREE_PLUS_DAYS)
        if ref_u.chat_left == 0 and ref_u.video_left == 0:
            ref_u.chat_left, ref_u.video_left, ref_u.music_left = p.monthly_chat, p.monthly_video, p.monthly_music
            ref_u.image_left, ref_u.voice_left, ref_u.doc_left = p.monthly_image, p.monthly_voice, p.monthly_doc
            ref_u.last_monthly_reset = utcnow()

        await bot.send_message(ref_u.tg_id, "🎁 Досум! Реферал иштеди: 7 күн PLUS ачылды 😎💎")
