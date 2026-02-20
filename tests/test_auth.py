"""
Integration tests for authentication routes.
"""
import pytest
from models import User, db


class TestLoginRoute:
    """Tests for the login functionality."""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data

    def test_login_success(self, client, test_user, test_app):
        """Test successful login."""
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Dashboard' in response.data or b'Logged in successfully' in response.data

    def test_login_wrong_password(self, client, test_user, test_app):
        """Test login with wrong password."""
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        assert b'Invalid email or password' in response.data

    def test_login_nonexistent_user(self, client, test_app):
        """Test login with non-existent user."""
        response = client.post('/login', data={
            'email': 'nonexistent@example.com',
            'password': 'somepassword'
        }, follow_redirects=True)

        assert b'Invalid email or password' in response.data

    def test_login_invalid_email_format(self, client, test_app):
        """Test login with invalid email format."""
        response = client.post('/login', data={
            'email': 'notanemail',
            'password': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Form should show validation error

    def test_login_redirect_when_authenticated(self, logged_in_client, test_app):
        """Test that authenticated users are redirected from login page."""
        response = logged_in_client.get('/login', follow_redirects=True)
        assert b'Dashboard' in response.data


class TestSignupRoute:
    """Tests for the signup functionality."""

    def test_signup_page_loads(self, client):
        """Test that signup page loads successfully."""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'Sign Up' in response.data or b'Create' in response.data

    def test_signup_success(self, client, test_app):
        """Test successful signup."""
        response = client.post('/signup', data={
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Account created successfully' in response.data or b'Login' in response.data

        # Verify user was created
        with test_app.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None

    def test_signup_password_mismatch(self, client, test_app):
        """Test signup with mismatched passwords."""
        response = client.post('/signup', data={
            'email': 'mismatch@example.com',
            'password': 'password123',
            'confirm_password': 'differentpassword'
        }, follow_redirects=True)

        assert b'Passwords must match' in response.data

    def test_signup_short_password(self, client, test_app):
        """Test signup with password too short."""
        response = client.post('/signup', data={
            'email': 'short@example.com',
            'password': '12345',
            'confirm_password': '12345'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should show validation error for short password

    def test_signup_duplicate_email(self, client, test_user, test_app):
        """Test signup with existing email."""
        response = client.post('/signup', data={
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        assert b'Email already registered' in response.data

    def test_signup_redirect_when_authenticated(self, logged_in_client, test_app):
        """Test that authenticated users are redirected from signup page."""
        response = logged_in_client.get('/signup', follow_redirects=True)
        assert b'Dashboard' in response.data


class TestLogoutRoute:
    """Tests for the logout functionality."""

    def test_logout_success(self, logged_in_client, test_app):
        """Test successful logout."""
        response = logged_in_client.get('/logout', follow_redirects=True)
        assert b'logged out' in response.data.lower() or b'Login' in response.data

    def test_logout_requires_login(self, client, test_app):
        """Test that logout requires authentication."""
        response = client.get('/logout', follow_redirects=True)
        assert b'Login' in response.data


class TestIndexRoute:
    """Tests for the index route."""

    def test_index_redirects_to_login(self, client, test_app):
        """Test that index redirects unauthenticated users to login."""
        response = client.get('/', follow_redirects=True)
        assert b'Login' in response.data

    def test_index_redirects_to_dashboard(self, logged_in_client, test_app):
        """Test that index redirects authenticated users to dashboard."""
        response = logged_in_client.get('/', follow_redirects=True)
        assert b'Dashboard' in response.data


class TestProtectedRoutes:
    """Tests for route protection."""

    def test_dashboard_requires_login(self, client, test_app):
        """Test that dashboard requires authentication."""
        response = client.get('/dashboard', follow_redirects=True)
        assert b'Login' in response.data

    def test_accounts_requires_login(self, client, test_app):
        """Test that accounts page requires authentication."""
        response = client.get('/accounts', follow_redirects=True)
        assert b'Login' in response.data

    def test_add_transaction_requires_login(self, client, test_app):
        """Test that add transaction requires authentication."""
        response = client.get('/transactions/add', follow_redirects=True)
        assert b'Login' in response.data

    def test_budget_requires_login(self, client, test_app):
        """Test that budget page requires authentication."""
        response = client.get('/budget', follow_redirects=True)
        assert b'Login' in response.data


class TestToggleCurrency:
    """Tests for currency toggle functionality."""

    def test_toggle_currency_usd_to_inr(self, logged_in_client, test_app):
        """Test toggling from USD to INR."""
        # First toggle (USD -> INR)
        response = logged_in_client.get('/toggle-currency', follow_redirects=True)
        assert response.status_code == 200

        with test_app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.display_currency == 'INR'

    def test_toggle_currency_inr_to_usd(self, logged_in_client, test_app):
        """Test toggling from INR back to USD."""
        # Toggle twice
        logged_in_client.get('/toggle-currency')
        logged_in_client.get('/toggle-currency')

        with test_app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.display_currency == 'USD'

    def test_toggle_currency_requires_login(self, client, test_app):
        """Test that currency toggle requires authentication."""
        response = client.get('/toggle-currency', follow_redirects=True)
        assert b'Login' in response.data
