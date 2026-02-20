#!/usr/bin/env python3
"""
Create a demo user account with comprehensive dummy data to showcase all features.
Email: demo@example.com
Password: demo123
"""

from datetime import datetime, timedelta
from app import app, db
from models import User, Account, Transaction, FixedDeposit, Budget, BudgetItem
import random

def create_demo_data():
    with app.app_context():
        # Check if demo user already exists
        existing_user = User.query.filter_by(email='demo@example.com').first()
        if existing_user:
            print("Demo user already exists. Deleting old data...")
            db.session.delete(existing_user)
            db.session.commit()
        
        # Create demo user
        demo_user = User(email='demo@example.com', display_currency='USD')
        demo_user.set_password('demo123')
        db.session.add(demo_user)
        db.session.commit()
        print(f"✓ Created demo user: demo@example.com")
        
        # Create accounts
        accounts = []
        
        # USD Checking Account
        chase_checking = Account(
            user_id=demo_user.id,
            name='Chase Checking',
            account_type='checking',
            currency='USD',
            initial_balance=5000.00
        )
        accounts.append(chase_checking)
        
        # USD Savings Account
        ally_savings = Account(
            user_id=demo_user.id,
            name='Ally Savings',
            account_type='savings',
            currency='USD',
            initial_balance=15000.00,
        )
        accounts.append(ally_savings)
        
        # INR Savings Account (for FDs)
        hdfc_savings = Account(
            user_id=demo_user.id,
            name='HDFC Savings',
            account_type='savings',
            currency='INR',
            initial_balance=500000.00,
        )
        accounts.append(hdfc_savings)
        
        # Investment Account
        vanguard = Account(
            user_id=demo_user.id,
            name='Vanguard 401k',
            account_type='investment',
            currency='USD',
            initial_balance=50000.00,
        )
        accounts.append(vanguard)
        
        # Credit Card
        chase_sapphire = Account(
            user_id=demo_user.id,
            name='Chase Sapphire',
            account_type='credit_card',
            currency='USD',
            initial_balance=0.00,
        )
        accounts.append(chase_sapphire)
        
        # Loan
        car_loan = Account(
            user_id=demo_user.id,
            name='Toyota Car Loan',
            account_type='loan',
            currency='USD',
            initial_balance=-25000.00,
        )
        accounts.append(car_loan)
        
        for account in accounts:
            db.session.add(account)
        db.session.commit()
        print(f"✓ Created {len(accounts)} accounts")
        
        # Create transactions for the last 3 months
        transactions = []
        categories = ['groceries', 'dining', 'transportation', 'utilities', 'entertainment', 
                     'shopping', 'healthcare', 'education', 'travel', 'other']
        
        # Income transactions
        for i in range(3):
            month_ago = datetime.now() - timedelta(days=30*i)
            salary = Transaction(
                account_id=chase_checking.id,
                transaction_date=month_ago.date(),
                description='Monthly Salary',
                category='income',
                amount=6500.00,
            )
            transactions.append(salary)
        
        # Expense transactions (varied)
        expense_data = [
            ('groceries', 'Whole Foods', -120.50),
            ('groceries', 'Trader Joes', -85.30),
            ('dining', 'Chipotle', -15.75),
            ('dining', 'Olive Garden', -45.20),
            ('transportation', 'Shell Gas', -55.00),
            ('transportation', 'Uber', -25.50),
            ('utilities', 'Electric Bill', -125.00),
            ('utilities', 'Internet Bill', -80.00),
            ('entertainment', 'Netflix', -15.99),
            ('entertainment', 'Movie Tickets', -35.00),
            ('shopping', 'Amazon', -125.50),
            ('shopping', 'Target', -78.25),
            ('healthcare', 'Pharmacy', -45.00),
            ('travel', 'Flight Booking', -450.00),
        ]
        
        for i in range(60):  # 60 days of transactions
            days_ago = datetime.now() - timedelta(days=i)
            category, desc, base_amount = random.choice(expense_data)
            amount = base_amount + random.uniform(-10, 10)
            
            # Randomly assign to checking or credit card
            account = chase_checking if random.random() > 0.3 else chase_sapphire
            
            trans = Transaction(
                account_id=account.id,
                transaction_date=days_ago.date(),
                description=desc,
                category=category,
                amount=amount,
            )
            transactions.append(trans)
        
        # Savings transfers
        for i in range(3):
            month_ago = datetime.now() - timedelta(days=30*i + 5)
            transfer = Transaction(
                account_id=ally_savings.id,
                transaction_date=month_ago.date(),
                description='Monthly Savings',
                category='savings',
                amount=1000.00,
            )
            transactions.append(transfer)
        
        # Investment contributions
        for i in range(3):
            month_ago = datetime.now() - timedelta(days=30*i + 10)
            contribution = Transaction(
                account_id=vanguard.id,
                transaction_date=month_ago.date(),
                description='401k Contribution',
                category='investment',
                amount=500.00,
            )
            transactions.append(contribution)
        
        # Loan payments
        for i in range(3):
            month_ago = datetime.now() - timedelta(days=30*i + 15)
            payment = Transaction(
                account_id=car_loan.id,
                transaction_date=month_ago.date(),
                description='Car Loan Payment',
                category='loan_payment',
                amount=850.00,
            )
            transactions.append(payment)
        
        for trans in transactions:
            db.session.add(trans)
        db.session.commit()
        print(f"✓ Created {len(transactions)} transactions")
        
        # Create Fixed Deposits
        fds = []
        
        fd1 = FixedDeposit(
            account_id=hdfc_savings.id,
            principal=100000.00,
            interest_rate=7.5,
            start_date=(datetime.now() - timedelta(days=180)).date(),
            maturity_date=(datetime.now() + timedelta(days=185)).date(),
            bank_name='HDFC Bank',
            fd_number='FD001234',
            is_matured=False
        )
        fds.append(fd1)
        
        fd2 = FixedDeposit(
            account_id=hdfc_savings.id,
            principal=200000.00,
            interest_rate=8.0,
            start_date=(datetime.now() - timedelta(days=90)).date(),
            maturity_date=(datetime.now() + timedelta(days=275)).date(),
            bank_name='ICICI Bank',
            fd_number='FD005678',
            is_matured=False
        )
        fds.append(fd2)
        
        # One matured FD
        fd3 = FixedDeposit(
            account_id=hdfc_savings.id,
            principal=50000.00,
            interest_rate=7.0,
            start_date=(datetime.now() - timedelta(days=400)).date(),
            maturity_date=(datetime.now() - timedelta(days=35)).date(),
            bank_name='SBI',
            fd_number='FD009012',
            is_matured=True
        )
        fds.append(fd3)
        
        for fd in fds:
            db.session.add(fd)
        db.session.commit()
        print(f"✓ Created {len(fds)} fixed deposits")
        
        # Create Budget
        budget = Budget(
            user_id=demo_user.id,
            currency='USD',
            expected_income=6500.00,
            expected_savings=1000.00,
            expected_investments=500.00
        )
        db.session.add(budget)
        db.session.commit()
        
        # Create Budget Items
        budget_items_data = [
            ('groceries', 400.00),
            ('dining', 200.00),
            ('transportation', 300.00),
            ('utilities', 250.00),
            ('entertainment', 150.00),
            ('shopping', 300.00),
            ('healthcare', 200.00),
        ]
        
        budget_items = []
        for category, amount in budget_items_data:
            item = BudgetItem(
                budget_id=budget.id,
                category=category,
                amount=amount
            )
            budget_items.append(item)
        
        for item in budget_items:
            db.session.add(item)
        db.session.commit()
        print(f"✓ Created budget with {len(budget_items)} categories")
        
        print("\n" + "="*50)
        print("✓ Demo account created successfully!")
        print("="*50)
        print("\nLogin credentials:")
        print("  Email: demo@example.com")
        print("  Password: demo123")
        print("\nDemo data includes:")
        print(f"  • {len(accounts)} accounts (checking, savings, investment, credit card, loan)")
        print(f"  • {len(transactions)} transactions over the last 3 months")
        print(f"  • {len(fds)} fixed deposits (2 active, 1 matured)")
        print(f"  • Budget with {len(budget_items)} expense categories")
        print("\nYou can now demo all features of the app!")

if __name__ == '__main__':
    create_demo_data()
