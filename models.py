from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_currency = db.Column(db.String(3), default='USD')  # USD or INR for display preference
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    accounts = db.relationship('Account', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Account(db.Model):
    __tablename__ = 'accounts'

    ACCOUNT_TYPES = ['checking', 'savings', 'credit_card', 'loan', 'investment']
    CURRENCIES = {
        'USD': {'symbol': '$', 'name': 'US Dollar', 'country': 'USA'},
        'INR': {'symbol': '₹', 'name': 'Indian Rupee', 'country': 'India'},
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')  # USD or INR
    initial_balance = db.Column(db.Float, default=0.0)
    display_order = db.Column(db.Integer, default=0)  # For custom ordering
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='account', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def current_balance(self):
        total_transactions = db.session.query(
            db.func.coalesce(db.func.sum(Transaction.amount), 0)
        ).filter(Transaction.account_id == self.id).scalar()
        return self.initial_balance + total_transactions

    @property
    def currency_symbol(self):
        return self.CURRENCIES.get(self.currency, {}).get('symbol', '$')

    @property
    def country(self) -> str:
        return self.CURRENCIES.get(self.currency, {}).get('country', 'USA')

    @property
    def total_fixed_deposits(self) -> float:
        """Sum of all active fixed deposit principals (INR accounts only)."""
        if self.currency != 'INR':
            return 0.0
        return db.session.query(
            db.func.coalesce(db.func.sum(FixedDeposit.principal), 0)
        ).filter(
            FixedDeposit.account_id == self.id,
            FixedDeposit.is_matured == False
        ).scalar()

    @property
    def total_value(self) -> float:
        """Account balance + fixed deposit principals."""
        return self.current_balance + self.total_fixed_deposits

    def __repr__(self) -> str:
        return f'<Account {self.name}>'


class Category(db.Model):
    __tablename__ = 'categories'

    DEFAULT_CATEGORIES = [
        'income', 'salary', 'groceries', 'utilities', 'rent', 'mortgage',
        'transportation', 'entertainment', 'dining', 'shopping',
        'healthcare', 'insurance', 'education', 'travel', 'transfer', 'other'
    ]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL for default categories
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: category name must be unique per user (or globally for defaults)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_user_category'),
    )

    @staticmethod
    def get_user_categories(user_id):
        """Get all categories available to a user (default + custom)"""
        default_cats = Category.query.filter_by(user_id=None).all()
        user_cats = Category.query.filter_by(user_id=user_id).all()
        return default_cats + user_cats

    @staticmethod
    def init_default_categories():
        """Initialize default categories if they don't exist"""
        for cat_name in Category.DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(user_id=None, name=cat_name).first()
            if not existing:
                category = Category(user_id=None, name=cat_name)
                db.session.add(category)
        db.session.commit()

    def __repr__(self):
        return f'<Category {self.name}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Full transaction amount (what was charged)
    my_share = db.Column(db.Float, nullable=True)  # User's personal share (NULL = same as amount)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def personal_amount(self):
        """Returns the user's personal share (my_share if set, otherwise full amount)"""
        return self.my_share if self.my_share is not None else self.amount

    def __repr__(self):
        return f'<Transaction {self.description}: {self.amount}>'


class FixedDeposit(db.Model):
    __tablename__ = 'fixed_deposits'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    principal = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)  # Annual rate as percentage (e.g., 7.5)
    start_date = db.Column(db.Date, nullable=False)
    maturity_date = db.Column(db.Date, nullable=False)
    bank_name = db.Column(db.String(100), nullable=True)
    fd_number = db.Column(db.String(50), nullable=True)
    is_matured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('Account', backref=db.backref('fixed_deposits', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def maturity_value(self) -> float:
        """Calculate the maturity value using compound interest (quarterly compounding)."""
        days = (self.maturity_date - self.start_date).days
        years = days / 365.0
        rate = self.interest_rate / 100  # Convert percentage to decimal
        n = 4  # Quarterly compounding
        # Compound interest formula: A = P * (1 + r/n)^(n*t)
        return self.principal * ((1 + rate / n) ** (n * years))

    @property
    def interest_earned(self) -> float:
        """Calculate total interest to be earned."""
        return self.maturity_value - self.principal

    @property
    def days_to_maturity(self) -> int:
        """Days remaining until maturity."""
        from datetime import date
        if self.is_matured:
            return 0
        remaining = (self.maturity_date - date.today()).days
        return max(0, remaining)

    @property
    def is_past_maturity(self) -> bool:
        """Check if FD has passed maturity date."""
        from datetime import date
        return date.today() > self.maturity_date

    def __repr__(self) -> str:
        return f'<FixedDeposit {self.principal} @ {self.interest_rate}%>'


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False, default='Monthly Budget')
    expected_income = db.Column(db.Float, default=0.0)
    expected_savings = db.Column(db.Float, default=0.0)  # Target savings per month
    expected_investments = db.Column(db.Float, default=0.0)  # Target investments per month
    currency = db.Column(db.String(3), default='USD')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to budget items (category-wise budgets)
    items = db.relationship('BudgetItem', backref='budget', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_expected_expenses(self):
        """Sum of all budget item amounts"""
        return sum(item.amount for item in self.items.all())

    @property
    def expected_balance(self):
        """Income - Expenses - Savings - Investments"""
        return self.expected_income - self.total_expected_expenses - self.expected_savings - self.expected_investments

    def __repr__(self):
        return f'<Budget {self.name}>'


class BudgetItem(db.Model):
    __tablename__ = 'budget_items'

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Expected expense amount for this category
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BudgetItem {self.category}: {self.amount}>'


class BudgetAccountGoal(db.Model):
    __tablename__ = 'budget_account_goals'

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    monthly_goal = db.Column(db.Float, nullable=False)  # Expected monthly contribution
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    budget = db.relationship('Budget', backref=db.backref('account_goals', lazy='dynamic', cascade='all, delete-orphan'))
    account = db.relationship('Account', backref=db.backref('budget_goals', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<BudgetAccountGoal {self.account_id}: {self.monthly_goal}>'
