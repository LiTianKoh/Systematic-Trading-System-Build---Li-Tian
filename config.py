# =================== config.py ===================
"""
Configuration file containing constants and settings.
"""

# 20 highly liquid US tech stocks
TECH_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    'INTC', 'TSLA', 'META', 'AVGO', 'MU', 
    'AMD', 'PLTR', 'TXN', 'TSM', 'ARM', 
    'ADI', 'SLAB', 'ORCL', 'IBM', 'CRM'
]

# Screener parameters
MIN_PRICE = 3.00
MIN_VOLUME = 300000
SMA_PERIOD = 50

# Riser parameters
RISER_WINDOW = 63
RISER_MIN_INCREASE = 30

# Consolidation parameters
CONSOLIDATION_MIN_DAYS = 4
CONSOLIDATION_MAX_DAYS = 40
MAX_RETRACEMENT = 25
UPPER_BUFFER = 0.01  # 1% above consolidation high
LOWER_BUFFER = 0.01  # 1% below consolidation low

# Entry parameters
BREAKOUT_BUFFER = 0.02  # 2% buffer for confirmation

# Executor parameters
ACCOUNT_EQUITY = 100000
MAX_RISK_PERCENT = 2.0
ATR_PERIOD = 14
TRAILING_SMA_PERIOD = 10