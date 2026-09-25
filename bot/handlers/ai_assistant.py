import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import MAX_AI_HISTORY
from bot.database import db
from bot.keyboards import back_button
from bot.services import ai_service

logger = logging.getLogger(__name__)
router = Router(name="ai_assistant")

AI_INTRO = (
    "🤖 <b>AI Assistant</b>\n\n"
    "Ask me anything, one-off with <code>/ai &lt;question&gt;</code>, or turn on "
    "AI mode below to chat back-and-forth like a normal conversation "
    "(remembers the last {n} messages).\n\n"
    "AI mode only works in a private chat with me, not in groups."
).format(n=MAX_AI_HISTORY)


def _ai_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Start AI Chat", callback_data="ai:start")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")],
    ])


def _ai_stop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Stop AI Chat", callback_data="ai:stop")],
    ])


@router.callback_query(F.data == "menu:ai")
async def show_ai_page(callback: CallbackQuery) -> None:
    if not ai_service.is_configured():
        await callback.message.edit_text(
            AI_INTRO + "\n\n⚠️ Not configured yet — the bot owner needs to set ANTHROPIC_API_KEY.",
            reply_markup=back_button(),
        )
    else:
        await callback.message.edit_text(AI_INTRO, reply_markup=_ai_start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "ai:start")
async def start_ai_mode(callback: CallbackQuery) -> None:
    await db.set_ai_mode(callback.from_user.id, True)
    await callback.message.edit_text(
        "🤖 AI mode is <b>ON</b>. Just send me a message!\n"
        "Tap below or send /stopai to end the conversation.",
        reply_markup=_ai_stop_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ai:stop")
async def stop_ai_mode_cb(callback: CallbackQuery) -> None:
    await db.set_ai_mode(callback.from_user.id, False)
    await callback.message.edit_text("AI mode is now off. Send /start to open the menu again.")
    await callback.answer()


@router.message(Command("stopai"))
async def stop_ai_mode_cmd(message: Message) -> None:
    await db.set_ai_mode(message.from_user.id, False)
    await message.answer("AI mode is now off.")


@router.message(Command("ai"))
async def cmd_ai_oneoff(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/ai &lt;question&gt;</code>")
        return
    if not ai_service.is_configured():
        await message.answer("⚠️ The AI assistant isn't configured yet (missing ANTHROPIC_API_KEY).")
        return

    thinking = await message.answer("💭 Thinking...")
    try:
        reply = await ai_service.get_reply([{"role": "user", "content": parts[1]}])
        await thinking.edit_text(reply or "(no response)")
    except ai_service.AIError as e:
        await thinking.edit_text(f"❌ {e}")


@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def ai_conversation(message: Message) -> None:
    if not await db.get_ai_mode(message.from_user.id):
        return  # not in AI mode — leave the message alone
    if not ai_service.is_configured():
        await message.answer("⚠️ The AI assistant isn't configured yet (missing ANTHROPIC_API_KEY).")
        return

    user_id = message.from_user.id
    await db.add_ai_message(user_id, "user", message.text)
    history = await db.get_ai_history(user_id, MAX_AI_HISTORY)

    thinking = await message.answer("💭 Thinking...")
    try:
        reply = await ai_service.get_reply(history)
        await db.add_ai_message(user_id, "assistant", reply)
        await thinking.edit_text(reply or "(no response)")
    except ai_service.AIError as e:
        await thinking.edit_text(f"❌ {e}")
