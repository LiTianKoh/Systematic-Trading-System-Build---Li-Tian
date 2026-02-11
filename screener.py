# =================== screener.py ===================
"""
Phase II: The Screener
- Liquidity Filter: Price >= $3 AND 50-day Avg Volume >= 300,000
- Trend Filter: Current Price above 50-day SMA
"""

import pandas as pd
from config import MIN_PRICE, MIN_VOLUME, SMA_PERIOD

def calculate_50_day_average_volume(stock_data):
    """
    Calculate 50-day average trading volume.
    Returns 0 if insufficient data.
    """
    if len(stock_data) < SMA_PERIOD:
        return 0
    
    volume_last_50 = stock_data['Volume'].iloc[-SMA_PERIOD:]
    avg_volume = volume_last_50.mean()
    
    # Convert to scalar if needed
    if hasattr(avg_volume, 'iloc'):
        avg_volume = avg_volume.iloc[0]
    elif hasattr(avg_volume, 'item'):
        avg_volume = avg_volume.item()
    
    return avg_volume


def calculate_50_day_sma(stock_data):
    """
    Calculate 50-day Simple Moving Average of closing prices.
    Returns 0 if insufficient data.
    """
    if len(stock_data) < SMA_PERIOD:
        return 0
    
    closes_last_50 = stock_data['Close'].iloc[-SMA_PERIOD:]
    sma_50 = closes_last_50.mean()
    
    # Convert to scalar if needed
    if hasattr(sma_50, 'iloc'):
        sma_50 = sma_50.iloc[0]
    elif hasattr(sma_50, 'item'):
        sma_50 = sma_50.item()
    
    return sma_50


def liquidity_filter(stock_data, symbol):
    """
    Check if stock meets liquidity requirements:
    1. Current price >= $3.00
    2. 50-day average volume >= 300,000 shares
    """
    # Get current price and convert to scalar
    current_price = stock_data['Close'].iloc[-1]
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    
    # Price check
    if current_price < MIN_PRICE:
        return False, f"Price ${current_price:.2f} < ${MIN_PRICE:.2f}"
    
    # Volume check
    avg_volume = calculate_50_day_average_volume(stock_data)
    if avg_volume < MIN_VOLUME:
        return False, f"50-day avg volume {avg_volume:,.0f} < {MIN_VOLUME:,}"
    
    return True, f"Passed liquidity: ${current_price:.2f}, vol {avg_volume:,.0f}"


def trend_filter(stock_data, symbol):
    """
    Check if stock is in uptrend:
    Current price > 50-day SMA
    """
    current_price = stock_data['Close'].iloc[-1]
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    
    sma_50 = calculate_50_day_sma(stock_data)
    
    if sma_50 == 0:
        return False, "Insufficient data for SMA"
    
    if current_price <= sma_50:
        return False, f"Price ${current_price:.2f} ≤ 50-SMA ${sma_50:.2f}"
    
    return True, f"Price ${current_price:.2f} > 50-SMA ${sma_50:.2f}"


def run_screener(stock_data, symbol):
    """
    Main screener function combining both filters.
    Returns: (passed, message)
    """
    # Liquidity check
    liquidity_passed, liquidity_msg = liquidity_filter(stock_data, symbol)
    if not liquidity_passed:
        return False, f"SCREENER FAIL - Liquidity: {liquidity_msg}"
    
    # Trend check
    trend_passed, trend_msg = trend_filter(stock_data, symbol)
    if not trend_passed:
        return False, f"SCREENER FAIL - Trend: {trend_msg}"
    
    return True, f"SCREENER PASS: {liquidity_msg}, {trend_msg}"