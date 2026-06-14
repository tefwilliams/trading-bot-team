import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame) -> pd.DataFrame:
    """
    Generates trading signals for the ARMR strategy.
    Entry: SMA200 filter + RSI(2) < 10.
    Returns the dataframe with indicators and a 'signal' column.
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
    
    # Calculate ATR(14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Entry Rule: Close > SMA200 AND RSI(2) < 10
    # Signal = 1 at the close of the day the condition is met
    df['signal'] = 0
    mask = (df['Close'] > df['SMA200']) & (df['RSI2'] < 10)
    df.loc[mask, 'signal'] = 1
    
    return df

def run_backtest():
    # 1. Setup Data
    ticker = "QQQ"
    df = yf.download(ticker, start="2010-01-01", interval='1d')
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df is None or df.empty:
        raise ValueError("Failed to download data.")

    # 2. Generate Indicators and Signals
    df = generate_signals(df)
    
    # 3. Simulate Trades
    # Parameters
    pos_size = 0.20
    trades = []
    
    in_position = False
    entry_price = 0.0
    entry_date = None
    entry_atr = 0.0
    
    # Loop from 200 (SMA200 warm-up)
    for i in range(200, len(df)):
        # Exit Logic
        if in_position:
            days_held = (i - entry_date)
            stop_price = entry_price - (1.5 * entry_atr)
            
            # Conditions
            rsi_exit = df['RSI2'].iloc[i] > 70
            atr_stop = df['Low'].iloc[i] <= stop_price
            time_stop = days_held >= 5
            
            if rsi_exit or atr_stop or time_stop:
                exit_price = stop_price if atr_stop else df['Open'].iloc[i]
                # Calculate return on the 20% position
                trade_ret = ((exit_price / entry_price) - 1) * pos_size
                trades.append(trade_ret)
                in_position = False
        
        # Entry Logic (1 day lag: signal at i-1 triggers entry at open of i)
        elif df['signal'].iloc[i-1] == 1 and not in_position:
            in_position = True
            entry_price = df['Open'].iloc[i]
            entry_date = i
            entry_atr = df['ATR14'].iloc[i-1]
            
    # 4. Metrics Calculation
    returns = pd.Series(trades)
    
    # Total return: sum of weighted returns
    total_return = float(returns.sum()) if not returns.empty else 0.0
    
    if not returns.empty:
        # For drawdown metrics, convert back to full strategy equity curve
        # We assume 80% cash, 20% invested
        equity_curve = (1 + (returns / pos_size)).cumprod()
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
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