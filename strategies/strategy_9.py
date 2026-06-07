"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Implements T-1 regime filters, state-based exit logic, partial exits, and portfolio circuit breaker.
"""

import pandas as pd
import numpy as np
import yfinance as yf

def calculate_indicators(df: pd.DataFrame):
    """Calculates technical indicators manually to avoid external dependency issues."""
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
    
    # Simple ADX placeholder (Wilder's approach requires complex smoothing)
    # Using a rolling volatility-based proxy to prevent crash
    df['ADX'] = df['atr'].rolling(14).std() 
    return df

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates signals using T-1 daily regime filters and intraday RSI-2.
    Expects 'data' to contain: '15m_Close', 'Daily_ADX', 'Daily_EMA200', 'Daily_VIX_Limit'.
    """
    data = calculate_indicators(data)
    
    long_cond = (data['rsi2'] < 15) & (data['Daily_ADX'] < 30) & \
                (data['15m_Close'] > data['Daily_EMA200']) & \
                (data['15m_Close'] < data['Daily_VIX_Limit'])
    
    short_cond = (data['rsi2'] > 85) & (data['Daily_ADX'] < 30) & \
                 (data['15m_Close'] < data['Daily_VIX_Limit'])
    
    signals = pd.Series(0, index=data.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    return signals

def run_backtest():
    """
    State-based backtest engine implementing ARMR exit logic and risk guardrails.
    """
    ticker = "AAPL"
    # Load Data
    df_15m = yf.download(ticker, period='1y', interval='15m', progress=False)
    df_daily = yf.download(ticker, period='1y', interval='1d', progress=False)
    vix = yf.download('^VIX', period='1y', progress=False)['Close']
    
    if df_15m.empty or df_daily.empty: return
    
    # Prepare Indicators
    df_daily['EMA200'] = df_daily['Close'].ewm(span=200).mean()
    vix_limit = vix.rolling(window=252).quantile(0.9)
    
    # Align Data
    df_daily_shifted = df_daily.shift(1)
    vix_limit_shifted = vix_limit.shift(1)
    
    combined = df_15m.copy()
    combined['date'] = combined.index.date
    combined = combined.merge(df_daily_shifted[['ADX', 'EMA200']], left_on='date', right_index=True, how='left')
    combined = combined.merge(vix_limit_shifted.rename('VIX_Limit'), left_on='date', right_index=True, how='left')
    combined = combined.rename(columns={'Close': '15m_Close', 'High': '15m_High', 'Low': '15m_Low',
                                        'ADX': 'Daily_ADX', 'EMA200': 'Daily_EMA200', 'VIX_Limit': 'Daily_VIX_Limit'})
    
    signals = generate_signals(combined)
    combined['rsi2'] = calculate_indicators(combined)['rsi2']
    combined['atr'] = calculate_indicators(combined)['atr']
    
    # Backtest Loop
    pos, entry_price, entry_atr, entry_idx = 0, 0, 0, 0
    pos_size, consecutive_losses = 1.0, 0
    portfolio_equity, daily_pnl = 100000.0, 0.0
    pnl_history = []
    
    for i in range(1, len(combined)):
        if combined.index[i].day != combined.index[i-1].day: daily_pnl = 0
        curr_price = combined['Open'].iloc[i] if 'Open' in combined.columns else combined['15m_Close'].iloc[i]
        
        if pos != 0:
            rsi = combined['rsi2'].iloc[i-1]
            stop_loss_hit = (curr_price - entry_price) * pos < -2.5 * entry_atr
            take_profit = (pos == 1 and rsi > 60) or (pos == -1 and rsi < 40)
            time_exit = (i - entry_idx) >= 130
            
            if take_profit and pos_size == 1.0:
                trade_pnl = ((curr_price - entry_price) * pos) * 0.5
                portfolio_equity += trade_pnl; daily_pnl += trade_pnl; pos_size = 0.5
            elif stop_loss_hit or time_exit or (take_profit and pos_size == 0.5):
                trade_pnl = ((curr_price - entry_price) * pos) * pos_size
                portfolio_equity += trade_pnl; daily_pnl += trade_pnl
                consecutive_losses = consecutive_losses + 1 if trade_pnl < 0 else 0
                pnl_history.append(trade_pnl); pos = 0; pos_size = 1.0
        
        if pos == 0 and signals.iloc[i-1] != 0 and abs(daily_pnl / portfolio_equity) < 0.03:
            if consecutive_losses < 5:
                pos = signals.iloc[i-1]; entry_price = curr_price
                entry_atr = combined['atr'].iloc[i-1]; entry_idx = i
            
    # Metrics
    returns = np.array(pnl_history)
    total_ret = (portfolio_equity - 100000) / 100000
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    print(f"--- Backtest {ticker}: Return={total_ret:.2%}, Sharpe={sharpe:.2f} ---")

if __name__ == "__main__":
    run_backtest()