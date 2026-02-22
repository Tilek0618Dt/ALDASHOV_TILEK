import httpx
from app.config import GROK_API_KEY

async def grok_answer(prompt: str) -> str:
    # Бул жерде сен өз Grok API'ңды туташтырасың.
    # Азырынча stub:
    if not prompt:
        return "Эмне дейсиң досум? 🙂"
    return f"Сен жаздың: {prompt}\n(Азырынча Grok stub жооп)"
