# app/services/media/kling.py
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
KLING_API_KEY = os.getenv("KLING_API_KEY", "").strip()

# Бул URL сенин Kling провайдериңде башка болушу мүмкүн.
# Документациядан так URL коюп кой.
KLING_BASE_URL = os.getenv("KLING_BASE_URL", "https://api.kling.ai").strip()

# Endpoint templates (универсал)
# Сенин аккаунттагы docs боюнча өзгөрт:
KLING_CREATE_TASK_PATH = os.getenv("KLING_CREATE_TASK_PATH", "/v1/tasks").strip()
KLING_GET_TASK_PATH = os.getenv("KLING_GET_TASK_PATH", "/v1/tasks/{task_id}").strip()

# Result download might be direct url in response, or separate endpoint
KLING_TIMEOUT_S = int(os.getenv("KLING_TIMEOUT_S", "60"))
KLING_RETRIES = int(os.getenv("KLING_RETRIES", "2"))


# =========================================================
# Exceptions
# =========================================================
class KlingError(RuntimeError):
    pass


class KlingAuthError(KlingError):
    pass


class KlingRateLimitError(KlingError):
    pass


class KlingBadRequest(KlingError):
    pass


class KlingServerError(KlingError):
    pass


# =========================================================
# Types / Settings
# =========================================================
TaskType = Literal["video", "image"]

@dataclass
class KlingOptions:
    task_type: TaskType = "video"
    prompt: str = ""
    negative_prompt: str = ""
    duration_sec: int = 5          # мисалы: 5/10
    aspect_ratio: str = "9:16"     # 9:16, 16:9, 1:1
    quality: str = "standard"      # standard / high (эгер бар болсо)
    seed: Optional[int] = None
    # кээ бир Kling'де "model" / "version" бар:
    model: Optional[str] = None
    # image-to-video: source image url/file path (сен өзүң жибересиң)
    source_image_url: Optional[str] = None


# =========================================================
# HTTP helpers
# =========================================================
def _headers() -> dict:
    if not KLING_API_KEY:
        raise KlingAuthError("KLING_API_KEY жок, досум 😭 Render ENVке кош!")
    return {
        "Authorization": f"Bearer {KLING_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    return f"{KLING_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _err_from_status(status: int, body_text: str) -> KlingError:
    msg = f"Kling error status={status}, body={body_text[:700]}"
    if status in (401, 403):
        return KlingAuthError(msg)
    if status == 429:
        return KlingRateLimitError(msg)
    if 400 <= status < 500:
        return KlingBadRequest(msg)
    if status >= 500:
        return KlingServerError(msg)
    return KlingError(msg)


async def _request_json(
    method: str,
    url: str,
    *,
    payload: Optional[dict] = None,
    timeout_s: int = KLING_TIMEOUT_S,
    retries: int = KLING_RETRIES,
) -> dict:
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=_headers(), json=payload) as resp:
                    text = await resp.text()
                    if 200 <= resp.status < 300:
                        # кээде бош жооп болушу мүмкүн
                        if not text.strip():
                            return {}
                        try:
                            return json.loads(text)
                        except Exception:
                            # JSON эмес болсо да кайтарабыз
                            return {"raw": text}

                    err = _err_from_status(resp.status, text)

                    # retry only for 429/5xx
                    if isinstance(err, (KlingRateLimitError, KlingServerError)) and attempt < retries:
                        await asyncio.sleep(1.2 * (attempt + 1))
                        last_err = err
                        continue

                    raise err

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise KlingError(f"Network/timeout error: {e}") from e

    raise KlingError(f"Unknown error: {last_err}")


async def _download_file(url: str, out_path: str, timeout_s: int = 120) -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=timeout_s)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise KlingError(f"Download failed status={resp.status}, body={text[:400]}")
            data = await resp.read()

    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


# =========================================================
# Kling API: create task
# =========================================================
def _build_payload(opt: KlingOptions) -> dict:
    """
    Бул payload сенин Kling API’ңда башкача болушу мүмкүн.
    Документациядагы field аттарын ушунда тууралайсың.
    """
    payload: dict[str, Any] = {
        "type": opt.task_type,                # "video" / "image"
        "prompt": opt.prompt,
    }

    if opt.negative_prompt:
        payload["negative_prompt"] = opt.negative_prompt

    # video options
    if opt.task_type == "video":
        payload["duration"] = int(opt.duration_sec)
        payload["aspect_ratio"] = opt.aspect_ratio
        payload["quality"] = opt.quality

        if opt.source_image_url:
            # image-to-video
            payload["source_image_url"] = opt.source_image_url

    # optional
    if opt.seed is not None:
        payload["seed"] = int(opt.seed)
    if opt.model:
        payload["model"] = opt.model

    return payload


async def create_task(opt: KlingOptions) -> str:
    """
    Returns task_id
    """
    if not opt.prompt.strip():
        raise KlingBadRequest("Prompt бош болуп калды 😅")

    url = _url(KLING_CREATE_TASK_PATH)
    payload = _build_payload(opt)

    data = await _request_json("POST", url, payload=payload)

    # Универсал парсинг: кимде task_id, кимде id, кимде result.id
    task_id = (
        data.get("task_id")
        or data.get("id")
        or (data.get("result") or {}).get("task_id")
        or (data.get("result") or {}).get("id")
    )

    if not task_id:
        raise KlingError(f"Task ID табылган жок. Response: {data}")
    return str(task_id)


# =========================================================
# Poll task status
# =========================================================
def _extract_status(data: dict) -> str:
    # common statuses: queued/running/success/failed
    return (
        (data.get("status") or "")
        or ((data.get("result") or {}).get("status") or "")
        or ""
    ).lower()


def _extract_result_url(data: dict) -> Optional[str]:
    """
    Кээ бир Kling response ичинде result.url же output.url болот.
    Ушунда тууралап аласың.
    """
    # try common places
    candidates = [
        (data.get("result") or {}).get("url"),
        (data.get("result") or {}).get("video_url"),
        (data.get("result") or {}).get("image_url"),
        (data.get("output") or {}).get("url"),
        data.get("url"),
    ]
    for c in candidates:
        if c and isinstance(c, str) and c.startswith("http"):
            return c
    return None


async def get_task(task_id: str) -> dict:
    url = _url(KLING_GET_TASK_PATH.format(task_id=task_id))
    return await _request_json("GET", url)


async def wait_result_url(
    task_id: str,
    *,
    timeout_sec: int = 180,
    poll_every_sec: float = 2.0,
) -> str:
    """
    Wait until task completed and return downloadable url.
    """
    started = time.time()
    last_data: dict = {}

    while True:
        if time.time() - started > timeout_sec:
            raise KlingError(f"Timeout күттүк ({timeout_sec}s). Last={last_data}")

        data = await get_task(task_id)
        last_data = data

        st = _extract_status(data)
        if st in ("success", "completed", "done", "succeeded"):
            url = _extract_result_url(data)
            if not url:
                raise KlingError(f"Success, бирок url табылган жок. Response={data}")
            return url

        if st in ("failed", "error", "cancelled"):
            raise KlingError(f"Task failed status={st}. Response={data}")

        await asyncio.sleep(poll_every_sec)


# =========================================================
# High-level: generate and download
# =========================================================
async def generate_video_to_file(
    prompt: str,
    out_path: str,
    *,
    negative_prompt: str = "",
    duration_sec: int = 5,
    aspect_ratio: str = "9:16",
    quality: str = "standard",
    source_image_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_sec: int = 180,
) -> dict:
    """
    One-shot:
    - create task
    - wait result url
    - download -> out_path
    Returns dict with task_id + url + path
    """
    opt = KlingOptions(
        task_type="video",
        prompt=prompt,
        negative_prompt=negative_prompt,
        duration_sec=duration_sec,
        aspect_ratio=aspect_ratio,
        quality=quality,
        source_image_url=source_image_url,
        model=model,
    )

    task_id = await create_task(opt)
    result_url = await wait_result_url(task_id, timeout_sec=timeout_sec)

    path = await _download_file(result_url, out_path)

    return {
        "task_id": task_id,
        "result_url": result_url,
        "file_path": path,
    }


async def generate_image_to_file(
    prompt: str,
    out_path: str,
    *,
    negative_prompt: str = "",
    aspect_ratio: str = "1:1",
    quality: str = "standard",
    model: Optional[str] = None,
    timeout_sec: int = 120,
) -> dict:
    opt = KlingOptions(
        task_type="image",
        prompt=prompt,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        quality=quality,
        model=model,
    )

    task_id = await create_task(opt)
    result_url = await wait_result_url(task_id, timeout_sec=timeout_sec)
    path = await _download_file(result_url, out_path)

    return {
        "task_id": task_id,
        "result_url": result_url,
        "file_path": path,
    }
