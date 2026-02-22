from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "menu:support")
async def support(c: CallbackQuery):
    await c.message.answer("🆘 Support: бул жерге админ контакт коёбуз")
    await c.answer()
