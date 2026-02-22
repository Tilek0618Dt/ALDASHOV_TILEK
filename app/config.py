# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY", "").strip()
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID", "").strip()

CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Render postgres:// берип койсо async форматка айлантабыз
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Мини текшерүү (логдо көрүнөт)
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in env")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in env")
