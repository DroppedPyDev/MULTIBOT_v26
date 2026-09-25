from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Downloader", callback_data="menu:download"),
            InlineKeyboardButton(text="🛡 Group MODERATION", callback_data="menu:moderation"),
        ],
        [
            InlineKeyboardButton(text="🤖 AI Assistant", callback_data="menu:ai"),
            InlineKeyboardButton(text="☁️ Personal Cloud Storage", callback_data="menu:cloud"),
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Developer INFO", callback_data="menu:dev"),
        ],
    ])


def back_button(callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data=callback_data)]
    ])


def with_back_row(rows: list[list[InlineKeyboardButton]], callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows + [
        [InlineKeyboardButton(text="🔙 Back", callback_data=callback_data)]
    ])
