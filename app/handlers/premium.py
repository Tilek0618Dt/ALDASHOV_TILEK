from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "menu:premium")
async def premium(c: CallbackQuery):
    await c.message.answer("⭐ Premium меню (кейин толтурабыз)")
    await c.answer()
