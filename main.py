# =================== main.py ===================
"""
Main orchestration file - ties all modules together.
"""

import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

from config import TECH_STOCKS
from screener import run_screener
from signaller import run_signaller
from executor import TradeExecutor


def safe_download(symbol, period="200d"):
    """Safely download single stock data."""
    data = yf.download(symbol, period=period, progress=False, auto_adjust=False)
    
    # Fix MultiIndex issue
    if isinstance(data.columns, pd.MultiIndex):
        try:
            data = data[symbol].copy()
        except:
            data = data.iloc[:, :6].copy()
            data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    
    return data


def run_full_system(symbol, account_equity=100000):
    """
    Run the complete trading system on a single symbol.
    """
    print(f"\n{'='*80}")
    print(f"RUNNING FULL SYSTEM: {symbol}")
    print('='*80)
    
    # Fetch data
    data = safe_download(symbol, period="200d")
    print(f"✓ Loaded {len(data)} days of data")
    print(f"  Current price: ${data['Close'].iloc[-1]:.2f}")
    
    # ===== PHASE II: SCREENER =====
    print(f"\n📊 PHASE II: SCREENER")
    screener_passed, screener_msg = run_screener(data, symbol)
    print(f"  {screener_msg}")
    
    if not screener_passed:
        print(f"\n❌ System stopped: Failed screener")
        return None
    
    # ===== PHASE III: SIGNALLER =====
    print(f"\n📈 PHASE III: SIGNALLER")
    signal = run_signaller(data, symbol)
    
    for msg in signal['messages']:
        print(f"  {msg}")
    
    print(f"\n  FINAL SIGNAL: {signal['signal']}")
    
    if signal['signal'] != 'BUY':
        print(f"\n❌ System stopped: No BUY signal")
        return signal
    
    # ===== PHASE IV: EXECUTOR =====
    print(f"\n💰 PHASE IV: EXECUTOR")
    executor = TradeExecutor(account_equity=account_equity)
    trade_plan = executor.execute_trade(
        data, 
        symbol,
        signal['entry_details'],
        signal['consolidation_info']
    )
    
    return {
        'screener_result': screener_msg,
        'signal_result': signal,
        'trade_plan': trade_plan
    }


def scan_all_stocks():
    """
    Scan all 20 tech stocks for BUY signals.
    """
    print(f"\n{'='*80}")
    print(f"SCANNING {len(TECH_STOCKS)} TECH STOCKS")
    print('='*80)
    
    results = []
    
    for i, symbol in enumerate(TECH_STOCKS, 1):
        print(f"\n[{i}/{len(TECH_STOCKS)}] {symbol}...")
        
        try:
            data = safe_download(symbol, period="200d")
            
            if len(data) < 63:
                print(f"  ⚠️  Insufficient data")
                continue
            
            # Run screener
            screener_passed, _ = run_screener(data, symbol)
            if not screener_passed:
                print(f"  ❌ Failed screener")
                continue
            
            # Run signaller
            signal = run_signaller(data, symbol)
            
            if signal['signal'] == 'BUY':
                print(f"  ✅ BUY SIGNAL at ${signal['current_price']:.2f}")
                results.append({
                    'symbol': symbol,
                    'price': signal['current_price'],
                    'signal': 'BUY'
                })
            elif signal['signal'] == 'HOLD':
                print(f"  ⏸️  HOLD (consolidating)")
                results.append({
                    'symbol': symbol,
                    'price': signal['current_price'],
                    'signal': 'HOLD'
                })
            else:
                print(f"  ❌ {signal['signal']}")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
    
    # Summary
    buy_signals = [r for r in results if r['signal'] == 'BUY']
    hold_signals = [r for r in results if r['signal'] == 'HOLD']
    
    print(f"\n{'='*80}")
    print(f"SCAN COMPLETE")
    print('='*80)
    print(f"✅ BUY signals: {len(buy_signals)}")
    for r in buy_signals:
        print(f"   • {r['symbol']}: ${r['price']:.2f}")
    print(f"\n⏸️  HOLD signals: {len(hold_signals)}")
    
    return results


if __name__ == "__main__":
    # Example: Run on NVDA
    run_full_system("NVDA")
    
    # Uncomment to scan all stocks
    # scan_all_stocks()