import aiosqlite
from typing import Optional

DB_PATH = "temp/moderation.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS warnings (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS banned_words (
    chat_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    PRIMARY KEY (chat_id, word)
);

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id INTEGER PRIMARY KEY,
    welcome_message TEXT,
    captcha_enabled INTEGER NOT NULL DEFAULT 1,
    max_warnings INTEGER NOT NULL DEFAULT 3,
    flood_limit INTEGER NOT NULL DEFAULT 5,
    flood_window_seconds INTEGER NOT NULL DEFAULT 10
);
"""


async def init_db() -> None:
    import os
    os.makedirs("temp", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


# ---------- warnings ----------

async def add_warning(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (chat_id, user_id, count) VALUES (?, ?, 1) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET count = count + 1",
            (chat_id, user_id),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_warnings(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def clear_warnings(chat_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        await db.commit()


async def remove_one_warning(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE warnings SET count = MAX(count - 1, 0) WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ---------- banned words ----------

async def add_banned_word(chat_id: int, word: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO banned_words (chat_id, word) VALUES (?, ?)",
            (chat_id, word.lower()),
        )
        await db.commit()


async def remove_banned_word(chat_id: int, word: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM banned_words WHERE chat_id = ? AND word = ?",
            (chat_id, word.lower()),
        )
        await db.commit()


async def list_banned_words(chat_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT word FROM banned_words WHERE chat_id = ?", (chat_id,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ---------- group settings ----------

async def get_settings(chat_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        # create defaults
        await db.execute(
            "INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,)
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
        )
        row = await cursor.fetchone()
        return dict(row)


async def update_setting(chat_id: int, key: str, value) -> None:
    allowed = {"welcome_message", "captcha_enabled", "max_warnings", "flood_limit", "flood_window_seconds"}
    if key not in allowed:
        raise ValueError(f"Unknown setting: {key}")
    await get_settings(chat_id)  # ensure row exists
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id)
        )
        await db.commit()
