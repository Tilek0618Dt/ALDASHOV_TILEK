# app/services/grok.py
from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError, AuthenticationError, BadRequestError


# =========================================================
# ENV
# =========================================================
GROK_API_KEY = os.getenv("GROK_API_KEY", "").strip()
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").strip()
GROK_MODEL = os.getenv("GROK_MODEL", "grok-beta").strip()
GROK_TIMEOUT_S = int(os.getenv("GROK_TIMEOUT_S", "45"))

# Telegram safe length (markdown)
TELEGRAM_MAX_CHARS = 3800


# =========================================================
# Client
# =========================================================
_client: Optional[AsyncOpenAI] = None


def _get_client() -> Optional[AsyncOpenAI]:
    global _client
    if not GROK_API_KEY:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=GROK_API_KEY,
            base_url=GROK_BASE_URL,
            timeout=GROK_TIMEOUT_S,
        )
    return _client


# =========================================================
# Tilek system prompt (core brand)
# =========================================================
def _tilek_system(lang: str, style_mode: str, is_pro: bool) -> str:
    """
    style_mode: "cool" | "hard" | "smart"
    """
    # тон
    if style_mode == "cool":
        persona = "Сен Tilek AIсың: дос, күлкүлүү, абдан боорукер, түшүнүктүү сүйлөйсүң."
    elif style_mode == "hard":
        persona = "Сен Tilek AIсың: бир аз катуураак, мотивация берип, бирок адамды сындырбайсың."
    else:
        persona = "Сен Tilek AIсың: азыр серьёзный, так, логикалуу, системалуу жооп бересиң."

    pro_hint = (
        "Колдонуучу PRO: жоопту так, кыска, максимал пайдалуу бер. "
        "Керек болсо 1-2 альтернатив сунушта."
        if is_pro else
        "Колдонуучу FREE/PLUS: ашыкча узартпай, түшүнүктүү бер."
    )

    # Негизги правила
    rules = (
        f"{persona}\n"
        f"Жооп тили: {lang}.\n"
        "Стиль: жеңил, түшүнүктүү, эмодзи орду менен.\n"
        "Ар дайым структура менен жооп бер:\n"
        "1) 📌 Негизги жооп (1-4 сүйлөм)\n"
        "2) 📊 Түшүндүрмө (1-3 пункт)\n"
        "3) 💡 Кеңеш/Кийинки кадам (1-2 пункт)\n"
        "Эгер суроо түшүнүксүз болсо — 1 тактоочу суроо бер.\n"
        "Эгер код сураса — кыска, иштей турган мисал бер.\n"
        "Узак текст жазба, бирок маанилүүсүн калтыр.\n"
        f"{pro_hint}"
    )
    return rules


def _pick_style(style_counter: int) -> str:
    # 0: 😎, 1: 😈, 2: 🧠 loop
    m = style_counter % 3
    if m == 0:
        return "cool"
    if m == 1:
        return "hard"
    return "smart"


def _safe_trim(text: str, limit: int = TELEGRAM_MAX_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit - 20].rstrip() + "\n\n…(кыска кесилди) 😅"


@dataclass
class GrokResult:
    ok: bool
    text: str
    model: str
    error: Optional[str] = None


# =========================================================
# Public function
# =========================================================
async def grok_chat(
    prompt: str,
    *,
    lang: str = "ky",
    style_counter: int = 0,
    is_pro: bool = False,
) -> GrokResult:
    """
    Returns GrokResult(text=...) always safe for Telegram.
    """

    prompt = (prompt or "").strip()
    if not prompt:
        return GrokResult(ok=True, text="📌 Негизги жооп:\nЭмне деп берейин, досум? 🙂\n\n💡 Кеңеш:\nСурооңду 1 сүйлөм менен тактап жазчы 😎", model="local")

    # DEMO режим
    client = _get_client()
    if client is None:
        demo = (
            "📌 Негизги жооп:\n"
            f"(DEMO) Сен жаздың: {prompt}\n\n"
            "📊 Түшүндүрмө:\n"
            "• Азыр GROK_API_KEY коюла элек\n"
            "• Render ENVке кошсоң — реал жооп иштейт\n\n"
            "💡 Кеңеш:\n"
            "Render → Environment → GROK_API_KEY кошуп, кайра Deploy кыл 😎"
        )
        return GrokResult(ok=True, text=_safe_trim(demo), model="demo")

    style_mode = _pick_style(style_counter)
    system = _tilek_system(lang, style_mode, is_pro)

    # PRO: бир аз көбүрөөк токен/сапат
    max_tokens = 900 if is_pro else 650
    temperature = 0.7 if style_mode != "smart" else 0.55

    try:
        resp = await client.chat.completions.create(
            model=GROK_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            content = "📌 Негизги жооп:\nАзыр жооп бош болуп калды 😅\n\n💡 Кеңеш:\nКайра 1 жолу жиберип көр, досум."

        return GrokResult(ok=True, text=_safe_trim(content), model=GROK_MODEL)

    except AuthenticationError:
        msg = (
            "📌 Негизги жооп:\nGrok key туура эмес болуп калды 😭\n\n"
            "📊 Түшүндүрмө:\n• GROK_API_KEY жараксыз/эски\n\n"
            "💡 Кеңеш:\nRender ENV’тен GROK_API_KEY жаңылап кой да кайра Deploy кыл 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error="auth")

    except RateLimitError:
        msg = (
            "📌 Негизги жооп:\nАзыр көп суроо болуп жатат (rate limit) 😅\n\n"
            "📊 Түшүндүрмө:\n• Сервер убактылуу жүктөлгөн\n\n"
            "💡 Кеңеш:\n30-60 сек күтүп кайра жибер, досум 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error="rate_limit")

    except (APIConnectionError, asyncio.TimeoutError):
        msg = (
            "📌 Негизги жооп:\nИнтернет/сервер байланышы үзүлдү окшойт 😭\n\n"
            "📊 Түшүндүрмө:\n• API жетпей калды же timeout болду\n\n"
            "💡 Кеңеш:\nКайра жиберип көр. Эгер кайталанса — Render логун карайбыз 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error="connection")

    except BadRequestError as e:
        msg = (
            "📌 Негизги жооп:\nСуроо форматы туура эмес болуп калды 😅\n\n"
            "📊 Түшүндүрмө:\n• API 'bad request' кайтарды\n\n"
            "💡 Кеңеш:\nСуроону кыскартып, жөнөкөй кылып кайра жазчы 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error=f"bad_request:{e}")

    except APIError as e:
        msg = (
            "📌 Негизги жооп:\nAI сервер ички ката берди 😭\n\n"
            "📊 Түшүндүрмө:\n• APIError болду\n\n"
            "💡 Кеңеш:\nКийинчерээк кайра аракет кыл. Эгер көп кайталанса — логдон көрөбүз 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error=f"api_error:{e}")

    except Exception as e:
        msg = (
            "📌 Негизги жооп:\nБелгисиз ката болуп калды 😭\n\n"
            "📊 Түшүндүрмө:\n• Ката: unknown\n\n"
            "💡 Кеңеш:\nКайра жибер. Эгер кайталанса — error текстин мага ташта 😎"
        )
        return GrokResult(ok=False, text=_safe_trim(msg), model=GROK_MODEL, error=f"unknown:{e}")
