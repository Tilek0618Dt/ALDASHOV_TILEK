# app/services/media/suno.py
from __future__ import annotations

import os
import json
import time
import asyncio
from dataclasses import dataclass
from typing import Optional, Literal, Any

import aiohttp


# =========================================================
# ENV (Render)
# =========================================================
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "").strip()

# Base URL: сен колдонгон Suno gateway'иң кайсы болсо ошону коёсуң
SUNO_BASE_URL = os.getenv("SUNO_BASE_URL", "").strip()

# Endpoint templates (өзгөрмө)
# Мисал:
#   create: /v1/generate
#   get:    /v1/tasks/{task_id}
#   download: result_url менен түз жүктөйбүз
SUNO_CREATE_PATH = os.getenv("SUNO_CREATE_PATH", "/v1/generate").strip()
SUNO_GET_TASK_PATH = os.getenv("SUNO_GET_TASK_PATH", "/v1/tasks/{task_id}").strip()

SUNO_TIMEOUT_S = int(os.getenv("SUNO_TIMEOUT_S", "60"))
SUNO_RETRIES = int(os.getenv("SUNO_RETRIES", "2"))

# Optional defaults
SUNO_DEFAULT_MODEL = os.getenv("SUNO_DEFAULT_MODEL", "").strip()
SUNO_DEFAULT_AUDIO_FORMAT = os.getenv("SUNO_DEFAULT_AUDIO_FORMAT", "mp3").strip()  # mp3/wav


# =========================================================
# Exceptions
# =========================================================
class SunoError(RuntimeError):
    pass


class SunoAuthError(SunoError):
    pass


class SunoRateLimitError(SunoError):
    pass


class SunoBadRequest(SunoError):
    pass


class SunoServerError(SunoError):
    pass


# =========================================================
# Types / Settings
# =========================================================
Genre = Literal["auto", "pop", "hiphop", "edm", "rock", "lofi", "trap", "cinematic", "folk", "sad", "motivational"]

@dataclass
class SunoOptions:
    prompt: str
    title: str = ""
    genre: Genre = "auto"
    lyrics: str = ""              # кааласаң колдонуучу lyrics берет
    instrumental: bool = False    # True болсо lyrics жок
    duration_sec: int = 60        # 60 / 180 / 300 (VIP минут)
    model: Optional[str] = None
    audio_format: str = SUNO_DEFAULT_AUDIO_FORMAT  # mp3/wav
    seed: Optional[int] = None


# =========================================================
# Helpers
# =========================================================
def _headers() -> dict:
    if not SUNO_API_KEY:
        raise SunoAuthError("SUNO_API_KEY жок, досум 😭 Render ENVке кош!")
    # Көп gateway'лер Bearer кабыл алат
    return {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    if not SUNO_BASE_URL:
        raise SunoError("SUNO_BASE_URL жок, досум 😭 (gateway base url керек)")
    return f"{SUNO_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _err_from_status(status: int, body_text: str) -> SunoError:
    msg = f"Suno error status={status}, body={body_text[:900]}"
    if status in (401, 403):
        return SunoAuthError(msg)
    if status == 429:
        return SunoRateLimitError(msg)
    if 400 <= status < 500:
        return SunoBadRequest(msg)
    if status >= 500:
        return SunoServerError(msg)
    return SunoError(msg)


async def _request_json(
    method: str,
    url: str,
    *,
    payload: Optional[dict] = None,
    timeout_s: int = SUNO_TIMEOUT_S,
    retries: int = SUNO_RETRIES,
) -> dict:
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=_headers(), json=payload) as resp:
                    text = await resp.text()

                    if 200 <= resp.status < 300:
                        if not text.strip():
                            return {}
                        try:
                            return json.loads(text)
                        except Exception:
                            return {"raw": text}

                    err = _err_from_status(resp.status, text)

                    # retry only for 429 / 5xx
                    if isinstance(err, (SunoRateLimitError, SunoServerError)) and attempt < retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        last_err = err
                        continue

                    raise err

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise SunoError(f"Network/timeout error: {e}") from e

    raise SunoError(f"Unknown error: {last_err}")


async def _download_file(url: str, out_path: str, timeout_s: int = 180) -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=timeout_s)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers={"Accept": "*/*"}) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise SunoError(f"Download failed status={resp.status}, body={text[:400]}")
            data = await resp.read()

    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def _clamp_duration_sec(sec: int) -> int:
    # Биздин продукт: VIP MUSIC 1/3/5 мин
    # 60/180/300 гана өткөрөбүз
    if sec <= 60:
        return 60
    if sec <= 180:
        return 180
    return 300


def _build_payload(opt: SunoOptions) -> dict:
    if not opt.prompt.strip():
        raise SunoBadRequest("Prompt бош 😅")

    duration = _clamp_duration_sec(int(opt.duration_sec))
    model = opt.model or (SUNO_DEFAULT_MODEL or None)

    # Универсал payload (gateway’ге жараша field аттары башка болушу мүмкүн)
    payload: dict[str, Any] = {
        "prompt": opt.prompt,
        "duration_sec": duration,
        "instrumental": bool(opt.instrumental),
        "audio_format": (opt.audio_format or "mp3"),
    }

    if opt.title:
        payload["title"] = opt.title

    if opt.genre and opt.genre != "auto":
        payload["genre"] = opt.genre

    if opt.lyrics and not opt.instrumental:
        payload["lyrics"] = opt.lyrics

    if model:
        payload["model"] = model

    if opt.seed is not None:
        payload["seed"] = int(opt.seed)

    return payload


# =========================================================
# API: create task
# =========================================================
async def create_music_task(opt: SunoOptions) -> str:
    url = _url(SUNO_CREATE_PATH)
    payload = _build_payload(opt)
    data = await _request_json("POST", url, payload=payload)

    # task id extraction (универсал)
    task_id = (
        data.get("id")
        or data.get("task_id")
        or (data.get("result") or {}).get("id")
        or (data.get("result") or {}).get("task_id")
        or data.get("job_id")
    )

    if not task_id:
        raise SunoError(f"Task ID табылган жок. Response: {data}")
    return str(task_id)


# =========================================================
# API: get task
# =========================================================
async def get_task(task_id: str) -> dict:
    url = _url(SUNO_GET_TASK_PATH.format(task_id=task_id))
    return await _request_json("GET", url)


def _extract_status(data: dict) -> str:
    return (
        (data.get("status") or "")
        or ((data.get("result") or {}).get("status") or "")
        or ""
    ).lower()


def _extract_audio_url(data: dict) -> Optional[str]:
    """
    Көп gateway’лерде:
    - result.audio_url
    - output.url
    - tracks[0].url
    - result.tracks[0].audio_url
    ж.б болушу мүмкүн.
    """
    candidates: list[Any] = []

    # direct audio_url
    candidates.append(data.get("audio_url"))
    candidates.append((data.get("result") or {}).get("audio_url"))
    candidates.append((data.get("output") or {}).get("url"))

    tracks = data.get("tracks")
    if isinstance(tracks, list) and tracks:
        candidates.append((tracks[0] or {}).get("url"))
        candidates.append((tracks[0] or {}).get("audio_url"))

    r_tracks = (data.get("result") or {}).get("tracks")
    if isinstance(r_tracks, list) and r_tracks:
        candidates.append((r_tracks[0] or {}).get("url"))
        candidates.append((r_tracks[0] or {}).get("audio_url"))

    for c in candidates:
        if isinstance(c, str) and c.startswith("http"):
            return c
    return None


async def wait_audio_url(
    task_id: str,
    *,
    timeout_sec: int = 240,
    poll_every_sec: float = 2.0,
) -> str:
    started = time.time()
    last: dict = {}

    while True:
        if time.time() - started > timeout_sec:
            raise SunoError(f"Timeout күттүк ({timeout_sec}s). Last={last}")

        data = await get_task(task_id)
        last = data

        st = _extract_status(data)
        if st in ("succeeded", "success", "completed", "done", "ready"):
            url = _extract_audio_url(data)
            if not url:
                raise SunoError(f"Success, бирок audio_url табылган жок. Response={data}")
            return url

        if st in ("failed", "error", "cancelled", "canceled"):
            raise SunoError(f"Task failed status={st}. Response={data}")

        await asyncio.sleep(poll_every_sec)


# =========================================================
# High-level: generate & download
# =========================================================
async def generate_music_to_file(
    *,
    prompt: str,
    out_path: str,
    minutes: int = 1,  # 1/3/5
    title: str = "",
    genre: Genre = "auto",
    lyrics: str = "",
    instrumental: bool = False,
    model: Optional[str] = None,
    audio_format: str = "mp3",
    timeout_sec: int = 300,
) -> dict:
    """
    minutes: 1/3/5 -> duration_sec: 60/180/300
    """
    if minutes not in (1, 3, 5):
        # коопсуздук: башка мин кирсе да closest кылып алабыз
        minutes = 1 if minutes < 3 else (3 if minutes < 5 else 5)

    opt = SunoOptions(
        prompt=prompt,
        title=title,
        genre=genre,
        lyrics=lyrics,
        instrumental=instrumental,
        duration_sec=minutes * 60,
        model=model,
        audio_format=audio_format,
    )

    task_id = await create_music_task(opt)
    audio_url = await wait_audio_url(task_id, timeout_sec=timeout_sec)
    file_path = await _download_file(audio_url, out_path)

    return {"task_id": task_id, "audio_url": audio_url, "file_path": file_path}
