from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu_keyboard, back_button
from bot.config import DEVELOPER_NAME, DEVELOPER_USERNAME, DEVELOPER_GITHUB

router = Router(name="start")

MAIN_TEXT = (
    "👋 <b>Welcome To Voidhaven Services!</b>\n\n"
    "This bot bundles four toolsets. Pick one below to see what it does, "
    "or just start using its commands directly."
)

DOWNLOAD_TEXT = (
    "📥 <b>Downloader & Media Converter</b>\n\n"
    "• <code>/download &lt;url&gt;</code> — download media from a link (YouTube, etc.)\n"
    "• Send me a video, audio, or document directly — I'll offer to convert it "
    "(extract MP3, convert to GIF/MP4) or save it to Cloud Storage.\n\n"
    "Telegram bots can't send files over 50MB, so very large media won't go through."
)

MODERATION_TEXT = (
    "🛡 <b>Group Management & Moderation</b>\n"
    "Add me to a group as admin (with ban/delete/restrict permissions) and "
    "disable privacy mode via @BotFather so I can see regular messages.\n\n"
    "• /ban, /kick, /mute [minutes], /unmute — reply to a user's message\n"
    "• /warn, /unwarn, /warnings, /clearwarnings\n"
    "• /purge &lt;n&gt; — delete the last n messages\n"
    "• /addword, /removeword, /words — banned-word filter\n"
    "• /setwelcome &lt;text&gt; — customize the join message ({name} placeholder)\n"
    "• /rules — show current moderation settings\n\n"
    "New members must pass a one-tap captcha before they can chat."
)

DEV_TEXT = (
    "👨‍💻 <b>Developer</b>\n\n"
    f"<b>Name:</b> {DEVELOPER_NAME}\n"
    f"<b>Telegram:</b> @{DEVELOPER_USERNAME}\n"
    + (f"<b>GitHub:</b> {DEVELOPER_GITHUB}\n" if DEVELOPER_GITHUB else "")
    + "\nBuilt with aiogram 3, yt-dlp, ffmpeg, and the Anthropic API."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(MAIN_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help", "menu"))
async def cmd_help(message: Message) -> None:
    await message.answer(MAIN_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:main")
async def show_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MAIN_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:download")
async def show_download_page(callback: CallbackQuery) -> None:
    await callback.message.edit_text(DOWNLOAD_TEXT, reply_markup=back_button())
    await callback.answer()


@router.callback_query(F.data == "menu:moderation")
async def show_moderation_page(callback: CallbackQuery) -> None:
    await callback.message.edit_text(MODERATION_TEXT, reply_markup=back_button())
    await callback.answer()


@router.callback_query(F.data == "menu:dev")
async def show_dev_page(callback: CallbackQuery) -> None:
    await callback.message.edit_text(DEV_TEXT, reply_markup=back_button())
    await callback.answer()
