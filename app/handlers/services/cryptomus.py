import hmac
import hashlib
from app.config import CRYPTOMUS_WEBHOOK_SECRET

def verify_webhook(body: bytes, header_sign: str) -> bool:
    if not CRYPTOMUS_WEBHOOK_SECRET:
        return False
    if not header_sign:
        return False

    # Most common: HMAC SHA256 hex
    calc = hmac.new(
        CRYPTOMUS_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    return calc == header_sign
