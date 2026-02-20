"""
Unit tests for the Fixed Deposit functionality.
"""
import pytest
from datetime import date, timedelta
from models import Account, FixedDeposit, Transaction, db


class TestFixedDepositModel:
    """Tests for the FixedDeposit model."""

    def test_fixed_deposit_creation(self, test_app, test_inr_account):
        """Test creating a fixed deposit."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.5,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            db.session.add(fd)
            db.session.commit()

            assert fd.id is not None
            assert fd.principal == 50000.0
            assert fd.interest_rate == 7.5
            assert fd.is_matured is False

    def test_maturity_value_calculation(self, test_app, test_inr_account):
        """Test maturity value calculation with compound interest (quarterly)."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=100000.0,
                interest_rate=7.0,
                start_date=date(2024, 1, 1),
                maturity_date=date(2025, 1, 1)  # 1 year
            )
            db.session.add(fd)
            db.session.commit()

            # Compound interest (quarterly): A = P * (1 + r/4)^(4*t)
            # Expected: 100000 * (1 + 0.07/4)^4 ≈ 107186
            # Allow small rounding difference due to leap year calculation
            assert abs(fd.maturity_value - 107186) < 200

    def test_interest_earned(self, test_app, test_inr_account):
        """Test interest earned calculation with compound interest."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=100000.0,
                interest_rate=8.0,
                start_date=date(2024, 1, 1),
                maturity_date=date(2025, 1, 1)
            )
            db.session.add(fd)
            db.session.commit()

            # Compound interest: A = 100000 * (1 + 0.08/4)^4 ≈ 108243
            # Interest ≈ 8243
            assert abs(fd.interest_earned - 8243) < 200

    def test_days_to_maturity(self, test_app, test_inr_account):
        """Test days to maturity calculation."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=100)
            )
            db.session.add(fd)
            db.session.commit()

            assert fd.days_to_maturity == 100

    def test_days_to_maturity_matured(self, test_app, test_inr_account):
        """Test days to maturity returns 0 when matured."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today() - timedelta(days=365),
                maturity_date=date.today() - timedelta(days=1),
                is_matured=True
            )
            db.session.add(fd)
            db.session.commit()

            assert fd.days_to_maturity == 0

    def test_is_past_maturity(self, test_app, test_inr_account):
        """Test is_past_maturity property."""
        with test_app.app_context():
            # Future maturity
            fd_future = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=100)
            )
            # Past maturity
            fd_past = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today() - timedelta(days=365),
                maturity_date=date.today() - timedelta(days=1)
            )
            db.session.add_all([fd_future, fd_past])
            db.session.commit()

            assert fd_future.is_past_maturity is False
            assert fd_past.is_past_maturity is True

    def test_fixed_deposit_repr(self, test_app, test_inr_account):
        """Test FixedDeposit string representation."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=100000.0,
                interest_rate=7.5,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            assert repr(fd) == '<FixedDeposit 100000.0 @ 7.5%>'


class TestAccountFixedDepositProperties:
    """Tests for Account model FD-related properties."""

    def test_total_fixed_deposits_inr_account(self, test_app, test_user):
        """Test total_fixed_deposits for INR account."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='INR Test',
                account_type='savings',
                currency='INR',
                initial_balance=200000.0
            )
            db.session.add(account)
            db.session.commit()

            fd1 = FixedDeposit(
                account_id=account.id,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            fd2 = FixedDeposit(
                account_id=account.id,
                principal=75000.0,
                interest_rate=7.5,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            db.session.add_all([fd1, fd2])
            db.session.commit()

            assert account.total_fixed_deposits == 125000.0

    def test_total_fixed_deposits_excludes_matured(self, test_app, test_user):
        """Test that matured FDs are excluded from total."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='INR Test',
                account_type='savings',
                currency='INR',
                initial_balance=200000.0
            )
            db.session.add(account)
            db.session.commit()

            fd_active = FixedDeposit(
                account_id=account.id,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365),
                is_matured=False
            )
            fd_matured = FixedDeposit(
                account_id=account.id,
                principal=75000.0,
                interest_rate=7.5,
                start_date=date.today() - timedelta(days=365),
                maturity_date=date.today(),
                is_matured=True
            )
            db.session.add_all([fd_active, fd_matured])
            db.session.commit()

            # Only active FD should be counted
            assert account.total_fixed_deposits == 50000.0

    def test_total_fixed_deposits_usd_account(self, test_app, test_user):
        """Test that USD accounts return 0 for fixed deposits."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='USD Test',
                account_type='savings',
                currency='USD',
                initial_balance=5000.0
            )
            db.session.add(account)
            db.session.commit()

            assert account.total_fixed_deposits == 0.0

    def test_total_value(self, test_app, test_user):
        """Test total_value includes FD principal."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='INR Test',
                account_type='savings',
                currency='INR',
                initial_balance=100000.0
            )
            db.session.add(account)
            db.session.commit()

            fd = FixedDeposit(
                account_id=account.id,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            db.session.add(fd)
            db.session.commit()

            # total_value = current_balance (100000) + fd_principal (50000)
            assert account.total_value == 150000.0


class TestFixedDepositRoutes:
    """Tests for Fixed Deposit routes."""

    def test_fixed_deposits_page_loads(self, logged_in_client, test_app):
        """Test that fixed deposits page loads."""
        response = logged_in_client.get('/fixed-deposits')
        assert response.status_code == 200
        assert b'Fixed Deposits' in response.data

    def test_add_fixed_deposit_requires_inr_account(self, logged_in_client, test_app, test_user):
        """Test that adding FD redirects when no INR account exists."""
        # No INR accounts exist (only USD from fixtures)
        response = logged_in_client.get('/fixed-deposits/add', follow_redirects=True)
        assert b'INR account' in response.data or b'Create' in response.data

    def test_add_fixed_deposit_form_loads(self, logged_in_client, test_app, test_inr_account):
        """Test that add FD form loads when INR account exists."""
        response = logged_in_client.get('/fixed-deposits/add')
        assert response.status_code == 200
        assert b'Principal' in response.data or b'Interest Rate' in response.data

    def test_add_fixed_deposit(self, logged_in_client, test_app, test_inr_account):
        """Test adding a fixed deposit."""
        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 100000,
            'interest_rate': 7.5,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() + timedelta(days=365)).isoformat(),
            'bank_name': 'SBI',
            'fd_number': 'FD123456'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'added successfully' in response.data or b'Fixed Deposit' in response.data

        with test_app.app_context():
            fd = FixedDeposit.query.filter_by(bank_name='SBI').first()
            assert fd is not None
            assert fd.principal == 100000.0

    def test_fixed_deposit_detail_page(self, logged_in_client, test_app, test_fixed_deposit):
        """Test fixed deposit detail page loads."""
        response = logged_in_client.get(f'/fixed-deposits/{test_fixed_deposit}')
        assert response.status_code == 200
        assert b'Principal' in response.data or b'Maturity' in response.data

    def test_edit_fixed_deposit(self, logged_in_client, test_app, test_fixed_deposit, test_inr_account):
        """Test editing a fixed deposit."""
        response = logged_in_client.post(f'/fixed-deposits/{test_fixed_deposit}/edit', data={
            'account_id': test_inr_account,
            'bank_name': 'HDFC Bank',
            'fd_number': 'NEW123',
            'is_matured': '0'
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            fd = FixedDeposit.query.get(test_fixed_deposit)
            assert fd.bank_name == 'HDFC Bank'
            assert fd.fd_number == 'NEW123'

    def test_delete_fixed_deposit(self, logged_in_client, test_app, test_inr_account):
        """Test deleting a fixed deposit."""
        # Create FD to delete
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            db.session.add(fd)
            db.session.commit()
            fd_id = fd.id

        response = logged_in_client.post(f'/fixed-deposits/{fd_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert b'deleted' in response.data

        with test_app.app_context():
            assert FixedDeposit.query.get(fd_id) is None

    def test_mark_fd_matured(self, logged_in_client, test_app, test_inr_account):
        """Test marking FD as matured."""
        with test_app.app_context():
            fd = FixedDeposit(
                account_id=test_inr_account,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today() - timedelta(days=365),
                maturity_date=date.today() - timedelta(days=1)
            )
            db.session.add(fd)
            db.session.commit()
            fd_id = fd.id

        response = logged_in_client.post(f'/fixed-deposits/{fd_id}/mark-matured', follow_redirects=True)
        assert response.status_code == 200

        with test_app.app_context():
            fd = FixedDeposit.query.get(fd_id)
            assert fd.is_matured is True


class TestFixedDepositValidation:
    """Tests for FD form validation."""

    def test_maturity_date_after_start_date(self, logged_in_client, test_app, test_inr_account):
        """Test that maturity date must be after start date."""
        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 50000,
            'interest_rate': 7.0,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() - timedelta(days=1)).isoformat()
        })

        # Should stay on form with error
        assert b'after start date' in response.data or response.status_code == 200

    def test_minimum_principal(self, logged_in_client, test_app, test_inr_account):
        """Test minimum principal validation."""
        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 500,  # Below minimum of 1000
            'interest_rate': 7.0,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() + timedelta(days=365)).isoformat()
        })

        assert b'1,000' in response.data or b'Minimum' in response.data


class TestCascadeDelete:
    """Tests for FD cascade delete behavior."""

    def test_account_delete_cascades_fixed_deposits(self, test_app, test_user):
        """Test that deleting an account deletes its fixed deposits."""
        with test_app.app_context():
            account = Account(
                user_id=test_user,
                name='Cascade Test',
                account_type='savings',
                currency='INR',
                initial_balance=100000.0
            )
            db.session.add(account)
            db.session.commit()
            account_id = account.id

            fd = FixedDeposit(
                account_id=account_id,
                principal=50000.0,
                interest_rate=7.0,
                start_date=date.today(),
                maturity_date=date.today() + timedelta(days=365)
            )
            db.session.add(fd)
            db.session.commit()
            fd_id = fd.id

            # Delete account
            db.session.delete(account)
            db.session.commit()

            # FD should be deleted
            assert FixedDeposit.query.get(fd_id) is None


class TestFixedDepositDebitFromAccount:
    """Tests for debit from account feature when creating FDs."""

    def test_add_fd_with_debit_creates_transaction(self, logged_in_client, test_app, test_inr_account):
        """Test that adding FD with debit_from_account creates a debit transaction."""
        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 100000,
            'interest_rate': 7.5,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() + timedelta(days=365)).isoformat(),
            'bank_name': 'SBI',
            'fd_number': 'FD999',
            'debit_from_account': 'y'
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            # Check FD was created
            fd = FixedDeposit.query.filter_by(fd_number='FD999').first()
            assert fd is not None
            assert fd.principal == 100000.0

            # Check transaction was created
            transaction = Transaction.query.filter_by(
                account_id=test_inr_account,
                category='transfer'
            ).filter(Transaction.description.contains('Fixed Deposit')).first()
            assert transaction is not None
            assert transaction.amount == -100000.0  # Negative for debit
            assert 'SBI' in transaction.description
            assert 'FD999' in transaction.description

    def test_add_fd_without_debit_no_transaction(self, logged_in_client, test_app, test_inr_account):
        """Test that adding FD without debit_from_account doesn't create a transaction."""
        with test_app.app_context():
            # Count existing transactions
            initial_count = Transaction.query.filter_by(account_id=test_inr_account).count()

        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 50000,
            'interest_rate': 6.5,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() + timedelta(days=180)).isoformat(),
            'bank_name': 'HDFC',
            'fd_number': 'FD888'
            # No debit_from_account field - checkbox unchecked
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            # Check FD was created
            fd = FixedDeposit.query.filter_by(fd_number='FD888').first()
            assert fd is not None

            # Check no new transaction was created
            final_count = Transaction.query.filter_by(account_id=test_inr_account).count()
            assert final_count == initial_count

    def test_add_fd_debit_transaction_date_matches_start_date(self, logged_in_client, test_app, test_inr_account):
        """Test that debit transaction date matches FD start date."""
        start_date = date.today() - timedelta(days=10)  # Start date in the past

        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 75000,
            'interest_rate': 7.0,
            'start_date': start_date.isoformat(),
            'maturity_date': (start_date + timedelta(days=365)).isoformat(),
            'bank_name': 'ICICI',
            'fd_number': 'FD777',
            'debit_from_account': 'y'
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            transaction = Transaction.query.filter_by(
                account_id=test_inr_account,
                category='transfer'
            ).filter(Transaction.description.contains('ICICI')).first()
            assert transaction is not None
            assert transaction.transaction_date == start_date

    def test_add_fd_debit_without_bank_info(self, logged_in_client, test_app, test_inr_account):
        """Test debit transaction description without bank name and FD number."""
        response = logged_in_client.post('/fixed-deposits/add', data={
            'account_id': test_inr_account,
            'principal': 25000,
            'interest_rate': 6.0,
            'start_date': date.today().isoformat(),
            'maturity_date': (date.today() + timedelta(days=90)).isoformat(),
            'debit_from_account': 'y'
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            transaction = Transaction.query.filter_by(
                account_id=test_inr_account,
                amount=-25000.0,
                category='transfer'
            ).first()
            assert transaction is not None
            assert transaction.description == 'Fixed Deposit'
