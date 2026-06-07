"""
strategies/strategy_3.py
RSI Mean Reversion - OOS Validation & Liquidity-Adjusted Regime Filtering
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- CONFIGURATION ---
TICKERS = ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "PEP", "COST"] # Subset of NDX
BENCHMARK = "QQQ"
START_DATE = "2024-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
COMMISSION_BPS = 0.0003  # 3 bps slippage/commission
RISK_PER_TRADE = 0.01    # 1% equity at risk
MAX_WEIGHT = 0.10        # 10% max allocation
ADT_LIMIT = 0.05         # Max 5% of 20-day ADT

def get_wilders_rsi(data, period=4):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest():
    # Download data
    data = yf.download(TICKERS + [BENCHMARK], start="2023-12-01", end=END_DATE)['Adj Close']
    vol = yf.download(TICKERS, start="2023-12-01", end=END_DATE)['Volume']
    
    qqq_sma = data[BENCHMARK].rolling(200).mean()
    
    results = []
    
    for ticker in TICKERS:
        df = pd.DataFrame({
            'price': data[ticker],
            'sma200': data[ticker].rolling(200).mean(),
            'atr': data[ticker].diff().abs().rolling(20).mean(), # Simplified ATR
            'adt': (data[ticker] * vol[ticker]).rolling(20).mean(),
            'rsi': get_wilders_rsi(data[ticker], 4),
            'adx': 25 # Placeholder for ADX logic
        }).dropna()
        
        # Filter for OOS period
        df = df[df.index >= START_DATE]
        
        # Logic Loop
        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            
            # Entry Conditions
            macro_filter = data[BENCHMARK].iloc[i] > qqq_sma.iloc[i]
            idio_filter = curr['price'] > curr['sma200']
            liquidity_filter = (1000000 * RISK_PER_TRADE) < (curr['adt'] * ADT_LIMIT)
            
            if macro_filter and idio_filter and liquidity_filter and curr['rsi'] < 30:
                # Position Sizing
                risk_amount = 1000000 * RISK_PER_TRADE
                pos_size = risk_amount / (3 * curr['atr'])
                weight = (pos_size * curr['price']) / 1000000
                
                if weight > MAX_WEIGHT: pos_size = (MAX_WEIGHT * 1000000) / curr['price']
                
                # Exit logic (Simplified simulation)
                # In a real production system, use a state-machine or event-driven loop
                results.append({
                    'ticker': ticker,
                    'entry_date': df.index[i],
                    'entry_price': curr['price'],
                    'size': pos_size
                })

    return pd.DataFrame(results)

if __name__ == "__main__":
    trades = run_backtest()
    print("OOS Validation Simulation Complete.")
    print(f"Total Signals Generated: {len(trades)}")
    print(trades.head())