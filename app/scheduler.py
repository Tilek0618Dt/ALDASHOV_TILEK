from future import annotations

import datetime as dt
from typing import Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import User
from app.constants import PLANS
from app.utils import utcnow, day_key_utc


# Notifier: async function like:
#   async def notify(tg_id: int, text: str) -> None: ...
Notifier = Optional[Callable[[int, str], Awaitable[None]]]


def _is_expired(plan_until: Optional[dt.datetime]) -> bool:
    return bool(plan_until and utcnow() >= plan_until)


def _ensure_anchor(u: User, now: dt.datetime) -> None:
    """
    Anchor date for monthly refill.
    If user plan is PLUS/PRO and last_monthly_reset is missing -> set now.
    """
    if u.plan in ("PLUS", "PRO") and not u.last_monthly_reset:
        u.last_monthly_reset = now


def _refill_monthly(u: User) -> None:
    if u.plan not in ("PLUS", "PRO"):
        return
    p = PLANS[u.plan]
    u.chat_left = p.monthly_chat
    u.video_left = p.monthly_video
    u.music_left = p.monthly_music
    u.image_left = p.monthly_image
    u.voice_left = p.monthly_voice
    u.doc_left = p.monthly_doc


def _drop_to_free(u: User) -> None:
    u.plan = "FREE"
    u.plan_until = None

    # paid limits to 0
    u.chat_left = 0
    u.video_left = 0
    u.music_left = 0
    u.image_left = 0
    u.voice_left = 0
    u.doc_left = 0
    # VIP credits stay untouched (vip_video_credits, vip_music_minutes)


def _next_refill_at(u: User) -> Optional[dt.datetime]:
    """
    Next refill time anchored to last_monthly_reset.
    If last_monthly_reset is set -> next = +30 days.
    """
    if u.plan not in ("PLUS", "PRO"):
        return None
    if not u.last_monthly_reset:
        return None
    return u.last_monthly_reset + dt.timedelta(days=30)


def _should_refill(u: User, now: dt.datetime) -> bool:
    nxt = _next_refill_at(u)
    return bool(nxt and now >= nxt)


def _text_unblocked() -> str:
    return (
        "✅ Досум, FREE блок ачылды!\n\n"
        "Эми кайра суроо берсең болот 😎💎\n"
        "💡 Кеңеш: Премиум алсаң лимит көп болот 😉"
    )


def _text_expired_upsell() -> str:
    return (
        "⏳ Досум, сенин PREMIUM мөөнөтү бүттү.\n\n"
        "💎 PLUS – көп чат + видео/музыка лимит\n"
        "🔴 PRO – приоритет + дагы көп лимит\n"
        "🎥 VIP VIDEO / 🪉 VIP MUSIC – кошумча күч\n\n"
        "👉 «💎 Премиум» менюдан кайра актив кыл 😎"
    )


async def ensure_resets(notify: Notifier = None) -> dict:
    """
    Run every ~60s.

    Does:
    - daily reset for FREE counter by UTC day_key
    - unblock users when blocked_until passed (optional notify)
    - premium expiry -> drop to FREE (optional notify with upsell)
    - monthly refill anchored to last_monthly_reset for PLUS/PRO
    """
    now = utcnow()
    today_key = day_key_utc()

    stats = {
        "users_scanned": 0,
        "daily_reset": 0,
        "unblocked": 0,
        "expired_to_free": 0,
        "monthly_refilled": 0,
        "notified": 0,
        "touched": 0,
    }

    # We collect notifications and send AFTER commit (safer)
    notifications: list[tuple[int, str]] = []

    async with SessionLocal() as s:  # type: AsyncSession
        res = await s.execute(select(User))
        users = res.scalars().all()
        stats["users_scanned"] = len(users)

        for u in users:
            changed = False

            # 0) anchor init
            _ensure_anchor(u, now)

            # 1) daily reset (FREE daily counter)
            if u.free_day_key != today_key:
                u.free_day_key = today_key
                u.free_today_count = 0
                changed = True
                stats["daily_reset"] += 1

            # 2) unblock
            if u.blocked_until and now >= u.blocked_until:
                u.blocked_until = None
                changed = True
                stats["unblocked"] += 1
                notifications.append((u.tg_id, _text_unblocked()))

            # 3) plan expiry
            if u.plan in ("PLUS", "PRO") and _is_expired(u.plan_until):
                _drop_to_free(u)
                changed = True
                stats["expired_to_free"] += 1
                notifications.append((u.tg_id, _text_expired_upsell()))

            # 4) monthly refill (only if still PLUS/PRO)
            if u.plan in ("PLUS", "PRO") and _should_refill(u, now):
                _refill_monthly(u)
                u.last_monthly_reset = now
                changed = True
                stats["monthly_refilled"] += 1

            if changed:
                u.updated_at = now
                stats["touched"] += 1

        if stats["touched"] > 0:
            await s.commit()

    # Send notifications after DB commit
    if notify:
        for tg_id, text in notifications:
            try:
                await notify(tg_id, text)
                stats["notified"] += 1
            except Exception:
                # ignore notify errors to prevent scheduler crash
                pass

    return stats 

    
