from aiogram import Router, F
from aiogram.types import Message
from app.services.grok import grok_answer
from app.style_engine import style_text

router = Router()

@router.message(F.text)
async def chat(m: Message):
    text = m.text.strip()
    ans = await grok_answer(text)
    await m.answer(style_text(ans))
