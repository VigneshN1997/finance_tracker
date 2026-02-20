"""
Unit tests for form validation.
"""
import pytest
from datetime import date
from forms import (
    LoginForm, SignupForm, AccountForm, TransactionForm,
    TransferForm, UpdateBalanceForm, EditAccountForm, BudgetForm
)
from models import User, db


class TestLoginForm:
    """Tests for LoginForm validation."""

    def test_valid_login_form(self, test_app):
        """Test valid login form data."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = LoginForm(data={
                    'email': 'test@example.com',
                    'password': 'password123'
                })
                assert form.validate() is True

    def test_login_form_requires_email(self, test_app):
        """Test that email is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = LoginForm(data={
                    'email': '',
                    'password': 'password123'
                })
                assert form.validate() is False
                assert 'email' in form.errors

    def test_login_form_requires_valid_email(self, test_app):
        """Test that email must be valid format."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = LoginForm(data={
                    'email': 'notanemail',
                    'password': 'password123'
                })
                assert form.validate() is False

    def test_login_form_requires_password(self, test_app):
        """Test that password is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = LoginForm(data={
                    'email': 'test@example.com',
                    'password': ''
                })
                assert form.validate() is False


class TestSignupForm:
    """Tests for SignupForm validation."""

    def test_valid_signup_form(self, test_app):
        """Test valid signup form data."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = SignupForm(data={
                    'email': 'newuser@example.com',
                    'password': 'password123',
                    'confirm_password': 'password123'
                })
                assert form.validate() is True

    def test_signup_password_mismatch(self, test_app):
        """Test password confirmation mismatch."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = SignupForm(data={
                    'email': 'test@example.com',
                    'password': 'password123',
                    'confirm_password': 'differentpassword'
                })
                assert form.validate() is False
                assert 'confirm_password' in form.errors

    def test_signup_password_too_short(self, test_app):
        """Test minimum password length."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = SignupForm(data={
                    'email': 'test@example.com',
                    'password': '12345',  # Too short
                    'confirm_password': '12345'
                })
                assert form.validate() is False
                assert 'password' in form.errors

    def test_signup_duplicate_email(self, test_app, test_user):
        """Test that duplicate email is rejected."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = SignupForm(data={
                    'email': 'test@example.com',  # Already exists
                    'password': 'password123',
                    'confirm_password': 'password123'
                })
                assert form.validate() is False
                assert 'email' in form.errors


class TestAccountForm:
    """Tests for AccountForm validation."""

    def test_valid_account_form(self, test_app):
        """Test valid account form data."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = AccountForm(data={
                    'name': 'My Account',
                    'account_type': 'checking',
                    'currency': 'USD',
                    'initial_balance': 1000.0
                })
                # SelectField choices are predefined in the form class
                assert form.name.data == 'My Account'
                assert form.account_type.data == 'checking'

    def test_account_name_required(self, test_app):
        """Test that account name is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = AccountForm(data={
                    'name': '',
                    'account_type': 'checking',
                    'currency': 'USD',
                    'initial_balance': 0
                })
                assert form.validate() is False
                assert 'name' in form.errors

    def test_account_type_required(self, test_app):
        """Test that account type is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = AccountForm(data={
                    'name': 'Test',
                    'account_type': '',
                    'currency': 'USD',
                    'initial_balance': 0
                })
                assert form.validate() is False

    def test_account_allows_negative_balance(self, test_app):
        """Test that negative initial balance is allowed (for credit cards)."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = AccountForm(data={
                    'name': 'Credit Card',
                    'account_type': 'credit_card',
                    'currency': 'USD',
                    'initial_balance': -500.0
                })
                # Verify negative balance is accepted
                assert form.initial_balance.data == -500.0


class TestTransactionForm:
    """Tests for TransactionForm validation."""

    def test_transaction_amount_required(self, test_app):
        """Test that amount is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = TransactionForm(data={
                    'account_id': 1,
                    'transaction_type': 'expense',
                    'amount': None,
                    'description': 'Test',
                    'category': 'other',
                    'transaction_date': date.today()
                })
                form.account_id.choices = [(1, 'Test Account')]
                form.category.choices = [('other', 'Other')]
                assert form.validate() is False

    def test_transaction_amount_must_be_positive(self, test_app):
        """Test that amount must be positive (sign is determined by type)."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = TransactionForm(data={
                    'account_id': 1,
                    'transaction_type': 'expense',
                    'amount': -50.0,  # Negative not allowed in form
                    'description': 'Test',
                    'category': 'other',
                    'transaction_date': date.today()
                })
                form.account_id.choices = [(1, 'Test Account')]
                form.category.choices = [('other', 'Other')]
                assert form.validate() is False

    def test_transaction_description_required(self, test_app):
        """Test that description is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = TransactionForm(data={
                    'account_id': 1,
                    'transaction_type': 'expense',
                    'amount': 50.0,
                    'description': '',
                    'category': 'other',
                    'transaction_date': date.today()
                })
                form.account_id.choices = [(1, 'Test Account')]
                form.category.choices = [('other', 'Other')]
                assert form.validate() is False


class TestTransferForm:
    """Tests for TransferForm validation."""

    def test_valid_transfer_form(self, test_app):
        """Test valid transfer form data."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = TransferForm(data={
                    'from_account_id': 1,
                    'to_account_id': 2,
                    'amount': 100.0,
                    'description': 'Transfer',
                    'transfer_date': date.today()
                })
                form.from_account_id.choices = [(1, 'Account 1'), (2, 'Account 2')]
                form.to_account_id.choices = [(1, 'Account 1'), (2, 'Account 2')]
                assert form.validate() is True

    def test_transfer_amount_positive(self, test_app):
        """Test that transfer amount must be positive."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = TransferForm(data={
                    'from_account_id': 1,
                    'to_account_id': 2,
                    'amount': -100.0,
                    'description': 'Transfer',
                    'transfer_date': date.today()
                })
                form.from_account_id.choices = [(1, 'Account 1'), (2, 'Account 2')]
                form.to_account_id.choices = [(1, 'Account 1'), (2, 'Account 2')]
                assert form.validate() is False


class TestBudgetForm:
    """Tests for BudgetForm validation."""

    def test_valid_budget_form(self, test_app):
        """Test valid budget form data."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = BudgetForm(data={
                    'name': 'Monthly Budget',
                    'expected_income': 5000.0,
                    'expected_savings': 500.0,
                    'expected_investments': 1000.0,
                    'currency': 'USD'
                })
                # Verify data is properly set
                assert form.name.data == 'Monthly Budget'
                assert form.expected_income.data == 5000.0

    def test_budget_name_required(self, test_app):
        """Test that budget name is required."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = BudgetForm(data={
                    'name': '',
                    'expected_income': 5000.0,
                    'expected_savings': 500.0,
                    'expected_investments': 1000.0,
                    'currency': 'USD'
                })
                assert form.validate() is False

    def test_budget_allows_zero_values(self, test_app):
        """Test that zero values are allowed for optional fields."""
        with test_app.app_context():
            with test_app.test_request_context():
                form = BudgetForm(data={
                    'name': 'Basic Budget',
                    'expected_income': 0,
                    'expected_savings': 0,
                    'expected_investments': 0,
                    'currency': 'USD'
                })
                # Verify zero values are accepted
                assert form.expected_income.data == 0
                assert form.expected_savings.data == 0
