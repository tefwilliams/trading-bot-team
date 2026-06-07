"""
strategies/strategy_3.py
RSI Mean Reversion - OOS Validation & Liquidity-Adjusted Regime Filtering
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- CONFIGURATION ---
TICKERS = ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "PEP", "COST"]
BENCHMARK = "QQQ"
START_DATE = "2024-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
COMMISSION_BPS = 0.0003
RISK_PER_TRADE = 0.01
MAX_WEIGHT = 0.10
ADT_LIMIT = 0.05
PORTFOLIO_EQUITY = 1_000_000

def get_indicators(df):
    # Wilder's RSI (4)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/4, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/4, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Wilder's ATR (20)
    tr = pd.concat([df['High'] - df['Low'], 
                    (df['High'] - df['Close'].shift(1)).abs(), 
                    (df['Low'] - df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1/20, adjust=False).mean()
    
    # Simple ADX (14) - Placeholder logic for trend strength
    plus_dm = (df['High'] - df['High'].shift(1)).clip(lower=0)
    minus_dm = (df['Low'].shift(1) - df['Low']).clip(lower=0)
    tr_smooth = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
    minus_di = 100 * (minus_dm.ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    df['adx'] = dx.ewm(alpha=1/14, adjust=False).mean()
    
    df['sma200'] = df['Close'].rolling(200).mean()
    df['adt'] = (df['Close'] * df['Volume']).rolling(20).mean()
    return df

def run_backtest():
    tickers_to_fetch = TICKERS + [BENCHMARK]
    data = yf.download(tickers_to_fetch, start="2023-01-01", end=END_DATE, group_by='ticker')
    
    qqq_sma = data[BENCHMARK]['Close'].rolling(200).mean()
    trades = []
    
    for ticker in TICKERS:
        df = get_indicators(data[ticker].copy())
        df = df[df.index >= START_DATE]
        
        active_trade = None
        
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            date = df.index[i]
            
            # Exit Logic
            if active_trade:
                exit_reason = None
                # Profit Target: RSI > 65 or 5% gain
                if curr['rsi'] > 65 or (curr['Close'] / active_trade['entry_price'] - 1) >= 0.05:
                    exit_reason = "PT"
                # Stop Loss: 3x ATR
                elif curr['Close'] <= (active_trade['entry_price'] - 3 * active_trade['entry_atr']):
                    exit_reason = "SL"
                # Time-based Exit: 10 days
                elif (date - active_trade['entry_date']).days >= 10:
                    exit_reason = "TIME"
                
                if exit_reason:
                    active_trade.update({'exit_date': date, 'exit_price': curr['Close'], 'reason': exit_reason})
                    trades.append(active_trade)
                    active_trade = None
                    continue

            # Entry Logic
            if not active_trade:
                macro_filter = data[BENCHMARK]['Close'].iloc[i] > qqq_sma.iloc[i]
                idio_filter = curr['Close'] > curr['sma200']
                liquidity_filter = (PORTFOLIO_EQUITY * RISK_PER_TRADE) < (curr['adt'] * ADT_LIMIT)
                
                if macro_filter and idio_filter and liquidity_filter and curr['rsi'] < 30 and curr['adx'] < 30:
                    pos_size = (PORTFOLIO_EQUITY * RISK_PER_TRADE) / (3 * curr['atr'])
                    weight = (pos_size * curr['Close']) / PORTFOLIO_EQUITY
                    if weight > MAX_WEIGHT: pos_size = (MAX_WEIGHT * PORTFOLIO_EQUITY) / curr['Close']
                    
                    active_trade = {
                        'ticker': ticker, 'entry_date': date, 'entry_price': curr['Close'],
                        'entry_atr': curr['atr'], 'size': pos_size
                    }

    return pd.DataFrame(trades)

if __name__ == "__main__":
    trades = run_backtest()
    if not trades.empty:
        trades['pnl'] = (trades['exit_price'] - trades['entry_price']) * trades['size']
        print(f"OOS Validation Complete. Total Trades: {len(trades)}")
        print(f"Total PnL: ${trades['pnl'].sum():.2f}")
        print(trades[['ticker', 'reason', 'pnl']].head())
    else:
        print("No trades generated in the OOS period.")