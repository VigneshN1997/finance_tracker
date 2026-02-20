"""
Pytest configuration and fixtures for the Finance Tracker application.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test database BEFORE importing app - this is critical!
# Create a temp file that persists for the test session
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix='.db', prefix='test_finance_')
os.close(_test_db_fd)
os.environ['DATABASE_URL'] = f'sqlite:///{_test_db_path}'

import pytest
from datetime import date
from app import app, db
from models import User, Account, Transaction, Category, Budget, BudgetItem, BudgetAccountGoal, FixedDeposit


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database after test session."""
    try:
        os.unlink(_test_db_path)
    except OSError:
        pass


@pytest.fixture(scope='function')
def test_app():
    """Create application for testing with isolated database."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        # Drop and recreate all tables for each test
        db.drop_all()
        db.create_all()
        Category.init_default_categories()
        yield app
        db.session.remove()


@pytest.fixture(scope='function')
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture(scope='function')
def test_user(test_app):
    """Create a test user."""
    with test_app.app_context():
        user = User(email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture(scope='function')
def logged_in_client(client, test_user, test_app):
    """Create a logged-in test client."""
    with test_app.app_context():
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
    return client


@pytest.fixture(scope='function')
def test_account(test_app, test_user):
    """Create a test account."""
    with test_app.app_context():
        account = Account(
            user_id=test_user,
            name='Test Checking',
            account_type='checking',
            currency='USD',
            initial_balance=1000.0
        )
        db.session.add(account)
        db.session.commit()
        return account.id


@pytest.fixture(scope='function')
def test_savings_account(test_app, test_user):
    """Create a test savings account."""
    with test_app.app_context():
        account = Account(
            user_id=test_user,
            name='Test Savings',
            account_type='savings',
            currency='USD',
            initial_balance=5000.0
        )
        db.session.add(account)
        db.session.commit()
        return account.id


@pytest.fixture(scope='function')
def test_investment_account(test_app, test_user):
    """Create a test investment account."""
    with test_app.app_context():
        account = Account(
            user_id=test_user,
            name='Test 401k',
            account_type='investment',
            currency='USD',
            initial_balance=10000.0
        )
        db.session.add(account)
        db.session.commit()
        return account.id


@pytest.fixture(scope='function')
def test_transaction(test_app, test_account):
    """Create a test transaction."""
    with test_app.app_context():
        transaction = Transaction(
            account_id=test_account,
            amount=-50.0,
            description='Test expense',
            category='groceries',
            transaction_date=date.today()
        )
        db.session.add(transaction)
        db.session.commit()
        return transaction.id


@pytest.fixture(scope='function')
def test_budget(test_app, test_user):
    """Create a test budget."""
    with test_app.app_context():
        budget = Budget(
            user_id=test_user,
            name='Test Budget',
            expected_income=5000.0,
            expected_savings=500.0,
            expected_investments=1000.0,
            currency='USD',
            is_active=True
        )
        db.session.add(budget)
        db.session.commit()
        return budget.id


@pytest.fixture(scope='function')
def test_inr_account(test_app, test_user):
    """Create a test INR account."""
    with test_app.app_context():
        account = Account(
            user_id=test_user,
            name='India Savings',
            account_type='savings',
            currency='INR',
            initial_balance=500000.0
        )
        db.session.add(account)
        db.session.commit()
        return account.id


@pytest.fixture(scope='function')
def test_fixed_deposit(test_app, test_inr_account):
    """Create a test fixed deposit."""
    from datetime import timedelta
    with test_app.app_context():
        fd = FixedDeposit(
            account_id=test_inr_account,
            principal=100000.0,
            interest_rate=7.5,
            start_date=date.today(),
            maturity_date=date.today() + timedelta(days=365),
            bank_name='SBI'
        )
        db.session.add(fd)
        db.session.commit()
        return fd.id
