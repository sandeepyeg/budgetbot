from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/add"), KeyboardButton(text="/split")],
            [KeyboardButton(text="/month"), KeyboardButton(text="/year")],
            [KeyboardButton(text="/monthdetails"), KeyboardButton(text="/yeardetails")],
            [KeyboardButton(text="/chart"), KeyboardButton(text="/compare")],
            [KeyboardButton(text="/budget"), KeyboardButton(text="/rules")],
            [KeyboardButton(text="/recurring"), KeyboardButton(text="/export")],
            [KeyboardButton(text="/undo"), KeyboardButton(text="/edit_last")],
            [KeyboardButton(text="/search"), KeyboardButton(text="/menu")],
        ],
        resize_keyboard=True,
    )
