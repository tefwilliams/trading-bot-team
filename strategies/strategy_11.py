import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(df: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    """
    Generates trading signals based on the VSRM strategy.
    """
    df = df.copy()
    df['VIX'] = vix['Close'].reindex(df.index).ffill()
    
    # Indicators
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['Mean20'] = df['Close'].rolling(window=20).mean()
    df['Std20'] = df['Close'].rolling(window=20).std()
    df['ZScore'] = (df['Close'] - df['Mean20']) / df['Std20']
    
    # ATR for Stop Loss
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Entry Rule: VIX < 30 AND Close > SMA200 AND ZScore < -2.0
    df['signal'] = 0
    mask = (df['VIX'] < 30) & (df['Close'] > df['SMA200']) & (df['ZScore'] < -2.0)
    df.loc[mask, 'signal'] = 1
    
    return df

def run_backtest():
    # 1. Setup Data
    ticker = "QQQ"
    df = yf.download(ticker, start="2010-01-01", interval='1d')
    vix = yf.download("^VIX", start="2010-01-01", interval='1d')
    
    for d in [df, vix]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
    
    if df is None or df.empty or vix is None or vix.empty:
        raise ValueError("Failed to download data.")

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
            rsi_exit = df['ZScore'].iloc[i] >= 0
            atr_stop = df['Low'].iloc[i] <= stop_price
            time_stop = days_held >= 10
            
            if rsi_exit or atr_stop or time_stop:
                exit_price = stop_price if atr_stop else df['Open'].iloc[i]
                trades.append(((exit_price / entry_price) - 1) * pos_size)
                in_position = False
        
        elif df['signal'].iloc[i-1] == 1 and not in_position:
            in_position = True
            entry_price = df['Open'].iloc[i]
            entry_date = i
            entry_atr = df['ATR14'].iloc[i-1]
            
    # 4. Metrics
    returns = pd.Series(trades)
    benchmark_ret = (df['Close'].iloc[-1] / df['Close'].iloc[200]) - 1
    
    # Cumulative return for drawdown (using 100% exposure simulation)
    cum_rets = (1 + (returns / pos_size)).cumprod()
    running_max = cum_rets.cummax()
    drawdown = (cum_rets - running_max) / running_max
    
    metrics = {
        "total_return": float(returns.sum()),
        "max_drawdown": float(drawdown.min()) if not returns.empty else 0.0,
        "sharpe_ratio": float((returns.mean() / returns.std()) * np.sqrt(252)) if returns.std() != 0 else 0.0,
        "total_trades": int(len(trades)),
        "benchmark_return": float(benchmark_ret)
    }
    
    # 5. Export
    output_path = os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json')
    with open(output_path, 'w') as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    run_backtest()