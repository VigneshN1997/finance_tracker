import requests
from datetime import datetime, timedelta

# Default exchange rate (fallback if API fails)
DEFAULT_EXCHANGE_RATE = 83.0  # 1 USD = 83 INR (approximate)

# Cache for exchange rate
_rate_cache = {
    'rate': DEFAULT_EXCHANGE_RATE,
    'last_updated': None
}


def get_exchange_rate():
    """
    Get current USD to INR exchange rate.
    Uses a free API with caching to avoid too many requests.
    Falls back to default rate if API fails.
    """
    global _rate_cache

    # Return cached rate if less than 1 hour old
    if _rate_cache['last_updated']:
        age = datetime.now() - _rate_cache['last_updated']
        if age < timedelta(hours=1):
            return _rate_cache['rate']

    try:
        # Using exchangerate-api.com free tier (no API key needed for USD base)
        response = requests.get(
            'https://api.exchangerate-api.com/v4/latest/USD',
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            rate = data.get('rates', {}).get('INR', DEFAULT_EXCHANGE_RATE)
            _rate_cache['rate'] = rate
            _rate_cache['last_updated'] = datetime.now()
            return rate
    except Exception:
        pass

    return _rate_cache['rate']


def convert_currency(amount, from_currency, to_currency):
    """
    Convert amount from one currency to another.
    Supports USD and INR.
    """
    if from_currency == to_currency:
        return amount

    rate = get_exchange_rate()

    if from_currency == 'USD' and to_currency == 'INR':
        return amount * rate
    elif from_currency == 'INR' and to_currency == 'USD':
        return amount / rate

    return amount


def format_currency(amount, currency='USD'):
    """Format amount with currency symbol."""
    symbols = {'USD': '$', 'INR': '₹'}
    symbol = symbols.get(currency, '$')

    if currency == 'INR':
        # Indian number formatting (lakhs, crores)
        return f"{symbol}{amount:,.2f}"
    else:
        return f"{symbol}{amount:,.2f}"


def get_currency_symbol(currency):
    """Get currency symbol."""
    symbols = {'USD': '$', 'INR': '₹'}
    return symbols.get(currency, '$')
