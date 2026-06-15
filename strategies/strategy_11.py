import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates VSRM strategy signals.
    - Entry: Price > SMA200 AND VIX < 30 AND Z-Score(20) < -2.0
    """
    # Download VIX for the same period
    start_date = data.index.min().strftime('%Y-%m-%d')
    end_date = (data.index.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    vix = yf.download("^VIX", start=start_date, end=end_date, interval='1d')
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    
    df = data.copy()
    df['VIX'] = vix['Close'].reindex(df.index).ffill()
    
    # Indicators
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    rolling_mean = df['Close'].rolling(window=20).mean()
    rolling_std = df['Close'].rolling(window=20).std().replace(0, np.nan)
    df['ZScore'] = (df['Close'] - rolling_mean) / rolling_std
    
    # ATR for Stop Loss
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Entry Trigger
    df['trigger'] = 0
    mask = (df['Close'] > df['SMA200']) & (df['VIX'] < 30) & (df['ZScore'] < -2.0)
    df.loc[mask, 'trigger'] = 1
    
    # Stateful Simulation to generate signals
    signals = pd.Series(0, index=df.index)
    state = 'FLAT'
    exit_at_open = False
    entry_price = 0.0
    entry_atr = 0.0
    days_held = 0
    
    for i in range(200, len(df)):
        if exit_at_open:
            state = 'FLAT'
            exit_at_open = False
            signals.iloc[i] = 0
            
        if state == 'LONG':
            days_held += 1
            signals.iloc[i] = 1
            low_i = df['Low'].iloc[i]
            open_i = df['Open'].iloc[i]
            zscore_i = df['ZScore'].iloc[i]
            stop_price = entry_price - 1.5 * entry_atr
            
            if low_i <= stop_price:
                state = 'FLAT'
                signals.iloc[i] = 0
            else:
                rsi_exit = zscore_i > 0
                time_exit = days_held >= 10
                if rsi_exit or time_exit:
                    exit_at_open = True
                    
        if state == 'FLAT' and not exit_at_open:
            if df['trigger'].iloc[i-1] == 1:
                state = 'LONG'
                entry_price = df['Open'].iloc[i]
                entry_atr = df['ATR14'].iloc[i-1]
                stop_price = entry_price - 1.5 * entry_atr
                days_held = 1
                signals.iloc[i] = 1
                
                low_i = df['Low'].iloc[i]
                open_i = df['Open'].iloc[i]
                zscore_i = df['ZScore'].iloc[i]
                
                if low_i <= stop_price:
                    state = 'FLAT'
                    signals.iloc[i] = 0
                else:
                    rsi_exit = zscore_i > 0
                    if rsi_exit:
                        exit_at_open = True
                        
    return signals

def run_backtest():
    # 1. Setup Data
    df = yf.download("QQQ", start="2010-01-01", interval='1d')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if df is None or df.empty:
        raise ValueError("Data download failed.")
        
    # Download VIX for the same period
    start_date = df.index.min().strftime('%Y-%m-%d')
    end_date = (df.index.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    vix = yf.download("^VIX", start=start_date, end=end_date, interval='1d')
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
        
    df['VIX'] = vix['Close'].reindex(df.index).ffill()
    
    # Calculate indicators
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    rolling_mean = df['Close'].rolling(window=20).mean()
    rolling_std = df['Close'].rolling(window=20).std().replace(0, np.nan)
    df['ZScore'] = (df['Close'] - rolling_mean) / rolling_std
    
    # Calculate ATR14
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Entry Rule
    df['trigger'] = 0
    mask = (df['Close'] > df['SMA200']) & (df['VIX'] < 30) & (df['ZScore'] < -2.0)
    df.loc[mask, 'trigger'] = 1
    
    # Run the stateful simulation
    signals = pd.Series(0, index=df.index)
    portfolio_returns = pd.Series(0.0, index=df.index)
    
    state = 'FLAT'
    exit_at_open = False
    entry_price = 0.0
    entry_atr = 0.0
    days_held = 0
    pos_size = 0.20
    
    for i in range(200, len(df)):
        if exit_at_open:
            qqq_return = (df['Open'].iloc[i] / df['Close'].iloc[i-1]) - 1
            portfolio_returns.iloc[i] = pos_size * qqq_return
            state = 'FLAT'
            exit_at_open = False
            signals.iloc[i] = 0
            
        if state == 'LONG':
            days_held += 1
            signals.iloc[i] = 1
            low_i = df['Low'].iloc[i]
            open_i = df['Open'].iloc[i]
            close_i = df['Close'].iloc[i]
            close_prev = df['Close'].iloc[i-1]
            zscore_i = df['ZScore'].iloc[i]
            stop_price = entry_price - 1.5 * entry_atr
            
            if low_i <= stop_price:
                actual_exit_price = stop_price if open_i >= stop_price else open_i
                qqq_return = (actual_exit_price / close_prev) - 1
                portfolio_returns.iloc[i] = pos_size * qqq_return
                state = 'FLAT'
                signals.iloc[i] = 0
            else:
                rsi_exit = zscore_i > 0
                time_exit = days_held >= 10
                if rsi_exit or time_exit:
                    qqq_return = (close_i / close_prev) - 1
                    portfolio_returns.iloc[i] = pos_size * qqq_return
                    exit_at_open = True
                else:
                    qqq_return = (close_i / close_prev) - 1
                    portfolio_returns.iloc[i] = pos_size * qqq_return
                    
        if state == 'FLAT' and not exit_at_open:
            if df['trigger'].iloc[i-1] == 1:
                state = 'LONG'
                entry_price = df['Open'].iloc[i]
                entry_atr = df['ATR14'].iloc[i-1]
                stop_price = entry_price - 1.5 * entry_atr
                days_held = 1
                signals.iloc[i] = 1
                
                low_i = df['Low'].iloc[i]
                open_i = df['Open'].iloc[i]
                close_i = df['Close'].iloc[i]
                zscore_i = df['ZScore'].iloc[i]
                
                if low_i <= stop_price:
                    actual_exit_price = stop_price if open_i >= stop_price else open_i
                    qqq_return = (actual_exit_price / entry_price) - 1
                    portfolio_returns.iloc[i] = pos_size * qqq_return
                    state = 'FLAT'
                    signals.iloc[i] = 0
                else:
                    rsi_exit = zscore_i > 0
                    if rsi_exit:
                        qqq_return = (close_i / entry_price) - 1
                        portfolio_returns.iloc[i] = pos_size * qqq_return
                        exit_at_open = True
                    else:
                        qqq_return = (close_i / entry_price) - 1
                        portfolio_returns.iloc[i] = pos_size * qqq_return

    # 4. Metrics Calculation
    equity = (1 + portfolio_returns.fillna(0)).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    running_max = equity.cummax()
    max_drawdown = float((equity / running_max - 1).min())
    std = portfolio_returns.std()
    sharpe_ratio = float((portfolio_returns.mean() / std) * (252 ** 0.5)) if std and std > 0 else 0.0
    
    # total_trades = number of completed round trips
    total_trades = int((signals.shift(1).fillna(0) != signals.fillna(0)).sum() // 2)
    
    # benchmark_return = buy-and-hold of the primary instrument over the same window
    benchmark_return = float(df["Close"].iloc[-1] / df["Close"].iloc[200] - 1)
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": total_trades,
        "benchmark_return": benchmark_return
    }
    
    # 5. Export
    output_path = os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json')
    with open(output_path, 'w') as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    run_backtest()