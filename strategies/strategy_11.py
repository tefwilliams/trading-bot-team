import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

def generate_signals(data: pd.DataFrame, vix_data: pd.Series) -> pd.DataFrame:
    """
    Generates trading signals for the VSRM strategy.
    Entry: VIX < 30 AND Close > SMA200 AND 20-day Z-Score < -2.0.
    """
    df = data.copy()
    
    # Calculate Indicators
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    rolling_mean = df['Close'].rolling(window=20).mean()
    rolling_std = df['Close'].rolling(window=20).std()
    df['ZScore'] = (df['Close'] - rolling_mean) / rolling_std
    
    # ATR for Stop Loss
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # Merge VIX
    df['VIX'] = vix_data.reindex(df.index).ffill()
    
    # Signal: 1 for Long, 0 for Flat
    df['signal'] = 0
    mask = (df['VIX'] < 30) & (df['Close'] > df['SMA200']) & (df['ZScore'] < -2.0)
    df.loc[mask, 'signal'] = 1
    
    return df

def run_backtest():
    # 1. Setup Data
    ticker = "QQQ"
    vix_ticker = "^VIX"
    
    df = yf.download(ticker, start="2010-01-01", interval='1d')
    vix_df = yf.download(vix_ticker, start="2010-01-01", interval='1d')
    
    for d in [df, vix_df]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
    
    if df is None or df.empty or vix_df is None or vix_df.empty:
        raise ValueError("Failed to download data.")

    # 2. Generate Signals
    df = generate_signals(df, vix_df['Close'])
    
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
            
            z_score = df['ZScore'].iloc[i]
            
            # Exit Conditions
            rsi_exit = z_score >= 0
            atr_stop = df['Low'].iloc[i] <= stop_price
            time_stop = days_held >= 10
            
            if rsi_exit or atr_stop or time_stop:
                exit_price = stop_price if atr_stop else df['Open'].iloc[i]
                trade_ret = ((exit_price / entry_price) - 1) * pos_size
                trades.append(trade_ret)
                in_position = False
        
        elif df['signal'].iloc[i-1] == 1 and not in_position:
            in_position = True
            entry_price = df['Open'].iloc[i]
            entry_date = i
            entry_atr = df['ATR14'].iloc[i-1]
            
    # 4. Metrics
    returns = pd.Series(trades)
    total_return = float(returns.sum())
    
    if not returns.empty:
        # Calculate drawdown based on 100% equivalent for metric comparability
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