from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.keyboards import main_menu_kb

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    await m.answer("Салам досум! Мен сенин AI ботум 😎💎", reply_markup=main_menu_kb())
