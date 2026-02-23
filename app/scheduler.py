import datetime as dt
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.utils import day_key_utc, utcnow
from app.constants import PLANS

async def ensure_resets():
    now = utcnow()
    today = day_key_utc()

    async with SessionLocal() as s:
        res = await s.execute(select(User))
        users = res.scalars().all()

        for u in users:
            # daily reset free counter
            if u.free_day_key != today:
                u.free_day_key = today
                u.free_today_count = 0

            # unblock if passed
            if u.blocked_until and now >= u.blocked_until:
                u.blocked_until = None

            # plan expiry
            if u.plan in ("PLUS", "PRO") and u.plan_until and now >= u.plan_until:
                u.plan = "FREE"
                u.plan_until = None
                u.chat_left = u.video_left = u.music_left = 0
                u.image_left = u.voice_left = u.doc_left = 0

            # monthly refill each 30 days
            if u.plan in ("PLUS", "PRO"):
                if (now - u.last_monthly_reset) >= dt.timedelta(days=30):
                    p = PLANS[u.plan]
                    u.chat_left = p.monthly_chat
                    u.video_left = p.monthly_video
                    u.music_left = p.monthly_music
                    u.image_left = p.monthly_image
                    u.voice_left = p.monthly_voice
                    u.doc_left = p.monthly_doc
                    u.last_monthly_reset = now

        await s.commit()
