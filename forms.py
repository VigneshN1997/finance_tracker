from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, DateField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, InputRequired, Optional
from models import User, Account, Transaction, Budget, BudgetItem


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class SignupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class AccountForm(FlaskForm):
    name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_type = SelectField('Account Type', choices=[
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan (Car, Personal, etc.)'),
        ('investment', 'Investment (401k, Stocks, Insurance, etc.)')
    ], validators=[DataRequired()])
    currency = SelectField('Country / Currency', choices=[
        ('USD', 'USA - US Dollar ($)'),
        ('INR', 'India - Indian Rupee (₹)')
    ], validators=[DataRequired()])
    initial_balance = FloatField('Initial Balance', validators=[InputRequired()], default=0.0)


class TransactionForm(FlaskForm):
    account_id = SelectField('Account', coerce=int, validators=[DataRequired()])
    transaction_type = SelectField('Type', choices=[
        ('expense', 'Expense (money out)'),
        ('income', 'Income (money in)')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message='Amount must be positive')])
    my_share = FloatField('My Share', validators=[Optional()])  # Optional - if empty, full amount is used
    description = StringField('Description', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', validators=[DataRequired()])
    new_category = StringField('New Category', validators=[Length(max=50)])
    transaction_date = DateField('Date', validators=[DataRequired()])


class TransferForm(FlaskForm):
    from_account_id = SelectField('From Account', coerce=int, validators=[DataRequired()])
    to_account_id = SelectField('To Account', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message='Amount must be positive')])
    description = StringField('Description', validators=[Length(max=200)])
    transfer_date = DateField('Date', validators=[DataRequired()])


class UpdateBalanceForm(FlaskForm):
    new_balance = FloatField('New Balance', validators=[InputRequired()])
    input_currency = SelectField('Currency', choices=[
        ('USD', 'USD ($)'),
        ('INR', 'INR (₹)')
    ], validators=[DataRequired()])


class EditAccountForm(FlaskForm):
    name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_type = SelectField('Account Type', choices=[
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan (Car, Personal, etc.)'),
        ('investment', 'Investment (401k, Stocks, Insurance, etc.)')
    ], validators=[DataRequired()])
    currency = SelectField('Country / Currency', choices=[
        ('USD', 'USA - US Dollar ($)'),
        ('INR', 'India - Indian Rupee (₹)')
    ], validators=[DataRequired()])
    initial_balance = FloatField('Initial Balance', validators=[InputRequired()])


class BudgetForm(FlaskForm):
    name = StringField('Budget Name', validators=[DataRequired(), Length(max=100)], default='Monthly Budget')
    expected_income = FloatField('Expected Monthly Income', validators=[InputRequired()], default=0.0)
    expected_savings = FloatField('Savings Goal', validators=[InputRequired()], default=0.0)
    expected_investments = FloatField('Investment Goal', validators=[InputRequired()], default=0.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'USD ($)'),
        ('INR', 'INR (₹)')
    ], validators=[DataRequired()])


class BudgetItemForm(FlaskForm):
    category = SelectField('Category', validators=[DataRequired()])
    amount = FloatField('Budget Amount', validators=[DataRequired(), NumberRange(min=0.01)])


class FixedDepositForm(FlaskForm):
    account_id = SelectField('Account', coerce=int, validators=[DataRequired()])
    principal = FloatField('Principal Amount', validators=[
        DataRequired(),
        NumberRange(min=1000, message='Minimum FD amount is Rs. 1,000')
    ])
    interest_rate = FloatField('Interest Rate (% per annum)', validators=[
        DataRequired(),
        NumberRange(min=0.1, max=15, message='Interest rate must be between 0.1% and 15%')
    ])
    start_date = DateField('Start Date', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[Length(max=100)])
    fd_number = StringField('FD Number/Reference', validators=[Length(max=50)])
    debit_from_account = BooleanField('Debit principal from account', default=True)

    def validate_maturity_date(self, field: DateField) -> None:
        if field.data and self.start_date.data:
            if field.data <= self.start_date.data:
                raise ValidationError('Maturity date must be after start date.')
            if (field.data - self.start_date.data).days < 7:
                raise ValidationError('Minimum FD tenure is 7 days.')


class EditFixedDepositForm(FlaskForm):
    account_id = SelectField('Linked Account', coerce=int, validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[Length(max=100)])
    fd_number = StringField('FD Number/Reference', validators=[Length(max=50)])
    is_matured = SelectField('Status', choices=[
        ('0', 'Active'),
        ('1', 'Matured/Closed')
    ], validators=[DataRequired()])
