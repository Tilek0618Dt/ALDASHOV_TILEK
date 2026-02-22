import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Channel gate
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()  # like "@mychannel" or "-100123..."

# Cryptomus
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY", "").strip()
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID", "").strip()
CRYPTOMUS_WEBHOOK_SECRET = os.getenv("CRYPTOMUS_WEBHOOK_SECRET", "").strip()

# OpenAI/Grok-like (optional)
GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip()
