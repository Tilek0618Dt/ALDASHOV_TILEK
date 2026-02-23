import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Channel gate
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()  # "@channel" or "-100..."
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()  # https://t.me/...

# Public base URL for webhook callbacks (Render service URL)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()

# Admins
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
SUPPORT_ADMINS = [x.strip() for x in os.getenv("SUPPORT_ADMINS", "").split(",") if x.strip()]

# AI provider (xAI Grok OpenAI-compatible)
GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip()
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").strip()
GROK_MODEL = os.getenv("GROK_MODEL", "grok-beta").strip()

# Cryptomus
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY", "").strip()
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID", "").strip()
CRYPTOMUS_WEBHOOK_SECRET = os.getenv("CRYPTOMUS_WEBHOOK_SECRET", "").strip()

# Media services (optional stubs)
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "").strip()
KLING_API_KEY = os.getenv("KLING_API_KEY", "").strip()
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()

# Required minimal checks
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in env")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in env")
if not PUBLIC_BASE_URL:
    # webhook үчүн керек, бирок демо режимде бот жүрө бериши мүмкүн
    # ошондуктан катуу токтотпойбуз
    pass
