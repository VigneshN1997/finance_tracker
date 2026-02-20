"""
Unit tests for the Finance Tracker models.
"""
import pytest
from datetime import date, datetime
from models import User, Account, Transaction, Category, Budget, BudgetItem, BudgetAccountGoal, db


class TestUserModel:
    """Tests for the User model."""

    def test_user_creation(self, test_app):
        """Test creating a new user."""
        with test_app.app_context():
            user = User(email='newuser@example.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'newuser@example.com'
            assert user.display_currency == 'USD'
            assert user.created_at is not None

    def test_user_password_hashing(self, test_app):
        """Test password hashing and verification."""
        with test_app.app_context():
            user = User(email='passtest@example.com')
            user.set_password('mysecretpassword')
            db.session.add(user)
            db.session.commit()

            assert user.password_hash != 'mysecretpassword'
            assert user.check_password('mysecretpassword') is True
            assert user.check_password('wrongpassword') is False

    def test_user_unique_email(self, test_app, test_user):
        """Test that duplicate emails are rejected."""
        with test_app.app_context():
            from sqlalchemy.exc import IntegrityError
            user2 = User(email='test@example.com')
            user2.set_password('anotherpass')
            db.session.add(user2)
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_user_repr(self, test_app):
        """Test User string representation."""
        with test_app.app_context():
            user = User(email='repr@example.com')
            assert repr(user) == '<User repr@example.com>'


class TestAccountModel:
    """Tests for the Account model."""

    def test_account_creation(self, test_app, test_user):
        """Test creating a new account."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='My Checking',
                account_type='checking',
                currency='USD',
                initial_balance=500.0
            )
            db.session.add(account)
            db.session.commit()

            assert account.id is not None
            assert account.name == 'My Checking'
            assert account.account_type == 'checking'
            assert account.currency == 'USD'
            assert account.initial_balance == 500.0

    def test_account_current_balance_no_transactions(self, test_app, test_user):
        """Test current balance with no transactions."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='Balance Test',
                account_type='savings',
                currency='USD',
                initial_balance=1000.0
            )
            db.session.add(account)
            db.session.commit()

            assert account.current_balance == 1000.0

    def test_account_current_balance_with_transactions(self, test_app, test_user):
        """Test current balance calculation with transactions."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='Trans Test',
                account_type='checking',
                currency='USD',
                initial_balance=1000.0
            )
            db.session.add(account)
            db.session.commit()

            # Add income
            t1 = Transaction(
                account_id=account.id,
                amount=500.0,
                description='Salary',
                category='income',
                transaction_date=date.today()
            )
            # Add expense
            t2 = Transaction(
                account_id=account.id,
                amount=-200.0,
                description='Groceries',
                category='groceries',
                transaction_date=date.today()
            )
            db.session.add_all([t1, t2])
            db.session.commit()

            assert account.current_balance == 1300.0  # 1000 + 500 - 200

    def test_account_currency_symbol(self, test_app, test_user):
        """Test currency symbol property."""
        with test_app.app_context():
            usd_account = Account(
                user_id=test_user,
                name='USD Account',
                account_type='checking',
                currency='USD',
                initial_balance=0
            )
            inr_account = Account(
                user_id=test_user,
                name='INR Account',
                account_type='checking',
                currency='INR',
                initial_balance=0
            )
            db.session.add_all([usd_account, inr_account])
            db.session.commit()

            assert usd_account.currency_symbol == '$'
            assert inr_account.currency_symbol == '₹'

    def test_account_country(self, test_app, test_user):
        """Test country property."""
        with test_app.app_context():
            usd_account = Account(
                user_id=test_user,
                name='USA Account',
                account_type='checking',
                currency='USD',
                initial_balance=0
            )
            inr_account = Account(
                user_id=test_user,
                name='India Account',
                account_type='checking',
                currency='INR',
                initial_balance=0
            )
            db.session.add_all([usd_account, inr_account])
            db.session.commit()

            assert usd_account.country == 'USA'
            assert inr_account.country == 'India'

    def test_account_types(self, test_app, test_user):
        """Test all account types can be created."""
        with test_app.app_context():
            for account_type in Account.ACCOUNT_TYPES:
                account = Account(
                    user_id=test_user,
                    name=f'{account_type} Account',
                    account_type=account_type,
                    currency='USD',
                    initial_balance=0
                )
                db.session.add(account)
            db.session.commit()

            accounts = Account.query.filter_by(user_id=test_user).all()
            assert len(accounts) == len(Account.ACCOUNT_TYPES)


class TestTransactionModel:
    """Tests for the Transaction model."""

    def test_transaction_creation(self, test_app, test_account):
        """Test creating a transaction."""
        with test_app.app_context():
            transaction = Transaction(
                account_id=test_account,
                amount=-75.50,
                description='Dinner',
                category='dining',
                transaction_date=date.today()
            )
            db.session.add(transaction)
            db.session.commit()

            assert transaction.id is not None
            assert transaction.amount == -75.50
            assert transaction.description == 'Dinner'
            assert transaction.category == 'dining'

    def test_transaction_personal_amount_without_share(self, test_app, test_account):
        """Test personal_amount when my_share is not set."""
        with test_app.app_context():
            transaction = Transaction(
                account_id=test_account,
                amount=-100.0,
                description='Full expense',
                category='other',
                transaction_date=date.today()
            )
            db.session.add(transaction)
            db.session.commit()

            assert transaction.personal_amount == -100.0

    def test_transaction_personal_amount_with_share(self, test_app, test_account):
        """Test personal_amount when my_share is set."""
        with test_app.app_context():
            transaction = Transaction(
                account_id=test_account,
                amount=-100.0,
                my_share=-50.0,
                description='Split expense',
                category='dining',
                transaction_date=date.today()
            )
            db.session.add(transaction)
            db.session.commit()

            assert transaction.personal_amount == -50.0

    def test_transaction_repr(self, test_app, test_account):
        """Test Transaction string representation."""
        with test_app.app_context():
            transaction = Transaction(
                account_id=test_account,
                amount=-25.0,
                description='Test Trans',
                category='other',
                transaction_date=date.today()
            )
            assert repr(transaction) == '<Transaction Test Trans: -25.0>'


class TestCategoryModel:
    """Tests for the Category model."""

    def test_default_categories_initialized(self, test_app):
        """Test that default categories are created."""
        with test_app.app_context():
            default_cats = Category.query.filter_by(user_id=None).all()
            assert len(default_cats) == len(Category.DEFAULT_CATEGORIES)

    def test_custom_category_creation(self, test_app, test_user):
        """Test creating a custom category."""
        with test_app.app_context():
            category = Category(user_id=test_user, name='custom_cat')
            db.session.add(category)
            db.session.commit()

            assert category.id is not None
            assert category.user_id == test_user
            assert category.name == 'custom_cat'

    def test_get_user_categories(self, test_app, test_user):
        """Test getting categories for a user."""
        with test_app.app_context():
            # Add custom category
            custom = Category(user_id=test_user, name='my_custom')
            db.session.add(custom)
            db.session.commit()

            categories = Category.get_user_categories(test_user)
            category_names = [c.name for c in categories]

            # Should include default categories
            assert 'groceries' in category_names
            assert 'income' in category_names
            # Should include custom category
            assert 'my_custom' in category_names


class TestBudgetModel:
    """Tests for the Budget model."""

    def test_budget_creation(self, test_app, test_user):
        """Test creating a budget."""
        with test_app.app_context():
            budget = Budget(
                user_id=test_user,
                name='My Budget',
                expected_income=5000.0,
                expected_savings=500.0,
                expected_investments=1000.0,
                currency='USD'
            )
            db.session.add(budget)
            db.session.commit()

            assert budget.id is not None
            assert budget.name == 'My Budget'
            assert budget.expected_income == 5000.0
            assert budget.is_active is True

    def test_budget_total_expected_expenses(self, test_app, test_user):
        """Test total expected expenses calculation."""
        with test_app.app_context():
            budget = Budget(
                user_id=test_user,
                name='Expense Budget',
                expected_income=5000.0,
                currency='USD'
            )
            db.session.add(budget)
            db.session.commit()

            # Add budget items
            item1 = BudgetItem(budget_id=budget.id, category='groceries', amount=500.0)
            item2 = BudgetItem(budget_id=budget.id, category='utilities', amount=200.0)
            db.session.add_all([item1, item2])
            db.session.commit()

            assert budget.total_expected_expenses == 700.0

    def test_budget_expected_balance(self, test_app, test_user):
        """Test expected balance calculation."""
        with test_app.app_context():
            budget = Budget(
                user_id=test_user,
                name='Balance Budget',
                expected_income=5000.0,
                expected_savings=500.0,
                expected_investments=1000.0,
                currency='USD'
            )
            db.session.add(budget)
            db.session.commit()

            item = BudgetItem(budget_id=budget.id, category='rent', amount=1500.0)
            db.session.add(item)
            db.session.commit()

            # Expected: 5000 - 1500 - 500 - 1000 = 2000
            assert budget.expected_balance == 2000.0


class TestBudgetItemModel:
    """Tests for the BudgetItem model."""

    def test_budget_item_creation(self, test_app, test_budget):
        """Test creating a budget item."""
        with test_app.app_context():
            item = BudgetItem(
                budget_id=test_budget,
                category='groceries',
                amount=400.0
            )
            db.session.add(item)
            db.session.commit()

            assert item.id is not None
            assert item.category == 'groceries'
            assert item.amount == 400.0


class TestBudgetAccountGoalModel:
    """Tests for the BudgetAccountGoal model."""

    def test_account_goal_creation(self, test_app, test_budget, test_savings_account):
        """Test creating an account goal."""
        with test_app.app_context():
            goal = BudgetAccountGoal(
                budget_id=test_budget,
                account_id=test_savings_account,
                monthly_goal=500.0
            )
            db.session.add(goal)
            db.session.commit()

            assert goal.id is not None
            assert goal.monthly_goal == 500.0


class TestCascadeDeletes:
    """Tests for cascade delete behavior."""

    def test_account_delete_cascades_transactions(self, test_app, test_user):
        """Test that deleting an account deletes its transactions."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='Cascade Test',
                account_type='checking',
                currency='USD',
                initial_balance=100.0
            )
            db.session.add(account)
            db.session.commit()
            account_id = account.id

            transaction = Transaction(
                account_id=account_id,
                amount=-50.0,
                description='Test',
                category='other',
                transaction_date=date.today()
            )
            db.session.add(transaction)
            db.session.commit()
            transaction_id = transaction.id

            # Delete account
            db.session.delete(account)
            db.session.commit()

            # Transaction should be deleted
            assert Transaction.query.get(transaction_id) is None

    def test_budget_delete_cascades_items(self, test_app, test_user):
        """Test that deleting a budget deletes its items."""
        with test_app.app_context():
            budget = Budget(
                user_id=test_user,
                name='Cascade Budget',
                expected_income=5000.0,
                currency='USD'
            )
            db.session.add(budget)
            db.session.commit()
            budget_id = budget.id

            item = BudgetItem(budget_id=budget_id, category='food', amount=300.0)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            # Delete budget
            db.session.delete(budget)
            db.session.commit()

            # Item should be deleted
            assert BudgetItem.query.get(item_id) is None
