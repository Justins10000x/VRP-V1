#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  VRP-V1 — vrp_proxy.py
  THE VARIANCE RISK PREMIUM, MEASURED TAIL-FIRST

  The premium: option-implied volatility (proxied by VIX) tends to sit ABOVE the
  volatility that actually shows up (realized vol). A volatility SELLER harvests
  that gap. It is one of the most documented edges in finance.

  The catch, and why this file leads with it: selling volatility earns small,
  steady premiums most months and then takes a large, fast loss when vol spikes.
  Pennies in front of a steamroller. So before we ask "is the premium there?",
  we measure the TAIL — the worst months, the skew, how many wins one disaster
  erases. Sizing must respect the tail, never the Sharpe.

  This V1 uses FREE data you already have:
    • VIX               → implied-vol proxy (30-day, annualized %)
    • SPY realized vol  → what actually happened over the next ~30 days

  USAGE:
    python vrp_proxy.py --demo
    python vrp_proxy.py --spy SPY.csv --vix VIX.csv
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252
HORIZON = 21            # ~30 calendar days, matching the VIX horizon


# ── self-contained loaders (this repo stands alone) ─────────────────────────
def load_prices(path):
    df = pd.read_csv(path, thousands=',')
    df.columns = df.columns.str.strip().str.replace('"', '')
    if 'Close/Last' in df.columns:
        df = df.rename(columns={'Close/Last': 'Close'})
    if 'Price' in df.columns and 'Close' not in df.columns:
        df = df.rename(columns={'Price': 'Close'})
    df['Date'] = pd.to_datetime(df['Date'].astype(str).str.replace('"', ''), format='mixed')
    df['Close'] = pd.to_numeric(df['Close'].astype(str).str.replace(',', ''), errors='coerce')
    return df[['Date', 'Close']].dropna().sort_values('Date').reset_index(drop=True)


def load_vix(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    dcol = next((c for c in df.columns if 'DATE' in c.upper()), df.columns[0])
    ccol = next((c for c in df.columns if 'CLOSE' in c.upper()), df.columns[-1])
    df = df.rename(columns={dcol: 'Date', ccol: 'VIX'})
    df['Date'] = pd.to_datetime(df['Date'], format='mixed')
    df['VIX'] = pd.to_numeric(df['VIX'], errors='coerce')
    return df[['Date', 'VIX']].dropna().sort_values('Date').reset_index(drop=True)


# ── core computation ────────────────────────────────────────────────────────
def build(spy, vix):
    d = spy.merge(vix, on='Date', how='inner').sort_values('Date').reset_index(drop=True)
    r = np.log(d['Close'] / d['Close'].shift(1))
    # realized vol over the NEXT HORIZON days, annualized %
    fwd_sumsq = (r ** 2).rolling(HORIZON).sum().shift(-HORIZON)
    d['RV_fwd'] = np.sqrt(TRADING_DAYS / HORIZON * fwd_sumsq) * 100
    d['VRP_vol'] = d['VIX'] - d['RV_fwd']                 # vol points (the premium)
    d['PnL_var'] = d['VIX'] ** 2 - d['RV_fwd'] ** 2       # short-vol P&L proxy (vol²)
    return d.dropna(subset=['RV_fwd']).reset_index(drop=True)


def analyze(d, label):
    print('\n' + '=' * 74)
    print(f'  VARIANCE RISK PREMIUM — {label}')
    print('=' * 74)

    # Non-overlapping monthly observations (avoid overlap-inflated stats)
    m = d.iloc[::HORIZON].reset_index(drop=True)
    pnl = m['PnL_var'].values
    vrp = m['VRP_vol'].values

    print(f'\n  Sample: {len(m)} non-overlapping ~monthly windows '
          f'({d["Date"].min().date()} → {d["Date"].max().date()})')

    print('\n  ── IS THE PREMIUM THERE? ──')
    print(f'     Mean VRP (implied − realized) : {vrp.mean():+.2f} vol points '
          f'{"(premium exists)" if vrp.mean() > 0 else "(no premium)"}')
    print(f'     Months implied > realized     : {(vrp > 0).mean()*100:.1f}%  '
          '(how often the seller wins)')
    print(f'     Mean short-vol P&L            : {pnl.mean():+.1f} vol²   '
          f'{"(positive edge)" if pnl.mean() > 0 else "(negative)"}')

    print('\n  ── NOW THE TAIL (the part that matters most) ──')
    sd = pnl.std()
    sharpe = pnl.mean() / sd * np.sqrt(12) if sd > 0 else 0
    print(f'     Naive annualized Sharpe       : {sharpe:.2f}   '
          '(flatters short-vol; it cannot price the crash)')
    print(f'     Skew / excess kurtosis        : {stats.skew(pnl):+.2f} / {stats.kurtosis(pnl):+.1f}   '
          '(fat-tailed; real VRP P&L skews sharply negative)')
    win = pnl[pnl > 0].mean() if (pnl > 0).any() else float('nan')
    worst = pnl.min()
    print(f'     Avg winning month             : {win:+.1f} vol²')
    print(f'     Worst month                   : {worst:+.1f} vol²')
    print(f'     One disaster erases           : {abs(worst/win):.0f} average winning months')

    cum = np.cumsum(pnl)
    dd = (cum - np.maximum.accumulate(cum)).min()
    print(f'     Max drawdown of the P&L        : {dd:.0f} vol²')

    print('\n     Worst 5 months (the steamroller):')
    w = m.assign(PnL=m['PnL_var']).nsmallest(5, 'PnL_var')
    for _, row in w.iterrows():
        print(f'        {row["Date"].date()}  VIX {row["VIX"]:5.1f}  '
              f'realized {row["RV_fwd"]:5.1f}  →  P&L {row["PnL_var"]:+8.0f}')

    print('\n  ' + '-' * 70)
    verdict = (vrp.mean() > 0 and pnl.mean() > 0)
    print(f'  VERDICT: the premium is {"REAL and positive" if verdict else "absent here"} — '
          'but the tail is the whole story.')
    print('  The edge is collectable; the risk is a known, modeled crash loss. V2 must')
    print('  size against THAT tail, not the flattering Sharpe. Honesty about the')
    print('  downside is the entry ticket for this strategy.')
    print('  ' + '-' * 70)


# ── demo data (premium baked in, with real vol spikes) ──────────────────────
def make_demo():
    rng = np.random.default_rng(3)
    n = TRADING_DAYS * 12
    vol = np.full(n, 0.008)
    for s in (800, 1600, 2400):           # three vol explosions (crashes)
        vol[s:s + 15] = 0.045
    vol *= np.exp(rng.normal(0, 0.18, n))
    rets = rng.normal(0.0003, 1.0, n) * vol
    price = 100 * np.cumprod(1 + rets)
    dates = pd.bdate_range('2014-01-01', periods=n)
    spy = pd.DataFrame({'Date': dates, 'Close': price})

    r = np.log(price[1:] / price[:-1])
    trail = pd.Series(r).pow(2).rolling(HORIZON).mean()
    trail_vol = (np.sqrt(TRADING_DAYS * trail) * 100).reindex(range(n)).ffill().bfill().values
    vix = np.clip(trail_vol + 3.0 + rng.normal(0, 1.2, n), 9, None)   # implied = trailing + ~3 premium
    vix_df = pd.DataFrame({'Date': dates, 'VIX': vix})
    return spy, vix_df


def main():
    ap = argparse.ArgumentParser(description='VRP-V1 — variance risk premium proxy')
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--spy'); ap.add_argument('--vix')
    a = ap.parse_args()

    print('\n' + '═' * 74)
    print('  VRP-V1 — VARIANCE RISK PREMIUM (tail-first)')
    print(f'  horizon={HORIZON}d (~30 calendar) | VIX = implied proxy | SPY = realized')
    print('═' * 74)

    if a.demo:
        spy, vix = make_demo()
        analyze(build(spy, vix), 'DEMO (synthetic, premium + 3 vol spikes)')
    elif a.spy and a.vix:
        analyze(build(load_prices(a.spy), load_vix(a.vix)), 'SPY / VIX')
    else:
        ap.error('need --demo, or --spy and --vix')


if __name__ == '__main__':
    main()
