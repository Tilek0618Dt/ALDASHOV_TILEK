# app/services/media/elevenlabs.py
from __future__ import annotations

import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any

import aiohttp


# =========================
# Config (ENV)
# =========================
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()  # default voice
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "").strip() or "eleven_multilingual_v2"

ELEVEN_API_BASE = os.getenv("ELEVENLABS_API_BASE", "").strip() or "https://api.elevenlabs.io/v1"

# Render үчүн коопсуз папка:
TMP_DIR = os.getenv("TMP_DIR", "").strip() or "/tmp"


# =========================
# Errors
# =========================
class ElevenLabsError(RuntimeError):
    pass


@dataclass
class TTSResult:
    path: str
    bytes_size: int
    seconds_est: float
    voice_id: str
    model_id: str


# =========================
# Internal helpers
# =========================
def _ensure_ready() -> None:
    if not ELEVENLABS_API_KEY:
        raise ElevenLabsError("ELEVENLABS_API_KEY жок (ENVке кош) 😭")
    if not ELEVENLABS_VOICE_ID:
        # voice id жок болсо да иштей берет — бирок көп учурда керек
        # Ошондуктан мажбурлайбыз:
        raise ElevenLabsError("ELEVENLABS_VOICE_ID жок (ENVке кош) 😭")


def _estimate_seconds(text: str) -> float:
    # Орточо сүйлөө 2.2–2.8 сөз/сек. Биз rough estimate кылабыз.
    words = max(1, len(text.split()))
    return round(words / 2.4, 2)


async def _request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: int = 60,
    retries: int = 2,
) -> bytes:
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=headers, json=json_body) as resp:
                    data = await resp.read()

                    if 200 <= resp.status < 300:
                        return data

                    # Try parse error message
                    msg = ""
                    try:
                        # if json error
                        import json as _json
                        msg = _json.loads(data.decode("utf-8", errors="ignore")).get("detail") or ""
                    except Exception:
                        msg = data.decode("utf-8", errors="ignore")[:400]

                    raise ElevenLabsError(f"ElevenLabs HTTP {resp.status}: {msg}")

        except Exception as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(0.7 * (attempt + 1))
                continue
            break

    raise ElevenLabsError(f"ElevenLabs request failed: {last_err}")


# =========================
# Public API
# =========================
async def tts_to_mp3(
    text: str,
    *,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    stability: float = 0.45,
    similarity_boost: float = 0.85,
    style: float = 0.2,
    speaker_boost: bool = True,
    out_dir: str = TMP_DIR,
) -> TTSResult:
    """
    Generate MP3 speech audio from text using ElevenLabs.

    Returns TTSResult with local file path (/tmp/xxx.mp3).
    """
    _ensure_ready()

    text = (text or "").strip()
    if not text:
        raise ElevenLabsError("Текст бош болуп калды 😅")

    vid = (voice_id or ELEVENLABS_VOICE_ID).strip()
    mid = (model_id or ELEVENLABS_MODEL_ID).strip()

    # Endpoint
    url = f"{ELEVEN_API_BASE}/text-to-speech/{vid}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": mid,
        "voice_settings": {
            "stability": float(stability),
            "similarity_boost": float(similarity_boost),
            "style": float(style),
            "use_speaker_boost": bool(speaker_boost),
        },
        # output_format кээ бир аккаунттарда колдолот, кээ биринде жок.
        # "output_format": "mp3_44100_128",
    }

    audio_bytes = await _request_with_retry("POST", url, headers=headers, json_body=payload)

    os.makedirs(out_dir, exist_ok=True)
    filename = f"tilek_voice_{uuid.uuid4().hex}.mp3"
    path = os.path.join(out_dir, filename)

    with open(path, "wb") as f:
        f.write(audio_bytes)

    return TTSResult(
        path=path,
        bytes_size=len(audio_bytes),
        seconds_est=_estimate_seconds(text),
        voice_id=vid,
        model_id=mid,
    )


async def list_voices() -> Dict[str, Any]:
    """
    Optional: list available voices (debug/admin use).
    """
    _ensure_ready()

    url = f"{ELEVEN_API_BASE}/voices"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "application/json",
    }

    raw = await _request_with_retry("GET", url, headers=headers, json_body=None, timeout_s=30, retries=1)
    try:
        import json
        return json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception:
        return {"raw": raw.decode("utf-8", errors="ignore")}


async def healthcheck() -> bool:
    """
    Quick check to see if API key works.
    """
    try:
        data = await list_voices()
        return bool(data)
    except Exception:
        return False
