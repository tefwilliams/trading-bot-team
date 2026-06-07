"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Implements T-1 regime filters, state-based exit logic, partial exits, and portfolio circuit breaker.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta

def generate_signals(df_15m: pd.DataFrame, daily_data: pd.DataFrame, vix_data: pd.Series) -> pd.Series:
    """
    Generates signals using T-1 daily regime filters to prevent look-ahead bias.
    """
    # 1. Prepare Daily Filters (T-1)
    daily_regime = daily_data.shift(1)
    
    # Calculate rolling 90th percentile of VIX (T-1)
    vix_limit = vix_data.rolling(window=252).quantile(0.9).shift(1)
    
    # 2. Merge Indicators
    df = df_15m.copy()
    df['date'] = df.index.date
    df = df.merge(daily_regime[['ADX', 'EMA200']], left_on='date', right_index=True, how='left')
    df = df.merge(vix_limit.rename('vix_limit'), left_on='date', right_index=True, how='left')
    
    # 3. Calculate Technical Indicators
    df['rsi2'] = ta.rsi(df['Close'], length=2)
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # 4. Logic Implementation
    # Long: RSI < 15, ADX < 30, Price > EMA200, VIX < Limit
    long_cond = (df['rsi2'] < 15) & (df['ADX'] < 30) & (df['Close'] > df['EMA200']) & (df['Close'] < df['vix_limit'])
    # Short: RSI > 85, ADX < 30, VIX < Limit
    short_cond = (df['rsi2'] > 85) & (df['ADX'] < 30) & (df['Close'] < df['vix_limit'])
    
    signals = pd.Series(0, index=df.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    return signals

def run_backtest(ticker: str = "AAPL"):
    """
    State-based backtest engine implementing ARMR exit logic and risk guardrails.
    """
    # Data Loading
    df_15m = yf.download(ticker, period='1y', interval='15m')
    df_daily = yf.download(ticker, period='1y', interval='1d')
    df_daily['EMA200'] = ta.ema(df_daily['Close'], length=200)
    adx_obj = ta.adx(df_daily['High'], df_daily['Low'], df_daily['Close'], length=14)
    df_daily['ADX'] = adx_obj['ADX_14']
    vix = yf.download('^VIX', period='1y')['Close']
    
    signals = generate_signals(df_15m, df_daily, vix)
    
    # State tracking
    pos = 0
    entry_price = 0
    entry_atr = 0
    entry_idx = 0
    pos_size = 1.0
    consecutive_losses = 0
    portfolio_equity = 100000.0
    daily_pnl = 0.0
    pnl_history = []
    
    for i in range(1, len(df_15m)):
        # Daily Reset for Circuit Breaker
        if df_15m.index[i].day != df_15m.index[i-1].day:
            daily_pnl = 0
            
        curr_price = df_15m['Open'].iloc[i]
        
        # Exit Logic
        if pos != 0:
            rsi = df_15m['rsi2'].iloc[i-1]
            bars_held = i - entry_idx
            
            stop_loss_hit = (curr_price - entry_price) * pos < -2.5 * entry_atr
            take_profit = (pos == 1 and rsi > 60) or (pos == -1 and rsi < 40)
            time_exit = bars_held >= 130 # 5 days * 26 bars
            
            if take_profit and pos_size == 1.0:
                # 50% Partial Exit
                trade_pnl = ((curr_price - entry_price) * pos) * 0.5
                portfolio_equity += trade_pnl
                daily_pnl += trade_pnl
                pos_size = 0.5
            elif stop_loss_hit or time_exit or (take_profit and pos_size == 0.5):
                # Full Exit
                trade_pnl = ((curr_price - entry_price) * pos) * pos_size
                portfolio_equity += trade_pnl
                daily_pnl += trade_pnl
                consecutive_losses = consecutive_losses + 1 if trade_pnl < 0 else 0
                pnl_history.append(trade_pnl)
                pos = 0
                pos_size = 1.0
        
        # Entry Logic
        # Circuit Breaker: Stop if daily drawdown > 3%
        if pos == 0 and signals.iloc[i-1] != 0 and abs(daily_pnl / portfolio_equity) < 0.03:
            if consecutive_losses < 5:
                pos = signals.iloc[i-1]
                entry_price = curr_price
                entry_atr = df_15m['atr'].iloc[i-1]
                entry_idx = i
            
    # Metrics
    returns = np.array(pnl_history)
    total_ret = (portfolio_equity - 100000) / 100000
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    print(f"--- Backtest Results: {ticker} ---")
    print(f"Total Return: {total_ret:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")

if __name__ == "__main__":
    run_backtest("AAPL")