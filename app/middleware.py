from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatMemberStatus

from app.config import REQUIRED_CHANNEL, CHANNEL_URL

def _is_channel_id(val: str) -> bool:
    return val.strip().lstrip("-").isdigit()

class ChannelGateMiddleware(BaseMiddleware):
    async def call(self, handler, event, data):
        if not REQUIRED_CHANNEL:
            return await handler(event, data)

        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if not user_id:
            return await handler(event, data)

        try:
            chat = int(REQUIRED_CHANNEL) if _is_channel_id(REQUIRED_CHANNEL) else REQUIRED_CHANNEL
            member = await bot.get_chat_member(chat_id=chat, user_id=user_id)
            ok = member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
            if ok:
                return await handler(event, data)
        except TelegramBadRequest:
            # туура эмес канал болсо блок кылбайбыз
            return await handler(event, data)
        except Exception:
            return await handler(event, data)

        text = (
            "🚪 Досум, биринчи каналга каттал!\n\n"
            f"👉 {CHANNEL_URL or REQUIRED_CHANNEL}\n\n"
            "Катталгандан кийин кайра /start бас 😎"
        )
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.message.answer(text)
            await event.answer()
        return
