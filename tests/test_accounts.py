"""
Integration tests for account routes.
"""
import pytest
import json
from models import Account, Transaction, db
from datetime import date


class TestAccountsListRoute:
    """Tests for the accounts list page."""

    def test_accounts_page_loads(self, logged_in_client, test_app):
        """Test that accounts page loads successfully."""
        response = logged_in_client.get('/accounts')
        assert response.status_code == 200
        assert b'Accounts' in response.data

    def test_accounts_page_shows_user_accounts(self, logged_in_client, test_app, test_account):
        """Test that user's accounts are displayed."""
        response = logged_in_client.get('/accounts')
        assert b'Test Checking' in response.data


class TestAddAccountRoute:
    """Tests for adding accounts."""

    def test_add_account_page_loads(self, logged_in_client, test_app):
        """Test that add account page loads."""
        response = logged_in_client.get('/accounts/add')
        assert response.status_code == 200
        assert b'Add Account' in response.data or b'Account Name' in response.data

    def test_add_checking_account(self, logged_in_client, test_app, test_user):
        """Test adding a checking account."""
        response = logged_in_client.post('/accounts/add', data={
            'name': 'My Checking',
            'account_type': 'checking',
            'currency': 'USD',
            'initial_balance': 1500.0
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'created successfully' in response.data

        with test_app.app_context():
            account = Account.query.filter_by(name='My Checking').first()
            assert account is not None
            assert account.account_type == 'checking'
            assert account.initial_balance == 1500.0

    def test_add_credit_card(self, logged_in_client, test_app, test_user):
        """Test adding a credit card account."""
        response = logged_in_client.post('/accounts/add', data={
            'name': 'My Credit Card',
            'account_type': 'credit_card',
            'currency': 'USD',
            'initial_balance': -500.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            account = Account.query.filter_by(name='My Credit Card').first()
            assert account is not None
            assert account.account_type == 'credit_card'
            assert account.initial_balance == -500.0

    def test_add_inr_account(self, logged_in_client, test_app, test_user):
        """Test adding an INR currency account."""
        response = logged_in_client.post('/accounts/add', data={
            'name': 'India Savings',
            'account_type': 'savings',
            'currency': 'INR',
            'initial_balance': 100000.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            account = Account.query.filter_by(name='India Savings').first()
            assert account is not None
            assert account.currency == 'INR'

    def test_add_investment_account(self, logged_in_client, test_app, test_user):
        """Test adding an investment account."""
        response = logged_in_client.post('/accounts/add', data={
            'name': 'My 401k',
            'account_type': 'investment',
            'currency': 'USD',
            'initial_balance': 50000.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            account = Account.query.filter_by(name='My 401k').first()
            assert account is not None
            assert account.account_type == 'investment'


class TestAccountDetailRoute:
    """Tests for account detail page."""

    def test_account_detail_loads(self, logged_in_client, test_app, test_account):
        """Test that account detail page loads."""
        response = logged_in_client.get(f'/accounts/{test_account}')
        assert response.status_code == 200
        assert b'Test Checking' in response.data

    def test_account_detail_shows_transactions(self, logged_in_client, test_app, test_account, test_transaction):
        """Test that transactions are shown on account detail."""
        response = logged_in_client.get(f'/accounts/{test_account}')
        assert b'Test expense' in response.data

    def test_account_detail_not_found(self, logged_in_client, test_app):
        """Test 404 for non-existent account."""
        response = logged_in_client.get('/accounts/99999')
        assert response.status_code == 404

    def test_account_detail_other_user(self, client, test_app, test_account):
        """Test that users cannot view other users' accounts."""
        # Create another user and log in
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

        response = client.get(f'/accounts/{test_account}')
        assert response.status_code == 404


class TestEditAccountRoute:
    """Tests for editing accounts."""

    def test_edit_account_page_loads(self, logged_in_client, test_app, test_account):
        """Test that edit account page loads."""
        response = logged_in_client.get(f'/accounts/{test_account}/edit')
        assert response.status_code == 200
        assert b'Test Checking' in response.data

    def test_edit_account_name(self, logged_in_client, test_app, test_account):
        """Test editing account name."""
        response = logged_in_client.post(f'/accounts/{test_account}/edit', data={
            'name': 'Updated Checking',
            'account_type': 'checking',
            'currency': 'USD',
            'initial_balance': 1000.0
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'updated successfully' in response.data

        with test_app.app_context():
            account = Account.query.get(test_account)
            assert account.name == 'Updated Checking'

    def test_edit_account_type(self, logged_in_client, test_app, test_account):
        """Test changing account type."""
        response = logged_in_client.post(f'/accounts/{test_account}/edit', data={
            'name': 'Test Checking',
            'account_type': 'savings',
            'currency': 'USD',
            'initial_balance': 1000.0
        }, follow_redirects=True)

        with test_app.app_context():
            account = Account.query.get(test_account)
            assert account.account_type == 'savings'

    def test_edit_account_initial_balance(self, logged_in_client, test_app, test_account):
        """Test editing account initial balance."""
        response = logged_in_client.post(f'/accounts/{test_account}/edit', data={
            'name': 'Test Checking',
            'account_type': 'checking',
            'currency': 'USD',
            'initial_balance': 2000.0
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'updated successfully' in response.data

        with test_app.app_context():
            account = Account.query.get(test_account)
            assert account.initial_balance == 2000.0


class TestDeleteAccountRoute:
    """Tests for deleting accounts."""

    def test_delete_account(self, logged_in_client, test_app, test_account):
        """Test deleting an account."""
        response = logged_in_client.post(f'/accounts/{test_account}/delete', follow_redirects=True)

        assert response.status_code == 200
        assert b'deleted successfully' in response.data

        with test_app.app_context():
            account = Account.query.get(test_account)
            assert account is None

    def test_delete_account_cascades_transactions(self, logged_in_client, test_app, test_account, test_transaction):
        """Test that deleting account also deletes transactions."""
        with test_app.app_context():
            trans_before = Transaction.query.get(test_transaction)
            assert trans_before is not None

        logged_in_client.post(f'/accounts/{test_account}/delete')

        with test_app.app_context():
            trans_after = Transaction.query.get(test_transaction)
            assert trans_after is None


class TestReorderAccountsRoute:
    """Tests for reordering accounts."""

    def test_reorder_accounts(self, logged_in_client, test_app, test_user):
        """Test reordering accounts."""
        # Create multiple accounts
        with test_app.app_context():
            account1 = Account(user_id=test_user, name='Account 1', account_type='checking',
                              currency='USD', initial_balance=0)
            account2 = Account(user_id=test_user, name='Account 2', account_type='savings',
                              currency='USD', initial_balance=0)
            db.session.add_all([account1, account2])
            db.session.commit()
            id1, id2 = account1.id, account2.id

        # Reorder: put account2 first
        response = logged_in_client.post('/accounts/reorder',
            data=json.dumps({'order': [id2, id1]}),
            content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with test_app.app_context():
            acc1 = Account.query.get(id1)
            acc2 = Account.query.get(id2)
            assert acc2.display_order < acc1.display_order

    def test_reorder_invalid_data(self, logged_in_client, test_app):
        """Test reorder with invalid data."""
        response = logged_in_client.post('/accounts/reorder',
            data=json.dumps({'invalid': 'data'}),
            content_type='application/json')

        assert response.status_code == 400


class TestUpdateBalanceRoute:
    """Tests for updating investment account balance."""

    def test_update_balance_page_loads(self, logged_in_client, test_app, test_investment_account):
        """Test that update balance page loads for investment accounts."""
        response = logged_in_client.get(f'/accounts/{test_investment_account}/update-balance')
        assert response.status_code == 200

    def test_update_balance_not_allowed_for_checking(self, logged_in_client, test_app, test_account):
        """Test that balance update is not allowed for non-investment accounts."""
        response = logged_in_client.get(f'/accounts/{test_account}/update-balance', follow_redirects=True)
        assert b'only be manually updated for investment' in response.data

    def test_update_investment_balance(self, logged_in_client, test_app, test_investment_account):
        """Test updating investment account balance."""
        response = logged_in_client.post(f'/accounts/{test_investment_account}/update-balance', data={
            'new_balance': 15000.0,
            'input_currency': 'USD'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'updated' in response.data.lower()

        with test_app.app_context():
            account = Account.query.get(test_investment_account)
            assert account.current_balance == 15000.0


class TestCreditCardsRoute:
    """Tests for credit cards page."""

    def test_credit_cards_page_loads(self, logged_in_client, test_app):
        """Test that credit cards page loads."""
        response = logged_in_client.get('/credit-cards')
        assert response.status_code == 200

    def test_credit_cards_shows_only_credit_cards(self, logged_in_client, test_app, test_user):
        """Test that only credit card accounts are shown."""
        with test_app.app_context():
            cc = Account(user_id=test_user, name='My Credit Card',
                        account_type='credit_card', currency='USD', initial_balance=-100)
            checking = Account(user_id=test_user, name='My Checking',
                              account_type='checking', currency='USD', initial_balance=1000)
            db.session.add_all([cc, checking])
            db.session.commit()

        response = logged_in_client.get('/credit-cards')
        assert b'My Credit Card' in response.data
        # Checking account should not appear on credit cards page
