# BudgetBot

BudgetBot is a Telegram personal-finance bot for fast, low-typing expense tracking with guided flows, smart categorization, budgets, recurring automation, reports, charts, and exports.

## Quick Start (60 seconds)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python scripts/init_db.py
python scripts/seed_categories.py
python -m app.bot.main
```

Then open `.env`, set `TELEGRAM_BOT_TOKEN`, and restart the bot.

## What It Does

- Guided expense entry with menu-first UX (`/add` flow).
- Split transactions across categories (`/split`).
- Short reference IDs for delete/edit actions.
- Undo and edit-last safety actions (`/undo`, `/edit_last`).
- Budget tracking with progress bars and monthly rollover mode.
- Rule-based auto-categorization (`/rules_*`).
- Recurring expense engine with pause/resume/cancel.
- Weekly digest notifications with budget alerts.
- Month/year reports, detailed breakdowns, compare, search chips, charts.
- CSV/XLSX exports delivered as Telegram documents.
- Receipt-photo ingestion (photo + caption).

## Tech Stack

- Python 3.12+
- Aiogram 3
- SQLAlchemy 2 (async)
- SQLite (`aiosqlite`) by default
- Pandas + OpenPyXL for exports
- Matplotlib + NumPy for charts
- Loguru for logging

## Project Structure

```text
.
├── app/
│   ├── bot/          # Handlers, keyboards, bot bootstrap
│   ├── core/         # Config, logging, storage helpers
│   ├── db/           # Models, base, session
│   ├── services/     # Business logic layer
│   └── utils/        # Parsing, dates, text helpers
├── scripts/          # Init and seed scripts
├── tests/            # Unit/integration-style async tests
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

## Setup

### 1) Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3) Configure `.env`

Copy `.env.example` to `.env` and set values:

```env
TELEGRAM_BOT_TOKEN=put-your-token-here
DATABASE_URL=sqlite+aiosqlite:///./data/expensebot.db
APP_ENV=dev
DEFAULT_CURRENCY=CAD
LOCAL_TIMEZONE=America/Edmonton
```

### 4) Initialize DB and seed categories

```bash
python scripts/init_db.py
python scripts/seed_categories.py
```

### 5) Run bot

```bash
python -m app.bot.main
```

Optional helper:

```bash
bash scripts/run.sh
```

## Main Commands

### Core expense flows

- `/start` - onboarding + quick examples + menu keyboard.
- `/menu` - re-open main menu keyboard.
- `/add` - guided add flow, or inline add syntax.
- `/split <item> <Category:Amount,...> [pm:method]` - split one purchase.
- `/undo` - remove last expense.
- `/edit_last` - edit field(s) of most recent expense.
- `/settags <expense_id_or_ref> <tag1,tag2,...>`
- `/setnote <expense_id_or_ref> <note>`

### Reports and analysis

- `/month [year month]`
- `/year [year]`
- `/monthdetails [year month group_by]` (`item` or `category`)
- `/yeardetails [year group_by]` (`item` or `category`)
- `/search <keyword>` (also quick chips)
- `/compare` (interactive) or explicit month/year compare
- `/chart` (interactive) or `month|year|yeartrend`
- `/export [csv|xlsx] [year] [month]`
- `/forecast [category]`
- `/ask <natural language query>`

### Categories, budgets, rules, recurring

- `/categories`
- `/setcategory <expense_id> <category>`
- `/budget` (guided)
- `/budget_add <scope> <limit> <period>`
- `/budget_list`
- `/budget_delete <ref>`
- `/rules` (guided)
- `/rules_add <keyword> <category>`
- `/rules_list`
- `/rules_delete <ref>`
- `/recurring` (help)
- `/recurring_list`
- `/recurring_pause <ref>`
- `/recurring_resume <ref>`
- `/recurring_cancel <ref>`

### Receipt workflow

Send a photo with caption like:

```text
Coffee 4.75 #food #morning
```

The bot stores an optimized image and attaches it to the created expense.

## Background Automation

- A recurring worker runs continuously and generates due recurring expenses.
- On Mondays, weekly digest messages are sent to users with spending totals and category breakdown.
- Budget alerts are included in weekly digests when thresholds are reached/exceeded.

## Testing and Quality

Run tests:

```bash
PYTHONPATH=. pytest tests -q
```

Run lint and type checks:

```bash
ruff check app tests
mypy app
```

Notes:

- `pytest.ini` contains focused warning filters for known third-party `matplotlib`/`pyparsing` deprecations so test output remains clean.
- Current suite includes parser, services, recurring generation, and handler callback regressions.

## Configuration Notes

- Default DB is SQLite via `DATABASE_URL`.
- For production, use a managed PostgreSQL URL and update `DATABASE_URL`.
- Local timezone behavior (digests/date handling) follows `LOCAL_TIMEZONE`.

## Development Tips

- Keep service-layer logic in `app/services` and handlers thin.
- Prefer short refs in user-facing commands for safety and usability.
- Validate behavior with tests when adding new commands/callbacks.
