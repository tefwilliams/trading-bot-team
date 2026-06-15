import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates trading signals for the ARMR strategy.
    Returns a Series of signals (1 for Long, 0 for Flat) representing the position state at the close of each day.
    """
    df = data.copy()
    
    # Calculate RSI(2)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=2).mean()
    avg_loss = loss.rolling(window=2).mean()
    
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    df['RSI2'] = np.where(avg_loss == 0, 100.0, 100.0 - (100.0 / (1.0 + rs)))
    df['RSI2'] = df['RSI2'].fillna(50.0)
    
    # Calculate SMA200 and SMA5
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    
    # Calculate ATR14
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Daily Return for Crash Filter
    df['Return'] = df['Close'].pct_change()
    
    # Simulate positions
    position = 0
    entry_idx = -1
    entry_price = 0.0
    stop_price = 0.0
    entry_atr = 0.0
    
    signals_arr = np.zeros(len(df))
    
    for i in range(200, len(df)):
        # Check exit if in position
        if position == 1:
            mr_trigger = df['Close'].iloc[i-1] > df['SMA5'].iloc[i-1]
            time_trigger = (i - entry_idx) >= 5
            
            if mr_trigger or time_trigger:
                # Exit at open of day i
                position = 0
                signals_arr[i] = 0
            else:
                # Check stop loss on day i
                open_i = df['Open'].iloc[i]
                low_i = df['Low'].iloc[i]
                if open_i <= stop_price or low_i <= stop_price:
                    # Stopped out
                    position = 0
                    signals_arr[i] = 0
                else:
                    # Still holding
                    position = 1
                    signals_arr[i] = 1
        else:
            # Check entry signal at close of i-1
            close_prev = df['Close'].iloc[i-1]
            sma200_prev = df['SMA200'].iloc[i-1]
            rsi2_prev = df['RSI2'].iloc[i-1]
            ret_prev = df['Return'].iloc[i-1]
            
            entry_signal = (close_prev > sma200_prev) and (rsi2_prev < 10) and (ret_prev >= -0.04)
            
            if entry_signal:
                # Enter at open of day i
                position = 1
                entry_idx = i
                entry_price = df['Open'].iloc[i]
                entry_atr = df['ATR14'].iloc[i-1]
                stop_price = entry_price - (2.0 * entry_atr)
                
                # Check if stop loss is hit on entry day itself
                open_i = df['Open'].iloc[i]
                low_i = df['Low'].iloc[i]
                if open_i <= stop_price or low_i <= stop_price:
                    # Stopped out immediately
                    position = 0
                    signals_arr[i] = 0
                else:
                    # Hold
                    position = 1
                    signals_arr[i] = 1
            else:
                position = 0
                signals_arr[i] = 0
                
    return pd.Series(signals_arr, index=df.index, name='signals')

def run_backtest():
    # 1. Setup Data
    ticker = "QQQ"
    df = yf.download(ticker, start="2010-01-01", interval='1d')
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    if df is None or df.empty:
        raise ValueError("Failed to download data.")
        
    # 2. Generate Signals
    signals = generate_signals(df)
    
    # 3. Calculate Indicators for Return Simulation
    delta = df['Close'].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=2).mean()
    avg_loss = loss.rolling(window=2).mean()
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    df['RSI2'] = np.where(avg_loss == 0, 100.0, 100.0 - (100.0 / (1.0 + rs)))
    df['RSI2'] = df['RSI2'].fillna(50.0)
    
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    df['Return'] = df['Close'].pct_change()
    
    # 4. Simulate Trades and Calculate Daily Returns
    position = 0
    entry_idx = -1
    entry_price = 0.0
    stop_price = 0.0
    entry_atr = 0.0
    
    strategy_returns = np.zeros(len(df))
    
    for i in range(200, len(df)):
        if position == 1:
            mr_trigger = df['Close'].iloc[i-1] > df['SMA5'].iloc[i-1]
            time_trigger = (i - entry_idx) >= 5
            
            if mr_trigger or time_trigger:
                # Exit at open of day i
                exit_price = df['Open'].iloc[i]
                day_return = (exit_price / df['Close'].iloc[i-1]) - 1.0
                strategy_returns[i] = day_return
                position = 0
            else:
                # Check stop loss on day i
                open_i = df['Open'].iloc[i]
                low_i = df['Low'].iloc[i]
                close_i = df['Close'].iloc[i]
                
                if open_i <= stop_price:
                    exit_price = open_i
                    day_return = (exit_price / df['Close'].iloc[i-1]) - 1.0
                    strategy_returns[i] = day_return
                    position = 0
                elif low_i <= stop_price:
                    exit_price = stop_price
                    day_return = (exit_price / df['Close'].iloc[i-1]) - 1.0
                    strategy_returns[i] = day_return
                    position = 0
                else:
                    day_return = (close_i / df['Close'].iloc[i-1]) - 1.0
                    strategy_returns[i] = day_return
                    position = 1
        else:
            close_prev = df['Close'].iloc[i-1]
            sma200_prev = df['SMA200'].iloc[i-1]
            rsi2_prev = df['RSI2'].iloc[i-1]
            ret_prev = df['Return'].iloc[i-1]
            
            entry_signal = (close_prev > sma200_prev) and (rsi2_prev < 10) and (ret_prev >= -0.04)
            
            if entry_signal:
                position = 1
                entry_idx = i
                entry_price = df['Open'].iloc[i]
                entry_atr = df['ATR14'].iloc[i-1]
                stop_price = entry_price - (2.0 * entry_atr)
                
                open_i = df['Open'].iloc[i]
                low_i = df['Low'].iloc[i]
                close_i = df['Close'].iloc[i]
                
                if open_i <= stop_price:
                    exit_price = open_i
                    day_return = (exit_price / entry_price) - 1.0
                    strategy_returns[i] = day_return
                    position = 0
                elif low_i <= stop_price:
                    exit_price = stop_price
                    day_return = (exit_price / entry_price) - 1.0
                    strategy_returns[i] = day_return
                    position = 0
                else:
                    day_return = (close_i / entry_price) - 1.0
                    strategy_returns[i] = day_return
                    position = 1
            else:
                strategy_returns[i] = 0.0
                position = 0
                
    # Convert to pandas Series
    strategy_returns_series = pd.Series(strategy_returns, index=df.index)
    
    # 5. Calculate Metrics
    equity = (1 + strategy_returns_series.fillna(0)).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    running_max = equity.cummax()
    max_drawdown = float((equity / running_max - 1).min()) if not equity.empty else 0.0
    std = strategy_returns_series.std()
    sharpe_ratio = float((strategy_returns_series.mean() / std) * (252 ** 0.5)) if std and std > 0 else 0.0
    
    # total_trades = number of completed round trips, i.e. transitions out of a position
    total_trades = int((signals.shift(1).fillna(0) != signals.fillna(0)).sum())
    
    # benchmark_return = buy-and-hold of the primary instrument over the same window
    benchmark_return = float(df["Close"].iloc[-1] / df["Close"].iloc[0] - 1)
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": total_trades,
        "benchmark_return": benchmark_return
    }
    
    # 6. Export to JSON
    output_path = os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json')
    with open(output_path, 'w') as f:
        json.dump(metrics, f)
        
    print(f"Backtest completed successfully. Results written to {output_path}")
    print(f"Metrics: {metrics}")

if __name__ == "__main__":
    run_backtest()