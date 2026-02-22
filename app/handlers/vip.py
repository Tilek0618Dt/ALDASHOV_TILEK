from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "menu:vip")
async def vip(c: CallbackQuery):
    await c.message.answer("🎥 VIP меню (кейин толтурабыз)")
    await c.answer()
