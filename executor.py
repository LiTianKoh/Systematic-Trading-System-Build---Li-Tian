# =================== executor.py ===================
"""
Phase IV: The Executor
- Risk Management: Fixed 2% risk of $100,000 account
- Stop Loss: LOD of entry candle, constrained to ≤ 1.0x ATR(14)
- Exit Logic: Trailing stop using 10-day SMA
"""

import pandas as pd
import numpy as np
from datetime import datetime
from config import ACCOUNT_EQUITY, MAX_RISK_PERCENT, ATR_PERIOD, TRAILING_SMA_PERIOD


class TradeExecutor:
    """
    Executor module for risk management and trade execution.
    """
    
    def __init__(self, account_equity=ACCOUNT_EQUITY, 
                 max_risk_percent=MAX_RISK_PERCENT, 
                 atr_period=ATR_PERIOD):
        
        self.account_equity = account_equity
        self.max_risk_percent = max_risk_percent
        self.atr_period = atr_period
        self.max_risk_amount = account_equity * (max_risk_percent / 100)
        self.positions = {}
    
    # ===== RISK MANAGEMENT & POSITION SIZING =====
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        Calculate position size based on 2% risk rule.
        Shares = floor(Max Risk Amount / Risk Per Share)
        """
        if entry_price <= stop_loss_price:
            return {"error": "Entry must be > stop loss"}
        
        risk_per_share = entry_price - stop_loss_price
        max_shares = self.max_risk_amount / risk_per_share
        shares = int(max_shares)  # Round down for conservative risk
        
        position_value = shares * entry_price
        actual_risk = shares * risk_per_share
        actual_risk_pct = (actual_risk / self.account_equity) * 100
        
        return {
            'shares': shares,
            'entry_price': entry_price,
            'stop_loss': stop_loss_price,
            'risk_per_share': risk_per_share,
            'position_value': position_value,
            'position_pct': (position_value / self.account_equity) * 100,
            'risk_amount': actual_risk,
            'risk_percent': actual_risk_pct,
            'max_risk_allowed': self.max_risk_amount,
            'risk_utilization': (actual_risk / self.max_risk_amount) * 100
        }
    
    # ===== STOP LOSS CALCULATION =====
    
    def calculate_atr(self, stock_data, period=ATR_PERIOD):
        """Calculate Average True Range for volatility measurement."""
        high_low = stock_data['High'] - stock_data['Low']
        high_close_prev = abs(stock_data['High'] - stock_data['Close'].shift(1))
        low_close_prev = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def calculate_stop_loss(self, stock_data, entry_price, entry_date):
        """
        Calculate stop loss with ATR constraint:
        1. Start with Low of Day (LOD) of entry candle
        2. If stop distance > 1.0x ATR, adjust to entry - ATR
        """
        try:
            # Get LOD of entry day
            entry_day = stock_data.loc[entry_date]
            low_of_day = entry_day['Low']
            
            if hasattr(low_of_day, 'iloc') or hasattr(low_of_day, 'item'):
                low_of_day = float(low_of_day)
            
            # Calculate ATR
            atr = self.calculate_atr(stock_data, self.atr_period)
            current_atr = atr.loc[entry_date] if entry_date in atr.index else atr.iloc[-1]
            
            if hasattr(current_atr, 'iloc') or hasattr(current_atr, 'item'):
                current_atr = float(current_atr)
            
            # Initial stop
            initial_stop = low_of_day
            stop_distance = entry_price - initial_stop
            
            # Check ATR constraint
            if stop_distance > current_atr:
                stop_price = entry_price - current_atr
                stop_type = 'ATR_ADJUSTED'
                adjusted = True
                reason = f"Stop > ATR: ${stop_distance:.2f} > ${current_atr:.2f}"
            else:
                stop_price = initial_stop
                stop_type = 'LOW_OF_DAY'
                adjusted = False
                reason = None
            
            return {
                'stop_loss_price': stop_price,
                'stop_loss_type': stop_type,
                'low_of_day': low_of_day,
                'atr_14': current_atr,
                'stop_distance': entry_price - stop_price,
                'stop_adjusted': adjusted,
                'adjustment_reason': reason,
                'atr_multiple': (entry_price - stop_price) / current_atr
            }
            
        except Exception as e:
            return {"error": f"Stop loss calculation failed: {str(e)}"}
    
    # ===== EXIT LOGIC (TRAILING STOP) =====
    
    def calculate_trailing_stop(self, stock_data, entry_price, entry_date, 
                                sma_period=TRAILING_SMA_PERIOD):
        """
        Implement trailing stop using 10-day SMA.
        Exit when price closes below 10-day SMA.
        """
        try:
            if entry_date not in stock_data.index:
                return {"error": "Entry date not in data"}
            
            entry_idx = stock_data.index.get_loc(entry_date)
            data_from_entry = stock_data.iloc[entry_idx:]
            
            if len(data_from_entry) < sma_period:
                return {"error": f"Need {sma_period} days post-entry"}
            
            # Calculate 10-day SMA
            sma_10 = data_from_entry['Close'].rolling(window=sma_period).mean()
            current_sma = sma_10.iloc[-1]
            current_price = stock_data['Close'].iloc[-1]
            
            if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
                current_price = float(current_price)
            if hasattr(current_sma, 'iloc') or hasattr(current_sma, 'item'):
                current_sma = float(current_sma)
            
            # Check exit signals
            exit_signals = []
            for idx, (date, row) in enumerate(data_from_entry.iterrows()):
                if idx < sma_period - 1:
                    continue
                
                close = row['Close']
                sma = sma_10.loc[date]
                
                if hasattr(close, 'iloc') or hasattr(close, 'item'):
                    close = float(close)
                if hasattr(sma, 'iloc') or hasattr(sma, 'item'):
                    sma = float(sma)
                
                if close < sma:
                    exit_signals.append({
                        'exit_date': date,
                        'exit_price': close,
                        'sma_10': sma,
                        'days_held': idx + 1,
                        'profit_loss': close - entry_price,
                        'profit_loss_pct': ((close - entry_price) / entry_price) * 100
                    })
                    break  # First exit signal only
            
            return {
                'current_price': current_price,
                'current_sma_10': current_sma,
                'price_below_sma': current_price < current_sma,
                'distance_to_sma': current_price - current_sma,
                'distance_pct': ((current_price - current_sma) / current_price) * 100,
                'should_exit_now': current_price < current_sma,
                'exit_signals': exit_signals,
                'days_since_entry': len(data_from_entry) - 1
            }
            
        except Exception as e:
            return {"error": f"Trailing stop calculation failed: {str(e)}"}
    
    # ===== RISK-REWARD ANALYSIS =====
    
    def calculate_risk_reward(self, entry_price, stop_price, consolidation_info):
        """
        Calculate risk-reward ratios based on consolidation range.
        Target 1: Measured move (1x range above breakout)
        Target 2: Original 63-day peak (if higher)
        """
        if not consolidation_info:
            return {"error": "No consolidation data"}
        
        consolidation_high = consolidation_info.get('consolidation_high', 0)
        consolidation_low = consolidation_info.get('consolidation_low', 0)
        
        if consolidation_high <= consolidation_low:
            return {"error": "Invalid consolidation range"}
        
        risk_per_share = entry_price - stop_price
        
        if risk_per_share <= 0:
            return {"error": "Invalid risk"}
        
        # Target 1: Measured move
        range_height = consolidation_high - consolidation_low
        target_1 = consolidation_high + range_height
        reward_1 = target_1 - entry_price
        rr_1 = reward_1 / risk_per_share
        
        # Target 2: Original peak
        original_peak = consolidation_info.get('peak_price', 0)
        if original_peak > consolidation_high:
            reward_2 = original_peak - entry_price
            rr_2 = reward_2 / risk_per_share
        else:
            reward_2 = 0
            rr_2 = 0
        
        return {
            'risk_per_share': risk_per_share,
            'target_1': target_1,
            'reward_1': reward_1,
            'rr_ratio_1': rr_1,
            'target_2': original_peak,
            'reward_2': reward_2,
            'rr_ratio_2': rr_2,
            'range_height': range_height
        }
    
    # ===== TRADE EXECUTION =====
    
    def execute_trade(self, stock_data, symbol, entry_details, consolidation_info):
        """
        Complete trade execution pipeline.
        """
        print(f"\n{'='*80}")
        print(f"EXECUTOR: {symbol} Trade Plan")
        print('='*80)
        
        trade_plan = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'status': 'ANALYZING',
            'warnings': [],
            'errors': []
        }
        
        # Extract entry data
        entry_price = entry_details.get('entry_price', 0)
        entry_date = entry_details.get('entry_date')
        
        if entry_price <= 0 or not entry_date:
            trade_plan['status'] = 'INVALID_ENTRY'
            trade_plan['errors'].append("Invalid entry price/date")
            return trade_plan
        
        # ===== STEP 1: CALCULATE STOP LOSS =====
        print("\n1. STOP LOSS CALCULATION:")
        stop_details = self.calculate_stop_loss(stock_data, entry_price, entry_date)
        
        if 'error' in stop_details:
            trade_plan['status'] = 'STOP_LOSS_ERROR'
            trade_plan['errors'].append(stop_details['error'])
            return trade_plan
        
        final_stop = stop_details['stop_loss_price']
        print(f"   Stop: ${final_stop:.2f} ({stop_details['stop_loss_type']})")
        print(f"   ATR(14): ${stop_details['atr_14']:.2f}")
        
        if stop_details.get('stop_adjusted'):
            print(f"   ⚠️  Adjusted: {stop_details['adjustment_reason']}")
            trade_plan['warnings'].append(stop_details['adjustment_reason'])
        
        # ===== STEP 2: CALCULATE POSITION SIZE =====
        print("\n2. POSITION SIZING (2% Risk Rule):")
        position = self.calculate_position_size(entry_price, final_stop)
        
        if 'error' in position:
            trade_plan['status'] = 'POSITION_ERROR'
            trade_plan['errors'].append(position['error'])
            return trade_plan
        
        if position['shares'] == 0:
            trade_plan['status'] = 'POSITION_TOO_SMALL'
            trade_plan['warnings'].append("0 shares - risk too high")
            print(f"   ⚠️  No shares: Risk/share ${position['risk_per_share']:.2f}")
        else:
            print(f"   Shares: {position['shares']:,}")
            print(f"   Position: ${position['position_value']:,.2f}")
            print(f"   Risk: ${position['risk_amount']:,.2f} ({position['risk_percent']:.1f}%)")
        
        # ===== STEP 3: CALCULATE TRAILING STOP =====
        print("\n3. EXIT STRATEGY (10-day SMA):")
        trailing = self.calculate_trailing_stop(stock_data, entry_price, entry_date)
        
        if 'error' in trailing:
            print(f"   ⚠️  {trailing['error']}")
            trade_plan['warnings'].append(trailing['error'])
        else:
            print(f"   Current SMA(10): ${trailing['current_sma_10']:.2f}")
            print(f"   Distance: ${trailing['distance_to_sma']:.2f}")
            print(f"   Exit now? {'YES' if trailing['should_exit_now'] else 'NO'}")
        
        # ===== STEP 4: RISK-REWARD ANALYSIS =====
        print("\n4. RISK-REWARD ANALYSIS:")
        rr = self.calculate_risk_reward(entry_price, final_stop, consolidation_info)
        
        if 'error' not in rr:
            print(f"   Target 1: ${rr['target_1']:.2f} (RR: {rr['rr_ratio_1']:.2f}:1)")
            if rr['rr_ratio_2'] > 0:
                print(f"   Target 2: ${rr['target_2']:.2f} (RR: {rr['rr_ratio_2']:.2f}:1)")
        
        # ===== COMPILE TRADE PLAN =====
        trade_plan.update({
            'entry_price': entry_price,
            'entry_date': entry_date,
            'stop_loss': stop_details,
            'position': position,
            'trailing_stop': trailing,
            'risk_reward': rr,
            'status': 'READY' if position['shares'] > 0 else 'SKIP'
        })
        
        print(f"\n{'='*80}")
        if position['shares'] > 0:
            print(f"✅ READY TO TRADE: Buy {position['shares']:,} shares of {symbol}")
        else:
            print(f"⏸️  TRADE SKIPPED: Position size = 0")
        print('='*80)
        
        return trade_plan