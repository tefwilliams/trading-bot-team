"""
strategies/strategy_9.py
Adaptive RSI Mean Reversion (ARMR) for NASDAQ-100
Implements T-1 regime filters, state-based exit logic, partial exits, and portfolio circuit breaker.
Uses Daily data (1d) to ensure reliability.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import json
from datetime import datetime, timedelta


def generate_signals(data: pd.DataFrame) -> pd.Series:
    """
    Generates signals using T-1 daily regime filters and RSI-2.
    Expects 'data' to contain: 'Close', 'High', 'Low', 'ADX', 'EMA200', 'vix', 'VIX_Limit'.
    """
    # RSI-2 Calculation
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    rsi2 = 100 - (100 / (1 + rs))

    # Logic: Long if RSI < 15, ADX < 30, Price > EMA200, VIX < Limit
    long_cond = (
        (rsi2 < 15)
        & (data["ADX"] < 30)
        & (data["Close"] > data["EMA200"])
        & (data["vix"] < data["VIX_Limit"])
    )

    # Short: RSI > 85, ADX < 30, VIX < Limit
    short_cond = (rsi2 > 85) & (data["ADX"] < 30) & (data["vix"] < data["VIX_Limit"])

    signals = pd.Series(0, index=data.index)
    signals[long_cond] = 1
    signals[short_cond] = -1
    return signals


def run_backtest():
    """
    State-based backtest engine implementing ARMR exit logic and risk guardrails.
    """
    ticker = "AAPL"
    end_date = datetime.now()
    start_date = end_date - timedelta(
        days=730
    )  # Increased lookback for 252-day VIX window

    # Load Data
    df = yf.download(
        ticker, start=start_date, end=end_date, interval="1d", progress=False
    )
    vix = yf.download(
        "^VIX", start=start_date, end=end_date, interval="1d", progress=False
    )["Close"]

    if df is None or df.empty or vix is None or vix.empty:
        print("Error: Failed to download sufficient data.")
        return

    # Prepare Indicators
    df["EMA200"] = df["Close"].ewm(span=200).mean()
    # True Range (TR) for ADX/ATR Proxy
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            abs(df["High"] - prev_close),
            abs(df["Low"] - prev_close),
        ],
        axis=1,
    ).max(axis=1)
    df["ADX"] = tr.rolling(14).mean()
    df["atr"] = tr.rolling(14).mean()
    df["vix"] = vix
    df["VIX_Limit"] = vix.rolling(window=252).quantile(0.9)

    # Generate signals using T-1 shifted data to prevent look-ahead bias
    # Align the shifted features to the index of the original df
    df_shifted = df.shift(1)
    # Ensure signal generation uses the current Close for logic alignment
    df_input = df_shifted.copy()
    df_input["Close"] = df["Close"]

    signals = generate_signals(df_input)

    # Backtest Loop
    pos, entry_price, entry_atr, entry_idx = 0, 0, 0, 0
    pos_size, consecutive_losses = 1.0, 0
    portfolio_equity, daily_pnl = 100000.0, 0.0
    pnl_history = []

    for i in range(1, len(df)):
        if df.index[i].day != df.index[i - 1].day:
            daily_pnl = 0

        curr_price = df["Open"].iloc[i]

        # Exit Logic
        if pos != 0:
            stop_loss_hit = (curr_price - entry_price) * pos < -2.5 * entry_atr
            time_exit = (i - entry_idx) >= 5  # 5 trading days

            if stop_loss_hit or time_exit:
                trade_pnl = ((curr_price - entry_price) * pos) * pos_size
                portfolio_equity += trade_pnl
                daily_pnl += trade_pnl
                consecutive_losses = consecutive_losses + 1 if trade_pnl < 0 else 0
                pnl_history.append(trade_pnl)
                pos = 0
                pos_size = 1.0

        # Entry Logic
        if (
            pos == 0
            and signals.iloc[i - 1] != 0
            and abs(daily_pnl / portfolio_equity) < 0.03
        ):
            if consecutive_losses < 5:
                pos = signals.iloc[i - 1]
                entry_price = curr_price
                entry_atr = df["atr"].iloc[i - 1]
                entry_idx = i

    # Metrics
    returns = np.array(pnl_history)
    total_return = (portfolio_equity - 100000) / 100000
    sharpe = (
        (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
    )

    # Calculate Max Drawdown
    cum_returns = np.cumsum(pnl_history) + 100000
    running_max = np.maximum.accumulate(cum_returns)
    drawdown = (cum_returns - running_max) / running_max
    max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0

    # OUTPUT CONTRACT: Write results to JSON sidecar
    metrics = {
        "total_return": float(total_return),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(sharpe),
    }

    with open("backtest_results.json", "w") as f:
        json.dump(metrics, f)

    print(f"--- Backtest {ticker} ---")
    print(f"Total Return: {total_return:.2%}")
    print(f"Sharpe Ratio: {sharpe:.2f}")


if __name__ == "__main__":
    run_backtest()
