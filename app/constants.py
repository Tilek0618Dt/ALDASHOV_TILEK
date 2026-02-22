from dataclasses import dataclass

@dataclass
class Plan:
    monthly_chat: int
    monthly_video: int
    monthly_music: int
    monthly_image: int
    monthly_voice: int
    monthly_doc: int

PLANS = {
    "PLUS": Plan(monthly_chat=300, monthly_video=20, monthly_music=60, monthly_image=80, monthly_voice=60, monthly_doc=30),
    "PRO":  Plan(monthly_chat=9999, monthly_video=200, monthly_music=600, monthly_image=500, monthly_voice=600, monthly_doc=200),
}

REF_BONUS_USD = 3.0
REF_FREE_PLUS_DAYS = 7
REF_FREE_PLUS_MIN_PAID_USD = 5.0
