import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, ChatPermissions, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated,
)
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION

from bot.database import db
from bot.filters.admin import IsAdmin
from bot.services import flood_control

logger = logging.getLogger(__name__)
router = Router(name="moderation")

CAPTCHA_TIMEOUT_SECONDS = 120
# Tracks users who joined and haven't clicked the captcha yet: {(chat_id, user_id): True}
_unverified: dict[tuple[int, int], bool] = {}


# ---------------------------------------------------------------------------
# New member captcha
# ---------------------------------------------------------------------------

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_member_join(event: ChatMemberUpdated, bot: Bot) -> None:
    settings = await db.get_settings(event.chat.id)
    user = event.new_chat_member.user
    if user.is_bot:
        return

    if not settings["captcha_enabled"]:
        if settings["welcome_message"]:
            await bot.send_message(event.chat.id, settings["welcome_message"].format(name=user.full_name))
        return

    # Restrict the new member until they pass the captcha
    await bot.restrict_chat_member(
        event.chat.id, user.id,
        permissions=ChatPermissions(can_send_messages=False),
    )
    _unverified[(event.chat.id, user.id)] = True

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ I'm not a robot", callback_data=f"verify:{user.id}")
    ]])
    msg = await bot.send_message(
        event.chat.id,
        f"Welcome {user.full_name}! Please tap the button below within "
        f"{CAPTCHA_TIMEOUT_SECONDS // 60} minutes to unlock chat.",
        reply_markup=keyboard,
    )

    async def _timeout_kick():
        await asyncio.sleep(CAPTCHA_TIMEOUT_SECONDS)
        if _unverified.pop((event.chat.id, user.id), None):
            try:
                await bot.ban_chat_member(event.chat.id, user.id)
                await bot.unban_chat_member(event.chat.id, user.id)  # ban+unban = kick, not permaban
                await msg.edit_text(f"{user.full_name} didn't verify in time and was removed.")
            except Exception:
                logger.exception("Failed to remove unverified member")

    asyncio.create_task(_timeout_kick())


@router.callback_query(F.data.startswith("verify:"))
async def on_verify_click(callback: CallbackQuery, bot: Bot) -> None:
    target_user_id = int(callback.data.split(":", 1)[1])
    if callback.from_user.id != target_user_id:
        await callback.answer("This button isn't for you.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    _unverified.pop((chat_id, target_user_id), None)
    await bot.restrict_chat_member(
        chat_id, target_user_id,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_other_messages=True,
        ),
    )
    settings = await db.get_settings(chat_id)
    welcome = settings["welcome_message"] or "Verified! Welcome to the group, {name}."
    await callback.message.edit_text(welcome.format(name=callback.from_user.full_name))
    await callback.answer("Verified ✅")


# ---------------------------------------------------------------------------
# Flood control + banned word filter (runs on every group text message)
# ---------------------------------------------------------------------------

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def moderate_message(message: Message, bot: Bot) -> None:
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status in {"administrator", "creator"}:
        return  # never auto-moderate admins

    settings = await db.get_settings(message.chat.id)

    # banned words
    words = await db.list_banned_words(message.chat.id)
    text_lower = message.text.lower()
    if any(w in text_lower for w in words):
        try:
            await message.delete()
        except Exception:
            pass
        count = await db.add_warning(message.chat.id, message.from_user.id)
        await _handle_warning_threshold(message.chat.id, message.from_user, count, settings, bot)
        return

    # flood control
    flood_control.record_message(message.chat.id, message.from_user.id)
    if flood_control.is_flooding(
        message.chat.id, message.from_user.id,
        settings["flood_limit"], settings["flood_window_seconds"],
    ):
        try:
            await bot.restrict_chat_member(
                message.chat.id, message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await message.answer(
                f"🔇 {message.from_user.full_name} was muted for flooding the chat."
            )
        except Exception:
            logger.exception("Failed to mute flooding user")


async def _handle_warning_threshold(chat_id, user, count, settings, bot: Bot) -> None:
    if count >= settings["max_warnings"]:
        await bot.ban_chat_member(chat_id, user.id)
        await db.clear_warnings(chat_id, user.id)
        await bot.send_message(chat_id, f"🚫 {user.full_name} was banned after {count} warnings.")
    else:
        await bot.send_message(
            chat_id,
            f"⚠️ {user.full_name} received a warning ({count}/{settings['max_warnings']}).",
        )


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

def _get_target(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    return None


@router.message(Command("ban"), IsAdmin())
async def cmd_ban(message: Message, bot: Bot) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /ban to ban them.")
        return
    await bot.ban_chat_member(message.chat.id, target.id)
    await message.answer(f"🚫 Banned {target.full_name}.")


@router.message(Command("kick"), IsAdmin())
async def cmd_kick(message: Message, bot: Bot) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /kick to remove them.")
        return
    await bot.ban_chat_member(message.chat.id, target.id)
    await bot.unban_chat_member(message.chat.id, target.id)
    await message.answer(f"👢 Kicked {target.full_name}.")


@router.message(Command("mute"), IsAdmin())
async def cmd_mute(message: Message, bot: Bot) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /mute [minutes] to mute them.")
        return
    parts = message.text.split()
    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    until_date = None
    if minutes:
        import time
        until_date = int(time.time()) + minutes * 60

    await bot.restrict_chat_member(
        message.chat.id, target.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date,
    )
    duration = f"{minutes} minute(s)" if minutes else "indefinitely"
    await message.answer(f"🔇 Muted {target.full_name} for {duration}.")


@router.message(Command("unmute"), IsAdmin())
async def cmd_unmute(message: Message, bot: Bot) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /unmute to unmute them.")
        return
    await bot.restrict_chat_member(
        message.chat.id, target.id,
        permissions=ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_other_messages=True,
        ),
    )
    await message.answer(f"🔊 Unmuted {target.full_name}.")


@router.message(Command("warn"), IsAdmin())
async def cmd_warn(message: Message, bot: Bot) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /warn to warn them.")
        return
    settings = await db.get_settings(message.chat.id)
    count = await db.add_warning(message.chat.id, target.id)
    await _handle_warning_threshold(message.chat.id, target, count, settings, bot)


@router.message(Command("unwarn"), IsAdmin())
async def cmd_unwarn(message: Message) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /unwarn to remove a warning.")
        return
    count = await db.remove_one_warning(message.chat.id, target.id)
    await message.answer(f"Removed a warning from {target.full_name} ({count} remaining).")


@router.message(Command("warnings"))
async def cmd_warnings(message: Message) -> None:
    target = _get_target(message) or message.from_user
    count = await db.get_warnings(message.chat.id, target.id)
    await message.answer(f"{target.full_name} has {count} warning(s).")


@router.message(Command("clearwarnings"), IsAdmin())
async def cmd_clearwarnings(message: Message) -> None:
    target = _get_target(message)
    if not target:
        await message.answer("Reply to a user's message with /clearwarnings.")
        return
    await db.clear_warnings(message.chat.id, target.id)
    await message.answer(f"Cleared all warnings for {target.full_name}.")


@router.message(Command("purge"), IsAdmin())
async def cmd_purge(message: Message, bot: Bot) -> None:
    parts = message.text.split()
    n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
    n = min(n, 100)
    deleted = 0
    for msg_id in range(message.message_id - 1, message.message_id - 1 - n, -1):
        try:
            await bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except Exception:
            pass
    await message.delete()
    notice = await message.answer(f"🧹 Purged {deleted} message(s).")
    await asyncio.sleep(3)
    await notice.delete()


@router.message(Command("addword"), IsAdmin())
async def cmd_addword(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /addword <word>")
        return
    await db.add_banned_word(message.chat.id, parts[1].strip())
    await message.answer(f"Added \"{parts[1].strip()}\" to the banned word list.")


@router.message(Command("removeword"), IsAdmin())
async def cmd_removeword(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /removeword <word>")
        return
    await db.remove_banned_word(message.chat.id, parts[1].strip())
    await message.answer(f"Removed \"{parts[1].strip()}\" from the banned word list.")


@router.message(Command("words"))
async def cmd_words(message: Message) -> None:
    words = await db.list_banned_words(message.chat.id)
    text = ", ".join(words) if words else "(none set)"
    await message.answer(f"Banned words: {text}")


@router.message(Command("setwelcome"), IsAdmin())
async def cmd_setwelcome(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setwelcome <message> — use {name} for the member's name.")
        return
    await db.update_setting(message.chat.id, "welcome_message", parts[1])
    await message.answer("Welcome message updated.")


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    settings = await db.get_settings(message.chat.id)
    await message.answer(
        f"📋 Group settings:\n"
        f"• Captcha for new members: {'on' if settings['captcha_enabled'] else 'off'}\n"
        f"• Max warnings before ban: {settings['max_warnings']}\n"
        f"• Flood limit: {settings['flood_limit']} messages / {settings['flood_window_seconds']}s"
    )
