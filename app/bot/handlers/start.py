from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router(name="start")


def _quick_actions_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/add"), KeyboardButton(text="/month")],
            [KeyboardButton(text="/budget"), KeyboardButton(text="/rules")],
            [KeyboardButton(text="/undo"), KeyboardButton(text="/edit_last")],
        ],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "👋 Welcome to BudgetBot\n\n"
        "Quick examples:\n"
        "• /add Coffee 4.50 #food\n"
        "• /month\n"
        "• /budget\n"
        "• /rules\n\n"
        "Tap a quick action below to run.",
        reply_markup=_quick_actions_kb(),
    )


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Main commands:\n"
        "• /add — guided expense entry\n"
        "• /month, /year — reports\n"
        "• /budget — guided budget flow\n"
        "• /rules — guided rules flow\n"
        "• /undo — remove last expense\n"
        "• /edit_last — edit last expense\n"
        "• /export [csv|xlsx] [year] [month]\n",
        reply_markup=_quick_actions_kb(),
    )
