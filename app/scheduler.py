import datetime as dt
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User
from app.utils import utcnow
from app.constants import PLANS

async def ensure_resets():
    # monthly reset example
    async with SessionLocal() as s:
        res = await s.execute(select(User))
        users = res.scalars().all()
        now = utcnow()

        for u in users:
            if u.plan in ("PLUS", "PRO"):
                # reset each 30 days since last reset
                if not u.last_monthly_reset:
                    u.last_monthly_reset = now

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
