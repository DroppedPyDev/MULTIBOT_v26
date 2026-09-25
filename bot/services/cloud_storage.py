from aiogram import Bot

from bot.config import CLOUD_STORAGE_CHANNEL_ID
from bot.database import db


class CloudStorageError(Exception):
    pass


def is_configured() -> bool:
    return CLOUD_STORAGE_CHANNEL_ID is not None


async def save_file(
    bot: Bot, user_id: int, file_id: str, file_type: str, filename: str,
    size_bytes: int | None, folder: str = "General",
) -> int:
    """Copies the file into the private storage channel (so it survives even
    if the user later deletes it from their own chat) and records it."""
    if not is_configured():
        raise CloudStorageError(
            "Cloud storage isn't configured yet — the bot owner needs to set "
            "CLOUD_STORAGE_CHANNEL_ID."
        )

    caption = f"📁 {folder} · from user {user_id}\n{filename}"
    if file_type == "video":
        sent = await bot.send_video(CLOUD_STORAGE_CHANNEL_ID, file_id, caption=caption)
    elif file_type == "audio":
        sent = await bot.send_audio(CLOUD_STORAGE_CHANNEL_ID, file_id, caption=caption)
    else:
        sent = await bot.send_document(CLOUD_STORAGE_CHANNEL_ID, file_id, caption=caption)

    return await db.add_cloud_file(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_id=file_id,
        storage_message_id=sent.message_id,
        size_bytes=size_bytes,
        folder=folder,
    )


async def deliver_file(bot: Bot, chat_id: int, file_record: dict) -> None:
    """Sends a stored file back to the user, preferring a fresh copy from the
    storage channel (robust even if the original file_id context is stale)."""
    if is_configured() and file_record.get("storage_message_id"):
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=CLOUD_STORAGE_CHANNEL_ID,
            message_id=file_record["storage_message_id"],
        )
        return

    # Fallback: resend directly via the original file_id
    file_type = file_record["file_type"]
    file_id = file_record["file_id"]
    if file_type == "video":
        await bot.send_video(chat_id, file_id)
    elif file_type == "audio":
        await bot.send_audio(chat_id, file_id)
    else:
        await bot.send_document(chat_id, file_id)


async def delete_file(bot: Bot, user_id: int, file_db_id: int) -> None:
    record = await db.get_file(user_id, file_db_id)
    if record and is_configured() and record.get("storage_message_id"):
        try:
            await bot.delete_message(CLOUD_STORAGE_CHANNEL_ID, record["storage_message_id"])
        except Exception:
            pass  # channel copy may already be gone; DB cleanup still proceeds
    await db.delete_file(user_id, file_db_id)
