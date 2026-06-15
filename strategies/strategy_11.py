import os
import json
import numpy as np
import pandas as pd
import yfinance as yf

def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates trading signals for the ARMR strategy.
    Entry: Close > SMA200 AND Close < SMA5 AND VIX < 35 AND RSI2 < 20-day 10th percentile of RSI2.
    Returns a Series of signals (1: Long, 0: Flat).
    """
    df = data.copy()
    
    # Download VIX to align with QQQ dates
    start_date = df.index[0].strftime('%Y-%m-%d')
    end_date = (df.index[-1] + pd.Timedelta(days=2)).strftime('%Y-%m-%d')
    vix = yf.download("^VIX", start=start_date, end=end_date, interval='1d')
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    
    # Align VIX
    df = df.join(vix['Close'].rename('VIX'), how='left')
    df['VIX'] = df['VIX'].ffill().bfill()
    
    # Calculate RSI(2)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    df['RSI2'] = 100 - (100 / (1 + rs))
    
    # Calculate SMAs
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    
    # Calculate RSI2 rolling 10th percentile
    df['RSI2_pct10'] = df['RSI2'].rolling(window=20).quantile(0.10)
    
    # Entry signal generation
    signals = pd.Series(0, index=df.index)
    mask = (
        (df['Close'] > df['SMA200']) &
        (df['Close'] < df['SMA5']) &
        (df['VIX'] < 35) &
        (df['RSI2'] < df['RSI2_pct10'])
    )
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
        
    if len(df) < 200:
        raise ValueError("Not enough data to run backtest (need at least 200 days for SMA200).")

    # 2. Generate Signals
    signals = generate_signals(df)
    df['entry_signal'] = signals
    
    # 3. Calculate indicators needed for execution
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    df['RSI2'] = 100 - (100 / (1 + rs))
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14).mean()
    
    # 4. Simulate Trades
    portfolio_values = [1.0] * len(df)
    portfolio_value = 1.0
    cash = 1.0
    shares = 0.0
    in_position = False
    entry_price = 0.0
    entry_date_idx = 0
    stop_price = 0.0
    total_completed_trades = 0
    
    for i in range(200, len(df)):
        open_i = df['Open'].iloc[i]
        high_i = df['High'].iloc[i]
        low_i = df['Low'].iloc[i]
        close_i = df['Close'].iloc[i]
        
        # Check if we are in a position
        if in_position:
            # 1. Check intraday stop loss first
            if low_i <= stop_price:
                exit_price = min(open_i, stop_price)
                cash = cash + shares * exit_price
                shares = 0.0
                in_position = False
                portfolio_value = cash
                total_completed_trades += 1
            else:
                # 2. Check if we had an exit signal from yesterday (day i-1)
                rsi_yesterday = df['RSI2'].iloc[i-1]
                close_yesterday = df['Close'].iloc[i-1]
                sma5_yesterday = df['SMA5'].iloc[i-1]
                days_held = i - entry_date_idx
                
                rsi_exit = rsi_yesterday > 70
                sma5_exit = close_yesterday > sma5_yesterday
                time_exit = days_held >= 5
                
                if rsi_exit or sma5_exit or time_exit:
                    cash = cash + shares * open_i
                    shares = 0.0
                    in_position = False
                    portfolio_value = cash
                    total_completed_trades += 1
                else:
                    portfolio_value = cash + shares * close_i
        
        # Check entry if not in position
        if not in_position:
            entry_signal_yesterday = df['entry_signal'].iloc[i-1]
            if entry_signal_yesterday == 1:
                position_size_cash = portfolio_value * 0.20
                shares = position_size_cash / open_i
                cash = portfolio_value - position_size_cash
                entry_price = open_i
                entry_date_idx = i
                stop_price = entry_price - (1.5 * df['ATR14'].iloc[i-1])
                in_position = True
                
                # Check if we get stopped out intraday on the entry day
                if low_i <= stop_price:
                    exit_price = min(open_i, stop_price)
                    cash = cash + shares * exit_price
                    shares = 0.0
                    in_position = False
                    portfolio_value = cash
                    total_completed_trades += 1
                else:
                    portfolio_value = cash + shares * close_i
            else:
                portfolio_value = cash
        
        portfolio_values[i] = portfolio_value
        
    # 5. Metrics Calculation
    portfolio_series = pd.Series(portfolio_values, index=df.index)
    active_portfolio = portfolio_series.iloc[200:]
    
    equity = active_portfolio / active_portfolio.iloc[0]
    total_return = float(equity.iloc[-1] - 1)
    
    running_max = equity.cummax()
    max_drawdown = float((equity / running_max - 1).min())
    
    strategy_returns = active_portfolio.pct_change().fillna(0)
    std = strategy_returns.std()
    sharpe_ratio = float((strategy_returns.mean() / std) * (252 ** 0.5)) if std and std > 0 else 0.0
    
    benchmark_return = float(df['Close'].iloc[-1] / df['Close'].iloc[200] - 1)
    
    metrics = {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "total_trades": int(total_completed_trades),
        "benchmark_return": benchmark_return
    }
    
    # Export
    output_path = os.getenv('BACKTEST_RESULTS_PATH', 'backtest_results.json')
    with open(output_path, 'w') as f:
        json.dump(metrics, f)

if __name__ == "__main__":
    run_backtest()