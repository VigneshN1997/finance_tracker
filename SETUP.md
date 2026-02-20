# Finance Tracker - Setup Guide

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### 2. Installation Steps

```bash
# Clone or download the project
cd finance_tracker

# Install dependencies
pip3 install -r requirements.txt

# Initialize the database
python3 init_db.py

# Run the application
python3 app.py
```

The app will be available at: **http://127.0.0.1:5000**

---

## Database Configuration

### Where to Configure Database

The database configuration is in **`config.py`**:

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///finance_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

### Database Options

#### Option 1: SQLite (Default - Recommended for Local Use)

**No configuration needed!** The app uses SQLite by default.

- Database file: `finance_tracker.db` (created automatically)
- Perfect for local development and personal use
- No separate database server required

#### Option 2: PostgreSQL (For Production)

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/finance_tracker"
python3 app.py
```

Or modify `config.py` directly:

```python
SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost:5432/finance_tracker'
```

#### Option 3: MySQL

```python
SQLALCHEMY_DATABASE_URI = 'mysql://username:password@localhost:3306/finance_tracker'
```

---

## Database Initialization Scripts

### `init_db.py` - Fresh Database Setup

Creates a NEW blank database with all tables initialized. **Preserves existing databases.**

**The script will prompt you for:**
1. Database name (or press Enter for auto-generated timestamp name)
2. Whether to create an admin user

```bash
# Run the script
python3 init_db.py

# Or with --admin flag to skip the admin user prompt
python3 init_db.py --admin
```

**Example interaction:**
```
Enter database name (press Enter for default):
Default: finance_tracker_20260125_143000.db
Database name: my_finance

Create admin user? (yes/no): yes

Summary:
  Database name: my_finance.db
  Create admin: Yes

Continue? (yes/no): yes
```

**After running**, the script will tell you:
- The database filename created
- The exact line to update in `config.py`

### `create_demo_data.py` - Demo Account

Creates a demo account with sample data for testing/demonstration.

```bash
python3 create_demo_data.py
```

**Demo Login:**
- Email: `demo@example.com`
- Password: `demo123`

---

## First Time Setup

### Method 1: Start Fresh

```bash
# 1. Initialize blank database
python3 init_db.py

# 2. Run the application
python3 app.py

# 3. Open browser to http://127.0.0.1:5000
# 4. Click "Sign Up" to create your account
```

### Method 2: Use Demo Data

```bash
# 1. Initialize database with demo data
python3 create_demo_data.py

# 2. Run the application
python3 app.py

# 3. Log in with demo@example.com / demo123
```

---

## Environment Variables

Create a `.env` file (optional):

```bash
# Secret key for session security
SECRET_KEY=your-very-secret-key-here

# Database URL (optional, defaults to SQLite)
DATABASE_URL=sqlite:///finance_tracker.db

# Flask environment
FLASK_ENV=development
FLASK_DEBUG=1
```

---

## Project Structure

```
finance_tracker/
├── app.py                  # Main application
├── config.py              # Configuration (DATABASE HERE!)
├── models.py              # Database models
├── forms.py               # Form definitions
├── currency.py            # Currency utilities
├── init_db.py            # Database initialization script
├── create_demo_data.py   # Demo data creation script
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
├── static/              # CSS, JS, images
└── finance_tracker.db   # SQLite database (auto-created)
```

---

## Troubleshooting

### Database Issues

**Problem**: "Table doesn't exist" error

**Solution**:
```bash
python3 init_db.py
```

**Problem**: "Database is locked"

**Solution**: Stop all running instances of the app, then restart.

### Port Already in Use

**Problem**: Port 5000 is already in use

**Solution**: Change the port in `app.py` (last line):
```python
app.run(debug=True, port=5001)  # Use different port
```

### Missing Dependencies

**Problem**: Import errors

**Solution**:
```bash
pip3 install -r requirements.txt
```

---

## Sharing the Application

### For Others to Set Up Locally

1. **Share these files**:
   - All Python files (`.py`)
   - `templates/` folder
   - `static/` folder
   - `requirements.txt`
   - This `SETUP.md` file

2. **Do NOT share**:
   - `finance_tracker.db` (database file - contains personal data)
   - `__pycache__/` folder
   - `.env` file (if you created one)

3. **Instructions for recipient**:
   ```bash
   # Install dependencies
   pip3 install -r requirements.txt
   
   # Initialize database
   python3 init_db.py
   
   # Run application
   python3 app.py
   ```

### For Production Deployment

1. Use PostgreSQL instead of SQLite
2. Set strong `SECRET_KEY` environment variable
3. Set `FLASK_ENV=production`
4. Use a production WSGI server (gunicorn, uwsgi)
5. Set up HTTPS/SSL
6. Configure backups for the database

---

## Features

- ✅ Multi-currency support (USD, INR)
- ✅ Account management (Checking, Savings, Credit Cards, Loans, Investments)
- ✅ Transaction tracking with categories
- ✅ Fixed Deposits (FD) tracking for INR accounts
- ✅ Budget planning and tracking
- ✅ Net worth visualization with pie charts
- ✅ Monthly reports and analytics
- ✅ Currency conversion
- ✅ Responsive design

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the code comments in `app.py` and `models.py`
3. Ensure all dependencies are installed correctly

---

## Security Notes

- Change default passwords immediately
- Use strong `SECRET_KEY` in production
- Never commit `.env` or database files to version control
- Add `.gitignore` with:
  ```
  *.db
  __pycache__/
  .env
  *.pyc
  ```
