from dataclasses import dataclass

# FREE limit settings
FREE_DAILY_QUESTIONS = 10
FREE_BLOCK_HOURS = 6

# Referral rules
REF_BONUS_USD = 3.0
REF_FREE_PLUS_DAYS = 7
REF_FREE_PLUS_MIN_PAID_USD = 5.0

@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    price_usd: float
    monthly_chat: int
    monthly_video: int
    monthly_music: int
    monthly_image: int
    monthly_voice: int
    monthly_doc: int

PLANS = {
    "FREE": Plan("FREE", "FREE", 0.0, 0, 0, 0, 0, 0, 0),
    "PLUS": Plan("PLUS", "PLUS", 12.0, 600, 3, 3, 15, 5, 5),
    "PRO":  Plan("PRO",  "PRO",  28.0, 1200, 6, 3, 30, 15, 15),
}

# VIP PACKS (сен мурда айткан баалар)
VIP_VIDEO_PACKS = {1: 19.99, 3: 49.99, 5: 79.99}     # credits count
VIP_MUSIC_PACKS = {3: 29.99, 5: 49.99}               # minutes

# Product kinds (invoice.kind)
KIND_PLAN_PLUS = "PLAN_PLUS"
KIND_PLAN_PRO = "PLAN_PRO"
def kind_vip_video(n: int) -> str:
    return f"VIP_VIDEO_{n}"

def kind_vip_music(minutes: int) -> str:
    return f"VIP_MUSIC_{minutes}"
