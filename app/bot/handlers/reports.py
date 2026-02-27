from aiogram import Router
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from app.core.charts import bar_chart_by_month, pie_chart_by_category
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from io import BytesIO
from app.services.expense_service import ExpenseService
from app.bot.keyboards import main_menu_kb

router = Router(name="reports")


def _chart_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="This Month", callback_data="chart:month")],
            [InlineKeyboardButton(text="This Year", callback_data="chart:year")],
            [InlineKeyboardButton(text="Year Trend", callback_data="chart:yeartrend")],
        ]
    )


def _compare_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Month vs Last Month", callback_data="compare:month")],
            [InlineKeyboardButton(text="Year vs Last Year", callback_data="compare:year")],
        ]
    )


def _export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="CSV (This Month)", callback_data="export:csv:month"),
                InlineKeyboardButton(text="XLSX (This Month)", callback_data="export:xlsx:month"),
            ],
            [
                InlineKeyboardButton(text="CSV (This Year)", callback_data="export:csv:year"),
                InlineKeyboardButton(text="XLSX (This Year)", callback_data="export:xlsx:year"),
            ],
        ]
    )


def _report_period_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="This Month", callback_data="report:month:current"),
                InlineKeyboardButton(text="Last Month", callback_data="report:month:last"),
            ],
            [
                InlineKeyboardButton(text="This Year", callback_data="report:year:current"),
                InlineKeyboardButton(text="Last Year", callback_data="report:year:last"),
            ],
        ]
    )


def _search_chip_kb() -> InlineKeyboardMarkup:
    chips = [
        "food", "transport", "shopping", "bills",
        "health", "entertainment", "coffee", "uber", "rent",
    ]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for chip in chips:
        row.append(InlineKeyboardButton(text=chip.title(), callback_data=f"search:kw:{chip}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _month_details_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="This Month • Item", callback_data="details:month:item:current"),
                InlineKeyboardButton(text="This Month • Category", callback_data="details:month:category:current"),
            ],
            [
                InlineKeyboardButton(text="Last Month • Item", callback_data="details:month:item:last"),
                InlineKeyboardButton(text="Last Month • Category", callback_data="details:month:category:last"),
            ],
        ]
    )


def _year_details_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="This Year • Item", callback_data="details:year:item:current"),
                InlineKeyboardButton(text="This Year • Category", callback_data="details:year:category:current"),
            ],
            [
                InlineKeyboardButton(text="Last Year • Item", callback_data="details:year:item:last"),
                InlineKeyboardButton(text="Last Year • Category", callback_data="details:year:category:last"),
            ],
        ]
    )


async def _send_month_report(target: Message, db: AsyncSession, user_id: int, year: int, month: int):
    svc = ExpenseService(db)
    summary = await svc.monthly_summary(user_id=user_id, year=year, month=month)
    if summary["total_cents"] == 0:
        await target.answer(f"📊 No expenses found for {year}-{month:02d}.")
        return

    total_dollars = summary["total_cents"] / 100
    lines = [f"📅 *{year}-{month:02d}*", f"💰 Total: ${total_dollars:.2f}"]
    for cat, cents in summary["breakdown"].items():
        dollars = (cents or 0) / 100
        lines.append(f" - {cat}: ${dollars:.2f}")
    await target.answer("\n".join(lines), parse_mode="Markdown")


async def _send_year_report(target: Message, db: AsyncSession, user_id: int, year: int):
    svc = ExpenseService(db)
    summary = await svc.yearly_summary(user_id=user_id, year=year)
    if summary["total_cents"] == 0:
        await target.answer(f"📊 No expenses found for {year}.")
        return

    total_dollars = summary["total_cents"] / 100
    lines = [f"📅 *{year}*", f"💰 Total: ${total_dollars:.2f}"]
    for cat, cents in summary["breakdown"].items():
        dollars = (cents or 0) / 100
        lines.append(f" - {cat}: ${dollars:.2f}")
    if summary["per_month"]:
        lines.append("\n📆 *By Month*")
        for m in range(1, 13):
            if m in summary["per_month"]:
                dollars = summary["per_month"][m] / 100
                lines.append(f" - {year}-{m:02d}: ${dollars:.2f}")
    await target.answer("\n".join(lines), parse_mode="Markdown")


async def _send_search_results(target: Message, db: AsyncSession, user_id: int, keyword: str):
    svc = ExpenseService(db)
    results = await svc.search_expenses(user_id, keyword)
    if not results:
        await target.answer(f"No expenses found for: {keyword}")
        return

    lines = [f"🔍 Results for *{keyword}* (latest {len(results)})"]
    for exp in results:
        dollars = exp.amount_cents / 100
        cat = f" · 🏷 {exp.category}" if exp.category else ""
        tags = f" · #{exp.tags.replace(',', ' #')}" if exp.tags else ""
        note = f"\n    📝 {exp.notes}" if exp.notes else ""
        lines.append(f"- {exp.item_name}: ${dollars:.2f}{cat}{tags} ({exp.local_date}){note}")
    await target.answer("\n".join(lines), parse_mode="Markdown")


async def _send_month_details(target: Message, db: AsyncSession, user_id: int, year: int, month: int, group_by: str):
    svc = ExpenseService(db)
    rows = await svc.monthly_details(user_id, year, month, group_by)
    if not rows:
        await target.answer(f"No expenses found for {year}-{month:02d}.")
        return

    lines = [f"📅 *{year}-{month:02d}* — grouped by {group_by}"]
    for key, cents in rows:
        dollars = (cents or 0) / 100
        lines.append(f" - {key or 'Uncategorized'}: ${dollars:.2f}")
    await target.answer("\n".join(lines), parse_mode="Markdown")


async def _send_year_details(target: Message, db: AsyncSession, user_id: int, year: int, group_by: str):
    svc = ExpenseService(db)
    rows = await svc.yearly_details(user_id, year, group_by)
    if not rows:
        await target.answer(f"No expenses found for {year}.")
        return

    lines = [f"📅 *{year}* — grouped by {group_by}"]
    for key, cents in rows:
        dollars = (cents or 0) / 100
        lines.append(f" - {key or 'Uncategorized'}: ${dollars:.2f}")
    await target.answer("\n".join(lines), parse_mode="Markdown")


async def _send_quick_export(target: Message, db: AsyncSession, user_id: int, file_format: str, period: str):
    now = datetime.now()
    year = now.year
    month = now.month if period == "month" else None

    svc = ExpenseService(db)
    df = await svc.export_expenses(user_id, year=year, month=month)
    if df is None:
        await target.answer("No expenses found for the selected period.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    period_label = f"{year}_{month:02d}" if month else f"{year}"

    if file_format == "xlsx":
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        data = buffer.getvalue()
        filename = f"expenses_{period_label}_{stamp}.xlsx"
    else:
        data = df.to_csv(index=False).encode("utf-8")
        filename = f"expenses_{period_label}_{stamp}.csv"

    document = BufferedInputFile(data, filename=filename)
    await target.answer_document(document, caption=f"📦 Export ready: {filename}")

@router.message(Command("month"))
async def month_report(message: Message, db: AsyncSession):
    """
    Usage:
      /month                → current month
      /month 2025 9         → year + month (YYYY M)
    """
    parts = (message.text or "").split()
    year, month = None, None
    if len(parts) == 1:
        now = datetime.now()
        year, month = now.year, now.month
    elif len(parts) >= 3:
        try:
            year, month = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("Usage: /month [year month]\nExample: /month 2025 9")
            return
    else:
        await message.answer("Usage: /month [year month]\nExample: /month 2025 9")
        return

    await _send_month_report(message, db, message.from_user.id, year, month)
    if len(parts) == 1:
        await message.answer("Quick report periods:", reply_markup=_report_period_kb())


@router.message(Command("year"))
async def year_report(message: Message, db: AsyncSession):
    """
    Usage:
      /year          → current year
      /year 2025     → specific year
    """
    parts = (message.text or "").split()
    if len(parts) == 1:
        now = datetime.now()
        year = now.year
    elif len(parts) == 2:
        try:
            year = int(parts[1])
        except ValueError:
            await message.answer("Usage: /year [YYYY]\nExample: /year 2025")
            return
    else:
        await message.answer("Usage: /year [YYYY]\nExample: /year 2025")
        return

    await _send_year_report(message, db, message.from_user.id, year)
    if len(parts) == 1:
        await message.answer("Quick report periods:", reply_markup=_report_period_kb())


@router.callback_query(F.data.regexp(r"^report:(month|year):(current|last)$"))
async def report_period_quick(callback: CallbackQuery, db: AsyncSession):
    _, mode, when = callback.data.split(":")
    now = datetime.now()

    if mode == "month":
        if when == "current":
            y, m = now.year, now.month
        else:
            y, m = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        await _send_month_report(callback.message, db, callback.from_user.id, y, m)
    else:
        y = now.year if when == "current" else now.year - 1
        await _send_year_report(callback.message, db, callback.from_user.id, y)

    await callback.message.answer("📋 Main menu ready.", reply_markup=main_menu_kb())
    await callback.answer()

@router.message(Command("monthdetails"))
async def month_details(message: Message, db: AsyncSession):
    """
    Usage:
      /monthdetails item          → current month, grouped by item
      /monthdetails category      → current month, grouped by category
      /monthdetails 2025 9 item   → specific year/month
    """
    parts = (message.text or "").split()
    now = datetime.now()
    year, month, group_by = now.year, now.month, "item"

    if len(parts) == 2:
        group_by = parts[1].lower()
    elif len(parts) == 4:
        try:
            year, month = int(parts[1]), int(parts[2])
            group_by = parts[3].lower()
        except ValueError:
            await message.answer("Usage: /monthdetails [year month group_by]\nExample: /monthdetails 2025 9 category")
            return

    if group_by not in ["item", "category"]:
        await message.answer("Group by must be 'item' or 'category'")
        return
    await _send_month_details(message, db, message.from_user.id, year, month, group_by)
    if len(parts) == 1:
        await message.answer("Quick month details:", reply_markup=_month_details_kb())


@router.message(Command("yeardetails"))
async def year_details(message: Message, db: AsyncSession):
    """
    Usage:
      /yeardetails item
      /yeardetails category
      /yeardetails 2025 item
    """
    parts = (message.text or "").split()
    now = datetime.now()
    year, group_by = now.year, "item"

    if len(parts) == 2:
        group_by = parts[1].lower()
    elif len(parts) == 3:
        try:
            year = int(parts[1])
            group_by = parts[2].lower()
        except ValueError:
            await message.answer("Usage: /yeardetails [year group_by]\nExample: /yeardetails 2025 category")
            return

    if group_by not in ["item", "category"]:
        await message.answer("Group by must be 'item' or 'category'")
        return
    await _send_year_details(message, db, message.from_user.id, year, group_by)
    if len(parts) == 1:
        await message.answer("Quick year details:", reply_markup=_year_details_kb())


@router.callback_query(F.data.regexp(r"^details:(month|year):(item|category):(current|last)$"))
async def details_quick(callback: CallbackQuery, db: AsyncSession):
    _, period, group_by, when = callback.data.split(":")
    now = datetime.now()

    if period == "month":
        if when == "current":
            y, m = now.year, now.month
        else:
            y, m = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        await _send_month_details(callback.message, db, callback.from_user.id, y, m, group_by)
    else:
        y = now.year if when == "current" else now.year - 1
        await _send_year_details(callback.message, db, callback.from_user.id, y, group_by)

    await callback.message.answer("📋 Main menu ready.", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("search"))
async def search_expenses_cmd(message: Message, db: AsyncSession):
    """
    Usage:
      /search coffee
      /search uber
    """
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Pick a keyword or type: /search <keyword>", reply_markup=_search_chip_kb())
        return

    keyword = parts[1].strip()
    await _send_search_results(message, db, message.from_user.id, keyword)


@router.callback_query(F.data.regexp(r"^search:kw:[a-z0-9_\-]+$"))
async def search_quick(callback: CallbackQuery, db: AsyncSession):
    keyword = callback.data.split(":", 2)[2]
    await _send_search_results(callback.message, db, callback.from_user.id, keyword)
    await callback.message.answer("📋 Main menu ready.", reply_markup=main_menu_kb())
    await callback.answer()

@router.message(Command("receipt"))
async def get_receipt(message: Message, db: AsyncSession):
    """
    Usage:
      /receipt <expense_id>
    Sends back the saved receipt if available.
    """
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /receipt <expense_id>")
        return

    expense_id = parts[1]
    svc = ExpenseService(db)
    exp = await svc.get_expense(expense_id)

    if not exp or exp.user_id != message.from_user.id:
        await message.answer("❌ Expense not found or not yours.")
        return

    if not exp.receipt_path:
        await message.answer("No receipt attached to this expense.")
        return

    try:
        with open(exp.receipt_path, "rb") as f:
            await message.answer_photo(f, caption=f"Receipt for {exp.item_name} (${exp.amount_cents/100:.2f})")
    except Exception:
        await message.answer("⚠️ Could not load the receipt file. Maybe deleted from disk.")

@router.message(Command("compare"))
async def compare_expenses(message: Message, db: AsyncSession):
    """
    Usage:
      /compare month                 → this month vs last month
      /compare year                  → this year vs last year
      /compare 2025 9 2025 8         → explicit months (year1 month1 year2 month2)
      /compare 2025 2024             → explicit years
    """
    parts = (message.text or "").split()
    now = datetime.now()
    svc = ExpenseService(db)

    if len(parts) == 2 and parts[1].lower() == "month":
        y1, m1 = now.year, now.month
        # handle last month wrap
        prev_year, prev_month = (y1 - 1, 12) if m1 == 1 else (y1, m1 - 1)
        cur = await svc.totals_for_period(message.from_user.id, y1, m1)
        prev = await svc.totals_for_period(message.from_user.id, prev_year, prev_month)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1}-{m1:02d} vs {prev_year}-{prev_month:02d}"

    elif len(parts) == 2 and parts[1].lower() == "year":
        y1, y0 = now.year, now.year - 1
        cur = await svc.totals_for_period(message.from_user.id, y1)
        prev = await svc.totals_for_period(message.from_user.id, y0)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1} vs {y0}"

    elif len(parts) == 5:
        try:
            y1, m1, y0, m0 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        except ValueError:
            await message.answer("Usage: /compare <y1 m1 y0 m0>")
            return
        cur = await svc.totals_for_period(message.from_user.id, y1, m1)
        prev = await svc.totals_for_period(message.from_user.id, y0, m0)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1}-{m1:02d} vs {y0}-{m0:02d}"

    elif len(parts) == 3:
        try:
            y1, y0 = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("Usage: /compare <year1 year0>")
            return
        cur = await svc.totals_for_period(message.from_user.id, y1)
        prev = await svc.totals_for_period(message.from_user.id, y0)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1} vs {y0}"

    else:
        await message.answer("Pick compare mode:", reply_markup=_compare_kb())
        return

    # format result
    lines = [f"📊 *Comparison: {title}*"]
    total = cmp["total"]
    arrow = "📈" if total["diff"] > 0 else ("📉" if total["diff"] < 0 else "➡️")
    pct = f"({total['pct']:.1f}%)" if total["pct"] is not None else ""
    lines.append(f"💰 Total: {arrow} {total['current']/100:.2f} vs {total['previous']/100:.2f} {pct}")

    lines.append("\n🏷 *By Category*")
    for cat, vals in cmp["categories"].items():
        arrow = "📈" if vals["diff"] > 0 else ("📉" if vals["diff"] < 0 else "➡️")
        pct = f"({vals['pct']:.1f}%)" if vals["pct"] is not None else ""
        lines.append(f"- {cat}: {arrow} {vals['current']/100:.2f} vs {vals['previous']/100:.2f} {pct}")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.callback_query(F.data.in_({"compare:month", "compare:year"}))
async def compare_quick(callback: CallbackQuery, db: AsyncSession):
    mode = callback.data.split(":", 1)[1]
    svc = ExpenseService(db)
    now = datetime.now()

    if mode == "month":
        y1, m1 = now.year, now.month
        prev_year, prev_month = (y1 - 1, 12) if m1 == 1 else (y1, m1 - 1)
        cur = await svc.totals_for_period(callback.from_user.id, y1, m1)
        prev = await svc.totals_for_period(callback.from_user.id, prev_year, prev_month)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1}-{m1:02d} vs {prev_year}-{prev_month:02d}"
    else:
        y1, y0 = now.year, now.year - 1
        cur = await svc.totals_for_period(callback.from_user.id, y1)
        prev = await svc.totals_for_period(callback.from_user.id, y0)
        cmp = svc.compare_periods(cur, prev)
        title = f"{y1} vs {y0}"

    lines = [f"📊 *Comparison: {title}*"]
    total = cmp["total"]
    arrow = "📈" if total["diff"] > 0 else ("📉" if total["diff"] < 0 else "➡️")
    pct = f"({total['pct']:.1f}%)" if total["pct"] is not None else ""
    lines.append(f"💰 Total: {arrow} {total['current']/100:.2f} vs {total['previous']/100:.2f} {pct}")
    lines.append("\n🏷 *By Category*")
    for cat, vals in cmp["categories"].items():
        arrow = "📈" if vals["diff"] > 0 else ("📉" if vals["diff"] < 0 else "➡️")
        pct = f"({vals['pct']:.1f}%)" if vals["pct"] is not None else ""
        lines.append(f"- {cat}: {arrow} {vals['current']/100:.2f} vs {vals['previous']/100:.2f} {pct}")

    await callback.message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu_kb())
    await callback.answer()

@router.message(Command("chart"))
async def chart_expenses(message: Message, db: AsyncSession):
    """
    Usage:
      /chart month            → pie chart by category (this month)
      /chart year             → pie chart by category (this year)
      /chart yeartrend        → bar chart by month (this year)
    """
    parts = (message.text or "").split()
    now = datetime.now()
    svc = ExpenseService(db)

    if len(parts) == 2 and parts[1].lower() == "month":
        data = await svc.monthly_summary(message.from_user.id, now.year, now.month)
        if data["total_cents"] == 0:
            await message.answer("No data for this month.")
            return
        buf = pie_chart_by_category(data["breakdown"], f"{now.year}-{now.month:02d} Expenses by Category")
        await message.answer_photo(buf)

    elif len(parts) == 2 and parts[1].lower() == "year":
        data = await svc.yearly_summary(message.from_user.id, now.year)
        if data["total_cents"] == 0:
            await message.answer("No data for this year.")
            return
        buf = pie_chart_by_category(data["breakdown"], f"{now.year} Expenses by Category")
        await message.answer_photo(buf)

    elif len(parts) == 2 and parts[1].lower() == "yeartrend":
        data = await svc.yearly_summary(message.from_user.id, now.year)
        if not data["per_month"]:
            await message.answer("No data for this year.")
            return
        buf = bar_chart_by_month(data["per_month"], f"{now.year} Monthly Spending Trend")
        await message.answer_photo(buf)

    else:
        await message.answer("Pick chart type:", reply_markup=_chart_kb())


@router.callback_query(F.data.in_({"chart:month", "chart:year", "chart:yeartrend"}))
async def chart_quick(callback: CallbackQuery, db: AsyncSession):
    mode = callback.data.split(":", 1)[1]
    now = datetime.now()
    svc = ExpenseService(db)

    if mode == "month":
        data = await svc.monthly_summary(callback.from_user.id, now.year, now.month)
        if data["total_cents"] == 0:
            await callback.message.answer("No data for this month.")
            await callback.answer()
            return
        buf = pie_chart_by_category(data["breakdown"], f"{now.year}-{now.month:02d} Expenses by Category")
        await callback.message.answer_photo(buf, reply_markup=main_menu_kb())
    elif mode == "year":
        data = await svc.yearly_summary(callback.from_user.id, now.year)
        if data["total_cents"] == 0:
            await callback.message.answer("No data for this year.")
            await callback.answer()
            return
        buf = pie_chart_by_category(data["breakdown"], f"{now.year} Expenses by Category")
        await callback.message.answer_photo(buf, reply_markup=main_menu_kb())
    else:
        data = await svc.yearly_summary(callback.from_user.id, now.year)
        if not data["per_month"]:
            await callback.message.answer("No data for this year.")
            await callback.answer()
            return
        buf = bar_chart_by_month(data["per_month"], f"{now.year} Monthly Spending Trend")
        await callback.message.answer_photo(buf, reply_markup=main_menu_kb())

    await callback.answer()


@router.message(Command("export"))
async def export_expenses_cmd(message: Message, db: AsyncSession):
    """
    Usage:
      /export
      /export csv
      /export xlsx 2026
      /export csv 2026 2
    """
    parts = (message.text or "").split()
    if len(parts) == 1:
        await message.answer("Pick export format:", reply_markup=_export_kb())
        return

    file_format = "csv"
    year = None
    month = None

    if len(parts) >= 2:
        maybe_format = parts[1].lower()
        if maybe_format in {"csv", "xlsx"}:
            file_format = maybe_format
            args = parts[2:]
        else:
            args = parts[1:]
    else:
        args = []

    if len(args) >= 1:
        try:
            year = int(args[0])
        except ValueError:
            await message.answer("Usage: /export [csv|xlsx] [year] [month]")
            return

    if len(args) >= 2:
        try:
            month = int(args[1])
            if month < 1 or month > 12:
                raise ValueError
        except ValueError:
            await message.answer("Month must be between 1 and 12.")
            return

    if len(args) > 2:
        await message.answer("Usage: /export [csv|xlsx] [year] [month]")
        return

    svc = ExpenseService(db)
    df = await svc.export_expenses(message.from_user.id, year=year, month=month)
    if df is None:
        await message.answer("No expenses found for the selected period.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    period_label = "all" if not year else (f"{year}" if not month else f"{year}_{month:02d}")

    if file_format == "xlsx":
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        data = buffer.getvalue()
        filename = f"expenses_{period_label}_{stamp}.xlsx"
    else:
        data = df.to_csv(index=False).encode("utf-8")
        filename = f"expenses_{period_label}_{stamp}.csv"

    document = BufferedInputFile(data, filename=filename)
    await message.answer_document(document, caption=f"📦 Export ready: {filename}")


@router.callback_query(F.data.regexp(r"^export:(csv|xlsx):(month|year)$"))
async def export_quick(callback: CallbackQuery, db: AsyncSession):
    _, file_format, period = callback.data.split(":")
    await _send_quick_export(callback.message, db, callback.from_user.id, file_format, period)
    await callback.message.answer("📋 Main menu ready.", reply_markup=main_menu_kb())
    await callback.answer()