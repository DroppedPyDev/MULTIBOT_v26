import asyncio
import logging
import os

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from bot.config import MAX_CONCURRENT_JOBS
from bot.services.downloader import download_media, DownloadError
from bot.services import converter, pending_files
from bot.utils.cleanup import safe_delete

logger = logging.getLogger(__name__)
router = Router(name="download")

# Caps how many downloads/conversions run at once, regardless of how many
# users are hitting the bot simultaneously.
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


@router.message(Command("download"))
async def cmd_download(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: <code>/download &lt;url&gt;</code>")
        return

    url = parts[1].strip()
    status = await message.answer("⏳ Downloading...")

    async with job_semaphore:
        try:
            result = await download_media(url)
        except DownloadError as e:
            await status.edit_text(f"❌ Couldn't download that: {e}")
            return
        except Exception:
            logger.exception("Unexpected download error")
            await status.edit_text("❌ Something went wrong downloading that.")
            return

    try:
        file = FSInputFile(result.file_path)
        if result.is_audio:
            await message.answer_audio(file, title=result.title)
        else:
            await message.answer_video(file, caption=result.title)
        await status.delete()
    finally:
        safe_delete(result.file_path)


def _file_type_and_name(message: Message) -> tuple[str, object]:
    if message.video:
        return "video", message.video
    if message.audio:
        return "audio", message.audio
    return "document", message.document


@router.message(F.video | F.audio | F.document)
async def handle_incoming_media(message: Message) -> None:
    """User sent a file directly — offer conversion and cloud-save options."""
    file_type, file_obj = _file_type_and_name(message)
    if file_obj.file_size and file_obj.file_size > 50 * 1024 * 1024:
        await message.answer("That file is over the 50MB bot limit, I can't fetch it.")
        return

    filename = getattr(file_obj, "file_name", None) or f"{file_type}_{file_obj.file_unique_id}"
    ref = pending_files.register(file_obj.file_id, file_type, filename, file_obj.file_size)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 Extract MP3", callback_data=f"conv:mp3:{ref}"),
            InlineKeyboardButton(text="🎞 To GIF", callback_data=f"conv:gif:{ref}"),
        ],
        [
            InlineKeyboardButton(text="📹 To MP4", callback_data=f"conv:mp4:{ref}"),
        ],
        [
            InlineKeyboardButton(text="☁️ Save to Cloud", callback_data=f"cloud:save:{ref}"),
        ],
    ])
    await message.answer("What would you like to do with this file?", reply_markup=keyboard)


@router.callback_query(F.data.startswith("conv:"))
async def handle_conversion_choice(callback: CallbackQuery) -> None:
    _, target_format, ref = callback.data.split(":", 2)
    await callback.answer()
    pending = pending_files.get(ref)
    if not pending:
        await callback.message.edit_text("That file reference expired, please resend it.")
        return
    file_id = pending.file_id
    await callback.message.edit_text(f"⏳ Converting to {target_format.upper()}...")

    bot = callback.bot
    tg_file = await bot.get_file(file_id)
    local_input = f"temp/{file_id}_in"
    os.makedirs("temp", exist_ok=True)
    await bot.download_file(tg_file.file_path, destination=local_input)

    output_path = None
    async with job_semaphore:
        try:
            if target_format == "mp3":
                output_path = await converter.to_mp3(local_input)
            elif target_format == "gif":
                output_path = await converter.to_gif(local_input)
            elif target_format == "mp4":
                output_path = await converter.to_mp4(local_input)
        except converter.ConversionError as e:
            await callback.message.edit_text(f"❌ Conversion failed: {e}")
            safe_delete(local_input)
            return
        except Exception:
            logger.exception("Unexpected conversion error")
            await callback.message.edit_text("❌ Something went wrong converting that.")
            safe_delete(local_input)
            return

    try:
        file = FSInputFile(output_path)
        if target_format == "mp3":
            await callback.message.answer_audio(file)
        elif target_format == "gif":
            await callback.message.answer_animation(file)
        else:
            await callback.message.answer_video(file)
        await callback.message.delete()
    finally:
        safe_delete(local_input, output_path)
