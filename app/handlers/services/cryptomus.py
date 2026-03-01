# app/services/cryptomus.py
from __future__ import annotations

import os
import json
import base64
import hashlib
import asyncio
from dataclasses import dataclass
from typing import Optional, Any

import aiohttp


# =========================================================
# ENV
# =========================================================
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY", "").strip()
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID", "").strip()

# Кээде webhook үчүн өзүнчө secret болот — көп учурда API KEY эле колдонулат.
# Биз verify үчүн: CRYPTOMUS_WEBHOOK_SECRET бар болсо ошол, болбосо API KEY колдонобуз.
CRYPTOMUS_WEBHOOK_SECRET = os.getenv("CRYPTOMUS_WEBHOOK_SECRET", "").strip()

CRYPTOMUS_BASE_URL = os.getenv("CRYPTOMUS_BASE_URL", "https://api.cryptomus.com").strip()
CRYPTOMUS_API_PREFIX = os.getenv("CRYPTOMUS_API_PREFIX", "/v1").strip()

CRYPTOMUS_TIMEOUT_S = int(os.getenv("CRYPTOMUS_TIMEOUT_S", "30"))
CRYPTOMUS_RETRIES = int(os.getenv("CRYPTOMUS_RETRIES", "2"))

# endpoints (эгер өзгөрсө ENV менен оңой алмашат)
CRYPTOMUS_CREATE_INVOICE_PATH = os.getenv("CRYPTOMUS_CREATE_INVOICE_PATH", "/payment").strip()
CRYPTOMUS_INFO_PATH = os.getenv("CRYPTOMUS_INFO_PATH", "/payment/info").strip()


# =========================================================
# Exceptions
# =========================================================
class CryptomusError(RuntimeError):
    pass


class CryptomusAuthError(CryptomusError):
    pass


class CryptomusBadRequest(CryptomusError):
    pass


class CryptomusRateLimit(CryptomusError):
    pass


class CryptomusServerError(CryptomusError):
    pass


# =========================================================
# DTO
# =========================================================
@dataclass
class InvoiceResult:
    order_id: str
    amount: str
    currency: str
    pay_url: Optional[str]
    raw: dict


# =========================================================
# Helpers
# =========================================================
def _require_env() -> None:
    if not CRYPTOMUS_API_KEY:
        raise CryptomusAuthError("CRYPTOMUS_API_KEY жок, досум 😭 (Render ENVке кош)")
    if not CRYPTOMUS_MERCHANT_ID:
        raise CryptomusAuthError("CRYPTOMUS_MERCHANT_ID жок, досум 😭 (Render ENVке кош)")


def _base_url(path: str) -> str:
    base = CRYPTOMUS_BASE_URL.rstrip("/")
    prefix = CRYPTOMUS_API_PREFIX.strip()
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    prefix = prefix.rstrip("/")
    path = path if path.startswith("/") else ("/" + path)
    return f"{base}{prefix}{path}"


def _json_compact(payload: dict) -> str:
    # Cryptomus sign үчүн compact JSON сунушталат
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _sign(payload: dict, secret: str) -> str:
    """
    Cryptomus docs (көпчүлүк учурда):
    sign = md5( base64_encode(json(payload)) + API_KEY )
    """
    dumped = _json_compact(payload).encode("utf-8")
    b64 = base64.b64encode(dumped)
    raw = b64 + secret.encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _headers(payload: dict) -> dict:
    _require_env()
    sig = _sign(payload, CRYPTOMUS_API_KEY)
    return {
        "merchant": CRYPTOMUS_MERCHANT_ID,
        "sign": sig,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "tilek-ai/1.0",
    }


def _err_by_status(status: int, body: str) -> CryptomusError:
    msg = f"Cryptomus status={status} body={body[:1200]}"
    if status in (401, 403):
        return CryptomusAuthError(msg)
    if status == 429:
        return CryptomusRateLimit(msg)
    if 400 <= status < 500:
        return CryptomusBadRequest(msg)
    if status >= 500:
        return CryptomusServerError(msg)
    return CryptomusError(msg)


async def _request_json(
    method: str,
    url: str,
    *,
    payload: Optional[dict] = None,
    timeout_s: int = CRYPTOMUS_TIMEOUT_S,
    retries: int = CRYPTOMUS_RETRIES,
) -> dict:
    """
    Safe HTTP client with retry for 429/5xx/network.
    """
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if payload is None:
                    headers = {"Accept": "application/json"}
                else:
                    headers = _headers(payload)

                async with session.request(method, url, json=payload, headers=headers) as resp:
                    text = await resp.text()

                    if 200 <= resp.status < 300:
                        if not text.strip():
                            return {}
                        try:
                            return json.loads(text)
                        except Exception:
                            return {"raw": text}

                    err = _err_by_status(resp.status, text)

                    # retry only if: rate-limit or server
                    if isinstance(err, (CryptomusRateLimit, CryptomusServerError)) and attempt < retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        last_err = err
                        continue

                    raise err

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise CryptomusError(f"Network/timeout error: {e}") from e

    raise CryptomusError(f"Unknown error: {last_err}")


def _extract_pay_url(data: dict) -> Optional[str]:
    """
    Cryptomus response ар башка болушу мүмкүн.
    Көп учурда: data["result"]["url"] же data["result"]["payment_url"]
    """
    if not isinstance(data, dict):
        return None
    result = data.get("result") or {}
    if isinstance(result, dict):
        for key in ("url", "pay_url", "payment_url", "paymentUrl", "invoice_url"):
            val = result.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val

    # fallback: түздөн-түз талаалар
    for key in ("url", "pay_url", "payment_url", "invoice_url"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    return None


# =========================================================
# Public API
# =========================================================
async def create_invoice(
    *,
    amount_usd: float,
    order_id: str,
    callback_url: str,
    success_url: str = "",
    return_url: str = "",
    currency: str = "USD",
    lifetime_sec: int = 3600,  # 1 саат (кааласаң өзгөрт)
) -> InvoiceResult:
    """
    Creates invoice in Cryptomus.

    callback_url: сенин Render URL: https://xxx.onrender.com/cryptomus/webhook
    """
    _require_env()

    url = _base_url(CRYPTOMUS_CREATE_INVOICE_PATH)

    payload: dict[str, Any] = {
        "amount": f"{amount_usd:.2f}",
        "currency": currency,
        "order_id": str(order_id),
        "url_callback": callback_url,
        "lifetime": int(lifetime_sec),
    }
    if success_url:
        payload["url_success"] = success_url
    if return_url:
        payload["url_return"] = return_url

    data = await _request_json("POST", url, payload=payload)

    # Cryptomus көбүнчө {state, result:{...}} форматта берет
    pay_url = _extract_pay_url(data)

    return InvoiceResult(
        order_id=str(order_id),
        amount=payload["amount"],
        currency=currency,
        pay_url=pay_url,
        raw=data,
    )


async def payment_info(order_id: str) -> dict:
    """
    Optional: check payment status by order_id
    Cryptomus payment/info endpoint колдонулат.
    """
    _require_env()
    url = _base_url(CRYPTOMUS_INFO_PATH)

    payload = {"order_id": str(order_id)}
    data = await _request_json("POST", url, payload=payload)
    return data


def verify_webhook(body_bytes: bytes, header_sign: str) -> bool:
    """
    Verify webhook signature.
    Many setups: sign is computed the same way as request sign.
    Secret: if CRYPTOMUS_WEBHOOK_SECRET exists -> use it, else API KEY.
    """
    if not header_sign:
        return False

    secret = CRYPTOMUS_WEBHOOK_SECRET or CRYPTOMUS_API_KEY
    if not secret:
        return False

    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return False

    expected = _sign(data, secret)
    return expected == header_sign


