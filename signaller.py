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
    Returns: (passed, message, riser_info)
    """
    if len(stock_data) < window_days:
        return False, f"Insufficient data: {len(stock_data)} < {window_days} days", {}
    
    current_price = stock_data['Close'].iloc[-1]
    price_ago = stock_data['Close'].iloc[-window_days]
    date_ago = stock_data.index[-window_days]
    
    # Convert to scalars
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    if hasattr(price_ago, 'iloc') or hasattr(price_ago, 'item'):
        price_ago = float(price_ago)
    
    increase_pct = ((current_price - price_ago) / price_ago) * 100
    increase_amount = current_price - price_ago
    
    riser_info = {
        'date_63_days_ago': date_ago.date(),
        'price_63_days_ago': price_ago,
        'current_price': current_price,
        'increase_amount': increase_amount,
        'increase_pct': increase_pct,
        'required_pct': min_increase,
        'passed': increase_pct >= min_increase
    }
    
    if increase_pct < min_increase:
        return False, f"Riser FAIL: +{increase_pct:.1f}% < {min_increase}%", riser_info
    
    return True, f"Riser PASS: +{increase_pct:.1f}% in {window_days} days", riser_info


def consolidation(stock_data, symbol):
    """
    Check if stock is in consolidation phase after a rise.
    Looks for: Price retraced <25% from 63-day peak,
    then formed a range for 4-40 days with price staying in range.
    
    Returns: (passed, message, consolidation_info)
    """
    # ========== INITIALIZE CONSOLIDATION INFO WITH DEFAULTS ==========
    consolidation_info = {
        'peak_price': 0,
        'peak_date': None,
        'days_since_peak': 0,
        'retracement_pct': 0,
        'retracement_low': 0,
        'retracement_low_date': None,
        'consolidation_start_date': None,  # New field
        'consolidation_high': 0,
        'consolidation_low': 0,
        'consolidation_high_date': None,
        'range_width_pct': 0,
        'range_height': 0,
        'days_in_consolidation': 0,
        'days_since_retracement': 0,
        'close_percentage_in_range': 0,
        'closes_in_range': 0,
        'total_days_in_range': 0,
        'current_price': 0,
        'breakout_level': 0,
        'stop_loss_level': 0,
        'upper_bound_with_buffer': 0,
        'lower_bound_with_buffer': 0,
        'failure_reason': None
    }
    
    # ========== VALIDATION ==========
    if len(stock_data) < RISER_WINDOW:
        consolidation_info['failure_reason'] = f"Need {RISER_WINDOW}+ days, got {len(stock_data)}"
        return False, f"Need {RISER_WINDOW}+ days, got {len(stock_data)}", consolidation_info
    
    # ========== FIND PEAK IN LAST 63 DAYS ==========
    last_63_days = stock_data.iloc[-RISER_WINDOW:]
    peak_price = last_63_days['High'].max()
    peak_date = last_63_days['High'].idxmax()
    peak_position = stock_data.index.get_loc(peak_date)
    
    # Convert peak to scalar
    if hasattr(peak_price, 'iloc') or hasattr(peak_price, 'item'):
        peak_price = float(peak_price)
    
    # Update consolidation info with peak data
    consolidation_info['peak_price'] = peak_price
    consolidation_info['peak_date'] = peak_date
    consolidation_info['days_since_peak'] = len(stock_data) - peak_position - 1
    
    # ========== FIND RETRACEMENT LOW AFTER PEAK ==========
    data_after_peak = stock_data.iloc[peak_position + 1:]
    
    if len(data_after_peak) == 0:
        consolidation_info['failure_reason'] = "Peak is most recent day - no consolidation"
        return False, "Peak is most recent day - no consolidation", consolidation_info
    
    retracement_low = data_after_peak['Low'].min()
    retracement_low_date = data_after_peak['Low'].idxmin()
    retracement_low_position = stock_data.index.get_loc(retracement_low_date)
    
    # Convert low to scalar
    if hasattr(retracement_low, 'iloc') or hasattr(retracement_low, 'item'):
        retracement_low = float(retracement_low)
    
    # Update consolidation info with retracement data
    consolidation_info['retracement_low'] = retracement_low
    consolidation_info['retracement_low_date'] = retracement_low_date
    consolidation_info['days_since_retracement'] = len(stock_data) - retracement_low_position - 1
    
    # ========== CHECK RETRACEMENT PERCENTAGE ==========
    retracement_pct = ((peak_price - retracement_low) / peak_price) * 100
    consolidation_info['retracement_pct'] = retracement_pct
    
    if retracement_pct >= MAX_RETRACEMENT:
        consolidation_info['failure_reason'] = f"Retracement {retracement_pct:.1f}% ≥ {MAX_RETRACEMENT}%"
        return False, f"Retracement {retracement_pct:.1f}% ≥ {MAX_RETRACEMENT}%", consolidation_info
    
    # ========== FIND CONSOLIDATION RANGE AFTER RETRACEMENT ==========
    data_after_retracement = stock_data.iloc[retracement_low_position:]

    # Set consolidation start date (the retracement low date itself)
    # The consolidation period STARTS at the retracement low
    consolidation_info['consolidation_start_date'] = retracement_low_date

    # Calculate days in consolidation:
    # This counts the number of trading days SINCE the retracement low (including the low day as day 0)
    # For example: 
    # - If low was today: 0 days in consolidation (just started)
    # - If low was yesterday: 1 day in consolidation
    # - If low was 2 days ago: 2 days in consolidation
    days_in_consolidation = len(stock_data) - retracement_low_position
    consolidation_info['days_in_consolidation'] = max(0, days_in_consolidation)

    # ONLY calculate range metrics if we have at least the low day itself
    if len(data_after_retracement) >= 1:
        # Data from the low through today (includes the low day)
        consolidation_period = data_after_retracement
        
        if len(consolidation_period) > 0:
            # Find consolidation high from the period starting AT the low
            # This allows the low day itself to be part of the consolidation range
            consolidation_high = consolidation_period['High'].max()
            consolidation_high_date = consolidation_period['High'].idxmax()
            consolidation_low = retracement_low  # Low is the retracement low
            
            # Convert high to scalar
            if hasattr(consolidation_high, 'iloc') or hasattr(consolidation_high, 'item'):
                consolidation_high = float(consolidation_high)
            
            # Update consolidation info with range data
            consolidation_info['consolidation_high'] = consolidation_high
            consolidation_info['consolidation_high_date'] = consolidation_high_date
            consolidation_info['consolidation_low'] = consolidation_low
            
            # Calculate range metrics
            if consolidation_high > consolidation_low:
                range_width_pct = ((consolidation_high - consolidation_low) / consolidation_high) * 100
                range_height = consolidation_high - consolidation_low
            else:
                range_width_pct = 0
                range_height = 0
            
            consolidation_info['range_width_pct'] = range_width_pct
            consolidation_info['range_height'] = range_height
            
            # Buffer levels
            consolidation_info['upper_bound_with_buffer'] = consolidation_high * (1 + UPPER_BUFFER)
            consolidation_info['lower_bound_with_buffer'] = consolidation_low * (1 - LOWER_BUFFER)
            
            # Breakout level and stop loss
            consolidation_info['breakout_level'] = consolidation_high
            consolidation_info['stop_loss_level'] = consolidation_low
            
            # ========== CHECK CLOSING PRICES WITHIN RANGE ==========
            closing_prices = consolidation_period['Close']
            closes_in_range = ((closing_prices >= consolidation_low) & 
                            (closing_prices <= consolidation_high)).sum()
            close_pct = (closes_in_range / len(closing_prices)) * 100
            
            consolidation_info['close_percentage_in_range'] = close_pct
            consolidation_info['closes_in_range'] = closes_in_range
            consolidation_info['total_days_in_range'] = len(closing_prices)
    
    # ========== CHECK CONSOLIDATION DURATION ==========
    if days_in_consolidation < CONSOLIDATION_MIN_DAYS:
        consolidation_info['failure_reason'] = f"Only {days_in_consolidation} days since retracement (need {CONSOLIDATION_MIN_DAYS}+)"
        return False, f"Only {days_in_consolidation} days since retracement", consolidation_info
    
    if days_in_consolidation > CONSOLIDATION_MAX_DAYS:
        consolidation_info['failure_reason'] = f"{days_in_consolidation} days > {CONSOLIDATION_MAX_DAYS} max"
        return False, f"{days_in_consolidation} days > {CONSOLIDATION_MAX_DAYS} max", consolidation_info
    
    # ========== CHECK PRICE STAYS IN RANGE ==========
    if len(consolidation_period) > 0:
        violations = []
        for date_idx, daily_bar in consolidation_period.iterrows():
            high = daily_bar['High']
            low = daily_bar['Low']
            
            if hasattr(high, 'iloc') or hasattr(high, 'item'):
                high = float(high)
            if hasattr(low, 'iloc') or hasattr(low, 'item'):
                low = float(low)
            
            if high > consolidation_info['upper_bound_with_buffer']:
                violations.append(f"{date_idx.date()}: High ${high:.2f} > ${consolidation_info['upper_bound_with_buffer']:.2f}")
            if low < consolidation_info['lower_bound_with_buffer']:
                violations.append(f"{date_idx.date()}: Low ${low:.2f} < ${consolidation_info['lower_bound_with_buffer']:.2f}")
        
        if violations:
            consolidation_info['failure_reason'] = f"Range violations: {violations[0]}"
            return False, f"Range violations: {violations[0]}", consolidation_info
    
    # ========== CHECK CLOSING PRICES WITHIN RANGE ==========
    if consolidation_info['close_percentage_in_range'] < 70:
        consolidation_info['failure_reason'] = f"Only {consolidation_info['close_percentage_in_range']:.1f}% closes within range (need 70%+)"
        return False, f"Only {consolidation_info['close_percentage_in_range']:.1f}% closes within range", consolidation_info
    
    # ========== GET CURRENT PRICE ==========
    current_price = stock_data['Close'].iloc[-1]
    if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
        current_price = float(current_price)
    consolidation_info['current_price'] = current_price
    
    message = (
        f"Consolidation PASS: {days_in_consolidation} days, "
        f"range ${consolidation_info['consolidation_low']:.2f}-${consolidation_info['consolidation_high']:.2f} "
        f"({consolidation_info['range_width_pct']:.1f}%), retrace {retracement_pct:.1f}%"
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
            'original_peak': consolidation_info.get('peak_price', breakout_level),
            'breakout_strength': ((current_high - breakout_level) / breakout_level) * 100,
            'breakout_threshold': breakout_level * (1 + BREAKOUT_BUFFER)
        }
        
        message = f"BUY: Broke ${breakout_level:.2f} +{BREAKOUT_BUFFER*100:.0f}% at ${current_price:.2f}"
        return True, message, current_price, entry_details
    
    # No breakout
    distance_to_breakout = breakout_level - current_price
    distance_to_breakout_pct = (distance_to_breakout / breakout_level) * 100
    required_price = breakout_level * (1 + BREAKOUT_BUFFER)
    distance_to_threshold = required_price - current_price
    distance_to_threshold_pct = (distance_to_threshold / required_price) * 100
    
    entry_details = {
        'symbol': symbol,
        'current_price': current_price,
        'current_high': current_high,
        'breakout_level': breakout_level,
        'breakout_threshold': required_price,
        'distance_to_breakout': distance_to_breakout,
        'distance_to_breakout_pct': distance_to_breakout_pct,
        'distance_to_threshold': distance_to_threshold,
        'distance_to_threshold_pct': distance_to_threshold_pct,
        'stop_loss_level': stop_loss_level
    }
    
    message = f"HOLD: Need +{distance_to_threshold_pct:.1f}% to break ${required_price:.2f}"
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
        
        # Stage info
        'riser_info': None,
        'consolidation_info': None,
        'entry_details': None,
        
        # Stage messages
        'messages': [],
        
        # Final signal
        'signal': 'NO_SIGNAL',
        'action': 'HOLD'
    }
    
    # ===== STAGE 1: RISER =====
    riser_passed, riser_msg, riser_info = riser(stock_data, symbol)
    results['riser_passed'] = riser_passed
    results['riser_info'] = riser_info
    results['messages'].append(f"RISER: {riser_msg}")
    
    if not riser_passed:
        results['signal'] = 'RISER_FAIL'
        return results
    
    # ===== STAGE 2: CONSOLIDATION =====
    cons_passed, cons_msg, cons_info = consolidation(stock_data, symbol)
    results['consolidation_passed'] = cons_passed
    results['messages'].append(f"CONSOLIDATION: {cons_msg}")
    results['consolidation_info'] = cons_info  # This now ALWAYS contains data, even on failure
    
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