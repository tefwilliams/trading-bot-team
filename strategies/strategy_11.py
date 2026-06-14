import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates trading signals for the ARMR strategy.
    Entry: SMA200 filter + RSI(2) < 10.
    Returns a Series of signals (1: Long, 0: Flat).
    """
    df = data.copy()
    
    # Calculate RSI(2)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    df['RSI2'] = 100 - (100 / (1 + rs))
    
    # Calculate SMA200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # Signal generation: 1 for Long, 0 for Flat
    signals = pd.Series(0, index=df.index)
    mask = (df['Close'] > df['SMA200']) & (df['RSI2'] < 10)
    signals.loc[mask] = 1
    
    return signals

def run_backtest():
    # 1. Setup Data
    ticker = "QQQ"
    df = yf.download(ticker, start="2010-01-01", interval='1d')
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df is None or df.empty:
        raise ValueError("Failed to download data.")

    # 2. Generate Signals and Indicators
    signals = generate_signals(df)
    
    # Re-calculate indicators for the loop
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    df['RSI2'] = 100 - (100 / (1 + rs))
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # 3. Simulate Trades
    # Position Sizing: 20% of Portfolio (Fixed)
    pos_size = 0.20
    trades = []
    
    in_position = False
    entry_price = 0.0
    entry_date = None
    entry_atr = 0.0
    
    # Loop from 200 to ensure SMA200 is warm
    for i in range(200, len(df)):
        # Exit Logic (Stop-Loss order logic: if Low < Stop, exit at Stop)
        if in_position:
            days_held = (i - entry_date)
            stop_price = entry_price - (1.5 * entry_atr)
            
            # Check conditions
            rsi_exit = df['RSI2'].iloc[i] > 70
            atr_stop = df['Low'].iloc[i] <= stop_price
            time_stop = days_held >= 5
            
            if rsi_exit or atr_stop or time_stop:
                # If stop hit, exit at stop_price, else open of next day
                exit_price = stop_price if atr_stop else df['Open'].iloc[i]
                # Return calculation: (exit_price/entry_price - 1) * fraction of portfolio
                trade_ret = (exit_price / entry_price - 1) * pos_size
                trades.append(trade_ret)
                in_position = False
        
        # Entry Logic (1 day lag)
        elif signals.iloc[i-1] == 1 and not in_position:
            in_position = True
            entry_price = df['Open'].iloc[i]
            entry_date = i
            entry_atr = df['ATR14'].iloc[i-1]
            
    # 4. Metrics Calculation
    returns = pd.Series(trades)
    
    # Metrics
    total_return = float(returns.sum()) if not returns.empty else 0.0
    
    if not returns.empty:
        # Drawdown calculation based on 100% exposure for portfolio view
        cum_rets = (1 + (returns / pos_size)).cumprod()
        running_max = cum_rets.cummax()
        drawdown = (cum_rets - running_max) / running_max
        max_drawdown = float(drawdown.min())
        sharpe = float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() != 0 else 0.0
    else:
        max_drawdown = 0.0
        sharpe = 0.0
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "total_trades": int(len(trades))
    }
    
    # 5. Export
    output_path = os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json')
    with open(output_path, 'w') as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    run_backtest()