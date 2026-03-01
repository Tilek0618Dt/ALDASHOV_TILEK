# app/services/media/runway.py
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
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "").strip()

# Runway base url (docs боюнча өзгөрүшү мүмкүн)
RUNWAY_BASE_URL = os.getenv("RUNWAY_BASE_URL", "https://api.runwayml.com").strip()

# Универсал endpoint templates:
# Сенин docs'та башкача болсо ENV'ден алмаштырасың.
RUNWAY_CREATE_TASK_PATH = os.getenv("RUNWAY_CREATE_TASK_PATH", "/v1/tasks").strip()
RUNWAY_GET_TASK_PATH = os.getenv("RUNWAY_GET_TASK_PATH", "/v1/tasks/{task_id}").strip()

RUNWAY_TIMEOUT_S = int(os.getenv("RUNWAY_TIMEOUT_S", "60"))
RUNWAY_RETRIES = int(os.getenv("RUNWAY_RETRIES", "2"))

# Кээ бир Runway API "version" же "model" сурайт
RUNWAY_DEFAULT_MODEL = os.getenv("RUNWAY_DEFAULT_MODEL", "").strip()


# =========================================================
# Exceptions
# =========================================================
class RunwayError(RuntimeError):
    pass


class RunwayAuthError(RunwayError):
    pass


class RunwayRateLimitError(RunwayError):
    pass


class RunwayBadRequest(RunwayError):
    pass


class RunwayServerError(RunwayError):
    pass


# =========================================================
# Types / Settings
# =========================================================
TaskType = Literal["text_to_video", "image_to_video", "image"]

@dataclass
class RunwayOptions:
    task_type: TaskType = "text_to_video"
    prompt: str = ""
    negative_prompt: str = ""
    seconds: int = 5                 # 5/10 etc
    aspect_ratio: str = "9:16"       # 9:16 / 16:9 / 1:1
    seed: Optional[int] = None
    model: Optional[str] = None      # gen-3 / gen-2 etc (docs)
    # For image-to-video
    image_url: Optional[str] = None
    # Optional quality knobs
    motion: Optional[float] = None   # 0..1 (if supported)
    cfg_scale: Optional[float] = None


# =========================================================
# Helpers
# =========================================================
def _headers() -> dict:
    if not RUNWAY_API_KEY:
        raise RunwayAuthError("RUNWAY_API_KEY жок, досум 😭 Render ENVке кош!")
    # Runway көбүнчө Bearer token колдонот
    return {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    return f"{RUNWAY_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _err_from_status(status: int, body_text: str) -> RunwayError:
    msg = f"Runway error status={status}, body={body_text[:700]}"
    if status in (401, 403):
        return RunwayAuthError(msg)
    if status == 429:
        return RunwayRateLimitError(msg)
    if 400 <= status < 500:
        return RunwayBadRequest(msg)
    if status >= 500:
        return RunwayServerError(msg)
    return RunwayError(msg)


async def _request_json(
    method: str,
    url: str,
    *,
    payload: Optional[dict] = None,
    timeout_s: int = RUNWAY_TIMEOUT_S,
    retries: int = RUNWAY_RETRIES,
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
                    if isinstance(err, (RunwayRateLimitError, RunwayServerError)) and attempt < retries:
                        await asyncio.sleep(1.3 * (attempt + 1))
                        last_err = err
                        continue

                    raise err

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise RunwayError(f"Network/timeout error: {e}") from e

    raise RunwayError(f"Unknown error: {last_err}")


async def _download_file(url: str, out_path: str, timeout_s: int = 180) -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=timeout_s)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RunwayError(f"Download failed status={resp.status}, body={text[:400]}")
            data = await resp.read()

    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


# =========================================================
# Payload builder (универсал)
# =========================================================
def _build_payload(opt: RunwayOptions) -> dict:
    """
    Бул payload field'дер Runway docs'тагы аттарга жараша өзгөрөт.
    СЕНИН docs'та кандай болсо — ушуну 1 жолу тууралап коёсуң.
    """
    model = opt.model or RUNWAY_DEFAULT_MODEL or None

    payload: dict[str, Any] = {
        "type": opt.task_type,   # "text_to_video" / "image_to_video" ...
        "prompt": opt.prompt,
        "seconds": int(opt.seconds),
        "aspect_ratio": opt.aspect_ratio,
    }

    if model:
        payload["model"] = model

    if opt.negative_prompt:
        payload["negative_prompt"] = opt.negative_prompt

    if opt.seed is not None:
        payload["seed"] = int(opt.seed)

    # image-to-video
    if opt.task_type == "image_to_video":
        if not opt.image_url:
            raise RunwayBadRequest("image_to_video үчүн image_url керек 😅")
        payload["image_url"] = opt.image_url

    # optional knobs (эгер сенде колдосо)
    if opt.motion is not None:
        payload["motion"] = float(opt.motion)
    if opt.cfg_scale is not None:
        payload["cfg_scale"] = float(opt.cfg_scale)

    return payload


# =========================================================
# API: create task
# =========================================================
async def create_task(opt: RunwayOptions) -> str:
    if not opt.prompt.strip():
        raise RunwayBadRequest("Prompt бош болуп калды 😅")

    url = _url(RUNWAY_CREATE_TASK_PATH)
    payload = _build_payload(opt)
    data = await _request_json("POST", url, payload=payload)

    # task id extraction (универсал)
    task_id = (
        data.get("id")
        or data.get("task_id")
        or (data.get("result") or {}).get("id")
        or (data.get("result") or {}).get("task_id")
    )

    if not task_id:
        raise RunwayError(f"Task ID табылган жок. Response: {data}")
    return str(task_id)


# =========================================================
# API: get task status
# =========================================================
async def get_task(task_id: str) -> dict:
    url = _url(RUNWAY_GET_TASK_PATH.format(task_id=task_id))
    return await _request_json("GET", url)


def _extract_status(data: dict) -> str:
    # queued/running/succeeded/failed ...
    return (
        (data.get("status") or "")
        or ((data.get("result") or {}).get("status") or "")
        or ""
    ).lower()


def _extract_result_url(data: dict) -> Optional[str]:
    """
    Runway response'та result видео url ар башкача болушу мүмкүн:
    - output.url
    - result.outputs[0].url
    - artifacts[0].url
    etc.
    Ушул жерде сен docs'ка жараша 1 жолу тууралап коёсуң.
    """
    # common candidates
    candidates: list[Any] = []

    # output.url
    candidates.append((data.get("output") or {}).get("url"))

    # result.url
    candidates.append((data.get("result") or {}).get("url"))

    # artifacts[0].url
    artifacts = data.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        candidates.append((artifacts[0] or {}).get("url"))

    # outputs[0].url
    outputs = (data.get("result") or {}).get("outputs")
    if isinstance(outputs, list) and outputs:
        candidates.append((outputs[0] or {}).get("url"))

    # direct url
    candidates.append(data.get("url"))

    for c in candidates:
        if isinstance(c, str) and c.startswith("http"):
            return c

    return None


async def wait_result_url(
    task_id: str,
    *,
    timeout_sec: int = 240,
    poll_every_sec: float = 2.0,
) -> str:
    started = time.time()
    last_data: dict = {}

    while True:
        if time.time() - started > timeout_sec:
            raise RunwayError(f"Timeout күттүк ({timeout_sec}s). Last={last_data}")

        data = await get_task(task_id)
        last_data = data

        st = _extract_status(data)

        if st in ("succeeded", "success", "completed", "done"):
            url = _extract_result_url(data)
            if not url:
                raise RunwayError(f"Success, бирок url табылган жок. Response={data}")
            return url

        if st in ("failed", "error", "cancelled", "canceled"):
            raise RunwayError(f"Task failed status={st}. Response={data}")

        await asyncio.sleep(poll_every_sec)


# =========================================================
# High-level: generate & download
# =========================================================
async def generate_text_to_video_to_file(
    prompt: str,
    out_path: str,
    *,
    negative_prompt: str = "",
    seconds: int = 5,
    aspect_ratio: str = "9:16",
    model: Optional[str] = None,
    timeout_sec: int = 240,
) -> dict:
    opt = RunwayOptions(
        task_type="text_to_video",
        prompt=prompt,
        negative_prompt=negative_prompt,
        seconds=seconds,
        aspect_ratio=aspect_ratio,
        model=model,
    )
    task_id = await create_task(opt)
    result_url = await wait_result_url(task_id, timeout_sec=timeout_sec)
    path = await _download_file(result_url, out_path)
    return {"task_id": task_id, "result_url": result_url, "file_path": path}


async def generate_image_to_video_to_file(
    prompt: str,
    image_url: str,
    out_path: str,
    *,
    negative_prompt: str = "",
    seconds: int = 5,
    aspect_ratio: str = "9:16",
    model: Optional[str] = None,
    timeout_sec: int = 240,
) -> dict:
    opt = RunwayOptions(
        task_type="image_to_video",
        prompt=prompt,
        negative_prompt=negative_prompt,
        seconds=seconds,
        aspect_ratio=aspect_ratio,
        model=model,
        image_url=image_url,
    )
    task_id = await create_task(opt)
    result_url = await wait_result_url(task_id, timeout_sec=timeout_sec)
    path = await _download_file(result_url, out_path)
    return {"task_id": task_id, "result_url": result_url, "file_path": path}
                  

