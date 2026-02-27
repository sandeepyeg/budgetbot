from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from app.bot.keyboards import main_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "👋 Welcome to BudgetBot\n\n"
        "Quick examples:\n"
        "• /add Coffee 4.50 #food\n"
        "• /split Dinner Food:20,Transport:10 pm:card\n"
        "• /month\n"
        "• /budget\n"
        "• /rules\n\n"
        "Use the menu keyboard below for mostly no-typing usage.",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Main commands:\n"
        "• /add — guided expense entry\n"
        "• /split — split one purchase across categories\n"
        "• /month, /year — reports\n"
        "• /monthdetails, /yeardetails — detailed breakdowns\n"
        "• /budget — guided budget flow\n"
        "• /rules — guided rules flow\n"
        "• /recurring — recurring management\n"
        "• /undo — remove last expense\n"
        "• /edit_last — edit last expense\n"
        "• /export [csv|xlsx] [year] [month]\n",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("menu"))
async def menu_cmd(message: Message):
    await message.answer("📋 Main menu is ready. Tap any command below.", reply_markup=main_menu_kb())
