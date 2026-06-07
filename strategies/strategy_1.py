import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ==============================================================================
# 1. STRATEGY SPECIFICATION & PARAMETERS
# ==============================================================================
# Universe: Top highly liquid Nasdaq-100 components
TICKERS = [
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 
    'META', 'TSLA', 'AVGO', 'COST', 'NFLX', 
    'AMD', 'PEP', 'ADBE', 'QCOM', 'TXN'
]
BENCHMARK_TICKER = 'QQQ'

# Backtest Window
START_DATE = '2016-01-01'
BACKTEST_START = '2018-01-01'
BACKTEST_END = '2023-12-31'

# Strategy Hyperparameters
RSI_PERIOD = 4
RSI_OVERSOLD = 15
RSI_EXIT = 55
REGIME_SMA = 200
EXIT_SMA = 5
ADX_PERIOD = 14
ADX_THRESHOLD = 25
ATR_PERIOD = 20
STOP_LOSS_MULT = 3

# Portfolio Constraints
INITIAL_CAPITAL = 100000.0
MAX_POSITIONS = 10
MAX_SINGLE_WEIGHT = 0.10
RISK_PER_TRADE = 0.01
SLIPPAGE = 0.0002  # 2 basis points

# ==============================================================================
# 2. TECHNICAL INDICATOR CALCULATIONS (WILDER'S FORMULAS)
# ==============================================================================
def calculate_rsi(series, period=4):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=20):
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def calculate_adx(df, period=14):
    up = df['High'].diff()
    down = -df['Low'].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    smoothed_plus_dm = pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    smoothed_minus_dm = pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (smoothed_plus_dm / (atr + 1e-10))
    minus_di = 100 * (smoothed_minus_dm / (atr + 1e-10))
    dx = 100 * (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10)
    return dx.ewm(alpha=1/period, adjust=False).mean()

# ==============================================================================
# 3. DATA ACQUISITION
# ==============================================================================
data_dict = {}
for ticker in TICKERS:
    df = yf.download(ticker, start=START_DATE, end=BACKTEST_END, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['SMA_200'] = df['Close'].rolling(window=REGIME_SMA).mean()
    df['SMA_5'] = df['Close'].rolling(window=EXIT_SMA).mean()
    df['RSI_4'] = calculate_rsi(df['Close'], period=RSI_PERIOD)
    df['ADX_14'] = calculate_adx(df, period=ADX_PERIOD)
    df['ATR_20'] = calculate_atr(df, period=ATR_PERIOD)
    df['ADV_20'] = (df['Close'] * df['Volume']).rolling(window=20).mean()
    data_dict[ticker] = df

qqq_df = yf.download(BENCHMARK_TICKER, start=START_DATE, end=BACKTEST_END, progress=False)
if isinstance(qqq_df.columns, pd.MultiIndex): qqq_df.columns = qqq_df.columns.get_level_values(0)
qqq_df['SMA_200'] = qqq_df['Close'].rolling(window=REGIME_SMA).mean()
backtest_dates = [d for d in qqq_df.index if d >= pd.Timestamp(BACKTEST_START)]

# Earnings Filter Simulation
earnings_dict = {t: set(data_dict[t].index[range(sum(ord(c) for c in t) % 40 + 15, len(data_dict[t]), 63)]) for t in TICKERS}

# ==============================================================================
# 4. BACKTESTING LOOP
# ==============================================================================
cash, active_positions, portfolio_history, trade_log = INITIAL_CAPITAL, {}, [], []

for current_date in backtest_dates:
    # Exit loop
    for ticker in list(active_positions.keys()):
        pos = active_positions[ticker]
        if current_date not in data_dict[ticker].index: continue
        row = data_dict[ticker].loc[current_date]
        stop_price = pos['entry_price'] - (STOP_LOSS_MULT * pos['entry_atr'])
        if row['Low'] <= stop_price or row['Close'] > row['SMA_5'] or row['RSI_4'] > RSI_EXIT:
            exit_price = min(row['Close'], stop_price) if row['Low'] <= stop_price else row['Close']
            revenue = pos['shares'] * exit_price * (1 - SLIPPAGE)
            cash += revenue
            trade_log.append({'Ticker': ticker, 'PnL': revenue - (pos['shares'] * pos['entry_price'] * (1 + SLIPPAGE))})
            del active_positions[ticker]

    # Entry loop
    current_equity = cash + sum(pos['shares'] * data_dict[t].loc[current_date, 'Close'] for t, pos in active_positions.items())
    if len(active_positions) < MAX_POSITIONS and current_date in qqq_df.index and qqq_df.loc[current_date, 'Close'] > qqq_df.loc[current_date, 'SMA_200']:
        candidates = []
        for ticker in TICKERS:
            if ticker in active_positions or current_date not in data_dict[ticker].index: continue
            df = data_dict[ticker]
            if any(current_date + pd.Timedelta(days=i) in earnings_dict[ticker] for i in range(4)): continue
            row = df.loc[current_date]
            if row['Close'] > row['SMA_200'] and row['ADX_14'] < ADX_THRESHOLD and row['RSI_4'] < RSI_OVERSOLD and row['ADV_20'] > 1e8:
                candidates.append((ticker, row['RSI_4'], row['Close'], row['ATR_20']))
        for ticker, _, close, atr in sorted(candidates, key=lambda x: x[1]):
            shares = min((current_equity * RISK_PER_TRADE) / (STOP_LOSS_MULT * atr), (current_equity * MAX_SINGLE_WEIGHT) / close)
            if shares * close <= cash:
                cash -= shares * close * (1 + SLIPPAGE)
                active_positions[ticker] = {'shares': shares, 'entry_price': close, 'entry_atr': atr}
    portfolio_history.append({'Date': current_date, 'Value': current_equity})

# ==============================================================================
# 5. METRICS & PLOTTING
# ==============================================================================
perf = pd.DataFrame(portfolio_history).set_index('Date')
print(f"Total Return: {((perf['Value'].iloc[-1]/INITIAL_CAPITAL)-1)*100:.2f}%")
print(f"Max Drawdown: {(perf['Value']/perf['Value'].cummax()-1).min()*100:.2f}%")
perf['Value'].plot(title="Strategy Equity Curve", figsize=(10, 5)).get_figure().show()