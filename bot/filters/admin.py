from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message

_ADMIN_STATUSES = {"administrator", "creator"}


class IsAdmin(BaseFilter):
    """Only lets the handler run if the message sender is an admin/creator
    of the group, or if used in a private chat (for testing)."""

    async def __call__(self, message: Message, bot: Bot) -> bool:
        if message.chat.type == "private":
            return True
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in _ADMIN_STATUSES
