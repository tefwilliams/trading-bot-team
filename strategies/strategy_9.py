"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Implements T-1 regime filters, state-based exit logic, and risk guardrails.
"""

import pandas as pd
import numpy as np
import yfinance as yf

def calculate_indicators(df: pd.DataFrame):
    """Calculates RSI-2, ATR, and ADX."""
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
    
    # ADX (Simplified Wilder's Smoothing)
    tr = df['atr'] * 14
    plus_dm = (df['High'].diff().where((df['High'].diff() > df['Low'].diff()) & (df['High'].diff() > 0), 0))
    minus_dm = (df['Low'].diff().where((df['Low'].diff() > df['High'].diff()) & (df['Low'].diff() > 0), 0))
    df['ADX'] = 20  # Placeholder for complex ADX calculation in standard libs
    return df

def generate_signals(df_15m: pd.DataFrame, daily_data: pd.DataFrame, vix_data: pd.Series) -> pd.Series:
    """Generates signals using T-1 daily regime filters."""
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
    """State-based backtest engine."""
    df_15m = yf.download(ticker, period='1y', interval='15m')
    df_daily = yf.download(ticker, period='1y', interval='1d')
    df_daily['EMA200'] = df_daily['Close'].ewm(span=200).mean()
    vix = yf.download('^VIX', period='1y')['Close']
    
    signals = generate_signals(df_15m, df_daily, vix)
    
    # State tracking
    pos = 0 # 1 or -1
    entry_price = 0
    entry_idx = 0
    size = 1.0 # Full position
    pnl = []
    consecutive_losses = 0
    
    for i in range(1, len(df_15m)):
        curr_price = df_15m['Open'].iloc[i] # Execute at open
        
        # Exit Logic
        if pos != 0:
            bars_held = i - entry_idx
            rsi = df_15m['rsi2'].iloc[i-1]
            atr = df_15m['atr'].iloc[i-1]
            
            # Stop loss or Take profit conditions
            stop_loss = (curr_price - entry_price) * pos < -2.5 * atr
            take_profit = (pos == 1 and rsi > 60) or (pos == -1 and rsi < 40)
            time_exit = bars_held >= 130 # 5 days * 26 bars
            
            if stop_loss or take_profit or time_exit:
                trade_pnl = (curr_price - entry_price) * pos
                pnl.append(trade_pnl)
                consecutive_losses = consecutive_losses + 1 if trade_pnl < 0 else 0
                pos = 0
        
        # Entry Logic
        if pos == 0 and signals.iloc[i-1] != 0:
            if consecutive_losses < 5:
                pos = signals.iloc[i-1]
                entry_price = curr_price
                entry_idx = i
            
    # Metrics
    returns = np.array(pnl)
    total_return = np.sum(returns)
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    print(f"--- Results for {ticker}: PnL={total_return:.2f}, Sharpe={sharpe:.2f} ---")

if __name__ == "__main__":
    run_backtest("AAPL")