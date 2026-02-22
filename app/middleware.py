from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from app.config import REQUIRED_CHANNEL

class ChannelGateMiddleware(BaseMiddleware):
    async def call(self, handler, event: TelegramObject, data: dict):
        if not REQUIRED_CHANNEL:
            return await handler(event, data)

        bot = data.get("bot")
        user = data.get("event_from_user")

        if not bot or not user:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(REQUIRED_CHANNEL, user.id)
            ok = member.status in ("member", "administrator", "creator")
        except TelegramBadRequest:
            ok = True  # if channel invalid, do not block
        except Exception:
            ok = True

        if not ok:
            text = f"❗️Досум, адегенде каналга кир: {REQUIRED_CHANNEL}\nАндан кийин кайра бас ✅"
            if isinstance(event, Message):
                await event.answer(text)
                return
            if isinstance(event, CallbackQuery):
                await event.message.answer(text)
                await event.answer()
                return

        return await handler(event, data)
