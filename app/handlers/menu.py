from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards import main_menu_kb

router = Router()

@router.callback_query(F.data.startswith("menu:"))
async def menu(c: CallbackQuery):
    await c.message.answer("Меню ✅", reply_markup=main_menu_kb())
    await c.answer()
