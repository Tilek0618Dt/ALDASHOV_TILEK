import datetime as dt
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Float, Text

class Base(DeclarativeBase):
    pass

class User(Base):
    tablename = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    language: Mapped[str] = mapped_column(String(8), default="ky")
    country_code: Mapped[str | None] = mapped_column(String(4), nullable=True)

    # plan
    plan: Mapped[str] = mapped_column(String(16), default="FREE")
    plan_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # remaining monthly limits (PLUS/PRO)
    chat_left: Mapped[int] = mapped_column(Integer, default=0)
    video_left: Mapped[int] = mapped_column(Integer, default=0)
    music_left: Mapped[int] = mapped_column(Integer, default=0)
    image_left: Mapped[int] = mapped_column(Integer, default=0)
    voice_left: Mapped[int] = mapped_column(Integer, default=0)
    doc_left: Mapped[int] = mapped_column(Integer, default=0)
    last_monthly_reset: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # FREE daily
    free_today_count: Mapped[int] = mapped_column(Integer, default=0)
    free_day_key: Mapped[str] = mapped_column(String(16), default="")
    blocked_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # style
    style_counter: Mapped[int] = mapped_column(Integer, default=0)

    # referral
    referrer_tg_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ref_balance_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # VIP credits
    vip_video_credits: Mapped[int] = mapped_column(Integer, default=0)
    vip_music_minutes: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

class Invoice(Base):
    tablename = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    tg_id: Mapped[int] = mapped_column(Integer, index=True)

    kind: Mapped[str] = mapped_column(String(64))  # PLAN_PLUS / PLAN_PRO / VIP_VIDEO_3 / VIP_MUSIC_5
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="created")  # created/paid/failed
    payment_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    paid_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
