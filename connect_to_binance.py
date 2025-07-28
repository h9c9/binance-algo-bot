# connect_to_binance.py

import ccxt

def connect_binance():
    """
    Returns a Binance exchange object using CCXT.
    """
    exchange = ccxt.binance({
        'enableRateLimit': True,  # Avoid getting banned by Binance for too many requests
    })
    return exchange
