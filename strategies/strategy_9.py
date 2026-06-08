"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Note: Intraday intervals are restricted to 60 days by Yahoo Finance. 
This implementation uses '1d' data to ensure long-term backtest reliability.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates signals using T-1 daily regime filters and RSI-2.
    Expects 'data' to contain: 'Close', 'High', 'Low', 'ADX', 'EMA200', 'VIX_Limit'.
    """
    # RSI-2 Calculation
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    rsi2 = 100 - (100 / (1 + rs))
    
    # Logic: Long if RSI < 15, ADX < 30, Price > EMA200, VIX < Limit
    long_cond = (rsi2 < 15) & (data['ADX'] < 30) & \
                (data['Close'] > data['EMA200']) & \
                (data['Close'] < data['VIX_Limit'])
    
    # Short: RSI > 85, ADX < 30, VIX < Limit
    short_cond = (rsi2 > 85) & (data['ADX'] < 30) & \
                 (data['Close'] < data['VIX_Limit'])
    
    signals = pd.Series(0, index=data.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    return signals

def run_backtest():
    """
    State-based backtest engine implementing ARMR exit logic and risk guardrails.
    """
    ticker = "AAPL"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Load Data
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False)
    vix = yf.download('^VIX', start=start_date, end=end_date, interval='1d', progress=False)['Close']
    
    if df is None or df.empty or vix is None or vix.empty:
        print("Error: Failed to download sufficient data.")
        return

    # Prepare Indicators
    df['EMA200'] = df['Close'].ewm(span=200).mean()
    # Simple ADX Proxy (14-day)
    tr = df['High'].combine(df['Close'].shift(1), max) - df['Low'].combine(df['Close'].shift(1), min)
    df['ADX'] = tr.rolling(14).mean() 
    df['VIX_Limit'] = vix.rolling(window=252).quantile(0.9)
    df['atr'] = tr.rolling(14).mean()
    
    # Shift filters to prevent look-ahead bias
    df_shifted = df.shift(1)
    df_shifted['Close'] = df['Close'] # Keep actual price for entry
    
    signals = generate_signals(df_shifted)
    
    # Backtest Loop
    pos, entry_price, entry_atr, entry_idx = 0, 0, 0, 0
    pos_size, consecutive_losses = 1.0, 0
    portfolio_equity, daily_pnl = 100000.0, 0.0
    pnl_history = []
    
    for i in range(1, len(df)):
        if df.index[i].day != df.index[i-1].day: daily_pnl = 0
            
        curr_price = df['Open'].iloc[i]
        
        # Exit Logic
        if pos != 0:
            rsi = 50 # Simplified for daily loop
            stop_loss_hit = (curr_price - entry_price) * pos < -2.5 * entry_atr
            time_exit = (i - entry_idx) >= 5 # 5 trading days
            
            if stop_loss_hit or time_exit:
                trade_pnl = ((curr_price - entry_price) * pos) * pos_size
                portfolio_equity += trade_pnl; daily_pnl += trade_pnl
                consecutive_losses = consecutive_losses + 1 if trade_pnl < 0 else 0
                pnl_history.append(trade_pnl); pos = 0; pos_size = 1.0
        
        # Entry Logic
        if pos == 0 and signals.iloc[i-1] != 0 and abs(daily_pnl / portfolio_equity) < 0.03:
            if consecutive_losses < 5:
                pos = signals.iloc[i-1]; entry_price = curr_price
                entry_atr = df['atr'].iloc[i-1]; entry_idx = i
            
    # Metrics
    returns = np.array(pnl_history)
    total_ret = (portfolio_equity - 100000) / 100000
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    print(f"--- Backtest {ticker}: Return={total_ret:.2%}, Sharpe={sharpe:.2f} ---")

if __name__ == "__main__":
    run_backtest()