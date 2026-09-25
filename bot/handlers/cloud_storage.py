import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database import db
from bot.keyboards import back_button
from bot.services import cloud_storage, pending_files
from bot.states import CloudStates

logger = logging.getLogger(__name__)
router = Router(name="cloud_storage")

CLOUD_INTRO = (
    "☁️ <b>Cloud Storage</b>\n\n"
    "Send me any file (via the Downloader page's \"Save to Cloud\" option) and "
    "I'll keep it organized in folders you can browse, search, move between, "
    "and delete."
)


def _cloud_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 My Files", callback_data="cloud:folders")],
        [InlineKeyboardButton(text="🔍 Search", callback_data="cloud:search")],
        [InlineKeyboardButton(text="➕ New Folder", callback_data="cloud:newfolder")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu:main")],
    ])


def _folders_keyboard(folders: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"📁 {f}", callback_data=f"cloud:folder:{f}")] for f in folders]
    rows.append([InlineKeyboardButton(text="➕ New Folder", callback_data="cloud:newfolder")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="cloud:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _files_keyboard(files: list[dict], back_cb: str) -> InlineKeyboardMarkup:
    rows = []
    for f in files:
        label = f["filename"][:30]
        rows.append([InlineKeyboardButton(text=f"📄 {label}", callback_data=f"cloud:file:{f['id']}")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _file_detail_keyboard(file_id: int, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬇️ Download", callback_data=f"cloud:dl:{file_id}"),
            InlineKeyboardButton(text="📂 Move", callback_data=f"cloud:move:{file_id}"),
        ],
        [InlineKeyboardButton(text="🗑 Delete", callback_data=f"cloud:del:{file_id}")],
        [InlineKeyboardButton(text="🔙 Back", callback_data=back_cb)],
    ])


def _move_keyboard(file_id: int, folders: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"📁 {f}", callback_data=f"cloud:moveto:{file_id}:{f}")] for f in folders]
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"cloud:file:{file_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _size_str(n: int | None) -> str:
    if not n:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


# ---------------------------------------------------------------------------
# Menu navigation
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "menu:cloud")
async def show_cloud_page(callback: CallbackQuery) -> None:
    text = CLOUD_INTRO
    if not cloud_storage.is_configured():
        text += "\n\n⚠️ Not configured yet — the bot owner needs to set CLOUD_STORAGE_CHANNEL_ID."
    await callback.message.edit_text(text, reply_markup=_cloud_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cloud:menu")
async def back_to_cloud_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(CLOUD_INTRO, reply_markup=_cloud_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cloud:folders")
async def show_folders(callback: CallbackQuery) -> None:
    folders = await db.list_folders(callback.from_user.id)
    await callback.message.edit_text("📁 <b>Your folders</b>", reply_markup=_folders_keyboard(folders))
    await callback.answer()


@router.callback_query(F.data.startswith("cloud:folder:"))
async def show_folder_files(callback: CallbackQuery) -> None:
    folder = callback.data.split(":", 2)[2]
    files = await db.list_files(callback.from_user.id, folder)
    if not files:
        await callback.message.edit_text(
            f"📁 <b>{folder}</b> is empty.", reply_markup=_files_keyboard([], "cloud:folders")
        )
    else:
        await callback.message.edit_text(
            f"📁 <b>{folder}</b>", reply_markup=_files_keyboard(files, "cloud:folders")
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cloud:file:"))
async def show_file_detail(callback: CallbackQuery) -> None:
    file_db_id = int(callback.data.split(":", 2)[2])
    record = await db.get_file(callback.from_user.id, file_db_id)
    if not record:
        await callback.answer("That file is no longer available.", show_alert=True)
        return
    text = (
        f"📄 <b>{record['filename']}</b>\n"
        f"Folder: {record['folder']}\n"
        f"Size: {_size_str(record['size_bytes'])}"
    )
    await callback.message.edit_text(
        text, reply_markup=_file_detail_keyboard(file_db_id, f"cloud:folder:{record['folder']}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cloud:dl:"))
async def download_file(callback: CallbackQuery, bot: Bot) -> None:
    file_db_id = int(callback.data.split(":", 2)[2])
    record = await db.get_file(callback.from_user.id, file_db_id)
    if not record:
        await callback.answer("That file is no longer available.", show_alert=True)
        return
    await cloud_storage.deliver_file(bot, callback.message.chat.id, record)
    await callback.answer("Sent!")


@router.callback_query(F.data.startswith("cloud:del:"))
async def delete_file(callback: CallbackQuery, bot: Bot) -> None:
    file_db_id = int(callback.data.split(":", 2)[2])
    await cloud_storage.delete_file(bot, callback.from_user.id, file_db_id)
    await callback.answer("Deleted.")
    folders = await db.list_folders(callback.from_user.id)
    await callback.message.edit_text("📁 <b>Your folders</b>", reply_markup=_folders_keyboard(folders))


@router.callback_query(F.data.startswith("cloud:move:"))
async def move_file_prompt(callback: CallbackQuery) -> None:
    file_db_id = int(callback.data.split(":", 2)[2])
    folders = await db.list_folders(callback.from_user.id)
    await callback.message.edit_text(
        "Move to which folder?", reply_markup=_move_keyboard(file_db_id, folders)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cloud:moveto:"))
async def move_file_apply(callback: CallbackQuery) -> None:
    _, _, file_db_id, folder = callback.data.split(":", 3)
    await db.move_file(callback.from_user.id, int(file_db_id), folder)
    await callback.answer(f"Moved to {folder}.")
    record = await db.get_file(callback.from_user.id, int(file_db_id))
    text = (
        f"📄 <b>{record['filename']}</b>\n"
        f"Folder: {record['folder']}\n"
        f"Size: {_size_str(record['size_bytes'])}"
    )
    await callback.message.edit_text(
        text, reply_markup=_file_detail_keyboard(int(file_db_id), f"cloud:folder:{folder}")
    )


# ---------------------------------------------------------------------------
# New folder (FSM)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cloud:newfolder")
async def new_folder_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CloudStates.waiting_folder_name)
    await callback.message.edit_text(
        "Send the name for the new folder (or /cancel).", reply_markup=back_button("cloud:folders")
    )
    await callback.answer()


@router.message(CloudStates.waiting_folder_name)
async def new_folder_receive(message: Message, state: FSMContext) -> None:
    name = message.text.strip()[:32]
    if name.startswith("/"):
        await state.clear()
        await message.answer("Cancelled.")
        return
    await db.create_folder(message.from_user.id, name)
    await state.clear()
    folders = await db.list_folders(message.from_user.id)
    await message.answer(f"Created folder \"{name}\".", reply_markup=_folders_keyboard(folders))


# ---------------------------------------------------------------------------
# Search (FSM)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "cloud:search")
async def search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CloudStates.waiting_search_query)
    await callback.message.edit_text(
        "Send a filename (or part of one) to search for (or /cancel).",
        reply_markup=back_button("cloud:menu"),
    )
    await callback.answer()


@router.message(CloudStates.waiting_search_query)
async def search_receive(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if query.startswith("/"):
        await state.clear()
        await message.answer("Cancelled.")
        return
    await state.clear()
    results = await db.search_files(message.from_user.id, query)
    if not results:
        await message.answer(f"No files matching \"{query}\".")
        return
    await message.answer(
        f"🔍 Results for \"{query}\":", reply_markup=_files_keyboard(results, "cloud:menu")
    )


# ---------------------------------------------------------------------------
# Saving a file (triggered from the downloader's "Save to Cloud" button)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("cloud:save:"))
async def save_pending_file(callback: CallbackQuery, bot: Bot) -> None:
    ref = callback.data.split(":", 2)[2]
    pending = pending_files.pop(ref)
    if not pending:
        await callback.answer("That file reference expired, please resend it.", show_alert=True)
        return

    if not cloud_storage.is_configured():
        await callback.answer(
            "Cloud storage isn't configured yet (missing CLOUD_STORAGE_CHANNEL_ID).",
            show_alert=True,
        )
        return

    await callback.answer("Saving...")
    file_db_id = await cloud_storage.save_file(
        bot, callback.from_user.id, pending.file_id, pending.file_type,
        pending.filename, pending.size_bytes,
    )
    await callback.message.edit_text(
        f"✅ Saved \"{pending.filename}\" to Cloud Storage (General).",
        reply_markup=_file_detail_keyboard(file_db_id, "cloud:folders"),
    )
