import os
import threading
import time
from datetime import datetime, date
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, extract
from config import Config
from models import db, User, Account, Transaction, Category, Budget, BudgetItem, BudgetAccountGoal, FixedDeposit
from forms import LoginForm, SignupForm, AccountForm, TransactionForm, TransferForm, UpdateBalanceForm, EditAccountForm, BudgetForm, BudgetItemForm, FixedDepositForm, EditFixedDepositForm
from currency import get_exchange_rate, convert_currency, format_currency, get_currency_symbol

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create database tables and initialize default categories
with app.app_context():
    db.create_all()
    Category.init_default_categories()


# Make currency functions available in templates
@app.context_processor
def utility_processor():
    def display_value(amount, from_currency):
        """Convert amount to user's display currency and format it"""
        if not current_user.is_authenticated:
            symbol = '$' if from_currency == 'USD' else '₹'
            return f"{symbol}{abs(amount):,.2f}"

        display_curr = current_user.display_currency or 'USD'
        if from_currency != display_curr:
            amount = convert_currency(amount, from_currency, display_curr)

        symbol = '$' if display_curr == 'USD' else '₹'
        return f"{symbol}{abs(amount):,.2f}"

    def get_display_currency():
        """Get user's display currency preference"""
        if current_user.is_authenticated:
            return current_user.display_currency or 'USD'
        return 'USD'

    def get_display_symbol():
        """Get symbol for user's display currency"""
        if current_user.is_authenticated:
            return '$' if (current_user.display_currency or 'USD') == 'USD' else '₹'
        return '$'

    def to_display_currency(amount, from_currency):
        """Convert amount to user's display currency (returns number, not formatted)"""
        if not current_user.is_authenticated:
            return amount
        display_curr = current_user.display_currency or 'USD'
        if from_currency != display_curr:
            return convert_currency(amount, from_currency, display_curr)
        return amount

    return {
        'get_exchange_rate': get_exchange_rate,
        'convert_currency': convert_currency,
        'format_currency': format_currency,
        'get_currency_symbol': get_currency_symbol,
        'display_value': display_value,
        'get_display_currency': get_display_currency,
        'get_display_symbol': get_display_symbol,
        'to_display_currency': to_display_currency
    }


# ============ Authentication Routes ============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page if next_page else url_for('dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/toggle-currency')
@login_required
def toggle_currency():
    """Toggle between USD and INR display preference"""
    if current_user.display_currency == 'USD':
        current_user.display_currency = 'INR'
    else:
        current_user.display_currency = 'USD'
    db.session.commit()

    # Redirect back to the page they came from
    return redirect(request.referrer or url_for('dashboard'))


# ============ Dashboard ============

@app.route('/dashboard')
@login_required
def dashboard():
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    # Calculate total balance in USD (converting INR accounts)
    # Use total_value to include fixed deposits
    total_balance_usd = 0
    for account in accounts:
        if account.currency == 'INR':
            total_balance_usd += convert_currency(account.total_value, 'INR', 'USD')
        else:
            total_balance_usd += account.total_value

    # Get recent transactions across all accounts
    account_ids = [a.id for a in accounts]
    recent_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids)
    ).order_by(Transaction.transaction_date.desc()).limit(10).all()

    # Calculate this month's personal expenses (using my_share when available)
    # Convert INR amounts to USD for consistent display
    today = date.today()
    account_currency_map = {a.id: a.currency for a in accounts}
    monthly_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        Transaction.amount < 0,
        Transaction.category != 'transfer',
        extract('month', Transaction.transaction_date) == today.month,
        extract('year', Transaction.transaction_date) == today.year
    ).all()
    monthly_expenses = 0
    for t in monthly_transactions:
        amount = t.personal_amount
        if amount >= 0:
            continue
        if account_currency_map.get(t.account_id, 'USD') == 'INR':
            amount = convert_currency(amount, 'INR', 'USD')
        monthly_expenses += amount

    return render_template('dashboard.html',
                           accounts=accounts,
                           total_balance=total_balance_usd,
                           recent_transactions=recent_transactions,
                           monthly_expenses=abs(monthly_expenses))


# ============ Account Routes ============

@app.route('/accounts')
@login_required
def accounts():
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.display_order, Account.created_at).all()
    return render_template('accounts.html', accounts=accounts)


@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_account():
    form = AccountForm()
    if form.validate_on_submit():
        account = Account(
            user_id=current_user.id,
            name=form.name.data,
            account_type=form.account_type.data,
            currency=form.currency.data,
            initial_balance=form.initial_balance.data
        )
        db.session.add(account)
        db.session.commit()
        flash(f'Account "{account.name}" created successfully!', 'success')
        return redirect(url_for('accounts'))

    return render_template('add_account.html', form=form)


@app.route('/accounts/<int:account_id>')
@login_required
def account_detail(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    transactions = Transaction.query.filter_by(account_id=account_id).order_by(
        Transaction.transaction_date.desc()
    ).all()
    return render_template('account_detail.html', account=account, transactions=transactions)


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    db.session.delete(account)
    db.session.commit()
    flash(f'Account "{account.name}" deleted successfully!', 'success')
    return redirect(url_for('accounts'))


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    form = EditAccountForm()

    if form.validate_on_submit():
        account.name = form.name.data
        account.account_type = form.account_type.data
        account.currency = form.currency.data
        account.initial_balance = form.initial_balance.data
        db.session.commit()
        flash(f'Account "{account.name}" updated successfully!', 'success')
        return redirect(url_for('accounts'))

    # Pre-fill form with current values
    if request.method == 'GET':
        form.name.data = account.name
        form.account_type.data = account.account_type
        form.currency.data = account.currency
        form.initial_balance.data = account.initial_balance

    return render_template('edit_account.html', form=form, account=account)


@app.route('/accounts/reorder', methods=['POST'])
@login_required
def reorder_accounts():
    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    order = data['order']  # List of account IDs in new order

    for index, account_id in enumerate(order):
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        if account:
            account.display_order = index

    db.session.commit()
    return jsonify({'success': True})


@app.route('/accounts/<int:account_id>/update-balance', methods=['GET', 'POST'])
@login_required
def update_balance(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    # Only allow updating balance for investment accounts
    if account.account_type != 'investment':
        flash('Balance can only be manually updated for investment accounts.', 'warning')
        return redirect(url_for('account_detail', account_id=account_id))

    form = UpdateBalanceForm()

    if form.validate_on_submit():
        new_balance = form.new_balance.data
        input_currency = form.input_currency.data

        # Convert to account's currency if different
        if input_currency != account.currency:
            new_balance = convert_currency(new_balance, input_currency, account.currency)

        # Calculate sum of all transactions
        transactions_sum = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.account_id == account_id
        ).scalar()

        # New initial_balance = new_balance - transactions_sum
        account.initial_balance = new_balance - transactions_sum
        db.session.commit()

        flash(f'Balance for "{account.name}" updated to {account.currency_symbol}{new_balance:,.2f}!', 'success')
        return redirect(url_for('account_detail', account_id=account_id))

    # Pre-fill with current balance and account's currency
    if request.method == 'GET':
        form.new_balance.data = account.current_balance
        form.input_currency.data = account.currency

    return render_template('update_balance.html', form=form, account=account)


# ============ Transaction Routes ============

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()

    # Populate account choices
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()
    form.account_id.choices = [(a.id, f"{a.name} ({a.account_type})") for a in user_accounts]

    # Populate category choices
    categories = Category.get_user_categories(current_user.id)
    form.category.choices = [('__new__', '+ Add New Category')] + [
        (cat.name, cat.name.replace('_', ' ').title()) for cat in categories
    ]

    if not user_accounts:
        flash('Please create an account first before adding transactions.', 'warning')
        return redirect(url_for('add_account'))

    # Pre-select account if provided via query parameter
    if request.method == 'GET' and request.args.get('account_id'):
        try:
            account_id = int(request.args.get('account_id'))
            # Verify account belongs to user
            if any(a.id == account_id for a in user_accounts):
                form.account_id.data = account_id
        except (ValueError, TypeError):
            pass

    if form.validate_on_submit():
        # Verify the account belongs to the user
        account = Account.query.filter_by(id=form.account_id.data, user_id=current_user.id).first()
        if not account:
            flash('Invalid account selected.', 'danger')
            return redirect(url_for('add_transaction'))

        # Handle new category creation
        category_name = form.category.data
        if category_name == '__new__':
            new_cat_name = form.new_category.data.strip().lower().replace(' ', '_')
            if not new_cat_name:
                flash('Please enter a name for the new category.', 'danger')
                return redirect(url_for('add_transaction'))

            # Check if category already exists
            existing = Category.query.filter(
                ((Category.user_id == current_user.id) | (Category.user_id == None)),
                Category.name == new_cat_name
            ).first()

            if not existing:
                new_category = Category(user_id=current_user.id, name=new_cat_name)
                db.session.add(new_category)
                db.session.commit()
                flash(f'Category "{new_cat_name.replace("_", " ").title()}" created!', 'info')

            category_name = new_cat_name

        # Determine amount sign based on transaction type
        amount = abs(form.amount.data)
        if form.transaction_type.data == 'expense':
            amount = -amount

        # Handle my_share - if provided, apply same sign as amount
        my_share = None
        if form.my_share.data is not None and form.my_share.data != 0:
            my_share = abs(form.my_share.data)
            if form.transaction_type.data == 'expense':
                my_share = -my_share

        transaction = Transaction(
            account_id=form.account_id.data,
            amount=amount,
            my_share=my_share,
            description=form.description.data,
            category=category_name,
            transaction_date=form.transaction_date.data
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('account_detail', account_id=form.account_id.data))

    # Set default date to today
    if request.method == 'GET':
        form.transaction_date.data = date.today()

    # Build account currency map for JavaScript
    account_currencies = {a.id: {'currency': a.currency, 'symbol': Account.CURRENCIES.get(a.currency, {}).get('symbol', '$')} for a in user_accounts}

    return render_template('add_transaction.html', form=form, account_currencies=account_currencies)


@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Verify the transaction belongs to the user
    account = Account.query.filter_by(id=transaction.account_id, user_id=current_user.id).first()
    if not account:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('dashboard'))

    form = TransactionForm()

    # Populate account choices
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()
    form.account_id.choices = [(a.id, f"{a.name} ({a.account_type})") for a in user_accounts]

    # Populate category choices
    categories = Category.get_user_categories(current_user.id)
    form.category.choices = [('__new__', '+ Add New Category')] + [
        (cat.name, cat.name.replace('_', ' ').title()) for cat in categories
    ]

    if form.validate_on_submit():
        # Verify the selected account belongs to the user
        new_account = Account.query.filter_by(id=form.account_id.data, user_id=current_user.id).first()
        if not new_account:
            flash('Invalid account selected.', 'danger')
            return redirect(url_for('edit_transaction', transaction_id=transaction_id))

        # Handle new category creation
        category_name = form.category.data
        if category_name == '__new__':
            new_cat_name = form.new_category.data.strip().lower().replace(' ', '_')
            if not new_cat_name:
                flash('Please enter a name for the new category.', 'danger')
                return redirect(url_for('edit_transaction', transaction_id=transaction_id))

            existing = Category.query.filter(
                ((Category.user_id == current_user.id) | (Category.user_id == None)),
                Category.name == new_cat_name
            ).first()

            if not existing:
                new_category = Category(user_id=current_user.id, name=new_cat_name)
                db.session.add(new_category)
                db.session.commit()
                flash(f'Category "{new_cat_name.replace("_", " ").title()}" created!', 'info')

            category_name = new_cat_name

        # Determine amount sign based on transaction type
        amount = abs(form.amount.data)
        if form.transaction_type.data == 'expense':
            amount = -amount

        # Handle my_share
        my_share = None
        if form.my_share.data is not None and form.my_share.data != 0:
            my_share = abs(form.my_share.data)
            if form.transaction_type.data == 'expense':
                my_share = -my_share

        # Update transaction
        transaction.account_id = form.account_id.data
        transaction.amount = amount
        transaction.my_share = my_share
        transaction.description = form.description.data
        transaction.category = category_name
        transaction.transaction_date = form.transaction_date.data

        db.session.commit()
        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('account_detail', account_id=form.account_id.data))

    # Pre-fill form with current values
    if request.method == 'GET':
        form.account_id.data = transaction.account_id
        form.transaction_type.data = 'expense' if transaction.amount < 0 else 'income'
        form.amount.data = abs(transaction.amount)
        form.my_share.data = abs(transaction.my_share) if transaction.my_share else None
        form.description.data = transaction.description
        form.category.data = transaction.category
        form.transaction_date.data = transaction.transaction_date

    # Build account currency map for JavaScript
    account_currencies = {a.id: {'currency': a.currency, 'symbol': Account.CURRENCIES.get(a.currency, {}).get('symbol', '$')} for a in user_accounts}

    return render_template('edit_transaction.html', form=form, transaction=transaction, account_currencies=account_currencies)


@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Verify the transaction belongs to the user
    account = Account.query.filter_by(id=transaction.account_id, user_id=current_user.id).first()
    if not account:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('dashboard'))

    account_id = transaction.account_id
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('account_detail', account_id=account_id))


# ============ Transfers ============

@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    form = TransferForm()

    # Populate account choices
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_choices = [(a.id, f"{a.name} ({a.account_type.replace('_', ' ').title()}) - ${a.current_balance:.2f}") for a in user_accounts]
    form.from_account_id.choices = account_choices
    form.to_account_id.choices = account_choices

    if len(user_accounts) < 2:
        flash('You need at least 2 accounts to make a transfer.', 'warning')
        return redirect(url_for('add_account'))

    if form.validate_on_submit():
        from_account_id = form.from_account_id.data
        to_account_id = form.to_account_id.data
        amount = abs(form.amount.data)
        description = form.description.data or 'Transfer'
        transfer_date = form.transfer_date.data

        # Validate accounts
        if from_account_id == to_account_id:
            flash('Cannot transfer to the same account.', 'danger')
            return redirect(url_for('transfer'))

        from_account = Account.query.filter_by(id=from_account_id, user_id=current_user.id).first()
        to_account = Account.query.filter_by(id=to_account_id, user_id=current_user.id).first()

        if not from_account or not to_account:
            flash('Invalid account selected.', 'danger')
            return redirect(url_for('transfer'))

        # Create outgoing transaction (negative amount from source)
        outgoing = Transaction(
            account_id=from_account_id,
            amount=-amount,
            description=f"Transfer to {to_account.name}: {description}",
            category='transfer',
            transaction_date=transfer_date
        )

        # Create incoming transaction (positive amount to destination)
        incoming = Transaction(
            account_id=to_account_id,
            amount=amount,
            description=f"Transfer from {from_account.name}: {description}",
            category='transfer',
            transaction_date=transfer_date
        )

        db.session.add(outgoing)
        db.session.add(incoming)
        db.session.commit()

        flash(f'Successfully transferred ${amount:.2f} from {from_account.name} to {to_account.name}!', 'success')
        return redirect(url_for('dashboard'))

    # Set default date to today
    if request.method == 'GET':
        form.transfer_date.data = date.today()

    return render_template('transfer.html', form=form)


# ============ Credit Cards ============

@app.route('/credit-cards')
@login_required
def credit_cards():
    cards = Account.query.filter_by(
        user_id=current_user.id,
        account_type='credit_card'
    ).all()

    total_balance = sum(card.current_balance for card in cards)

    return render_template('credit_cards.html',
                           cards=cards,
                           total_balance=total_balance)


# ============ Reports ============

@app.route('/reports/monthly')
@login_required
def monthly_report():
    # Get month/year from query params or default to current month
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_ids = [a.id for a in accounts]

    # Build account currency map for conversions
    account_currency_map = {a.id: a.currency for a in accounts}

    # Get all transactions for the month
    monthly_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        extract('month', Transaction.transaction_date) == month,
        extract('year', Transaction.transaction_date) == year
    ).all()

    # Calculate personal expenses by category (using my_share when available)
    # Convert INR amounts to USD for consistent display
    expenses_by_category = {}
    total_income = 0
    total_expenses = 0

    for t in monthly_transactions:
        personal = t.personal_amount
        # Convert INR amounts to USD
        account_currency = account_currency_map.get(t.account_id, 'USD')
        if account_currency == 'INR':
            personal = convert_currency(personal, 'INR', 'USD')

        if personal > 0 and t.category != 'transfer':
            total_income += personal
        elif personal < 0 and t.category != 'transfer':
            total_expenses += personal
            cat = t.category
            if cat not in expenses_by_category:
                expenses_by_category[cat] = 0
            expenses_by_category[cat] += abs(personal)

    # Get user's budget for comparison
    user_budget = Budget.query.filter_by(user_id=current_user.id, is_active=True).first()

    # Build budget comparison data
    budget_items = {}
    if user_budget:
        for item in user_budget.items:
            budget_items[item.category] = item.amount

    # Calculate savings and investment contributions for the month
    savings_accounts = Account.query.filter_by(user_id=current_user.id, account_type='savings').all()
    investment_accounts = Account.query.filter_by(user_id=current_user.id, account_type='investment').all()

    savings_account_ids = [a.id for a in savings_accounts]
    investment_account_ids = [a.id for a in investment_accounts]

    savings_contributions = 0
    if savings_account_ids:
        savings_transfers = Transaction.query.filter(
            Transaction.account_id.in_(savings_account_ids),
            Transaction.amount > 0,
            Transaction.category == 'transfer',
            extract('month', Transaction.transaction_date) == month,
            extract('year', Transaction.transaction_date) == year
        ).all()
        for t in savings_transfers:
            amount = t.amount
            if account_currency_map.get(t.account_id, 'USD') == 'INR':
                amount = convert_currency(amount, 'INR', 'USD')
            savings_contributions += amount

    investment_contributions = 0
    if investment_account_ids:
        investment_transfers = Transaction.query.filter(
            Transaction.account_id.in_(investment_account_ids),
            Transaction.amount > 0,
            Transaction.category == 'transfer',
            extract('month', Transaction.transaction_date) == month,
            extract('year', Transaction.transaction_date) == year
        ).all()
        for t in investment_transfers:
            amount = t.amount
            if account_currency_map.get(t.account_id, 'USD') == 'INR':
                amount = convert_currency(amount, 'INR', 'USD')
            investment_contributions += amount

    # Format expenses for display with budget comparison
    expenses_data = []
    for cat, amount in expenses_by_category.items():
        budgeted = budget_items.get(cat, 0)
        expenses_data.append({
            'category': cat.replace('_', ' ').title(),
            'category_key': cat,
            'amount': amount,
            'budgeted': budgeted,
            'difference': budgeted - amount if budgeted > 0 else None
        })
    expenses_data.sort(key=lambda x: x['amount'], reverse=True)

    return render_template('monthly_report.html',
                           expenses=expenses_data,
                           total_income=total_income,
                           total_expenses=abs(total_expenses),
                           net=total_income + total_expenses,
                           year=year,
                           month=month,
                           month_name=date(year, month, 1).strftime('%B'),
                           budget=user_budget,
                           savings_contributions=savings_contributions,
                           investment_contributions=investment_contributions)


@app.route('/reports/monthly/category-transactions')
@login_required
def monthly_category_transactions() -> 'flask.Response':
    """Return transactions for a specific category in a given month as JSON."""
    category = request.args.get('category', '')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_ids = [a.id for a in accounts]
    account_map = {a.id: a for a in accounts}
    account_currency_map = {a.id: a.currency for a in accounts}

    transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        Transaction.category == category,
        extract('month', Transaction.transaction_date) == month,
        extract('year', Transaction.transaction_date) == year
    ).order_by(Transaction.transaction_date.desc()).all()

    result = []
    for t in transactions:
        personal = t.personal_amount
        account_currency = account_currency_map.get(t.account_id, 'USD')
        amount_usd = convert_currency(abs(personal), account_currency, 'USD') if account_currency == 'INR' else abs(personal)
        result.append({
            'date': t.transaction_date.strftime('%b %d, %Y'),
            'description': t.description,
            'account': account_map[t.account_id].name,
            'amount': amount_usd,
        })

    return jsonify(result)


@app.route('/reports/monthly/summary-transactions')
@login_required
def monthly_summary_transactions() -> 'flask.Response':
    """Return income or expense transactions for a given month as JSON."""
    txn_type = request.args.get('type', '')  # 'income' or 'expenses'
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if txn_type not in ('income', 'expenses'):
        return jsonify([])

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_ids = [a.id for a in accounts]
    account_map = {a.id: a for a in accounts}
    account_currency_map = {a.id: a.currency for a in accounts}

    monthly_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        Transaction.category != 'transfer',
        extract('month', Transaction.transaction_date) == month,
        extract('year', Transaction.transaction_date) == year
    ).order_by(Transaction.transaction_date.desc()).all()

    result = []
    for t in monthly_transactions:
        personal = t.personal_amount
        account_currency = account_currency_map.get(t.account_id, 'USD')
        amount_usd = convert_currency(abs(personal), account_currency, 'USD') if account_currency == 'INR' else abs(personal)

        if txn_type == 'income' and personal > 0:
            result.append({
                'date': t.transaction_date.strftime('%b %d, %Y'),
                'description': t.description,
                'account': account_map[t.account_id].name,
                'category': t.category.replace('_', ' ').title(),
                'amount': amount_usd,
            })
        elif txn_type == 'expenses' and personal < 0:
            result.append({
                'date': t.transaction_date.strftime('%b %d, %Y'),
                'description': t.description,
                'account': account_map[t.account_id].name,
                'category': t.category.replace('_', ' ').title(),
                'amount': amount_usd,
            })

    return jsonify(result)


@app.route('/reports/monthly/contribution-transactions')
@login_required
def monthly_contribution_transactions() -> 'flask.Response':
    """Return savings or investment transfer transactions for a given month as JSON."""
    account_type = request.args.get('type', '')  # 'savings' or 'investment'
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if account_type not in ('savings', 'investment'):
        return jsonify([])

    accounts = Account.query.filter_by(user_id=current_user.id, account_type=account_type).all()
    account_ids = [a.id for a in accounts]
    account_map = {a.id: a for a in accounts}
    account_currency_map = {a.id: a.currency for a in accounts}

    transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        Transaction.amount > 0,
        Transaction.category == 'transfer',
        extract('month', Transaction.transaction_date) == month,
        extract('year', Transaction.transaction_date) == year
    ).order_by(Transaction.transaction_date.desc()).all()

    result = []
    for t in transactions:
        account_currency = account_currency_map.get(t.account_id, 'USD')
        amount_usd = convert_currency(t.amount, account_currency, 'USD') if account_currency == 'INR' else t.amount
        result.append({
            'date': t.transaction_date.strftime('%b %d, %Y'),
            'description': t.description,
            'account': account_map[t.account_id].name,
            'amount': amount_usd,
        })

    return jsonify(result)


# ============ Currency Summary ============

@app.route('/currency-summary')
@login_required
def currency_summary():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    exchange_rate = get_exchange_rate()

    # Group accounts by currency
    usd_accounts = [a for a in accounts if a.currency == 'USD']
    inr_accounts = [a for a in accounts if a.currency == 'INR']

    # Calculate totals
    # Use total_value to include fixed deposits
    usd_total = sum(a.total_value for a in usd_accounts)
    inr_total = sum(a.total_value for a in inr_accounts)

    # Convert to common currency for total net worth
    usd_total_in_inr = convert_currency(usd_total, 'USD', 'INR')
    inr_total_in_usd = convert_currency(inr_total, 'INR', 'USD')

    total_in_usd = usd_total + inr_total_in_usd
    total_in_inr = usd_total_in_inr + inr_total

    return render_template('currency_summary.html',
                           usd_accounts=usd_accounts,
                           inr_accounts=inr_accounts,
                           usd_total=usd_total,
                           inr_total=inr_total,
                           usd_total_in_inr=usd_total_in_inr,
                           inr_total_in_usd=inr_total_in_usd,
                           total_in_usd=total_in_usd,
                           total_in_inr=total_in_inr,
                           exchange_rate=exchange_rate)


# ============ Net Worth ============

@app.route('/net-worth')
@login_required
def net_worth():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    exchange_rate = get_exchange_rate()

    # Group accounts by type
    checking_accounts = [a for a in accounts if a.account_type == 'checking']
    savings_accounts = [a for a in accounts if a.account_type == 'savings']
    credit_cards = [a for a in accounts if a.account_type == 'credit_card']
    loans = [a for a in accounts if a.account_type == 'loan']
    investments = [a for a in accounts if a.account_type == 'investment']

    # Helper to convert balance to USD (includes fixed deposits)
    def to_usd(account):
        balance = account.total_value
        if account.currency == 'INR':
            return convert_currency(balance, 'INR', 'USD')
        return balance

    # Calculate totals in USD
    checking_total = sum(to_usd(a) for a in checking_accounts)
    savings_total = sum(to_usd(a) for a in savings_accounts)
    credit_card_total = sum(to_usd(a) for a in credit_cards)
    loan_total = sum(to_usd(a) for a in loans)
    investment_total = sum(to_usd(a) for a in investments)

    # Assets = positive balances (checking, savings, investments)
    total_assets = checking_total + savings_total + investment_total

    # Liabilities = negative balances (credit cards, loans - typically negative)
    total_liabilities = abs(credit_card_total) + abs(loan_total)

    # Net worth = Assets - Liabilities (but since loans/cc are already negative, we add them)
    net_worth_usd = checking_total + savings_total + investment_total + credit_card_total + loan_total
    net_worth_inr = convert_currency(net_worth_usd, 'USD', 'INR')

    return render_template('net_worth.html',
                           checking_accounts=checking_accounts,
                           savings_accounts=savings_accounts,
                           credit_cards=credit_cards,
                           loans=loans,
                           investments=investments,
                           checking_total=checking_total,
                           savings_total=savings_total,
                           credit_card_total=credit_card_total,
                           loan_total=loan_total,
                           investment_total=investment_total,
                           total_assets=total_assets,
                           total_liabilities=total_liabilities,
                           net_worth_usd=net_worth_usd,
                           net_worth_inr=net_worth_inr,
                           exchange_rate=exchange_rate,
                           to_usd=to_usd)


# ============ Budget ============

@app.route('/budget')
@login_required
def budget():
    # Get user's active budget or None
    user_budget = Budget.query.filter_by(user_id=current_user.id, is_active=True).first()

    # Get categories for adding budget items
    categories = Category.get_user_categories(current_user.id)
    category_choices = [(cat.name, cat.name.replace('_', ' ').title()) for cat in categories]

    # Calculate actual spending for current month
    today = date.today()
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_ids = [a.id for a in accounts]

    # Build account currency map for conversions
    account_currency_map = {a.id: a.currency for a in accounts}

    monthly_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids),
        extract('month', Transaction.transaction_date) == today.month,
        extract('year', Transaction.transaction_date) == today.year
    ).all()

    # Calculate actual income and expenses by category (converting INR to USD)
    actual_income = 0
    actual_expenses_by_category = {}

    for t in monthly_transactions:
        personal = t.personal_amount
        # Convert INR amounts to USD for consistent display
        account_currency = account_currency_map.get(t.account_id, 'USD')
        if account_currency == 'INR':
            personal = convert_currency(personal, 'INR', 'USD')

        if personal > 0 and t.category != 'transfer':
            actual_income += personal
        elif personal < 0 and t.category != 'transfer':
            cat = t.category
            if cat not in actual_expenses_by_category:
                actual_expenses_by_category[cat] = 0
            actual_expenses_by_category[cat] += abs(personal)

    total_actual_expenses = sum(actual_expenses_by_category.values())

    # Calculate savings/investment contributions this month
    savings_accounts = Account.query.filter_by(user_id=current_user.id, account_type='savings').all()
    investment_accounts = Account.query.filter_by(user_id=current_user.id, account_type='investment').all()

    savings_account_ids = [a.id for a in savings_accounts]
    investment_account_ids = [a.id for a in investment_accounts]

    # Savings contributions: incoming transfers to savings accounts
    savings_contributions = 0
    if savings_account_ids:
        savings_transfers = Transaction.query.filter(
            Transaction.account_id.in_(savings_account_ids),
            Transaction.amount > 0,
            Transaction.category == 'transfer',
            extract('month', Transaction.transaction_date) == today.month,
            extract('year', Transaction.transaction_date) == today.year
        ).all()
        for t in savings_transfers:
            amount = t.amount
            if account_currency_map.get(t.account_id, 'USD') == 'INR':
                amount = convert_currency(amount, 'INR', 'USD')
            savings_contributions += amount

    # Investment contributions: incoming transfers to investment accounts
    investment_contributions = 0
    if investment_account_ids:
        investment_transfers = Transaction.query.filter(
            Transaction.account_id.in_(investment_account_ids),
            Transaction.amount > 0,
            Transaction.category == 'transfer',
            extract('month', Transaction.transaction_date) == today.month,
            extract('year', Transaction.transaction_date) == today.year
        ).all()
        for t in investment_transfers:
            amount = t.amount
            if account_currency_map.get(t.account_id, 'USD') == 'INR':
                amount = convert_currency(amount, 'INR', 'USD')
            investment_contributions += amount

    # Calculate per-account contributions this month
    account_contributions = {}
    all_target_accounts = savings_accounts + investment_accounts
    for account in all_target_accounts:
        transfers = Transaction.query.filter(
            Transaction.account_id == account.id,
            Transaction.amount > 0,
            Transaction.category == 'transfer',
            extract('month', Transaction.transaction_date) == today.month,
            extract('year', Transaction.transaction_date) == today.year
        ).all()
        total = 0
        for t in transfers:
            amount = t.amount
            if account.currency == 'INR':
                amount = convert_currency(amount, 'INR', 'USD')
            total += amount
        account_contributions[account.id] = total

    # Get account goals if budget exists
    account_goals = {}
    total_investment_goal = 0
    total_savings_goal = 0
    if user_budget:
        for goal in user_budget.account_goals:
            account_goals[goal.account_id] = goal
            # Convert goal to USD for consistent summing
            goal_amount = goal.monthly_goal
            if goal.account.currency == 'INR':
                goal_amount = convert_currency(goal_amount, 'INR', 'USD')
            if goal.account.account_type == 'investment':
                total_investment_goal += goal_amount
            elif goal.account.account_type == 'savings':
                total_savings_goal += goal_amount

    # Calculate effective goals in USD for accurate percentage calculations
    if user_budget:
        if total_savings_goal > 0:
            effective_savings_usd = total_savings_goal
        else:
            effective_savings_usd = user_budget.expected_savings
            if user_budget.currency == 'INR':
                effective_savings_usd = convert_currency(effective_savings_usd, 'INR', 'USD')

        if total_investment_goal > 0:
            effective_investments_usd = total_investment_goal
        else:
            effective_investments_usd = user_budget.expected_investments
            if user_budget.currency == 'INR':
                effective_investments_usd = convert_currency(effective_investments_usd, 'INR', 'USD')
    else:
        effective_savings_usd = 0
        effective_investments_usd = 0

    return render_template('budget.html',
                          budget=user_budget,
                          categories=category_choices,
                          actual_income=actual_income,
                          actual_expenses=actual_expenses_by_category,
                          total_actual_expenses=total_actual_expenses,
                          savings_contributions=savings_contributions,
                          investment_contributions=investment_contributions,
                          savings_accounts=savings_accounts,
                          investment_accounts=investment_accounts,
                          account_contributions=account_contributions,
                          account_goals=account_goals,
                          total_investment_goal=total_investment_goal,
                          total_savings_goal=total_savings_goal,
                          effective_savings_usd=effective_savings_usd,
                          effective_investments_usd=effective_investments_usd,
                          month_name=today.strftime('%B'),
                          year=today.year)


@app.route('/budget/edit', methods=['GET', 'POST'])
@login_required
def edit_budget():
    # Get existing budget or create new one
    user_budget = Budget.query.filter_by(user_id=current_user.id, is_active=True).first()

    form = BudgetForm()

    if form.validate_on_submit():
        if user_budget:
            # Update existing budget
            user_budget.name = form.name.data
            user_budget.expected_income = form.expected_income.data
            user_budget.expected_savings = form.expected_savings.data
            user_budget.expected_investments = form.expected_investments.data
            user_budget.currency = form.currency.data
        else:
            # Create new budget
            user_budget = Budget(
                user_id=current_user.id,
                name=form.name.data,
                expected_income=form.expected_income.data,
                expected_savings=form.expected_savings.data,
                expected_investments=form.expected_investments.data,
                currency=form.currency.data
            )
            db.session.add(user_budget)

        db.session.commit()
        flash('Budget settings saved!', 'success')
        return redirect(url_for('budget'))

    # Pre-fill form with existing values
    if request.method == 'GET' and user_budget:
        form.name.data = user_budget.name
        form.expected_income.data = user_budget.expected_income
        form.expected_savings.data = user_budget.expected_savings
        form.expected_investments.data = user_budget.expected_investments
        form.currency.data = user_budget.currency

    return render_template('edit_budget.html', form=form, budget=user_budget)


@app.route('/budget/items/add', methods=['POST'])
@login_required
def add_budget_item():
    user_budget = Budget.query.filter_by(user_id=current_user.id, is_active=True).first()

    if not user_budget:
        flash('Please create a budget first.', 'warning')
        return redirect(url_for('edit_budget'))

    category = request.form.get('category')
    new_category = request.form.get('new_category', '').strip()
    amount = request.form.get('amount')

    # Handle new category creation
    if category == '__new__':
        if not new_category:
            flash('Please enter a name for the new category.', 'danger')
            return redirect(url_for('budget'))

        new_cat_name = new_category.lower().replace(' ', '_')

        # Check if category already exists
        existing_cat = Category.query.filter(
            ((Category.user_id == current_user.id) | (Category.user_id == None)),
            Category.name == new_cat_name
        ).first()

        if not existing_cat:
            new_category_obj = Category(user_id=current_user.id, name=new_cat_name)
            db.session.add(new_category_obj)
            db.session.commit()
            flash(f'Category "{new_cat_name.replace("_", " ").title()}" created!', 'info')

        category = new_cat_name

    if not category or not amount:
        flash('Please provide both category and amount.', 'danger')
        return redirect(url_for('budget'))

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        flash('Amount must be a positive number.', 'danger')
        return redirect(url_for('budget'))

    # Check if category already has a budget item
    existing = BudgetItem.query.filter_by(budget_id=user_budget.id, category=category).first()
    if existing:
        existing.amount = amount
        flash(f'Budget for {category.replace("_", " ").title()} updated!', 'success')
    else:
        item = BudgetItem(
            budget_id=user_budget.id,
            category=category,
            amount=amount
        )
        db.session.add(item)
        flash(f'Budget for {category.replace("_", " ").title()} added!', 'success')

    db.session.commit()
    return redirect(url_for('budget'))


@app.route('/budget/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_budget_item(item_id):
    item = BudgetItem.query.get_or_404(item_id)

    # Verify the item belongs to the user's budget
    if item.budget.user_id != current_user.id:
        flash('Budget item not found.', 'danger')
        return redirect(url_for('budget'))

    if request.method == 'POST':
        amount = request.form.get('amount')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            flash('Amount must be a positive number.', 'danger')
            return redirect(url_for('edit_budget_item', item_id=item_id))

        item.amount = amount
        db.session.commit()
        flash(f'Budget for {item.category.replace("_", " ").title()} updated!', 'success')
        return redirect(url_for('budget'))

    # Get categories for the form
    categories = Category.get_user_categories(current_user.id)
    category_choices = [(cat.name, cat.name.replace('_', ' ').title()) for cat in categories]

    return render_template('edit_budget_item.html', item=item, categories=category_choices)


@app.route('/budget/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_budget_item(item_id):
    item = BudgetItem.query.get_or_404(item_id)

    # Verify the item belongs to the user's budget
    if item.budget.user_id != current_user.id:
        flash('Budget item not found.', 'danger')
        return redirect(url_for('budget'))

    category_name = item.category.replace('_', ' ').title()
    db.session.delete(item)
    db.session.commit()
    flash(f'Budget for {category_name} deleted.', 'success')
    return redirect(url_for('budget'))


@app.route('/budget/account-goals/add', methods=['POST'])
@login_required
def add_account_goal():
    user_budget = Budget.query.filter_by(user_id=current_user.id, is_active=True).first()

    if not user_budget:
        flash('Please create a budget first.', 'warning')
        return redirect(url_for('edit_budget'))

    account_id = request.form.get('account_id')
    monthly_goal = request.form.get('monthly_goal')

    if not account_id or not monthly_goal:
        flash('Please provide both account and monthly goal.', 'danger')
        return redirect(url_for('budget'))

    # Verify account belongs to user
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
    if not account:
        flash('Invalid account selected.', 'danger')
        return redirect(url_for('budget'))

    try:
        monthly_goal = float(monthly_goal)
        if monthly_goal <= 0:
            raise ValueError()
    except ValueError:
        flash('Monthly goal must be a positive number.', 'danger')
        return redirect(url_for('budget'))

    # Check if account already has a goal
    existing = BudgetAccountGoal.query.filter_by(budget_id=user_budget.id, account_id=account_id).first()
    if existing:
        existing.monthly_goal = monthly_goal
        flash(f'Goal for {account.name} updated!', 'success')
    else:
        goal = BudgetAccountGoal(
            budget_id=user_budget.id,
            account_id=int(account_id),
            monthly_goal=monthly_goal
        )
        db.session.add(goal)
        flash(f'Goal for {account.name} added!', 'success')

    db.session.commit()
    return redirect(url_for('budget'))


@app.route('/budget/account-goals/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account_goal(goal_id):
    goal = BudgetAccountGoal.query.get_or_404(goal_id)

    # Verify the goal belongs to the user's budget
    if goal.budget.user_id != current_user.id:
        flash('Goal not found.', 'danger')
        return redirect(url_for('budget'))

    if request.method == 'POST':
        monthly_goal = request.form.get('monthly_goal')
        try:
            monthly_goal = float(monthly_goal)
            if monthly_goal <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            flash('Monthly goal must be a positive number.', 'danger')
            return redirect(url_for('edit_account_goal', goal_id=goal_id))

        goal.monthly_goal = monthly_goal
        db.session.commit()
        flash(f'Goal for {goal.account.name} updated!', 'success')
        return redirect(url_for('budget'))

    return render_template('edit_account_goal.html', goal=goal)


@app.route('/budget/account-goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_account_goal(goal_id):
    goal = BudgetAccountGoal.query.get_or_404(goal_id)

    # Verify the goal belongs to the user's budget
    if goal.budget.user_id != current_user.id:
        flash('Goal not found.', 'danger')
        return redirect(url_for('budget'))

    account_name = goal.account.name
    db.session.delete(goal)
    db.session.commit()
    flash(f'Goal for {account_name} deleted.', 'success')
    return redirect(url_for('budget'))


# ============ Fixed Deposits ============

@app.route('/fixed-deposits')
@login_required
def fixed_deposits():
    """List all fixed deposits for the user."""
    inr_accounts = Account.query.filter_by(
        user_id=current_user.id,
        currency='INR'
    ).all()
    account_ids = [a.id for a in inr_accounts]

    active_fds = []
    matured_fds = []
    if account_ids:
        active_fds = FixedDeposit.query.filter(
            FixedDeposit.account_id.in_(account_ids),
            FixedDeposit.is_matured == False
        ).order_by(FixedDeposit.maturity_date).all()

        matured_fds = FixedDeposit.query.filter(
            FixedDeposit.account_id.in_(account_ids),
            FixedDeposit.is_matured == True
        ).order_by(FixedDeposit.maturity_date.desc()).limit(10).all()

    total_principal = sum(fd.principal for fd in active_fds)
    total_maturity = sum(fd.maturity_value for fd in active_fds)
    total_interest = total_maturity - total_principal

    return render_template('fixed_deposits.html',
                           active_fds=active_fds,
                           matured_fds=matured_fds,
                           total_principal=total_principal,
                           total_maturity=total_maturity,
                           total_interest=total_interest,
                           inr_accounts=inr_accounts)


@app.route('/fixed-deposits/add', methods=['GET', 'POST'])
@login_required
def add_fixed_deposit():
    """Add a new fixed deposit."""
    form = FixedDepositForm()

    inr_accounts = Account.query.filter_by(
        user_id=current_user.id,
        currency='INR'
    ).all()
    form.account_id.choices = [(a.id, f"{a.name} ({a.account_type})") for a in inr_accounts]

    if not inr_accounts:
        flash('You need an INR account to add fixed deposits. Please create one first.', 'warning')
        return redirect(url_for('add_account'))

    if form.validate_on_submit():
        account = Account.query.filter_by(
            id=form.account_id.data,
            user_id=current_user.id,
            currency='INR'
        ).first()

        if not account:
            flash('Invalid account selected.', 'danger')
            return redirect(url_for('add_fixed_deposit'))

        fd = FixedDeposit(
            account_id=form.account_id.data,
            principal=form.principal.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            maturity_date=form.maturity_date.data,
            bank_name=form.bank_name.data or None,
            fd_number=form.fd_number.data or None
        )
        db.session.add(fd)

        # Create debit transaction if requested
        if form.debit_from_account.data:
            bank_info = f" ({form.bank_name.data})" if form.bank_name.data else ""
            fd_ref = f" - {form.fd_number.data}" if form.fd_number.data else ""
            transaction = Transaction(
                account_id=form.account_id.data,
                amount=-form.principal.data,  # Negative for debit
                description=f"Fixed Deposit{bank_info}{fd_ref}",
                category='transfer',
                transaction_date=form.start_date.data
            )
            db.session.add(transaction)

        db.session.commit()

        flash(f'Fixed Deposit of ₹{fd.principal:,.2f} added successfully!', 'success')
        return redirect(url_for('fixed_deposits'))

    if request.method == 'GET':
        form.start_date.data = date.today()

    return render_template('add_fixed_deposit.html', form=form)


@app.route('/fixed-deposits/<int:fd_id>')
@login_required
def fixed_deposit_detail(fd_id: int):
    """View fixed deposit details."""
    fd = FixedDeposit.query.get_or_404(fd_id)

    if fd.account.user_id != current_user.id:
        flash('Fixed deposit not found.', 'danger')
        return redirect(url_for('fixed_deposits'))

    return render_template('fixed_deposit_detail.html', fd=fd, today=date.today())


@app.route('/fixed-deposits/<int:fd_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_fixed_deposit(fd_id: int):
    """Edit a fixed deposit."""
    fd = FixedDeposit.query.get_or_404(fd_id)

    if fd.account.user_id != current_user.id:
        flash('Fixed deposit not found.', 'danger')
        return redirect(url_for('fixed_deposits'))

    form = EditFixedDepositForm()

    # Populate account choices with INR accounts
    inr_accounts = Account.query.filter_by(user_id=current_user.id, currency='INR').all()
    form.account_id.choices = [(a.id, a.name) for a in inr_accounts]

    if form.validate_on_submit():
        fd.account_id = form.account_id.data
        fd.bank_name = form.bank_name.data or None
        fd.fd_number = form.fd_number.data or None
        fd.is_matured = form.is_matured.data == '1'
        db.session.commit()

        flash('Fixed deposit updated successfully!', 'success')
        return redirect(url_for('fixed_deposits'))

    if request.method == 'GET':
        form.account_id.data = fd.account_id
        form.bank_name.data = fd.bank_name
        form.fd_number.data = fd.fd_number
        form.is_matured.data = '1' if fd.is_matured else '0'

    return render_template('edit_fixed_deposit.html', form=form, fd=fd)


@app.route('/fixed-deposits/<int:fd_id>/delete', methods=['POST'])
@login_required
def delete_fixed_deposit(fd_id: int):
    """Delete a fixed deposit."""
    fd = FixedDeposit.query.get_or_404(fd_id)

    if fd.account.user_id != current_user.id:
        flash('Fixed deposit not found.', 'danger')
        return redirect(url_for('fixed_deposits'))

    principal = fd.principal
    db.session.delete(fd)
    db.session.commit()

    flash(f'Fixed deposit of ₹{principal:,.2f} deleted.', 'success')
    return redirect(url_for('fixed_deposits'))


@app.route('/fixed-deposits/<int:fd_id>/mark-matured', methods=['POST'])
@login_required
def mark_fd_matured(fd_id: int):
    """Mark a fixed deposit as matured."""
    fd = FixedDeposit.query.get_or_404(fd_id)

    if fd.account.user_id != current_user.id:
        flash('Fixed deposit not found.', 'danger')
        return redirect(url_for('fixed_deposits'))

    fd.is_matured = True
    db.session.commit()

    flash(f'Fixed deposit marked as matured. Maturity value: ₹{fd.maturity_value:,.2f}', 'success')
    return redirect(url_for('fixed_deposits'))


# ============ Scheduled Backup ============

def _start_backup_scheduler() -> None:
    """Start a daemon thread that creates a backup every 24 hours.

    The thread wakes up hourly and checks whether 24 hours have elapsed since
    the last backup, so app restarts don't unnecessarily reset the schedule.
    """
    from backup import backup_database, get_last_backup_time

    BACKUP_INTERVAL_SECS = 24 * 60 * 60
    CHECK_INTERVAL_SECS = 60 * 60  # wake up every hour to check

    def _run() -> None:
        while True:
            time.sleep(CHECK_INTERVAL_SECS)
            try:
                last = get_last_backup_time()
                elapsed = (
                    (datetime.now() - last).total_seconds()
                    if last is not None
                    else BACKUP_INTERVAL_SECS + 1  # no backup yet → run now
                )
                if elapsed >= BACKUP_INTERVAL_SECS:
                    path = backup_database()
                    app.logger.info('Scheduled backup created: %s', path.name)
            except Exception as exc:
                app.logger.error('Scheduled backup failed: %s', exc)

    t = threading.Thread(target=_run, name='backup-scheduler', daemon=True)
    t.start()
    app.logger.info('Backup scheduler started (interval: 24 h, check: 1 h)')


# Avoid double-starting under Werkzeug's debug reloader
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    _start_backup_scheduler()


if __name__ == '__main__':
    app.run(debug=True)
