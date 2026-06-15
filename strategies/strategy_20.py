import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

def get_data():
    tickers = ['SPY', '^GSPC', '^VIX']
    df = yf.download(tickers, start='2005-01-01', end='2023-12-31', interval='1d')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(1)
    df = df.ffill().dropna()
    return df

def generate_signals(data):
    spy_close = data['SPY']['Close']
    spy_open = data['SPY']['Open']
    gspc_close = data['^GSPC']['Close']
    vix_close = data['^VIX']['Close']
    
    sma200_gspc = gspc_close.rolling(200).mean()
    trend = np.where(gspc_close > sma200_gspc, 'BULL', 'BEAR')
    
    vol_state = ['CALM'] * len(data)
    for i in range(1, len(data)):
        if vol_state[i-1] == 'CALM' and vix_close.iloc[i] > 25:
            vol_state[i] = 'VOLATILE'
        elif vol_state[i-1] == 'VOLATILE' and vix_close.iloc[i] < 20:
            vol_state[i] = 'CALM'
        else:
            vol_state[i] = vol_state[i-1]
            
    regime = [f'{t}_{v}' for t, v in zip(trend, vol_state)]
    
    signals = pd.Series(0, index=data.index)
    in_position = False
    entry_price = 0.0
    hold_days = 0
    
    sma50_spy = spy_close.rolling(50).mean()
    sma200_spy = spy_close.rolling(200).mean()
    delta = spy_close.diff()
    gain = delta.clip(lower=0).rolling(2).mean()
    loss = delta.clip(upper=0).abs().rolling(2).mean()
    rsi = 100 - (100 / (1 + (gain / loss)))
    sma5_spy = spy_close.rolling(5).mean()
    
    for i in range(200, len(data) - 1):
        reg = regime[i]
        curr_open = spy_open.iloc[i+1]
        
        if in_position:
            hold_days += 1
            if (curr_open <= entry_price * 0.95) or (reg == 'BEAR_CALM'):
                in_position = False
            elif reg == 'BULL_CALM' and sma50_spy.iloc[i] < sma200_spy.iloc[i]:
                in_position = False
            elif reg in ['BULL_VOLATILE', 'BEAR_VOLATILE'] and (rsi.iloc[i] > 70 or spy_close.iloc[i] > sma5_spy.iloc[i] or hold_days >= 5):
                in_position = False
        else:
            if reg == 'BULL_CALM' and sma50_spy.iloc[i] > sma200_spy.iloc[i]:
                in_position = True
                entry_price = curr_open
                hold_days = 0
            elif reg in ['BULL_VOLATILE', 'BEAR_VOLATILE'] and rsi.iloc[i] < 10:
                in_position = True
                entry_price = curr_open
                hold_days = 0
        
        signals.iloc[i+1] = 1 if in_position else 0
        
    return signals

def run_backtest():
    data = get_data()
    signals = generate_signals(data)
    strategy_returns = signals.shift(1) * data['SPY']['Close'].pct_change()
    
    equity = (1 + strategy_returns.fillna(0)).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    running_max = equity.cummax()
    max_drawdown = float((equity / running_max - 1).min())
    std = strategy_returns.std()
    sharpe_ratio = float((strategy_returns.mean() / std) * (252 ** 0.5)) if std > 0 else 0.0
    total_trades = int((signals.diff().abs().fillna(0)).sum())
    benchmark_return = float(data['SPY']['Close'].iloc[-1] / data['SPY']['Close'].iloc[0] - 1)
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": total_trades,
        "benchmark_return": benchmark_return
    }
    
    with open(os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json'), 'w') as f:
        json.dump(metrics, f)

if __name__ == '__main__':
    run_backtest()