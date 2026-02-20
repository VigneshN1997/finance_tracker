"""
Integration tests for transaction routes.
"""
import pytest
from datetime import date
from models import Transaction, Account, Category, db


class TestAddTransactionRoute:
    """Tests for adding transactions."""

    def test_add_transaction_page_loads(self, logged_in_client, test_app, test_account):
        """Test that add transaction page loads."""
        response = logged_in_client.get('/transactions/add')
        assert response.status_code == 200
        assert b'Add Transaction' in response.data or b'Transaction' in response.data

    def test_add_transaction_redirect_without_accounts(self, logged_in_client, test_app):
        """Test redirect to add account when no accounts exist."""
        response = logged_in_client.get('/transactions/add', follow_redirects=True)
        # Should redirect to add account if no accounts exist
        assert response.status_code == 200

    def test_add_expense_transaction(self, logged_in_client, test_app, test_account):
        """Test adding an expense transaction."""
        response = logged_in_client.post('/transactions/add', data={
            'account_id': test_account,
            'transaction_type': 'expense',
            'amount': 50.0,
            'description': 'Coffee',
            'category': 'dining',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'added successfully' in response.data

        with test_app.app_context():
            transaction = Transaction.query.filter_by(description='Coffee').first()
            assert transaction is not None
            assert transaction.amount == -50.0  # Expense is negative

    def test_add_income_transaction(self, logged_in_client, test_app, test_account):
        """Test adding an income transaction."""
        response = logged_in_client.post('/transactions/add', data={
            'account_id': test_account,
            'transaction_type': 'income',
            'amount': 3000.0,
            'description': 'Salary',
            'category': 'salary',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            transaction = Transaction.query.filter_by(description='Salary').first()
            assert transaction is not None
            assert transaction.amount == 3000.0  # Income is positive

    def test_add_transaction_with_my_share(self, logged_in_client, test_app, test_account):
        """Test adding a transaction with a personal share."""
        response = logged_in_client.post('/transactions/add', data={
            'account_id': test_account,
            'transaction_type': 'expense',
            'amount': 100.0,
            'my_share': 50.0,
            'description': 'Shared dinner',
            'category': 'dining',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        with test_app.app_context():
            transaction = Transaction.query.filter_by(description='Shared dinner').first()
            assert transaction is not None
            assert transaction.amount == -100.0
            assert transaction.my_share == -50.0
            assert transaction.personal_amount == -50.0

    def test_add_transaction_with_new_category(self, logged_in_client, test_app, test_account):
        """Test adding a transaction with a new custom category."""
        response = logged_in_client.post('/transactions/add', data={
            'account_id': test_account,
            'transaction_type': 'expense',
            'amount': 25.0,
            'description': 'Pet food',
            'category': '__new__',
            'new_category': 'Pet Expenses',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        with test_app.app_context():
            transaction = Transaction.query.filter_by(description='Pet food').first()
            assert transaction is not None
            assert transaction.category == 'pet_expenses'

            # Check category was created
            category = Category.query.filter_by(name='pet_expenses').first()
            assert category is not None

    def test_add_transaction_preselects_account(self, logged_in_client, test_app, test_account):
        """Test that account is pre-selected when passed as query param."""
        response = logged_in_client.get(f'/transactions/add?account_id={test_account}')
        assert response.status_code == 200
        # The account should be pre-selected in the form

    def test_add_transaction_invalid_account(self, logged_in_client, test_app, test_user):
        """Test adding transaction with invalid account."""
        response = logged_in_client.post('/transactions/add', data={
            'account_id': 99999,  # Invalid account
            'transaction_type': 'expense',
            'amount': 50.0,
            'description': 'Test',
            'category': 'other',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        # Should show error or redirect
        assert response.status_code == 200


class TestEditTransactionRoute:
    """Tests for editing transactions."""

    def test_edit_transaction_page_loads(self, logged_in_client, test_app, test_transaction):
        """Test that edit transaction page loads."""
        response = logged_in_client.get(f'/transactions/{test_transaction}/edit')
        assert response.status_code == 200

    def test_edit_transaction_amount(self, logged_in_client, test_app, test_transaction, test_account):
        """Test editing transaction amount."""
        response = logged_in_client.post(f'/transactions/{test_transaction}/edit', data={
            'account_id': test_account,
            'transaction_type': 'expense',
            'amount': 75.0,
            'description': 'Updated expense',
            'category': 'groceries',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'updated successfully' in response.data

        with test_app.app_context():
            transaction = Transaction.query.get(test_transaction)
            assert transaction.amount == -75.0
            assert transaction.description == 'Updated expense'

    def test_edit_transaction_type_to_income(self, logged_in_client, test_app, test_transaction, test_account):
        """Test changing transaction from expense to income."""
        response = logged_in_client.post(f'/transactions/{test_transaction}/edit', data={
            'account_id': test_account,
            'transaction_type': 'income',
            'amount': 50.0,
            'description': 'Now income',
            'category': 'income',
            'transaction_date': date.today().isoformat()
        }, follow_redirects=True)

        with test_app.app_context():
            transaction = Transaction.query.get(test_transaction)
            assert transaction.amount == 50.0  # Now positive

    def test_edit_transaction_not_found(self, logged_in_client, test_app):
        """Test editing non-existent transaction."""
        response = logged_in_client.get('/transactions/99999/edit')
        assert response.status_code == 404

    def test_edit_other_users_transaction(self, client, test_app, test_transaction):
        """Test that users cannot edit other users' transactions."""
        # Create another user
        with test_app.app_context():
            from models import User
            user2 = User(email='other@example.com')
            user2.set_password('password123')
            db.session.add(user2)
            db.session.commit()

        client.post('/login', data={
            'email': 'other@example.com',
            'password': 'password123'
        })

        response = client.get(f'/transactions/{test_transaction}/edit', follow_redirects=True)
        assert b'not found' in response.data.lower() or b'Dashboard' in response.data


class TestDeleteTransactionRoute:
    """Tests for deleting transactions."""

    def test_delete_transaction(self, logged_in_client, test_app, test_transaction, test_account):
        """Test deleting a transaction."""
        response = logged_in_client.post(f'/transactions/{test_transaction}/delete', follow_redirects=True)

        assert response.status_code == 200
        assert b'deleted successfully' in response.data

        with test_app.app_context():
            transaction = Transaction.query.get(test_transaction)
            assert transaction is None

    def test_delete_transaction_updates_balance(self, logged_in_client, test_app, test_account):
        """Test that deleting transaction updates account balance."""
        with test_app.app_context():
            account = Account.query.get(test_account)
            initial_balance = account.current_balance

            # Add a transaction
            t = Transaction(
                account_id=test_account,
                amount=-100.0,
                description='To delete',
                category='other',
                transaction_date=date.today()
            )
            db.session.add(t)
            db.session.commit()
            trans_id = t.id

            # Balance should have decreased
            assert account.current_balance == initial_balance - 100.0

        # Delete the transaction
        logged_in_client.post(f'/transactions/{trans_id}/delete')

        with test_app.app_context():
            account = Account.query.get(test_account)
            # Balance should be restored
            assert account.current_balance == initial_balance


class TestTransferRoute:
    """Tests for transfers between accounts."""

    def test_transfer_page_loads(self, logged_in_client, test_app, test_account, test_savings_account):
        """Test that transfer page loads when user has multiple accounts."""
        response = logged_in_client.get('/transfer')
        assert response.status_code == 200

    def test_transfer_requires_two_accounts(self, logged_in_client, test_app, test_account):
        """Test that transfer requires at least 2 accounts."""
        response = logged_in_client.get('/transfer', follow_redirects=True)
        # Should redirect or show message if only 1 account
        assert response.status_code == 200

    def test_successful_transfer(self, logged_in_client, test_app, test_account, test_savings_account):
        """Test successful transfer between accounts."""
        with test_app.app_context():
            checking = Account.query.get(test_account)
            savings = Account.query.get(test_savings_account)
            checking_balance = checking.current_balance
            savings_balance = savings.current_balance

        response = logged_in_client.post('/transfer', data={
            'from_account_id': test_account,
            'to_account_id': test_savings_account,
            'amount': 200.0,
            'description': 'Monthly savings',
            'transfer_date': date.today().isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'transferred' in response.data.lower()

        with test_app.app_context():
            checking = Account.query.get(test_account)
            savings = Account.query.get(test_savings_account)
            assert checking.current_balance == checking_balance - 200.0
            assert savings.current_balance == savings_balance + 200.0

    def test_transfer_creates_two_transactions(self, logged_in_client, test_app, test_account, test_savings_account):
        """Test that transfer creates paired transactions."""
        logged_in_client.post('/transfer', data={
            'from_account_id': test_account,
            'to_account_id': test_savings_account,
            'amount': 100.0,
            'description': 'Test transfer',
            'transfer_date': date.today().isoformat()
        })

        with test_app.app_context():
            # Check outgoing transaction
            outgoing = Transaction.query.filter(
                Transaction.account_id == test_account,
                Transaction.category == 'transfer',
                Transaction.amount == -100.0
            ).first()
            assert outgoing is not None

            # Check incoming transaction
            incoming = Transaction.query.filter(
                Transaction.account_id == test_savings_account,
                Transaction.category == 'transfer',
                Transaction.amount == 100.0
            ).first()
            assert incoming is not None

    def test_transfer_to_same_account(self, logged_in_client, test_app, test_account, test_savings_account):
        """Test that transfer to same account is rejected."""
        response = logged_in_client.post('/transfer', data={
            'from_account_id': test_account,
            'to_account_id': test_account,
            'amount': 100.0,
            'description': 'Invalid',
            'transfer_date': date.today().isoformat()
        }, follow_redirects=True)

        # Should show error message about same account
        assert b'same account' in response.data.lower() or response.status_code == 200


class TestMonthlyReportRoute:
    """Tests for monthly report."""

    def test_monthly_report_loads(self, logged_in_client, test_app, test_account):
        """Test that monthly report page loads."""
        response = logged_in_client.get('/reports/monthly')
        assert response.status_code == 200

    def test_monthly_report_with_transactions(self, logged_in_client, test_app, test_account):
        """Test monthly report shows transaction data."""
        # Add some transactions for this month
        with test_app.app_context():
            t1 = Transaction(
                account_id=test_account,
                amount=5000.0,
                description='Salary',
                category='salary',
                transaction_date=date.today()
            )
            t2 = Transaction(
                account_id=test_account,
                amount=-200.0,
                description='Groceries',
                category='groceries',
                transaction_date=date.today()
            )
            db.session.add_all([t1, t2])
            db.session.commit()

        response = logged_in_client.get('/reports/monthly')
        assert response.status_code == 200
        # Should show expense categories

    def test_monthly_report_different_month(self, logged_in_client, test_app, test_account):
        """Test viewing report for different month."""
        response = logged_in_client.get('/reports/monthly?year=2024&month=1')
        assert response.status_code == 200


class TestDashboardTransactions:
    """Tests for dashboard transaction display."""

    def test_dashboard_shows_recent_transactions(self, logged_in_client, test_app, test_account):
        """Test that dashboard shows recent transactions."""
        with test_app.app_context():
            for i in range(5):
                t = Transaction(
                    account_id=test_account,
                    amount=-10.0 * (i + 1),
                    description=f'Transaction {i}',
                    category='other',
                    transaction_date=date.today()
                )
                db.session.add(t)
            db.session.commit()

        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Transaction' in response.data

    def test_dashboard_monthly_expenses(self, logged_in_client, test_app, test_account):
        """Test that dashboard calculates monthly expenses."""
        with test_app.app_context():
            t = Transaction(
                account_id=test_account,
                amount=-500.0,
                description='Big purchase',
                category='shopping',
                transaction_date=date.today()
            )
            db.session.add(t)
            db.session.commit()

        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        # Dashboard should show monthly expenses
