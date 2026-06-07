"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Implements state-based exit logic, T-1 filters, and risk guardrails.
"""

import pandas as pd
import numpy as np
import yfinance as yf

def calculate_indicators(df: pd.DataFrame):
    """Calculates necessary technical indicators."""
    # RSI-2
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    df['rsi2'] = 100 - (100 / (1 + rs))
    
    # ATR (14-period)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['atr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
    
    return df

def generate_signals(df_15m: pd.DataFrame, daily_data: pd.DataFrame, vix_data: pd.Series) -> pd.Series:
    """Generates signals using T-1 daily filters."""
    daily_regime = daily_data.shift(1)
    vix_limit = vix_data.rolling(252).quantile(0.9).shift(1)
    
    df = df_15m.copy()
    df['date'] = df.index.date
    df = df.merge(daily_regime[['ADX', 'EMA200']], left_on='date', right_index=True, how='left')
    df = df.merge(vix_limit.rename('vix_limit'), left_on='date', right_index=True, how='left')
    
    df = calculate_indicators(df)
    
    long_cond = (df['rsi2'] < 15) & (df['ADX'] < 30) & (df['Close'] > df['EMA200']) & (df['Close'] < df['vix_limit'])
    short_cond = (df['rsi2'] > 85) & (df['ADX'] < 30) & (df['Close'] < df['vix_limit'])
    
    signals = pd.Series(0, index=df.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    return signals

def run_backtest(ticker: str):
    """Backtest engine incorporating state-based exit logic."""
    df_15m = yf.download(ticker, period='1y', interval='15m')
    df_daily = yf.download(ticker, period='1y', interval='1d')
    # Simple ADX placeholder logic (normally requires high/low/close)
    df_daily['EMA200'] = df_daily['Close'].ewm(span=200).mean()
    df_daily['ADX'] = 20
    vix = yf.download('^VIX', period='1y')['Close']
    
    signals = generate_signals(df_15m, df_daily, vix)
    
    # State tracking
    position = 0
    entry_price = 0
    entry_idx = 0
    pnl = []
    consecutive_losses = 0
    
    for i in range(len(df_15m)):
        curr_price = df_15m['Close'].iloc[i]
        
        # Exit Logic
        if position != 0:
            days_held = (df_15m.index[i] - df_15m.index[entry_idx]).days
            rsi_val = df_15m['rsi2'].iloc[i]
            
            exit_signal = False
            if position == 1 and (rsi_val > 60 or days_held >= 5): exit_signal = True
            if position == -1 and (rsi_val < 40 or days_held >= 5): exit_signal = True
            
            if exit_signal:
                trade_pnl = (curr_price - entry_price) * position
                pnl.append(trade_pnl)
                if trade_pnl < 0: consecutive_losses += 1
                else: consecutive_losses = 0
                position = 0
        
        # Entry Logic
        if position == 0 and signals.iloc[i] != 0:
            if consecutive_losses >= 5: continue # Reduction rule
            position = signals.iloc[i]
            entry_price = curr_price
            entry_idx = i
            
    # Calculate Metrics
    returns = np.array(pnl)
    total_return = np.sum(returns)
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    
    print(f"--- Backtest Results: {ticker} ---")
    print(f"Total PnL: {total_return:.2f}")
    print(f"Sharpe Ratio: {sharpe:.2f}")

if __name__ == "__main__":
    run_backtest("AAPL")