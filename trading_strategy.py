import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

#20 highly liquid US tech stocks
tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
                'INTC', 'TSLA', 'META', 'AVGO', 'MU', 
                'AMD', 'PLTR', 'TXN', 'TSM', 'ARM', 
                'ADI', 'SLAB', 'ORCL', 'IBM', 'CRM']

def calculate_50_day_average_volume(stock_data): #E.g. stock_data = yf.download("AAPL", period="5d", progress=False). It'll give the list of data shown under historical data in YF
    if len(stock_data) < 50:    #Checks if YF has 50 days worth of historical data
        return 0    #Not enough information
    volume_in_last_50days = stock_data['Volume'].iloc[-50:] #Extract the volume over the past 50 days from current date
    avg_50day_moving = volume_in_last_50days.mean() #50-day Average

    return avg_50day_moving

#Create a liquidity_filter function
def liquidity_filter(stock_data, symbol):
    current_price = stock_data['Close'].iloc[-1] #Get current price from stock_data

    if (current_price < 3.00):
        return False, f"Stock's price is ${current_price:.2f}, under $3. Choose a stock that's above $3!"
    
    #only proceed to check if the stock's 50-day Average Volume >= 300k shares
    avg_volume_50Day = calculate_50_day_average_volume(stock_data)
    if (avg_volume_50Day < 300000):
        return False, f"50-day Average Volume ({avg_volume_50Day}), under 300,000 shares. Pick another one!"
    
    #Passes both the price and volume check
    return True, f"{symbol}'s 50-day Average Volume is trading at {avg_volume_50Day} shares."

def calculate_50_day_sma(stock_data):         
    if (len(stock_data) < 50):
        return 0
    closingPrice_50days = stock_data['Close'].iloc[-50:] #Fetches the closing prices in the last 50 days
    sma_50 = closingPrice_50days.mean()

    return sma_50

def trend_filter (stock_data, symbol):
    current_price = stock_data['Close'].iloc[-1] #Get current price from stock_data
    sma_50 = calculate_50_day_sma(stock_data)

    if (current_price <= sma_50):
        return False, "Current price is below the 50 SMA. Please wait another time"
    
    return True, f"{symbol} is above the 50 SMA."

def the_screener(stock_data, symbol):
    # Get results from both filters
    liquidity_passed, liquidity_msg = liquidity_filter(stock_data, symbol)
    trend_passed, trend_msg = trend_filter(stock_data, symbol)

    # Check both conditions
    if not liquidity_passed:
        return False, liquidity_msg
    if not trend_passed:
        return False, trend_msg
    
    return True, f"{symbol} passed the both liquidity and trend filters"

def riser(stock_data, symbol, window_days = 63, min_increase = 30):
    """
    Check if stock price increased by min_increase% in last window_days
    """
    if len(stock_data) < window_days:
        return False, f"Not enough data. Need {window_days} days, have {len(stock_data)}"
    
    # Get prices
    current_price = stock_data['Close'].iloc[-1]
    price_window_ago = stock_data['Close'].iloc[-window_days]
    
    # Calculate percentage increase
    price_increase_pct = ((current_price - price_window_ago) / price_window_ago) * 100
    
    if price_increase_pct < min_increase:
        return False, f"Price increased by {price_increase_pct:.1f}% (needs to be ≥{min_increase}%)"
    
    return True, f"Price increased by {price_increase_pct:.1f}% in last {window_days} days"

def consolidation(stock_data, symbol, consolidation_min=4, consolidation_max=40, max_retracement=25):
    """
    Check if stock is in consolidation phase after a rise.
    Looks for: Price retraced <25% from 63-day peak, then formed a 
    consolidation range (lower high + retracement low) for 4-40 days.
    
    Returns: (passed, message, consolidation_info)
    """
    
    # =================== VALIDATION ===================
    if len(stock_data) < 63:
        return False, f"Need at least 63 days of data, got {len(stock_data)}", {}
    
    # =================== FIND PEAK IN LAST 63 DAYS ===================
    last_63_days = stock_data.iloc[-63:]
    peak_price = last_63_days['High'].max()
    peak_date = last_63_days['High'].idxmax()
    peak_position = stock_data.index.get_loc(peak_date)
    
    # =================== FIND RETRACEMENT LOW AFTER PEAK ===================
    data_after_peak = stock_data.iloc[peak_position + 1:]
    
    if len(data_after_peak) == 0:
        return False, "Peak is the most recent day - no consolidation possible", {}
    
    # Find the lowest point AFTER the peak (retracement low)
    retracement_low = data_after_peak['Low'].min()
    retracement_low_date = data_after_peak['Low'].idxmin()
    retracement_low_position = stock_data.index.get_loc(retracement_low_date)
    
    # =================== CHECK RETRACEMENT ===================
    retracement_pct = ((peak_price - retracement_low) / peak_price) * 100
    
    if retracement_pct >= max_retracement:
        return False, f"Retracement {retracement_pct:.1f}% ≥ {max_retracement}% limit", {}
    
    # =================== FIND CONSOLIDATION RANGE AFTER RETRACEMENT ===================
    # Look at data AFTER the retracement low was established
    data_after_retracement = stock_data.iloc[retracement_low_position:]
    
    if len(data_after_retracement) < consolidation_min:
        return False, f"Only {len(data_after_retracement)} days since retracement low", {}
    
    # Find the HIGHEST high in the consolidation period (this becomes upper bound)
    # This could be LOWER than the original peak!
    consolidation_high = data_after_retracement['High'].max()
    consolidation_high_date = data_after_retracement['High'].idxmax()
    
    # The lower bound is the retracement low we already found
    consolidation_low = retracement_low
    
    # =================== CHECK CONSOLIDATION DURATION ===================
    # Days from retracement low to today
    current_position = len(stock_data) - 1
    days_in_consolidation = current_position - retracement_low_position
    
    if days_in_consolidation < consolidation_min:
        return False, f"Only {days_in_consolidation} days in consolidation (needs {consolidation_min}+)", {}
    
    if days_in_consolidation > consolidation_max:
        return False, f"{days_in_consolidation} days in consolidation (exceeds {consolidation_max} max)", {}
    
    # =================== CHECK PRICE STAYS IN CONSOLIDATION RANGE ===================
    # Get the consolidation period data (from retracement low onward)
    consolidation_period = stock_data.iloc[retracement_low_position:]
    
    # Define range with buffer for wicks
    UPPER_BUFFER = 0.01  # 1% above consolidation high
    LOWER_BUFFER = 0.01  # 1% below consolidation low
    
    upper_bound = consolidation_high * (1 + UPPER_BUFFER)
    lower_bound = consolidation_low * (1 - LOWER_BUFFER)
    
    # Track range violations
    violations = []
    
    for date_idx, daily_bar in consolidation_period.iterrows():
        # Check if price broke above range
        if daily_bar['High'] > upper_bound:
            violations.append(f"{date_idx.date()}: High ${daily_bar['High']:.2f} > ${upper_bound:.2f}")
        
        # Check if price broke below range
        if daily_bar['Low'] < lower_bound:
            violations.append(f"{date_idx.date()}: Low ${daily_bar['Low']:.2f} < ${lower_bound:.2f}")
    
    if violations:
        # Show first 2 violations only to keep message concise
        violation_msg = "; ".join(violations[:2])
        if len(violations) > 2:
            violation_msg += f" ... and {len(violations) - 2} more"
        
        return False, f"Price broke consolidation range: {violation_msg}", {}
    
    # =================== ADDITIONAL CHECKS ===================
    # Verify consolidation high is meaningful (not just a wick)
    # Check that closing prices also respect the range
    closing_prices = consolidation_period['Close']
    
    # Most closes should be within the actual range (not just buffer range)
    closes_in_range = ((closing_prices >= consolidation_low) & 
                       (closing_prices <= consolidation_high)).sum()
    close_percentage = (closes_in_range / len(closing_prices)) * 100
    
    if close_percentage < 70:  # At least 70% of closes should be in range
        return False, f"Only {close_percentage:.1f}% of closes within consolidation range", {}
    
    # =================== PREPARE CONSOLIDATION INFO ===================
    current_price = stock_data['Close'].iloc[-1]
    range_width_pct = ((consolidation_high - consolidation_low) / consolidation_high) * 100
    
    # Calculate where current price is within the range (0-100%)
    if consolidation_high > consolidation_low:
        current_position_pct = ((current_price - consolidation_low) / 
                               (consolidation_high - consolidation_low)) * 100
    else:
        current_position_pct = 50  # Default if range is zero (shouldn't happen)
    
    consolidation_info = {
        # Original peak (for riser calculation)
        'peak_63day_price': peak_price,
        'peak_63day_date': peak_date,
        'retracement_pct': retracement_pct,
        
        # Consolidation range (what matters for trading)
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
        'current_position_in_range': current_position_pct,
        'close_percentage_in_range': close_percentage,
        
        # For entry trigger
        'breakout_level': consolidation_high,  # Break above this to enter
        'stop_loss_level': consolidation_low,  # Stop below this
        
        # Range boundaries (with buffer)
        'range_upper_with_buffer': upper_bound,
        'range_lower_with_buffer': lower_bound,
    }
    
    # =================== SUCCESS MESSAGE ===================
    success_message = (
        f"Consolidation confirmed: {days_in_consolidation} days, "
        f"range: ${consolidation_low:.2f}-${consolidation_high:.2f} "
        f"({range_width_pct:.1f}% width). "
        f"Original peak: ${peak_price:.2f} (-{retracement_pct:.1f}% retracement)"
    )
    
    return True, success_message, consolidation_info

def entry_trigger(stock_data, symbol, consolidation_info):
    """
    Check if price breaks above consolidation high for BUY signal.
    Now uses the lower high from consolidation, not the original peak.
    """
    
    if consolidation_info is None or len(consolidation_info) == 0:
        return False, "No consolidation data available", 0.0, {}
    
    # Extract the consolidation high (which may be lower than original peak)
    breakout_level = consolidation_info.get('breakout_level', 0)
    stop_loss_level = consolidation_info.get('stop_loss_level', 0)
    
    if breakout_level <= 0 or stop_loss_level <= 0:
        return False, "Invalid consolidation levels", 0.0, {}
    
    # Get current price data
    current_price = stock_data['Close'].iloc[-1]
    current_high = stock_data['High'].iloc[-1]
    
    # Breakout check with small buffer
    BREAKOUT_BUFFER = 0.02  # 2% buffer. You want that extra reassurance that price actually broke the upper bound
    
    #==============================================<Market Order>===========================================================
    if current_high > breakout_level * (1 + BREAKOUT_BUFFER):
        # Breakout confirmed
        entry_price = current_price   
        
        # Calculate distance from original peak (for context)
        original_peak = consolidation_info.get('peak_63day_price', breakout_level)
        distance_from_peak = ((entry_price - original_peak) / original_peak) * 100
        
        entry_details = {
            'symbol': symbol,
            'entry_price': entry_price,
            'entry_date': stock_data.index[-1],
            'breakout_level': breakout_level,
            'stop_loss_level': stop_loss_level,
            'risk_per_share': entry_price - stop_loss_level,
            'risk_percentage': ((entry_price - stop_loss_level) / entry_price) * 100,
            'breakout_strength': ((current_price - breakout_level) / breakout_level) * 100,
            'distance_from_original_peak_pct': distance_from_peak,
            'original_peak_price': original_peak
        }
        
        message = (
            f"BUY: {symbol} broke above consolidation high (${breakout_level:.2f}) "
            f"at ${entry_price:.2f}. "
            f"Original 63-day peak: ${original_peak:.2f} ({distance_from_peak:+.1f}%). "
            f"Risk: ${entry_details['risk_per_share']:.2f} per share "
            f"({entry_details['risk_percentage']:.1f}%)"
        )
        
        return True, message, entry_price, entry_details
    #================================================<No breakouts>========================================================
    current_distance_pct = ((breakout_level - current_price) / breakout_level) * 100
    
    entry_details = {
        'entry_price': entry_price, 
        'symbol': symbol,
        'current_price': current_price,
        'breakout_level_needed': breakout_level,
        'distance_to_breakout_pct': current_distance_pct,
        'stop_loss_level': stop_loss_level,
        'original_peak': consolidation_info.get('peak_63day_price', 0),
        'consolidation_width_pct': consolidation_info.get('range_width_pct', 0)
    }
    
    message = (
        f"HOLD: {symbol} at ${current_price:.2f}, "
        f"needs +{current_distance_pct:.1f}% to break ${breakout_level:.2f}. "
        f"Consolidation range: ${stop_loss_level:.2f}-${breakout_level:.2f} "
        f"({entry_details['consolidation_width_pct']:.1f}% width)"
    )
    
    return False, message, current_price, entry_details
    #====================================================================================================================

def signaller(stock_data, symbol, riser_window=63, riser_min_increase=30):
    """
    Main signaller function combining Riser, Consolidation, and Entry Trigger.
    Now with proper 63-day riser window and flexible consolidation logic.
    
    Parameters:
    -----------
    stock_data : pandas.DataFrame
        Historical OHLCV data with Date index
    symbol : str
        Stock ticker symbol
    riser_window : int
        Window to check for price increase (default: 63 days)
    riser_min_increase : float
        Minimum percentage increase required (default: 30%)
    
    Returns:
    --------
    dict : Comprehensive signal results with all intermediate checks
    """
    
    # Initialize results structure
    signal_results = {
        'symbol': symbol,
        'analysis_date': stock_data.index[-1],
        'current_price': stock_data['Close'].iloc[-1],
        'data_days_available': len(stock_data),
        
        # Stage results
        'screener_passed': False,
        'riser_passed': False,
        'consolidation_passed': False,
        'entry_triggered': False,
        
        # Messages and details
        'stage_messages': [],
        'stage_details': {},
        'consolidation_info': None,
        'entry_details': None,
        
        # Final signal
        'final_signal': 'NO SIGNAL',
        'final_message': '',
        'recommended_action': 'HOLD'
    }
    
    # =================== PRE-CHECK: DATA SUFFICIENCY ===================
    if len(stock_data) < riser_window:
        signal_results['final_message'] = f"Insufficient data: {len(stock_data)} days < {riser_window} days needed"
        signal_results['final_signal'] = 'INSUFFICIENT_DATA'
        return signal_results
    
    # =================== STAGE 1: SCREENER (Liquidity + Trend) ===================
    screener_passed, screener_msg = the_screener(stock_data, symbol)
    signal_results['screener_passed'] = screener_passed
    signal_results['stage_messages'].append(f"SCREENER: {screener_msg}")
    signal_results['stage_details']['screener'] = {'passed': screener_passed, 'message': screener_msg}
    
    if not screener_passed:
        signal_results['final_message'] = f"Failed screener: {screener_msg}"
        signal_results['final_signal'] = 'SCREENER_FAIL'
        signal_results['recommended_action'] = 'IGNORE'
        return signal_results
    
    # =================== STAGE 2: RISER (63-day ≥30% increase) ===================
    riser_passed, riser_msg = riser(stock_data, symbol, window_days=riser_window, min_increase=riser_min_increase)
    signal_results['riser_passed'] = riser_passed
    signal_results['stage_messages'].append(f"RISER ({riser_window}-day): {riser_msg}")
    
    # Extract riser metrics if available
    if "increased by" in riser_msg:
        try:
            # Parse the percentage from message: "Price increased by 35.2% in last 63 days"
            percent_str = riser_msg.split("increased by ")[1].split("%")[0]
            riser_percentage = float(percent_str)
            signal_results['stage_details']['riser'] = {
                'passed': riser_passed,
                'percentage': riser_percentage,
                'window_days': riser_window,
                'min_required': riser_min_increase
            }
        except:
            signal_results['stage_details']['riser'] = {'passed': riser_passed, 'message': riser_msg}
    
    if not riser_passed:
        signal_results['final_message'] = f"Failed riser: {riser_msg}"
        signal_results['final_signal'] = 'RISER_FAIL'
        signal_results['recommended_action'] = 'MONITOR'
        return signal_results
    
    # =================== STAGE 3: CONSOLIDATION (4-40 days range) ===================
    consolidation_passed, consolidation_msg, consolidation_info = consolidation(stock_data, symbol)
    signal_results['consolidation_passed'] = consolidation_passed
    signal_results['stage_messages'].append(f"CONSOLIDATION: {consolidation_msg}")
    signal_results['consolidation_info'] = consolidation_info
    
    if not consolidation_passed:
        signal_results['final_message'] = f"Failed consolidation: {consolidation_msg}"
        signal_results['final_signal'] = 'CONSOLIDATION_FAIL'
        signal_results['recommended_action'] = 'MONITOR'
        return signal_results
    
    # =================== STAGE 4: ENTRY TRIGGER (Breakout) ===================
    entry_triggered, entry_msg, entry_price, entry_details = entry_trigger(
        stock_data, symbol, consolidation_info
    )
    
    signal_results['entry_triggered'] = entry_triggered
    signal_results['entry_details'] = entry_details
    signal_results['stage_messages'].append(f"ENTRY: {entry_msg}")
    
    # =================== FINAL SIGNAL DETERMINATION ===================
    if entry_triggered:
        signal_results['final_signal'] = 'BUY'
        signal_results['final_message'] = f"BUY signal confirmed: {entry_msg}"
        signal_results['recommended_action'] = 'BUY'
        signal_results['target_entry'] = entry_details['entry_price']
        signal_results['stop_loss'] = entry_details['stop_loss_level']
        signal_results['risk_per_share'] = entry_details['risk_per_share']
        signal_results['risk_percentage'] = entry_details['risk_percentage']
        signal_results['breakout_level'] = entry_details['breakout_level']
        
        # Add consolidation context
        if consolidation_info:
            signal_results['consolidation_range'] = {
                'high': consolidation_info['consolidation_high'],
                'low': consolidation_info['consolidation_low'],
                'width_pct': consolidation_info['range_width_pct'],
                'days': consolidation_info['days_in_consolidation']
            }
    else:
        signal_results['final_signal'] = 'HOLD'
        signal_results['final_message'] = f"Consolidation confirmed, waiting for breakout: {entry_msg}"
        signal_results['recommended_action'] = 'MONITOR'
        
        if entry_details:
            signal_results['distance_to_breakout'] = entry_details.get('distance_to_breakout_pct', 0)
            signal_results['breakout_level'] = entry_details.get('breakout_level_needed', 0)
            
            if consolidation_info:
                signal_results['consolidation_range'] = {
                    'high': consolidation_info['consolidation_high'],
                    'low': consolidation_info['consolidation_low'],
                    'width_pct': consolidation_info['range_width_pct'],
                    'days': consolidation_info['days_in_consolidation'],
                    'current_position': consolidation_info['current_position_in_range']
                }
    
    return signal_results

class TradeExecutor:
    """
    Executor module for systematic momentum trading system.
    Handles position sizing, risk management, stop loss placement, and exit logic.
    """
    
    def risk_setup(self, account_equity=100000, max_risk_percent=2.0, atr_period=14):
        """
        Initialize the executor with account parameters.
        
        Parameters:
        -----------
        account_equity : float
            Total account equity (default: $100,000)
        max_risk_percent : float
            Maximum risk per trade as percentage of equity (default: 2%)
        atr_period : int
            Period for Average True Range calculation (default: 14)
        """
        self.account_equity = account_equity
        self.max_risk_percent = max_risk_percent
        self.atr_period = atr_period
        self.max_risk_amount = account_equity * (max_risk_percent / 100)
        
        # Active positions tracking
        self.positions = {}
        
        print(f"✓ Executor initialized:")
        print(f"  Account Equity: ${account_equity:,.2f}")
        print(f"  Max Risk per Trade: {max_risk_percent}% (${self.max_risk_amount:,.2f})")
        print(f"  ATR Period: {atr_period} days")
    
    # =================== RISK MANAGEMENT & POSITION SIZING ===================
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        Calculate position size based on fixed 2% risk of account equity.
        
        Formula: Position Size = Max Risk Amount / (Entry Price - Stop Loss Price)
        
        Parameters:
        -----------
        entry_price : float
            Entry price for the trade
        stop_loss_price : float
            Stop loss price
            
        Returns:
        --------
        dict : Position size details including shares and dollar amounts
        """
        if entry_price <= stop_loss_price:
            return {"error": "Entry price must be greater than stop loss price"}
        
        # Calculate risk per share
        risk_per_share = entry_price - stop_loss_price
        
        # Calculate maximum shares based on 2% risk
        max_shares = self.max_risk_amount / risk_per_share
        
        # Round down to whole shares
        shares = int(max_shares)
        
        # Calculate actual position value and risk
        position_value = shares * entry_price
        actual_risk = shares * risk_per_share
        actual_risk_percent = (actual_risk / self.account_equity) * 100 #Shares always rounded down, so overall risk will always be ≤ 2% regardless. It's to notify traders on the risk they're currently taking
        
        position_details = {
            'shares': shares,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'risk_per_share': risk_per_share,
            'position_value': position_value,
            'position_percent_of_account': (position_value / self.account_equity) * 100,
            'actual_risk_amount': actual_risk,
            'actual_risk_percent': actual_risk_percent
        }
        
        return position_details
    
    # =================== STOP LOSS CALCULATION ===================
    
    def calculate_stop_loss(self, stock_data, entry_price, entry_date):
        """
        Calculate stop loss price:
        1. Stop loss = Low of Day (LOD) of the candle that triggers the Buy signal
        2. Constraint: Stop distance (Entry - Stop) must NOT exceed 1.0x ATR(14)
        
        Parameters:
        -----------
        stock_data : pandas.DataFrame
            Historical OHLCV data
        entry_price : float
            Entry price for the trade
        entry_date : datetime
            Date of entry (index in stock_data)
            
        Returns:
        --------
        dict : Stop loss details including price and validation
        """
        try:
            # Get the entry day's data
            entry_day_data = stock_data.loc[entry_date]
            low_of_day = entry_day_data['Low']
            
            # Calculate ATR(14)
            atr = self.calculate_atr(stock_data, self.atr_period)
            current_atr = atr.loc[entry_date] if entry_date in atr.index else atr.iloc[-1]
            
            # Initial stop loss: Low of Day
            initial_stop = low_of_day
            
            # Calculate stop distance
            stop_distance = entry_price - initial_stop
            
            # Constraint: Stop distance must NOT exceed 1.0x ATR(14)
            if stop_distance > current_atr:
                # Adjust stop to be exactly 1.0x ATR from entry
                adjusted_stop = entry_price - current_atr
                
                stop_details = {
                    'stop_loss_price': adjusted_stop,
                    'stop_loss_type': 'ATR_ADJUSTED',
                    'low_of_day': low_of_day,
                    'atr_14': current_atr,
                    'initial_stop_distance': stop_distance,
                    'adjusted_stop_distance': current_atr,
                    'stop_adjusted': True,
                    'adjustment_reason': f"Initial stop ${stop_distance:.2f} > ATR ${current_atr:.2f}",
                    'distance_as_atr_multiple': stop_distance / current_atr
                }
            else:
                stop_details = {
                    'stop_loss_price': initial_stop,
                    'stop_loss_type': 'LOW_OF_DAY',
                    'low_of_day': low_of_day,
                    'atr_14': current_atr,
                    'stop_distance': stop_distance,
                    'stop_adjusted': False,
                    'distance_as_atr_multiple': stop_distance / current_atr
                }
            
            # Add validation
            if stop_details['stop_loss_price'] <= 0:
                stop_details['error'] = "Invalid stop loss price (≤ 0)"
            
            return stop_details
            
        except Exception as e:
            return {"error": f"Error calculating stop loss: {str(e)}"}
    
    def calculate_atr(self, stock_data, period=14):
        """
        Calculate Average True Range (ATR) for volatility measurement.
        
        True Range = max(High - Low, abs(High - Prev Close), abs(Low - Prev Close))
        ATR = SMA of True Range over specified period
        
        Parameters:
        -----------
        stock_data : pandas.DataFrame
            Historical OHLCV data
        period : int
            Period for ATR calculation (default: 14)
            
        Returns:
        --------
        pandas.Series : ATR values
        """
        # Calculate True Range
        high_low = stock_data['High'] - stock_data['Low']
        high_close_prev = abs(stock_data['High'] - stock_data['Close'].shift(1))
        low_close_prev = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # Calculate ATR as Simple Moving Average of True Range
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    # =================== EXIT LOGIC (TRAILING STOP) ===================
    
    def calculate_trailing_stop(self, stock_data, entry_price, entry_date, sma_period=10):
        """
        Implement trailing stop using 10-day SMA to exit the entire position.
        
        Logic: When price closes below 10-day SMA, exit the position.
        
        Parameters:
        -----------
        stock_data : pandas.DataFrame
            Historical OHLCV data
        entry_price : float
            Entry price for the trade
        entry_date : datetime
            Date of entry
        sma_period : int
            Period for Simple Moving Average (default: 10)
            
        Returns:
        --------
        dict : Trailing stop details including exit signals
        """
        try:
            # Find position of entry date in the data
            if entry_date not in stock_data.index:
                return {"error": f"Entry date {entry_date} not in stock data"}
            
            entry_idx = stock_data.index.get_loc(entry_date)
            
            # Get data from entry date onward
            data_from_entry = stock_data.iloc[entry_idx:]
            
            if len(data_from_entry) < sma_period:
                return {"error": f"Not enough data after entry for {sma_period}-day SMA"}
            
            # Calculate 10-day SMA
            sma_10 = data_from_entry['Close'].rolling(window=sma_period).mean()
            
            # Check for exit signals
            exit_signals = []
            current_price = stock_data['Close'].iloc[-1]
            
            for idx, (date, row) in enumerate(data_from_entry.iterrows()):
                # Skip first sma_period-1 days (SMA needs data)
                if idx < sma_period - 1:
                    continue
                
                current_close = row['Close']
                current_sma = sma_10.loc[date]
                
                # Exit signal: Close price crosses below SMA
                if current_close < current_sma:
                    exit_signals.append({
                        'exit_date': date,
                        'exit_price': current_close,
                        'sma_10_at_exit': current_sma,
                        'days_held': idx + 1,
                        'profit_loss': current_close - entry_price,
                        'profit_loss_pct': ((current_close - entry_price) / entry_price) * 100
                    })
            
            # Current status
            current_sma = sma_10.iloc[-1]
            price_below_sma = current_price < current_sma
            
            trailing_stop_info = {
                'current_price': current_price,
                'current_sma_10': current_sma,
                'price_below_sma': price_below_sma,
                'distance_to_sma': current_price - current_sma,
                'distance_to_sma_pct': ((current_price - current_sma) / current_price) * 100,
                'exit_signals': exit_signals,
                'should_exit_now': price_below_sma,
                'days_since_entry': len(data_from_entry) - 1
            }
            
            # If there are exit signals, add the first one (earliest exit)
            if exit_signals:
                first_exit = exit_signals[0]
                trailing_stop_info.update({
                    'first_exit_signal': first_exit['exit_date'],
                    'first_exit_price': first_exit['exit_price'],
                    'first_exit_profit_pct': first_exit['profit_loss_pct'],
                    'days_to_first_exit': first_exit['days_held']
                })
            
            return trailing_stop_info
            
        except Exception as e:
            return {"error": f"Error calculating trailing stop: {str(e)}"}
    
    # =================== COMPLETE TRADE EXECUTION ===================
    
    def execute_trade(self, stock_data, symbol, entry_details, consolidation_info):
        """
        Complete trade execution pipeline.
        
        Parameters:
        -----------
        stock_data : pandas.DataFrame
            Historical OHLCV data
        symbol : str
            Stock ticker symbol
        entry_details : dict
            From entry_trigger() function
        consolidation_info : dict
            From consolidation() function
            
        Returns:
        --------
        dict : Complete trade execution plan
        """
        print(f"\n{'='*80}")
        print(f"TRADE EXECUTION PLAN: {symbol}")
        print('='*80)
        
        trade_plan = {
            'symbol': symbol,
            'execution_timestamp': datetime.now(),
            'status': 'ANALYSIS_COMPLETE',
            'warnings': [],
            'errors': []
        }
        
        # Extract key information
        entry_price = entry_details.get('entry_price', 0)
        entry_date = entry_details.get('entry_date')
        breakout_level = entry_details.get('breakout_level', 0)
        stop_loss_level = entry_details.get('stop_loss_level', 0)  # From consolidation low
        
        if entry_price <= 0 or not entry_date:
            trade_plan['status'] = 'INVALID_ENTRY'
            trade_plan['errors'].append("Invalid entry price or date")
            return trade_plan
        
        # ========== STEP 1: CALCULATE STOP LOSS ==========
        print(f"\n1. STOP LOSS CALCULATION:")
        stop_details = self.calculate_stop_loss(stock_data, entry_price, entry_date)
        
        if 'error' in stop_details:
            trade_plan['status'] = 'STOP_LOSS_ERROR'
            trade_plan['errors'].append(stop_details['error'])
            return trade_plan
        
        # Use the calculated stop loss (may be adjusted by ATR constraint)
        final_stop_price = stop_details['stop_loss_price']
        
        # Validate stop loss is below entry
        if final_stop_price >= entry_price:
            trade_plan['status'] = 'INVALID_STOP'
            trade_plan['errors'].append(f"Stop loss ${final_stop_price:.2f} ≥ entry ${entry_price:.2f}")
            return trade_plan
        
        print(f"   Initial Stop (LOD): ${stop_details.get('low_of_day', 0):.2f}")
        print(f"   ATR(14): ${stop_details.get('atr_14', 0):.2f}")
        print(f"   Final Stop Price: ${final_stop_price:.2f}")
        print(f"   Stop Type: {stop_details.get('stop_loss_type', 'UNKNOWN')}")
        
        if stop_details.get('stop_adjusted', False):
            print(f"   ⚠️  Stop adjusted: {stop_details.get('adjustment_reason', '')}")
            trade_plan['warnings'].append(stop_details.get('adjustment_reason', 'Stop adjusted for ATR constraint'))
        
        # ========== STEP 2: CALCULATE POSITION SIZE ==========
        print(f"\n2. POSITION SIZING (2% Risk Rule):")
        position_details = self.calculate_position_size(entry_price, final_stop_price)
        
        if 'error' in position_details:
            trade_plan['status'] = 'POSITION_SIZE_ERROR'
            trade_plan['errors'].append(position_details['error'])
            return trade_plan
        
        if position_details['shares'] == 0:
            trade_plan['status'] = 'POSITION_TOO_SMALL'
            trade_plan['warnings'].append("Position size is 0 shares - risk too high relative to account")
            print(f"   ⚠️  Position size is 0 shares")
            print(f"   Risk per share: ${position_details['risk_per_share']:.2f}")
            print(f"   Max risk amount: ${self.max_risk_amount:,.2f}")
        else:
            print(f"   Shares to buy: {position_details['shares']:,}")
            print(f"   Position value: ${position_details['position_value']:,.2f}")
            print(f"   Position % of account: {position_details['position_percent_of_account']:.1f}%")
            print(f"   Actual risk: ${position_details['actual_risk_amount']:,.2f}")
            print(f"   Actual risk %: {position_details['actual_risk_percent']:.1f}%")
        
        # ========== STEP 3: CALCULATE TRAILING STOP EXIT ==========
        print(f"\n3. EXIT STRATEGY (10-day SMA Trailing Stop):")
        trailing_stop_info = self.calculate_trailing_stop(stock_data, entry_price, entry_date)
        
        if 'error' in trailing_stop_info:
            print(f"   ⚠️  {trailing_stop_info['error']}")
            trade_plan['warnings'].append(trailing_stop_info['error'])
        else:
            print(f"   Current price: ${trailing_stop_info['current_price']:.2f}")
            print(f"   Current 10-day SMA: ${trailing_stop_info['current_sma_10']:.2f}")
            print(f"   Distance to SMA: ${trailing_stop_info['distance_to_sma']:.2f}")
            print(f"   Should exit now? {'YES' if trailing_stop_info['should_exit_now'] else 'NO'}")
            
            if trailing_stop_info.get('first_exit_signal'):
                print(f"   First exit would have been: {trailing_stop_info['first_exit_signal'].date()}")
                print(f"   Exit price: ${trailing_stop_info['first_exit_price']:.2f}")
                print(f"   P&L: {trailing_stop_info['first_exit_profit_pct']:+.1f}%")
        
        # ========== STEP 4: COMPILE TRADE PLAN ==========
        trade_plan.update({
            'entry_price': entry_price,
            'entry_date': entry_date,
            'breakout_level': breakout_level,
            'stop_loss_details': stop_details,
            'position_details': position_details,
            'trailing_stop_details': trailing_stop_info,
            
            # Summary metrics
            'risk_reward_ratio': self.calculate_risk_reward(
                entry_price, final_stop_price, consolidation_info
            ),
            'volatility_adjusted_position': self.adjust_for_volatility(
                position_details, stock_data, entry_date
            )
        })
        
        # Add consolidation context
        if consolidation_info:
            trade_plan['consolidation_context'] = {
                'consolidation_high': consolidation_info.get('consolidation_high', 0),
                'consolidation_low': consolidation_info.get('consolidation_low', 0),
                'range_width_pct': consolidation_info.get('range_width_pct', 0),
                'days_in_consolidation': consolidation_info.get('days_in_consolidation', 0)
            }
        
        print(f"\n{'='*80}")
        print(f"TRADE EXECUTION SUMMARY:")
        print('='*80)
        
        if position_details['shares'] > 0:
            print(f"✅ EXECUTE TRADE:")
            print(f"   Buy {position_details['shares']:,} shares of {symbol}")
            print(f"   Entry: ${entry_price:.2f}")
            print(f"   Stop Loss: ${final_stop_price:.2f}")
            print(f"   Position Value: ${position_details['position_value']:,.2f}")
            print(f"   Max Loss: ${position_details['actual_risk_amount']:,.2f} ({position_details['actual_risk_percent']:.1f}%)")
            print(f"   Exit Strategy: Sell when price closes below 10-day SMA")
        else:
            print(f"⛔ DO NOT EXECUTE:")
            print(f"   Position size is 0 shares")
            print(f"   Risk per share (${position_details['risk_per_share']:.2f}) too high for account")
        
        print('='*80)
        
        return trade_plan
    
    # =================== HELPER METHODS ===================
    
    def calculate_risk_reward(self, entry_price, stop_price, consolidation_info):
        """
        Calculate risk-reward ratio based on consolidation range.
        Target could be measured move of consolidation range.
        """
        if not consolidation_info:
            return {"error": "No consolidation info"}
        
        consolidation_high = consolidation_info.get('consolidation_high', 0)
        consolidation_low = consolidation_info.get('consolidation_low', 0)
        
        if consolidation_high <= consolidation_low:
            return {"error": "Invalid consolidation range"}
        
        # Risk = Entry - Stop
        risk = entry_price - stop_price
        
        # Reward 1: Breakout target (1x range above breakout)
        range_height = consolidation_high - consolidation_low
        target_1 = consolidation_high + range_height
        reward_1 = target_1 - entry_price
        rr_ratio_1 = reward_1 / risk if risk > 0 else 0
        
        # Reward 2: Previous peak (if consolidation high < original peak)
        original_peak = consolidation_info.get('peak_63day_price', 0)
        if original_peak > consolidation_high:
            reward_2 = original_peak - entry_price
            rr_ratio_2 = reward_2 / risk if risk > 0 else 0
        else:
            reward_2 = 0
            rr_ratio_2 = 0
        
        return {
            'risk_per_share': risk,
            'target_1': target_1,
            'reward_1': reward_1,
            'rr_ratio_1': rr_ratio_1,
            'target_2': original_peak,
            'reward_2': reward_2,
            'rr_ratio_2': rr_ratio_2,
            'consolidation_range_height': range_height
        }
    
    def adjust_for_volatility(self, position_details, stock_data, entry_date):
        """
        Optional: Adjust position size based on recent volatility.
        """
        # Calculate recent volatility (standard deviation of returns)
        recent_returns = stock_data['Close'].pct_change().dropna()
        if len(recent_returns) >= 20:
            recent_volatility = recent_returns.tail(20).std() * np.sqrt(252)  # Annualized
            
            # Reduce position if volatility is high
            if recent_volatility > 0.4:  # 40% annualized volatility
                adjustment_factor = 0.5  # Cut position in half
                adjusted_shares = int(position_details['shares'] * adjustment_factor)
                
                return {
                    'original_shares': position_details['shares'],
                    'adjusted_shares': adjusted_shares,
                    'adjustment_factor': adjustment_factor,
                    'recent_volatility': recent_volatility,
                    'adjustment_reason': f"High volatility: {recent_volatility:.1%}"
                }
        
        return {
            'original_shares': position_details['shares'],
            'adjusted_shares': position_details['shares'],
            'adjustment_factor': 1.0,
            'recent_volatility': None,
            'adjustment_reason': "No adjustment needed"
        }