# VRP — Variance Risk Premium

The volatility line of the firm. A research framework for harvesting the
**variance risk premium**: option-implied volatility tends to sit above the
volatility that actually shows up, and a seller of volatility is paid that gap.

This is a *risk premium*, not a prediction. We are not forecasting where the
market goes — we are being compensated for bearing a risk (sudden volatility)
that most participants pay to offload. That is why the edge persists where
direction-prediction edges do not.

> **Disclaimer:** Research and educational use only, not financial advice.
> **Selling volatility can lose more than the capital committed.** Respect it.

## The one principle: tail first

Selling volatility earns small, steady premiums most months and then takes a
large, fast loss when volatility spikes — pennies in front of a steamroller.
So this repo is built backwards from the usual order: **before asking "is the
premium there?", we measure the tail** — the worst months, the fat-tailed
distribution, how many winning months a single crash erases. Every sizing and
go-live decision is made against that tail, never against the flattering Sharpe.

Honesty about the downside is the entry ticket for this strategy.

## V1 — the proxy (this release)

`vrp_proxy.py` measures the premium with free data we already have:

- **VIX** as the implied-volatility proxy (30-day, annualized).
- **SPY realized volatility** over the matching forward ~30-day window.
- Premium = implied − realized; short-vol P&L proxy = implied² − realized².

It reports whether the premium exists, how often a seller wins, and — front and
center — the tail: skew, kurtosis, the worst months by date, and the ratio of
the worst loss to an average win.

```bash
pip install -r requirements.txt
python vrp_proxy.py --demo                          # synthetic, no files needed
python vrp_proxy.py --spy SPY.csv --vix VIX.csv     # real data
```

## Roadmap

- **V1 — proxy.** Is the premium real, and how brutal is the tail? *(here)*
- **V2 — real options backtest.** Replace the VIX/realized proxy with actual
  option positions (short straddles or variance swaps), with strikes, Greeks, and
  delta-hedging to strip out direction — only if V1 shows the premium is worth it.
- **V3 — risk-managed sizing.** Size positions against the measured tail (not the
  Sharpe): position limits, tail hedges (cheap far OTM puts), and a regime switch
  that cuts exposure when conditions turn. The crash defines the size.

The through-line, same as the equity line: try to *kill* the strategy with the
most honest test, and ship only what survives — with the tail respected up front.

## Relationship to MAAS

This is the firm's second strategy line. **MAAS** is the directional-equity line
(buy-the-dip research, sealed at v3.0). **VRP** is the volatility line. They are
separate repos because they trade different instruments, use different data, and
harvest different edge types — one tries to predict price, the other gets paid to
bear risk. Keeping them apart keeps each repo honest about what it actually does.
