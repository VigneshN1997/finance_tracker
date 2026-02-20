# Finance Tracker

A personal finance management web app for tracking accounts, transactions, budgets, fixed deposits, and net worth — with multi-currency support (USD and INR).

---

## Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Accounts
![Accounts](docs/screenshots/accounts.png)

### Account Detail
![Account Detail](docs/screenshots/account_detail.png)

### Monthly Report
![Monthly Report](docs/screenshots/monthly_report.png)

### Budget
![Budget](docs/screenshots/budget.png)

### Net Worth
![Net Worth](docs/screenshots/net_worth.png)

### Fixed Deposits
![Fixed Deposits](docs/screenshots/fixed_deposits.png)

### Currency Summary
![Currency Summary](docs/screenshots/currency_summary.png)

### Credit Cards
![Credit Cards](docs/screenshots/credit_cards.png)

### Add Transaction
![Add Transaction](docs/screenshots/add_transaction.png)

### Transfer Between Accounts
![Transfer](docs/screenshots/transfer.png)

---

## Features

- **Dashboard** — Quick overview of total balance, account count, and recent transactions
- **Accounts** — Support for Checking, Savings, Credit Card, Loan, and Investment account types
- **Transactions** — Record income and expenses with custom categories; track shared expenses via `my_share`
- **Transfers** — Transfer money between your own accounts with automatic matching debit/credit entries
- **Fixed Deposits** — Track INR fixed deposits with quarterly compounding interest and maturity dates
- **Budgets** — Set category-wise spending budgets and monthly savings/investment goals; compare actual vs. budgeted
- **Reports** — Monthly expense breakdown by category with income/expense summaries
- **Net Worth** — Asset and liability breakdown by account type
- **Multi-Currency** — USD and INR accounts with live exchange rates; toggle display currency globally
- **Credit Cards** — Dedicated credit card summary view

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+, Flask 2.3 |
| ORM | Flask-SQLAlchemy, SQLAlchemy 2.0 |
| Auth | Flask-Login, Werkzeug password hashing |
| Forms | Flask-WTF, WTForms |
| Database | SQLite (default), PostgreSQL, MySQL |
| Frontend | Bootstrap 5.3, Bootstrap Icons, Flatpickr, Tom Select |
| Testing | pytest |
| Exchange Rates | exchangerate-api.com (live fetch) |

---

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd finance_tracker

# Install dependencies
pip3 install -r requirements.txt

# Initialize the database
python3 init_db.py

# Run the app
python3 app.py
```

Open your browser to **http://127.0.0.1:5000** and sign up for an account.

### Try with Demo Data

```bash
python3 create_demo_data.py
python3 app.py
```

Login with:
- **Email:** `demo@example.com`
- **Password:** `demo123`

---

## Project Structure

```
finance_tracker/
├── app.py                   # Main Flask application and all routes
├── models.py                # SQLAlchemy models (User, Account, Transaction, etc.)
├── forms.py                 # WTForms form definitions
├── config.py                # App configuration (database URL, secret key)
├── currency.py              # Currency conversion utilities
├── init_db.py               # Database initialization script
├── create_demo_data.py      # Demo data generator
├── reset_password.py        # Password reset utility
├── requirements.txt         # Python dependencies
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── accounts.html
│   ├── monthly_report.html
│   ├── budget.html
│   ├── net_worth.html
│   ├── fixed_deposits.html
│   └── ...
├── static/
│   └── style.css            # Custom styles
└── tests/                   # pytest test suite
    ├── conftest.py
    ├── test_auth.py
    ├── test_accounts.py
    ├── test_transactions.py
    ├── test_budgets.py
    ├── test_fixed_deposits.py
    ├── test_currency.py
    ├── test_forms.py
    └── test_models.py
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```bash
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=sqlite:///finance_tracker.db
FLASK_ENV=development
FLASK_DEBUG=1
```

### Database Options

| Option | URI Format |
|--------|-----------|
| SQLite (default) | `sqlite:///finance_tracker.db` |
| PostgreSQL | `postgresql://user:password@localhost:5432/finance_tracker` |
| MySQL | `mysql://user:password@localhost:3306/finance_tracker` |

Set `DATABASE_URL` as an environment variable or edit `config.py` directly.

---

## Running Tests

```bash
pytest
```

Run a specific test file:

```bash
pytest tests/test_transactions.py
```

---

## Deployment (PythonAnywhere)

1. **Push changes to GitHub:**
   ```bash
   git add .
   git commit -m "your message"
   git push origin main
   ```

2. **Pull on PythonAnywhere** (Bash console):
   ```bash
   cd ~/finance_tracker
   git pull origin main
   ```

3. **Install any new dependencies:**
   ```bash
   pip install -r requirements.txt --user
   ```

4. **Reload the web app** from the PythonAnywhere **Web** tab.

---

## Security Notes

- Use a strong, randomly generated `SECRET_KEY` in production
- Never commit `.env` or database files to version control
- Recommended `.gitignore` entries:
  ```
  *.db
  __pycache__/
  .env
  *.pyc
  instance/
  ```
