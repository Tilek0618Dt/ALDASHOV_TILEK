from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Суроо берүү", callback_data="m:chat")],
        [InlineKeyboardButton(text="🎥 Видео", callback_data="m:video"),
         InlineKeyboardButton(text="🪉 Музыка", callback_data="m:music")],
        [InlineKeyboardButton(text="🖼 Сүрөт", callback_data="m:image"),
         InlineKeyboardButton(text="🔊 Үн", callback_data="m:voice")],
        [InlineKeyboardButton(text="📄 Документ", callback_data="m:doc")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="m:premium"),
         InlineKeyboardButton(text="🎁 Реферал", callback_data="m:ref")],
        [InlineKeyboardButton(text="🌐 Тил/Өлкө", callback_data="m:lang"),
         InlineKeyboardButton(text="🆘 Жардам", callback_data="m:support")],
        [InlineKeyboardButton(text="😎 Tilek ким?", callback_data="m:history")]
    ])

def kb_premium() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 PLUS – $12/ай", callback_data="buy:plan:PLUS")],
        [InlineKeyboardButton(text="🔴 PRO – $28/ай", callback_data="buy:plan:PRO")],
        [InlineKeyboardButton(text="🎥 VIP VIDEO (пакет)", callback_data="m:vip_video")],
        [InlineKeyboardButton(text="🪉 VIP MUSIC (пакет)", callback_data="m:vip_music")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:back")]
    ])

def kb_vip_video() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 1 видео – $19.99", callback_data="buy:vip_video:1")],
        [InlineKeyboardButton(text="🎥 3 видео – $49.99", callback_data="buy:vip_video:3")],
        [InlineKeyboardButton(text="🎥 5 видео – $79.99", callback_data="buy:vip_video:5")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:premium")]
    ])

def kb_vip_music() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪉 3 мин – $29.99", callback_data="buy:vip_music:3")],
        [InlineKeyboardButton(text="🪉 5 мин – $49.99", callback_data="buy:vip_music:5")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="m:premium")]
    ])

def kb_after_pay(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Төлөмдү ачуу", url=url)],
        [InlineKeyboardButton(text="⬅️ Артка меню", callback_data="m:back")]
    ])
