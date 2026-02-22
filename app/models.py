import datetime as dt
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Float

class Base(DeclarativeBase):
    pass

class User(Base):
    tablename = "users"

    tg_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    plan: Mapped[str] = mapped_column(String(16), default="FREE")
    plan_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chat_left: Mapped[int] = mapped_column(Integer, default=0)
    video_left: Mapped[int] = mapped_column(Integer, default=0)
    music_left: Mapped[int] = mapped_column(Integer, default=0)
    image_left: Mapped[int] = mapped_column(Integer, default=0)
    voice_left: Mapped[int] = mapped_column(Integer, default=0)
    doc_left: Mapped[int] = mapped_column(Integer, default=0)

    vip_video_credits: Mapped[int] = mapped_column(Integer, default=0)
    vip_music_minutes: Mapped[int] = mapped_column(Integer, default=0)

    referrer_tg_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ref_balance_usd: Mapped[float] = mapped_column(Float, default=0.0)

    last_monthly_reset: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Invoice(Base):
    tablename = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer, index=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    kind: Mapped[str] = mapped_column(String(64))   # PLAN_PLUS, PLAN_PRO, VIP_VIDEO_10 ...
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/paid
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=dt.datetime.utcnow)
    paid_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
