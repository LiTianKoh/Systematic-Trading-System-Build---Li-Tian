# =================== interactive_test.py ===================
"""
Interactive Test Console for Trading System
Run this file to test any stock in real-time
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import trading system modules
from config import TECH_STOCKS
from screener import run_screener
from signaller import run_signaller
from executor import TradeExecutor
from main import safe_download


class TradingTestConsole:
    """Interactive console for testing trading system on any stock."""
    
    def __init__(self):
        self.results_history = []
        self.current_data = None
        self.current_symbol = None
        
    def print_header(self, title):
        """Print a clean section header."""
        print(f"\n{'╔' + '═'*78 + '╗'}")
        print(f"║{title:^78}║")
        print(f"{'╚' + '═'*78 + '╝'}")
    
    def print_section(self, title):
        """Print a section header."""
        print(f"\n┌{'─'*78}┐")
        print(f"│ {title:<77}│")
        print(f"└{'─'*78}┘")
    
    def print_success(self, message):
        print(f"  ✅ {message}")
    
    def print_warning(self, message):
        print(f"  ⚠️  {message}")
    
    def print_error(self, message):
        print(f"  ❌ {message}")
    
    def print_info(self, message):
        print(f"  ℹ️  {message}")
    
    def print_table(self, headers, rows):
        """Print a formatted table."""
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Print header
        header_str = "  "
        for i, h in enumerate(headers):
            header_str += f" {h:<{col_widths[i]}} │"
        print(header_str[:-1])  # Remove last │
        
        # Print separator
        sep = "  " + "─" * (sum(col_widths) + 3 * (len(headers) - 1))
        print(sep)
        
        # Print rows
        for row in rows:
            row_str = "  "
            for i, cell in enumerate(row):
                row_str += f" {str(cell):<{col_widths[i]}} │"
            print(row_str[:-1])
    
    def get_user_input(self):
        """Get stock symbol from user."""
        print("\n" + "─" * 80)
        print("📈 TRADING SYSTEM TEST CONSOLE")
        print("─" * 80)
        print("\nOptions:")
        print("  1. Enter a stock ticker (e.g., NVDA, AAPL, MSFT)")
        print("  2. Enter 'list' to see available tech stocks")
        print("  3. Enter 'scan' to scan all tech stocks")
        print("  4. Enter 'history' to see previous tests")
        print("  5. Enter 'exit' to quit")
        print("\n" + "─" * 80)
        
        choice = input("\n🔍 Enter ticker: ").strip().upper()
        return choice
    
    def list_stocks(self):
        """Display available tech stocks."""
        self.print_section("AVAILABLE TECH STOCKS")
        
        # Display in 5 columns
        cols = 5
        for i in range(0, len(TECH_STOCKS), cols):
            row = TECH_STOCKS[i:i+cols]
            print("  " + "  ".join(f"{s:<6}" for s in row))
        
        print(f"\n  Total: {len(TECH_STOCKS)} highly liquid US tech stocks")
    
    def show_history(self):
        """Show test history."""
        if not self.results_history:
            self.print_warning("No tests in history yet")
            return
        
        self.print_section("TEST HISTORY")
        
        headers = ["Symbol", "Date", "Price", "Signal", "Risk %", "Shares"]
        rows = []
        
        for result in self.results_history[-10:]:  # Last 10 tests
            rows.append([
                result['symbol'],
                result['date'].strftime('%H:%M:%S'),
                f"${result['price']:.2f}",
                result['signal'],
                f"{result.get('risk_pct', 0):.1f}%",
                result.get('shares', 0)
            ])
        
        self.print_table(headers, rows)
    
    def test_stock(self, symbol):
        """Test a single stock."""
        self.print_header(f" ANALYZING {symbol} ")
        
        try:
            # Download data
            print(f"\n📥 Downloading data for {symbol}...", end="", flush=True)
            data = safe_download(symbol, period="200d")
            print(" ✅")
            
            if len(data) < 63:
                self.print_error(f"Insufficient data: {len(data)} days (need 63+)")
                return None
            
            # Display stock info
            current_price = data['Close'].iloc[-1]
            if hasattr(current_price, 'iloc') or hasattr(current_price, 'item'):
                current_price = float(current_price)
            
            print(f"\n📊 STOCK SNAPSHOT:")
            print(f"     Price: ${current_price:.2f}")
            print(f"     Date: {data.index[-1].date()}")
            print(f"     Days: {len(data)} trading days")
            print(f"     Range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")
            
            # ===== PHASE II: SCREENER =====
            self.print_section("PHASE II: SCREENER")
            screener_passed, screener_msg = run_screener(data, symbol)
            
            if screener_passed:
                self.print_success(f"PASSED: {screener_msg}")
            else:
                self.print_error(f"FAILED: {screener_msg}")
                return self._save_result(symbol, current_price, "SCREENER_FAIL", data)
            
            # ===== PHASE III: SIGNALLER =====
            self.print_section("PHASE III: SIGNALLER")
            signal = run_signaller(data, symbol)
            
            # Display signal stages
            stage_data = []
            for msg in signal['messages']:
                if 'RISER' in msg:
                    stage = "Riser"
                    result = "✅" if "PASS" in msg else "❌"
                elif 'CONSOLIDATION' in msg:
                    stage = "Consolidation"
                    result = "✅" if "PASS" in msg else "❌"
                elif 'ENTRY' in msg:
                    stage = "Entry"
                    result = "✅" if "BUY" in msg else "⏸️"
                else:
                    continue
                
                # Clean up message
                clean_msg = msg.split(': ')[1] if ': ' in msg else msg
                if len(clean_msg) > 50:
                    clean_msg = clean_msg[:47] + "..."
                
                stage_data.append([stage, result, clean_msg])
            
            self.print_table(["Stage", "Result", "Details"], stage_data)
            
            # Final signal
            if signal['signal'] == 'BUY':
                self.print_success(f"🚀 BUY SIGNAL GENERATED")
            elif signal['signal'] == 'HOLD':
                self.print_warning(f"⏸️  HOLD - Consolidating, waiting for breakout")
            else:
                self.print_error(f"❌ NO SIGNAL - {signal['signal']}")
            
            # Show consolidation info if available
            if signal.get('consolidation_info'):
                ci = signal['consolidation_info']
                print(f"\n     📊 Consolidation Range:")
                print(f"        High: ${ci['consolidation_high']:.2f}")
                print(f"        Low:  ${ci['consolidation_low']:.2f}")
                print(f"        Width: {ci['range_width_pct']:.1f}%")
                print(f"        Days: {ci['days_in_consolidation']}")
            
            # ===== PHASE IV: EXECUTOR (if BUY signal) =====
            trade_plan = None
            if signal['signal'] == 'BUY':
                self.print_section("PHASE IV: EXECUTOR")
                
                executor = TradeExecutor(account_equity=100000)
                trade_plan = executor.execute_trade(
                    data,
                    symbol,
                    signal['entry_details'],
                    signal['consolidation_info']
                )
                
                # Display trade plan
                if trade_plan['status'] == 'READY':
                    pos = trade_plan['position']
                    print(f"\n     💰 TRADE EXECUTION PLAN:")
                    print(f"        Buy {pos['shares']:,} shares @ ${pos['entry_price']:.2f}")
                    print(f"        Stop Loss: ${pos['stop_loss']:.2f}")
                    print(f"        Position: ${pos['position_value']:,.2f} ({pos['position_pct']:.1f}% of account)")
                    print(f"        Risk: ${pos['risk_amount']:,.2f} ({pos['risk_percent']:.1f}%)")
                    
                    # Risk-Reward
                    rr = trade_plan.get('risk_reward', {})
                    if 'rr_ratio_1' in rr:
                        print(f"        Risk/Reward: {rr['rr_ratio_1']:.2f}:1")
                    
                    self.print_success("TRADE READY FOR EXECUTION")
            
            # Save result
            result = self._save_result(
                symbol, 
                current_price, 
                signal['signal'], 
                data, 
                signal, 
                trade_plan
            )
            
            return result
            
        except Exception as e:
            self.print_error(f"Error testing {symbol}: {str(e)}")
            return None
    
    def _save_result(self, symbol, price, signal, data, signal_data=None, trade_plan=None):
        """Save test result to history."""
        result = {
            'symbol': symbol,
            'date': datetime.now(),
            'price': price,
            'signal': signal,
            'data_days': len(data)
        }
        
        if trade_plan and 'position' in trade_plan:
            result['shares'] = trade_plan['position'].get('shares', 0)
            result['risk_pct'] = trade_plan['position'].get('risk_percent', 0)
            result['entry'] = trade_plan['position'].get('entry_price', 0)
            result['stop'] = trade_plan['position'].get('stop_loss', 0)
        
        self.results_history.append(result)
        return result
    
    def scan_all_stocks(self):
        """Scan all tech stocks for signals."""
        self.print_header(" SCANNING ALL TECH STOCKS ")
        
        print(f"\n📊 Scanning {len(TECH_STOCKS)} stocks...\n")
        
        results = []
        
        for i, symbol in enumerate(TECH_STOCKS, 1):
            # Progress bar
            progress = int((i / len(TECH_STOCKS)) * 40)
            bar = '█' * progress + '░' * (40 - progress)
            print(f"\r   [{bar}] {i}/{len(TECH_STOCKS)} {symbol:<6}", end="", flush=True)
            
            try:
                data = safe_download(symbol, period="200d")
                
                if len(data) < 63:
                    continue
                
                # Run screener
                screener_passed, _ = run_screener(data, symbol)
                if not screener_passed:
                    continue
                
                # Run signaller
                signal = run_signaller(data, symbol)
                
                results.append({
                    'symbol': symbol,
                    'price': float(data['Close'].iloc[-1]),
                    'signal': signal['signal'],
                    'consolidation': signal.get('consolidation_passed', False)
                })
                
            except Exception:
                continue
        
        print("\n\n" + "─" * 80)
        print("📊 SCAN RESULTS")
        print("─" * 80)
        
        # Table headers
        headers = ["Symbol", "Price", "Signal", "Status", "Action"]
        rows = []
        
        buy_count = 0
        hold_count = 0
        
        for r in sorted(results, key=lambda x: x['signal']):
            if r['signal'] == 'BUY':
                signal_icon = "✅ BUY"
                status = "Breakout detected"
                action = "🚀 BUY"
                buy_count += 1
            elif r['signal'] == 'HOLD':
                signal_icon = "⏸️  HOLD"
                status = "Consolidating"
                action = "👀 Monitor"
                hold_count += 1
            else:
                signal_icon = "❌ FAIL"
                status = "No setup"
                action = "⏸️ Skip"
            
            rows.append([
                r['symbol'],
                f"${r['price']:.2f}",
                signal_icon,
                status,
                action
            ])
        
        self.print_table(headers, rows)
        
        print(f"\n{'─'*80}")
        print(f"   SUMMARY: ✅ BUY: {buy_count} | ⏸️  HOLD: {hold_count} | ❌ FAIL: {len(results)-buy_count-hold_count}")
        print(f"{'─'*80}")
        
        return results
    
    def run(self):
        """Main interactive loop."""
        while True:
            choice = self.get_user_input()
            
            if choice == 'EXIT':
                self.print_header(" GOODBYE ")
                print("\n  Thank you for using the Trading System Test Console!\n")
                break
            
            elif choice == 'LIST':
                self.list_stocks()
            
            elif choice == 'HISTORY':
                self.show_history()
            
            elif choice == 'SCAN':
                self.scan_all_stocks()
            
            elif choice in TECH_STOCKS or len(choice) <= 5:  # Allow any valid ticker
                self.test_stock(choice)
            
            else:
                self.print_error(f"Unknown ticker: {choice}")
                print("  Try 'list' to see available stocks")


# =================== QUICK TEST FUNCTION ===================
def quick_test(symbol=None):
    """Quick one-line test without the interactive console."""
    if not symbol:
        symbol = input("Enter stock ticker: ").strip().upper()
    
    console = TradingTestConsole()
    console.test_stock(symbol)


# =================== MAIN ===================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Trading System Test Console')
    parser.add_argument('symbol', nargs='?', help='Stock symbol to test (optional)')
    parser.add_argument('--scan', action='store_true', help='Scan all tech stocks')
    parser.add_argument('--quick', action='store_true', help='Quick test mode')
    
    args = parser.parse_args()
    
    if args.symbol:
        # Command line mode: python interactive_test.py NVDA
        console = TradingTestConsole()
        console.test_stock(args.symbol.upper())
    
    elif args.scan:
        # Scan mode: python interactive_test.py --scan
        console = TradingTestConsole()
        console.scan_all_stocks()
    
    elif args.quick:
        # Quick test mode: python interactive_test.py --quick
        quick_test()
    
    else:
        # Interactive mode
        console = TradingTestConsole()
        console.run()