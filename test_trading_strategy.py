# =================== test_trading_strategy.py ===================
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from trading_strategy import *

def safe_download(symbol, period="200d"):
    """Safely download single stock data (no MultiIndex)"""
    data = yf.download(symbol, period=period, progress=False, auto_adjust=False)
    
    # Fix MultiIndex issue
    if isinstance(data.columns, pd.MultiIndex):
        # Extract just this symbol's data
        try:
            data = data[symbol].copy()
        except:
            # Manual column rename
            data = data.iloc[:, :6].copy()
            data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    
    return data

def test_single_stock(symbol="NEM"):
    """Test one stock"""
    print(f"\n🔍 Testing {symbol}...")
    
    data = safe_download(symbol, period="200d")
    print(f"✓ Loaded {len(data)} days of data")
    print(f"  Current price: ${data['Close'].iloc[-1]:.2f}")
    
    signal = signaller(data, symbol)
    print(f"\n📊 FINAL SIGNAL: {signal['final_signal']}")
    
    for msg in signal['stage_messages']:
        print(f"  • {msg}")
    
    return signal

def screen_all_stocks():
    """Screen all 20 tech stocks"""
    print(f"\n{'='*80}")
    print(f"SCREENING {len(tech_stocks)} STOCKS")
    print('='*80)
    
    results = []
    
    for i, symbol in enumerate(tech_stocks, 1):
        print(f"\n[{i}/{len(tech_stocks)}] {symbol}...", end="")
        
        try:
            data = safe_download(symbol, period="200d")
            
            if len(data) < 63:
                print(f" ⚠️ Insufficient data ({len(data)} days)")
                continue
            
            signal = signaller(data, symbol)
            
            if signal['final_signal'] == 'BUY':
                print(f" ✅ BUY (${signal['current_price']:.2f})")
            elif signal['final_signal'] == 'HOLD':
                print(f" ⏸️ HOLD (${signal['current_price']:.2f})")
            else:
                print(f" ❌ {signal['final_signal']}")
            
            results.append({
                'symbol': symbol,
                'signal': signal['final_signal'],
                'price': signal['current_price']
            })
            
        except Exception as e:
            print(f" ❌ Error: {str(e)[:50]}")
    
    # Summary
    buy_count = sum(1 for r in results if r['signal'] == 'BUY')
    hold_count = sum(1 for r in results if r['signal'] == 'HOLD')
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: ✅ BUY: {buy_count} | ⏸️ HOLD: {hold_count} | ❌ FAIL: {len(results)-buy_count-hold_count}")
    print('='*80)
    
    return results

if __name__ == "__main__":
    # Test one stock first
    test_single_stock("NEM")
    
    # Uncomment to screen all stocks
    # screen_all_stocks()