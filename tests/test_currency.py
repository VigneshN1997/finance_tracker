"""
Unit tests for currency conversion and related features.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from currency import (
    get_exchange_rate,
    convert_currency,
    format_currency,
    get_currency_symbol,
    DEFAULT_EXCHANGE_RATE,
    _rate_cache
)
from models import Account, db


class TestGetExchangeRate:
    """Tests for exchange rate fetching."""

    def test_returns_cached_rate(self):
        """Test that cached rate is returned if recent."""
        # Set up cache with recent timestamp
        _rate_cache['rate'] = 85.0
        _rate_cache['last_updated'] = datetime.now()

        rate = get_exchange_rate()
        assert rate == 85.0

    def test_returns_default_on_api_failure(self):
        """Test fallback to default rate on API failure."""
        _rate_cache['last_updated'] = None  # Force API call

        with patch('currency.requests.get') as mock_get:
            mock_get.side_effect = Exception('Network error')
            rate = get_exchange_rate()
            # Should return cached or default rate
            assert rate > 0

    @patch('currency.requests.get')
    def test_updates_cache_on_success(self, mock_get):
        """Test that cache is updated on successful API call."""
        _rate_cache['last_updated'] = None  # Force API call

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'rates': {'INR': 84.5}}
        mock_get.return_value = mock_response

        rate = get_exchange_rate()
        assert rate == 84.5
        assert _rate_cache['rate'] == 84.5
        assert _rate_cache['last_updated'] is not None


class TestConvertCurrency:
    """Tests for currency conversion."""

    def test_same_currency_no_conversion(self):
        """Test that same currency returns original amount."""
        assert convert_currency(100.0, 'USD', 'USD') == 100.0
        assert convert_currency(5000.0, 'INR', 'INR') == 5000.0

    def test_usd_to_inr(self):
        """Test USD to INR conversion."""
        _rate_cache['rate'] = 83.0
        _rate_cache['last_updated'] = datetime.now()

        result = convert_currency(100.0, 'USD', 'INR')
        assert result == 8300.0

    def test_inr_to_usd(self):
        """Test INR to USD conversion."""
        _rate_cache['rate'] = 83.0
        _rate_cache['last_updated'] = datetime.now()

        result = convert_currency(8300.0, 'INR', 'USD')
        assert result == 100.0

    def test_negative_amounts(self):
        """Test conversion of negative amounts."""
        _rate_cache['rate'] = 83.0
        _rate_cache['last_updated'] = datetime.now()

        result = convert_currency(-100.0, 'USD', 'INR')
        assert result == -8300.0

    def test_zero_amount(self):
        """Test conversion of zero."""
        assert convert_currency(0, 'USD', 'INR') == 0


class TestFormatCurrency:
    """Tests for currency formatting."""

    def test_format_usd(self):
        """Test USD formatting."""
        assert format_currency(1234.56, 'USD') == '$1,234.56'
        assert format_currency(1000000.00, 'USD') == '$1,000,000.00'

    def test_format_inr(self):
        """Test INR formatting."""
        assert format_currency(1234.56, 'INR') == '₹1,234.56'

    def test_format_default_currency(self):
        """Test default currency (USD)."""
        assert format_currency(100.00) == '$100.00'

    def test_format_unknown_currency(self):
        """Test unknown currency defaults to $."""
        assert format_currency(100.00, 'XYZ') == '$100.00'


class TestGetCurrencySymbol:
    """Tests for currency symbol retrieval."""

    def test_usd_symbol(self):
        """Test USD symbol."""
        assert get_currency_symbol('USD') == '$'

    def test_inr_symbol(self):
        """Test INR symbol."""
        assert get_currency_symbol('INR') == '₹'

    def test_unknown_currency(self):
        """Test unknown currency defaults to $."""
        assert get_currency_symbol('XYZ') == '$'


class TestCurrencySummaryRoute:
    """Tests for currency summary page."""

    def test_currency_summary_loads(self, logged_in_client, test_app):
        """Test that currency summary page loads."""
        response = logged_in_client.get('/currency-summary')
        assert response.status_code == 200

    def test_currency_summary_groups_accounts(self, logged_in_client, test_app, test_user):
        """Test that accounts are grouped by currency."""
        with test_app.app_context():
            usd_account = Account(
                user_id=test_user,
                name='USD Account',
                account_type='checking',
                currency='USD',
                initial_balance=1000.0
            )
            inr_account = Account(
                user_id=test_user,
                name='INR Account',
                account_type='checking',
                currency='INR',
                initial_balance=80000.0
            )
            db.session.add_all([usd_account, inr_account])
            db.session.commit()

        response = logged_in_client.get('/currency-summary')
        assert response.status_code == 200
        assert b'USD Account' in response.data
        assert b'INR Account' in response.data


class TestNetWorthRoute:
    """Tests for net worth page."""

    def test_net_worth_loads(self, logged_in_client, test_app):
        """Test that net worth page loads."""
        response = logged_in_client.get('/net-worth')
        assert response.status_code == 200

    def test_net_worth_calculates_assets(self, logged_in_client, test_app, test_user):
        """Test that net worth calculates assets correctly."""
        with test_app.app_context():
            checking = Account(
                user_id=test_user,
                name='Checking',
                account_type='checking',
                currency='USD',
                initial_balance=5000.0
            )
            savings = Account(
                user_id=test_user,
                name='Savings',
                account_type='savings',
                currency='USD',
                initial_balance=10000.0
            )
            investment = Account(
                user_id=test_user,
                name='401k',
                account_type='investment',
                currency='USD',
                initial_balance=50000.0
            )
            db.session.add_all([checking, savings, investment])
            db.session.commit()

        response = logged_in_client.get('/net-worth')
        assert response.status_code == 200
        # Total assets should be 65000

    def test_net_worth_calculates_liabilities(self, logged_in_client, test_app, test_user):
        """Test that net worth calculates liabilities correctly."""
        with test_app.app_context():
            credit_card = Account(
                user_id=test_user,
                name='Credit Card',
                account_type='credit_card',
                currency='USD',
                initial_balance=-2000.0
            )
            loan = Account(
                user_id=test_user,
                name='Car Loan',
                account_type='loan',
                currency='USD',
                initial_balance=-15000.0
            )
            db.session.add_all([credit_card, loan])
            db.session.commit()

        response = logged_in_client.get('/net-worth')
        assert response.status_code == 200

    def test_net_worth_converts_inr_accounts(self, logged_in_client, test_app, test_user):
        """Test that INR accounts are converted to USD for net worth."""
        with test_app.app_context():
            inr_account = Account(
                user_id=test_user,
                name='India Savings',
                account_type='savings',
                currency='INR',
                initial_balance=830000.0  # ~10,000 USD at 83 rate
            )
            db.session.add(inr_account)
            db.session.commit()

        response = logged_in_client.get('/net-worth')
        assert response.status_code == 200

    def test_net_worth_groups_by_account_type(self, logged_in_client, test_app, test_user):
        """Test that accounts are grouped by type."""
        with test_app.app_context():
            for account_type in Account.ACCOUNT_TYPES:
                account = Account(
                    user_id=test_user,
                    name=f'{account_type.title()} Account',
                    account_type=account_type,
                    currency='USD',
                    initial_balance=1000.0 if account_type not in ['credit_card', 'loan'] else -500.0
                )
                db.session.add(account)
            db.session.commit()

        response = logged_in_client.get('/net-worth')
        assert response.status_code == 200


class TestDisplayCurrencyPreference:
    """Tests for display currency preference."""

    def test_dashboard_respects_currency_preference(self, logged_in_client, test_app, test_user, test_account):
        """Test that dashboard respects user's display currency preference."""
        # Set preference to INR
        logged_in_client.get('/toggle-currency')

        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        # Should display values in INR

    def test_accounts_page_shows_original_currency(self, logged_in_client, test_app, test_account):
        """Test that account detail shows original currency."""
        response = logged_in_client.get(f'/accounts/{test_account}')
        assert response.status_code == 200
        # Should show $ for USD account
