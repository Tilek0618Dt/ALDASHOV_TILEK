from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чат", callback_data="menu:chat")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="menu:premium")],
        [InlineKeyboardButton(text="🎥 VIP", callback_data="menu:vip")],
        [InlineKeyboardButton(text="🆘 Support", callback_data="menu:support")],
    ])
