# Reference: Well-Known Daily Trading Strategies

A starter set of established, well-documented strategies suitable for **daily** (`1d`) data and
single/few liquid instruments — the constraints this project's backtester operates under. Use these
as grounded starting points; adapt parameters to the objective rather than copying blindly. None is a
guaranteed money-maker — each has known failure modes, listed.

---

## 1. RSI(2) Mean Reversion (Connors–Alvarez)
- **Hypothesis:** Short-term pullbacks within an uptrend tend to revert. A very fast RSI catches
  "rubber-band" oversold stretches.
- **Regime filter:** Price > 200-day SMA (only trade longs in an uptrend).
- **Entry (long):** RSI(2) < 10 (deeply oversold).
- **Exit:** RSI(2) > 70, or price closes above the 5-day SMA, or a time stop (e.g. 5 days).
- **Typical universe:** Liquid index ETFs (SPY, QQQ) or large-cap stocks.
- **Failure modes:** Catches falling knives if the regime filter is dropped; struggles in strong
  downtrends and during volatility spikes.

## 2. Cross-Sectional / Time-Series Momentum (12–1)
- **Hypothesis:** Assets that have risen over the past ~12 months (skipping the most recent month)
  tend to keep rising over the next month.
- **Signal:** Return from t-252 to t-21 (the "12 minus 1 month" return). Long if positive (time-series)
  or pick the top-ranked names (cross-sectional).
- **Rebalance:** Monthly. Hold roughly a month.
- **Skip-month:** Excluding the most recent ~21 days avoids short-term reversal contamination.
- **Failure modes:** Sharp momentum crashes at market turning points; whipsaws in choppy regimes.

## 3. Moving-Average Crossover (Trend Following)
- **Hypothesis:** Sustained trends persist; a fast MA crossing a slow MA marks a regime change.
- **Entry (long):** Fast SMA (e.g. 50) crosses **above** slow SMA (e.g. 200) — "golden cross".
- **Exit:** Fast SMA crosses **below** slow SMA — "death cross".
- **Notes:** Very few trades; most return comes from a handful of large trends. Often paired with a
  volatility-based position size.
- **Failure modes:** Many small losing whipsaws in range-bound markets; late entries/exits by design.

## 4. Bollinger Band Reversion
- **Hypothesis:** Price tends to revert toward its moving average after stretching to a band extreme.
- **Bands:** 20-day SMA ± 2 standard deviations.
- **Entry (long):** Close below the lower band (optionally with an uptrend regime filter).
- **Exit:** Close back above the middle band (the 20-day SMA).
- **Failure modes:** In a strong downtrend price "walks the band" down — a regime filter or stop is
  essential.

## 5. Donchian Channel Breakout (Turtle-style)
- **Hypothesis:** A breakout to a new N-day high signals the start of a trend worth riding.
- **Entry (long):** Close above the highest high of the last 20 days.
- **Exit:** Close below the lowest low of the last 10 days (a shorter trailing channel), or an
  ATR-based stop.
- **Notes:** Classic trend-following entry; pairs well with volatility-scaled sizing.
- **Failure modes:** False breakouts in choppy markets; gives back open profit on reversals.

---

## Cross-cutting guidance
- **Avoid look-ahead bias:** act on bar *t*'s signal at bar *t+1* (lag signals before computing returns).
- **Warm-up:** indicators with long lookbacks (e.g. SMA200) need enough history before the first trade.
- **Risk controls:** always define position sizing and a hard stop / max-loss.
- **Overfitting:** prefer round, defensible parameters; be suspicious of oddly specific thresholds that
  only work on one historical window.
