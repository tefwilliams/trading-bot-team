"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

def calculate_rsi(series, period=2):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_signals(df_15m: pd.DataFrame, daily_data: pd.DataFrame, vix_data: pd.Series) -> pd.Series:
    """
    Generates signals based on T-1 Daily Regime Filters and Intraday RSI-2.
    df_15m: 15-minute bars.
    daily_data: Daily bars containing 'Close', 'ADX', 'EMA200'.
    vix_data: Daily VIX closing prices.
    """
    # 1. Align Daily Filters (T-1) to 15m index
    # Using .shift(1) on daily data to ensure we use previous day close
    daily_regime = daily_data.shift(1)
    
    # Merge daily indicators into 15m dataframe
    df = df_15m.copy()
    df['date'] = df.index.date
    df = df.join(daily_regime, on='date', rsuffix='_daily')
    
    # 2. Volatility Filter (90th percentile of 252-day VIX)
    vix_threshold = vix_data.rolling(window=252).quantile(0.9)
    df = df.join(vix_threshold.rename('vix_limit'), on='date')
    
    # 3. RSI-2 Trigger
    df['rsi2'] = calculate_rsi(df['Close'], period=2)
    
    # 4. Logic Implementation
    # Long: RSI < 15, ADX < 30, Price > EMA200, VIX < Limit
    long_cond = (df['rsi2'] < 15) & (df['ADX_daily'] < 30) & \
                (df['Close'] > df['EMA200_daily']) & (df['Close'] < df['vix_limit'])
    
    # Short: RSI > 85, ADX < 30, Price < EMA200 (optional), VIX < Limit
    short_cond = (df['rsi2'] > 85) & (df['ADX_daily'] < 30) & (df['Close'] < df['vix_limit'])
    
    signals = pd.Series(0, index=df.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    
    return signals

def run_backtest(ticker: str):
    """
    Executes a basic backtest simulation for a single asset.
    """
    # Fetch Data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    df_15m = yf.download(ticker, start=start_date, end=end_date, interval='15m')
    df_daily = yf.download(ticker, start=start_date, end=end_date, interval='1d')
    vix = yf.download('^VIX', start=start_date, end=end_date)['Close']
    
    # Simple indicator prep for demo
    df_daily['EMA200'] = df_daily['Close'].ewm(span=200).mean()
    # Placeholder for ADX calculation
    df_daily['ADX'] = 20 
    
    signals = generate_signals(df_15m, df_daily, vix)
    
    # Performance Metrics Calculation
    returns = df_15m['Close'].pct_change() * signals.shift(1)
    cum_ret = (1 + returns).cumprod()
    
    total_return = cum_ret.iloc[-1] - 1
    max_dd = (cum_ret.cummax() - cum_ret).max() / cum_ret.cummax()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 26) # Annualized
    
    print(f"--- Backtest Results: {ticker} ---")
    print(f"Total Return: {total_return:.2%}")
    print(f"Max Drawdown: {max_dd:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")

if __name__ == "__main__":
    # Example usage for a NASDAQ-100 component
    run_backtest("AAPL")