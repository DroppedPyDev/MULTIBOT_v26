from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="start")

WELCOME = (
    "👋 <b>File Downloader & Media Converter Bot</b>\n\n"
    "• <code>/download &lt;url&gt;</code> — download media from a link (YouTube, etc.)\n"
    "• Send me a video or audio file directly — I'll offer conversion options "
    "(extract MP3, convert to GIF, convert to MP4)\n\n"
    "Files over Telegram's 50MB bot upload limit can't be sent, sorry!"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME)
