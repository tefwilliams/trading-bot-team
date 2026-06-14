import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame, vix_data: pd.DataFrame) -> pd.DataFrame:
    """
    Generates VSRM strategy signals.
    - Entry: Price > SMA200 AND VIX < 30 AND Z-Score(20) < -2.0
    """
    df = data.copy()
    df['VIX'] = vix_data['Close'].reindex(df.index).ffill()
    
    # Indicators
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    rolling_mean = df['Close'].rolling(window=20).mean()
    rolling_std = df['Close'].rolling(window=20).std()
    df['ZScore'] = (df['Close'] - rolling_mean) / rolling_std
    
    # Signals
    df['signal'] = 0
    mask = (df['Close'] > df['SMA200']) & (df['VIX'] < 30) & (df['ZScore'] < -2.0)
    df.loc[mask, 'signal'] = 1
    
    # ATR for Stop Loss
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    return df

def run_backtest():
    # 1. Setup Data
    df = yf.download("QQQ", start="2010-01-01", interval='1d')
    vix = yf.download("^VIX", start="2010-01-01", interval='1d')
    
    for d in [df, vix]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
    
    if df is None or df.empty or vix is None or vix.empty:
        raise ValueError("Data download failed.")

    # 2. Generate Signals
    df = generate_signals(df, vix)
    
    # 3. Simulate Trades
    pos_size = 0.20
    trades = []
    in_position = False
    entry_price = 0.0
    entry_date = None
    entry_atr = 0.0
    
    for i in range(200, len(df)):
        if in_position:
            days_held = (i - entry_date)
            stop_price = entry_price - (1.5 * entry_atr)
            
            # Exit Conditions
            exit_cond = (df['ZScore'].iloc[i] > 0) or (df['Low'].iloc[i] <= stop_price) or (days_held >= 10)
            
            if exit_cond:
                exit_price = stop_price if df['Low'].iloc[i] <= stop_price else df['Open'].iloc[i]
                trades.append(((exit_price / entry_price) - 1) * pos_size)
                in_position = False
        
        elif df['signal'].iloc[i-1] == 1 and not in_position:
            in_position = True
            entry_price = df['Open'].iloc[i]
            entry_date = i
            entry_atr = df['ATR14'].iloc[i-1]
            
    # 4. Metrics
    returns = pd.Series(trades)
    total_return = float(returns.sum()) if not returns.empty else 0.0
    
    if not returns.empty:
        # Standardize return to 100% allocation for drawdown calc
        cum_rets = (1 + (returns / pos_size)).cumprod()
        running_max = cum_rets.cummax()
        drawdown = (cum_rets - running_max) / running_max
        max_drawdown = float(drawdown.min())
        sharpe = float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() != 0 else 0.0
    else:
        max_drawdown, sharpe = 0.0, 0.0
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "total_trades": int(len(trades))
    }
    
    with open(os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json'), 'w') as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    run_backtest()