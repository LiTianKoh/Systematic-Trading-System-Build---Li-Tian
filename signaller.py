# =================== signaller.py ===================
"""
Phase III: The Signaller
- The Riser (Impulse): 30%+ increase in last 63 trading days
- The Tread (Consolidation): 4-40 days, max retracement <25%
- Entry Trigger: Break above consolidation high
"""

import pandas as pd
from config import (
    RISER_WINDOW, RISER_MIN_INCREASE,
    CONSOLIDATION_MIN_DAYS, CONSOLIDATION_MAX_DAYS, MAX_RETRACEMENT,
    UPPER_BUFFER, LOWER_BUFFER, BREAKOUT_BUFFER
)


def riser(stock_data, symbol, window_days=RISER_WINDOW, min_increase=RISER_MIN_INCREASE):
    """
    Check if stock price increased by min_increase% in last window_days.
    Returns: (passed, message)
    """
    if len(stock_data) < window_days:
        return False, f"Insufficient data: {len(stock_data)} < {window_days} days"
    
    current_price = stock_data['Close'].iloc[-1]
    price_ago = stock_data['Close'].iloc[-window_days]
    
    # Convert to scalars
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    if hasattr(price_ago, 'iloc') or hasattr(price_ago, 'item'):
        price_ago = float(price_ago)
    
    increase_pct = ((current_price - price_ago) / price_ago) * 100
    
    if increase_pct < min_increase:
        return False, f"Riser FAIL: +{increase_pct:.1f}% < {min_increase}%"
    
    return True, f"Riser PASS: +{increase_pct:.1f}% in {window_days} days"


def consolidation(stock_data, symbol):
    """
    Check if stock is in consolidation phase after a rise.
    Looks for: Price retraced <25% from 63-day peak,
    then formed a range for 4-40 days with price staying in range.
    
    Returns: (passed, message, consolidation_info)
    """
    # ========== VALIDATION ==========
    if len(stock_data) < RISER_WINDOW:
        return False, f"Need {RISER_WINDOW}+ days, got {len(stock_data)}", {}
    
    # ========== FIND PEAK IN LAST 63 DAYS ==========
    last_63_days = stock_data.iloc[-RISER_WINDOW:]
    peak_price = last_63_days['High'].max()
    peak_date = last_63_days['High'].idxmax()
    peak_position = stock_data.index.get_loc(peak_date)
    
    # Convert peak to scalar
    if hasattr(peak_price, 'iloc') or hasattr(peak_price, 'item'):
        peak_price = float(peak_price)
    
    # ========== FIND RETRACEMENT LOW AFTER PEAK ==========
    data_after_peak = stock_data.iloc[peak_position + 1:]
    
    if len(data_after_peak) == 0:
        return False, "Peak is most recent day - no consolidation", {}
    
    retracement_low = data_after_peak['Low'].min()
    retracement_low_date = data_after_peak['Low'].idxmin()
    retracement_low_position = stock_data.index.get_loc(retracement_low_date)
    
    # Convert low to scalar
    if hasattr(retracement_low, 'iloc') or hasattr(retracement_low, 'item'):
        retracement_low = float(retracement_low)
    
    # ========== CHECK RETRACEMENT PERCENTAGE ==========
    retracement_pct = ((peak_price - retracement_low) / peak_price) * 100
    
    if retracement_pct >= MAX_RETRACEMENT:
        return False, f"Retracement {retracement_pct:.1f}% ≥ {MAX_RETRACEMENT}%", {}
    
    # ========== FIND CONSOLIDATION RANGE AFTER RETRACEMENT ==========
    data_after_retracement = stock_data.iloc[retracement_low_position:]
    
    if len(data_after_retracement) < CONSOLIDATION_MIN_DAYS:
        return False, f"Only {len(data_after_retracement)} days since retracement", {}
    
    consolidation_high = data_after_retracement['High'].max()
    consolidation_high_date = data_after_retracement['High'].idxmax()
    consolidation_low = retracement_low
    
    # Convert high to scalar
    if hasattr(consolidation_high, 'iloc') or hasattr(consolidation_high, 'item'):
        consolidation_high = float(consolidation_high)
    
    # ========== CHECK CONSOLIDATION DURATION ==========
    current_position = len(stock_data) - 1
    days_in_consolidation = current_position - retracement_low_position
    
    if days_in_consolidation < CONSOLIDATION_MIN_DAYS:
        return False, f"Only {days_in_consolidation} days consolidation", {}
    
    if days_in_consolidation > CONSOLIDATION_MAX_DAYS:
        return False, f"{days_in_consolidation} days > {CONSOLIDATION_MAX_DAYS} max", {}
    
    # ========== CHECK PRICE STAYS IN RANGE ==========
    consolidation_period = stock_data.iloc[retracement_low_position:]
    
    upper_bound = consolidation_high * (1 + UPPER_BUFFER)
    lower_bound = consolidation_low * (1 - LOWER_BUFFER)
    
    violations = []
    for date_idx, daily_bar in consolidation_period.iterrows():
        high = daily_bar['High']
        low = daily_bar['Low']
        
        if hasattr(high, 'iloc') or hasattr(high, 'item'):
            high = float(high)
        if hasattr(low, 'iloc') or hasattr(low, 'item'):
            low = float(low)
        
        if high > upper_bound:
            violations.append(f"{date_idx.date()}: High ${high:.2f} > ${upper_bound:.2f}")
        if low < lower_bound:
            violations.append(f"{date_idx.date()}: Low ${low:.2f} < ${lower_bound:.2f}")
    
    if violations:
        return False, f"Range violations: {violations[0]}", {}
    
    # ========== CHECK CLOSING PRICES WITHIN RANGE ==========
    closing_prices = consolidation_period['Close']
    closes_in_range = ((closing_prices >= consolidation_low) & 
                       (closing_prices <= consolidation_high)).sum()
    close_pct = (closes_in_range / len(closing_prices)) * 100
    
    if close_pct < 70:
        return False, f"Only {close_pct:.1f}% closes within range", {}
    
    # ========== PREPARE CONSOLIDATION INFO ==========
    current_price = stock_data['Close'].iloc[-1]
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    
    range_width_pct = ((consolidation_high - consolidation_low) / consolidation_high) * 100
    
    if consolidation_high > consolidation_low:
        current_pos_pct = ((current_price - consolidation_low) / 
                          (consolidation_high - consolidation_low)) * 100
    else:
        current_pos_pct = 50
    
    consolidation_info = {
        # Peak info
        'peak_price': peak_price,
        'peak_date': peak_date,
        'retracement_pct': retracement_pct,
        
        # Consolidation range
        'consolidation_high': consolidation_high,
        'consolidation_high_date': consolidation_high_date,
        'consolidation_low': consolidation_low,
        'consolidation_low_date': retracement_low_date,
        
        # Duration
        'days_in_consolidation': days_in_consolidation,
        'days_since_peak': current_position - peak_position,
        
        # Metrics
        'range_width_pct': range_width_pct,
        'current_price': current_price,
        'current_position_in_range': current_pos_pct,
        'close_percentage_in_range': close_pct,
        
        # For entry trigger
        'breakout_level': consolidation_high,
        'stop_loss_level': consolidation_low
    }
    
    message = (
        f"Consolidation PASS: {days_in_consolidation} days, "
        f"range ${consolidation_low:.2f}-${consolidation_high:.2f} "
        f"({range_width_pct:.1f}%), retrace {retracement_pct:.1f}%"
    )
    
    return True, message, consolidation_info


def entry_trigger(stock_data, symbol, consolidation_info):
    """
    Check if price breaks above consolidation high for BUY signal.
    Returns: (triggered, message, entry_price, entry_details)
    """
    if not consolidation_info:
        return False, "No consolidation data", 0.0, {}
    
    breakout_level = consolidation_info.get('breakout_level', 0)
    stop_loss_level = consolidation_info.get('stop_loss_level', 0)
    
    if breakout_level <= 0 or stop_loss_level <= 0:
        return False, "Invalid consolidation levels", 0.0, {}
    
    # Get current price data
    current_price = stock_data['Close'].iloc[-1]
    current_high = stock_data['High'].iloc[-1]
    
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    if hasattr(current_high, 'iloc') or hasattr(current_high, 'item'):
        current_high = float(current_high)
    
    # Check for breakout
    if current_high > breakout_level * (1 + BREAKOUT_BUFFER):
        entry_details = {
            'symbol': symbol,
            'entry_price': current_price,
            'entry_date': stock_data.index[-1],
            'breakout_level': breakout_level,
            'stop_loss_level': stop_loss_level,
            'risk_per_share': current_price - stop_loss_level,
            'risk_percentage': ((current_price - stop_loss_level) / current_price) * 100,
            'original_peak': consolidation_info.get('peak_price', breakout_level)
        }
        
        message = f"BUY: Broke ${breakout_level:.2f} at ${current_price:.2f}"
        return True, message, current_price, entry_details
    
    # No breakout
    distance_pct = ((breakout_level - current_price) / breakout_level) * 100
    
    entry_details = {
        'symbol': symbol,
        'current_price': current_price,
        'breakout_level_needed': breakout_level,
        'distance_to_breakout_pct': distance_pct,
        'stop_loss_level': stop_loss_level
    }
    
    message = f"HOLD: Need +{distance_pct:.1f}% to break ${breakout_level:.2f}"
    return False, message, current_price, entry_details


def run_signaller(stock_data, symbol):
    """
    Main signaller function orchestrating all three stages.
    Returns: dict with complete signal results
    """
    results = {
        'symbol': symbol,
        'analysis_date': stock_data.index[-1],
        'current_price': float(stock_data['Close'].iloc[-1]),
        'data_days': len(stock_data),
        
        # Stage results
        'riser_passed': False,
        'consolidation_passed': False,
        'entry_triggered': False,
        
        # Stage messages
        'messages': [],
        
        # Data for executor
        'consolidation_info': None,
        'entry_details': None,
        
        # Final signal
        'signal': 'NO_SIGNAL',
        'action': 'HOLD'
    }
    
    # ===== STAGE 1: RISER =====
    riser_passed, riser_msg = riser(stock_data, symbol)
    results['riser_passed'] = riser_passed
    results['messages'].append(f"RISER: {riser_msg}")
    
    if not riser_passed:
        results['signal'] = 'RISER_FAIL'
        return results
    
    # ===== STAGE 2: CONSOLIDATION =====
    cons_passed, cons_msg, cons_info = consolidation(stock_data, symbol)
    results['consolidation_passed'] = cons_passed
    results['messages'].append(f"CONSOLIDATION: {cons_msg}")
    results['consolidation_info'] = cons_info
    
    if not cons_passed:
        results['signal'] = 'CONSOLIDATION_FAIL'
        return results
    
    # ===== STAGE 3: ENTRY TRIGGER =====
    entry_triggered, entry_msg, entry_price, entry_details = entry_trigger(
        stock_data, symbol, cons_info
    )
    results['entry_triggered'] = entry_triggered
    results['entry_details'] = entry_details
    results['messages'].append(f"ENTRY: {entry_msg}")
    
    # ===== FINAL SIGNAL =====
    if entry_triggered:
        results['signal'] = 'BUY'
        results['action'] = 'BUY'
    else:
        results['signal'] = 'HOLD'
        results['action'] = 'MONITOR'
    
    return results