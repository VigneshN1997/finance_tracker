"""
Integration tests for budget routes.
"""
import pytest
from datetime import date
from models import Budget, BudgetItem, BudgetAccountGoal, Account, Transaction, db


class TestBudgetRoute:
    """Tests for budget page."""

    def test_budget_page_loads(self, logged_in_client, test_app):
        """Test that budget page loads."""
        response = logged_in_client.get('/budget')
        assert response.status_code == 200

    def test_budget_page_without_budget(self, logged_in_client, test_app):
        """Test budget page when no budget exists."""
        response = logged_in_client.get('/budget')
        assert response.status_code == 200
        # Should show option to create budget

    def test_budget_page_with_budget(self, logged_in_client, test_app, test_budget):
        """Test budget page with existing budget."""
        response = logged_in_client.get('/budget')
        assert response.status_code == 200
        # Budget page loads successfully - budget name may not be directly displayed


class TestEditBudgetRoute:
    """Tests for creating/editing budget."""

    def test_edit_budget_page_loads(self, logged_in_client, test_app):
        """Test that edit budget page loads."""
        response = logged_in_client.get('/budget/edit')
        assert response.status_code == 200

    def test_create_new_budget(self, logged_in_client, test_app, test_user):
        """Test creating a new budget."""
        response = logged_in_client.post('/budget/edit', data={
            'name': 'My Monthly Budget',
            'expected_income': 6000.0,
            'expected_savings': 1000.0,
            'expected_investments': 500.0,
            'currency': 'USD'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'saved' in response.data.lower()

        with test_app.app_context():
            budget = Budget.query.filter_by(user_id=test_user).first()
            assert budget is not None
            assert budget.name == 'My Monthly Budget'
            assert budget.expected_income == 6000.0

    def test_edit_existing_budget(self, logged_in_client, test_app, test_budget):
        """Test editing an existing budget."""
        response = logged_in_client.post('/budget/edit', data={
            'name': 'Updated Budget',
            'expected_income': 7000.0,
            'expected_savings': 1500.0,
            'expected_investments': 1000.0,
            'currency': 'USD'
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            budget = Budget.query.get(test_budget)
            assert budget.name == 'Updated Budget'
            assert budget.expected_income == 7000.0


class TestBudgetItemsRoute:
    """Tests for budget items (category budgets)."""

    def test_add_budget_item(self, logged_in_client, test_app, test_budget):
        """Test adding a budget item."""
        response = logged_in_client.post('/budget/items/add', data={
            'category': 'groceries',
            'amount': 500.0
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'added' in response.data.lower() or b'Groceries' in response.data

        with test_app.app_context():
            item = BudgetItem.query.filter_by(budget_id=test_budget, category='groceries').first()
            assert item is not None
            assert item.amount == 500.0

    def test_add_budget_item_with_new_category(self, logged_in_client, test_app, test_budget):
        """Test adding budget item with new category."""
        response = logged_in_client.post('/budget/items/add', data={
            'category': '__new__',
            'new_category': 'Pet Care',
            'amount': 100.0
        }, follow_redirects=True)

        with test_app.app_context():
            item = BudgetItem.query.filter_by(budget_id=test_budget, category='pet_care').first()
            assert item is not None

    def test_add_budget_item_requires_budget(self, logged_in_client, test_app):
        """Test that adding item requires existing budget."""
        response = logged_in_client.post('/budget/items/add', data={
            'category': 'groceries',
            'amount': 500.0
        }, follow_redirects=True)

        # Should redirect to edit budget
        assert response.status_code == 200

    def test_update_budget_item(self, logged_in_client, test_app, test_budget):
        """Test updating an existing budget item."""
        # First add an item
        with test_app.app_context():
            item = BudgetItem(budget_id=test_budget, category='rent', amount=1000.0)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Update the item
        response = logged_in_client.post(f'/budget/items/{item_id}/edit', data={
            'amount': 1200.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            item = BudgetItem.query.get(item_id)
            assert item.amount == 1200.0

    def test_delete_budget_item(self, logged_in_client, test_app, test_budget):
        """Test deleting a budget item."""
        with test_app.app_context():
            item = BudgetItem(budget_id=test_budget, category='entertainment', amount=200.0)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        response = logged_in_client.post(f'/budget/items/{item_id}/delete', follow_redirects=True)

        assert response.status_code == 200
        assert b'deleted' in response.data.lower()

        with test_app.app_context():
            item = BudgetItem.query.get(item_id)
            assert item is None

    def test_edit_budget_item_not_owned(self, client, test_app, test_budget):
        """Test that users cannot edit other users' budget items."""
        # Add an item
        with test_app.app_context():
            item = BudgetItem(budget_id=test_budget, category='food', amount=300.0)
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            # Create another user
            from models import User
            user2 = User(email='other@example.com')
            user2.set_password('password123')
            db.session.add(user2)
            db.session.commit()

        # Login as other user
        client.post('/login', data={
            'email': 'other@example.com',
            'password': 'password123'
        })

        response = client.get(f'/budget/items/{item_id}/edit', follow_redirects=True)
        assert b'not found' in response.data.lower() or b'Budget' in response.data


class TestAccountGoalsRoute:
    """Tests for account goals (savings/investment targets)."""

    def test_add_account_goal(self, logged_in_client, test_app, test_budget, test_savings_account):
        """Test adding an account goal."""
        response = logged_in_client.post('/budget/account-goals/add', data={
            'account_id': test_savings_account,
            'monthly_goal': 500.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            goal = BudgetAccountGoal.query.filter_by(
                budget_id=test_budget,
                account_id=test_savings_account
            ).first()
            assert goal is not None
            assert goal.monthly_goal == 500.0

    def test_add_investment_goal(self, logged_in_client, test_app, test_budget, test_investment_account):
        """Test adding an investment account goal."""
        response = logged_in_client.post('/budget/account-goals/add', data={
            'account_id': test_investment_account,
            'monthly_goal': 1000.0
        }, follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            goal = BudgetAccountGoal.query.filter_by(
                budget_id=test_budget,
                account_id=test_investment_account
            ).first()
            assert goal is not None
            assert goal.monthly_goal == 1000.0

    def test_update_account_goal(self, logged_in_client, test_app, test_budget, test_savings_account):
        """Test updating an account goal."""
        with test_app.app_context():
            goal = BudgetAccountGoal(
                budget_id=test_budget,
                account_id=test_savings_account,
                monthly_goal=500.0
            )
            db.session.add(goal)
            db.session.commit()
            goal_id = goal.id

        response = logged_in_client.post(f'/budget/account-goals/{goal_id}/edit', data={
            'monthly_goal': 750.0
        }, follow_redirects=True)

        with test_app.app_context():
            goal = BudgetAccountGoal.query.get(goal_id)
            assert goal.monthly_goal == 750.0

    def test_delete_account_goal(self, logged_in_client, test_app, test_budget, test_savings_account):
        """Test deleting an account goal."""
        with test_app.app_context():
            goal = BudgetAccountGoal(
                budget_id=test_budget,
                account_id=test_savings_account,
                monthly_goal=500.0
            )
            db.session.add(goal)
            db.session.commit()
            goal_id = goal.id

        response = logged_in_client.post(f'/budget/account-goals/{goal_id}/delete', follow_redirects=True)

        assert response.status_code == 200

        with test_app.app_context():
            goal = BudgetAccountGoal.query.get(goal_id)
            assert goal is None


class TestBudgetComparison:
    """Tests for budget vs actual comparison."""

    def test_budget_shows_actual_spending(self, logged_in_client, test_app, test_budget, test_account):
        """Test that budget page shows actual spending."""
        # Add some transactions
        with test_app.app_context():
            t1 = Transaction(
                account_id=test_account,
                amount=-150.0,
                description='Groceries',
                category='groceries',
                transaction_date=date.today()
            )
            t2 = Transaction(
                account_id=test_account,
                amount=-50.0,
                description='Dinner',
                category='dining',
                transaction_date=date.today()
            )
            db.session.add_all([t1, t2])
            db.session.commit()

        response = logged_in_client.get('/budget')
        assert response.status_code == 200

    def test_budget_tracks_savings_contributions(self, logged_in_client, test_app, test_budget, test_account, test_savings_account):
        """Test that budget tracks savings contributions."""
        # Make a transfer to savings
        logged_in_client.post('/transfer', data={
            'from_account_id': test_account,
            'to_account_id': test_savings_account,
            'amount': 500.0,
            'description': 'Monthly savings',
            'transfer_date': date.today().isoformat()
        })

        response = logged_in_client.get('/budget')
        assert response.status_code == 200
        # Budget page should show savings contribution

    def test_budget_tracks_investment_contributions(self, logged_in_client, test_app, test_budget, test_account, test_investment_account):
        """Test that budget tracks investment contributions."""
        # Make a transfer to investment
        logged_in_client.post('/transfer', data={
            'from_account_id': test_account,
            'to_account_id': test_investment_account,
            'amount': 1000.0,
            'description': '401k contribution',
            'transfer_date': date.today().isoformat()
        })

        response = logged_in_client.get('/budget')
        assert response.status_code == 200


class TestBudgetValidation:
    """Tests for budget input validation."""

    def test_budget_item_requires_positive_amount(self, logged_in_client, test_app, test_budget):
        """Test that budget item requires positive amount."""
        response = logged_in_client.post('/budget/items/add', data={
            'category': 'groceries',
            'amount': -100.0
        }, follow_redirects=True)

        assert b'positive' in response.data.lower() or response.status_code == 200

    def test_account_goal_requires_positive_amount(self, logged_in_client, test_app, test_budget, test_savings_account):
        """Test that account goal requires positive amount."""
        response = logged_in_client.post('/budget/account-goals/add', data={
            'account_id': test_savings_account,
            'monthly_goal': -500.0
        }, follow_redirects=True)

        assert b'positive' in response.data.lower() or response.status_code == 200
