# BudgetBot

BudgetBot is a **Telegram-based personal finance management bot** that helps users track expenses, manage budgets, and generate insightful reports. Designed for simplicity and accessibility, BudgetBot allows users to log expenses, set recurring payments, and monitor their financial health directly from Telegram.

---

## Features

- **Expense Tracking**: Log expenses with categories, tags, and notes.
- **Budget Management**: Set budgets and receive alerts when limits are exceeded.
- **Recurring Expenses**: Automate tracking of subscriptions, rent, and other recurring payments.
- **Reports & Charts**: Generate monthly/yearly summaries and visualize spending habits.
- **Forecasting**: Predict future expenses based on historical data.
- **Receipt Management**: Upload and process receipts for expense logging.

---

## Architecture

### Tech Stack
- **Programming Language**: Python 3.12
- **Frameworks**: Aiogram (Telegram Bot), SQLAlchemy (ORM)
- **Database**: SQLite (development), PostgreSQL (recommended for production)
- **Utilities**: Loguru (logging), Pandas (data processing), Matplotlib (charting)

### Design Patterns
- **Service Layer Pattern**: Encapsulates business logic in service classes.
- **Command Pattern**: Maps Telegram commands to specific handler functions.
- **Dependency Injection**: Injects database sessions into bot handlers.

### Request Flow
1. **User Input**: A user sends a command (e.g., `/add Pizza 12.50 #food`).
2. **Bot Handler**: The handler parses the input and delegates logic to the appropriate service.
3. **Service Layer**: The service processes the request and interacts with the database.
4. **Database Layer**: Executes queries and returns results.
5. **Response**: The bot sends a response back to the user via Telegram.

---

## Folder Structure

```
.
├── app/
│   ├── bot/                # Telegram bot handlers for user interaction
│   ├── core/               # Core utilities (logging, config, storage)
│   ├── db/                 # Database models and session management
│   ├── services/           # Business logic for expenses, budgets, etc.
│   └── utils/              # Helper functions (e.g., parsing, text processing)
├── data/                   # SQLite database files
├── scripts/                # Utility scripts (e.g., database initialization)
├── requirements.txt        # Application dependencies
├── requirements-dev.txt    # Development dependencies
└── README.md               # Project documentation
```

---

## Setup & Installation

### Prerequisites
- Python 3.12+
- SQLite (default) or PostgreSQL (recommended for production)
- Telegram Bot Token (create via BotFather on Telegram)

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/sandeepyeg/budgetbot.git
   cd budgetbot
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   - Create a `.env` file in the root directory.
   - Add the following variables:
     ```env
     TELEGRAM_BOT_TOKEN=your-telegram-bot-token
     DATABASE_URL=sqlite:///data/budgetbot.db
     ```

5. **Initialize the database**:
   ```bash
   python scripts/init_db.py
   ```

6. **Run the bot**:
   ```bash
   python app/bot/main.py
   ```

---

## Configuration

- **Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: Token for the Telegram bot.
  - `DATABASE_URL`: Database connection string (e.g., `sqlite:///data/budgetbot.db` or `postgresql://user:password@localhost/dbname`).
- **Environment-Specific Notes**:
  - Use SQLite for development and PostgreSQL for production.
  - Update `DATABASE_URL` accordingly in the `.env` file.

---

## Usage

### Example Commands
- **Add an Expense**:
  ```
  /add Pizza 12.50 #food
  ```
  Response:
  ```
  Expense added: Pizza - $12.50 (Category: Food)
  ```

- **View Monthly Report**:
  ```
  /month
  ```
  Response:
  ```
  Total Expenses: $450.00
  Top Categories: Food ($200), Rent ($150), Entertainment ($100)
  ```

---

## Testing

1. **Run Unit Tests**:
   - Ensure `pytest` is installed:
     ```bash
     pip install pytest
     ```
   - Run tests:
     ```bash
     pytest
     ```

2. **Static Analysis**:
   - Run `mypy` for type checking:
     ```bash
     mypy app/
     ```
   - Run `ruff` for linting:
     ```bash
     ruff check app/
     ```

---

## Contributing

We welcome contributions! To get started:
1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a clear description of your changes.

---

## License & Credits

- **License**: [MIT License](LICENSE).
- **Credits**: Developed by Sandeep Singh.

---
