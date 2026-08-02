# Dollar Cost Averaging Calculator — Bitcoin & S&P 500

## Project Background

Dollar Cost Averaging (DCA) is an investment strategy where an investor divides up the total amount to be invested across periodic purchases of a target asset, to reduce the impact of volatility on the overall purchase. This project replays that strategy against real historical prices for two very different assets — **Bitcoin**, and the **S&P 500** in the style of a 401(k) contribution — so the same mechanic can be compared across a highly volatile asset and a broad equity index.

## Live Tool

**[DCA Calculator](https://dca-btc-with-me.netlify.app/)** — a browser-based simulator. Pick an asset, set a start date, contribution frequency and dollar amount, and see your total return, portfolio growth chart, and full purchase history.

- Bitcoin: <https://dca-btc-with-me.netlify.app/>
- S&P 500: <https://dca-btc-with-me.netlify.app/?asset=sp500>

The S&P 500 view adds an **employer match** field, mirroring how a 401(k) actually accrues.

> Previously two separate projects. `project-401k` was merged into this repo (history included) so both assets share one engine instead of two near-identical forks.

## Data Sources & Workflow

Both assets are driven by pre-baked static JSON committed to this repo, with an identical schema, so the simulation engine is asset-agnostic.

| | Bitcoin | S&P 500 |
|---|---|---|
| Source | [Kaggle `mczielinski`](https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data) — minute-level Bitstamp, aggregated to daily closes | [Yahoo Finance `^GSPC`](https://finance.yahoo.com/quote/%5EGSPC/) via `yfinance` |
| Coverage | 2012-01-01 → today (5,300+ closes) | 1927-12-30 → today (24,700+ closes) |
| Schedule | Daily, 08:00 UTC | Weekdays, 21:00 UTC (after US close) |
| Credentials | **Requires `KAGGLE_USERNAME` + `KAGGLE_KEY`** | None |
| Script | `scripts/fetch_btc_prices.py` | `scripts/fetch_sp500_prices.py` |
| Output | `data/btc-prices.json` | `data/sp500-prices.json` |

Kaggle downloads require authentication, so add `KAGGLE_USERNAME` and `KAGGLE_KEY` under *Settings → Secrets and variables → Actions*. Generate them from your Kaggle account under *Settings → API → Create New Token*. **Expired Kaggle credentials are the most likely cause of stale Bitcoin data** — the job fails, commits nothing, and the site keeps serving the last good file.

Each scheduled Action writes its JSON, commits it, and Netlify auto-deploys. This means:

- **No client-side API calls** — price data is pre-baked and served from the CDN
- **No credentials in the browser** — secrets are only ever read by the Actions runner
- **No CORS or rate-limit issues** — the browser only fetches a local static file
- **Upstream dependencies** — the Bitcoin dataset is volunteer-maintained on Kaggle. If either upstream stalls, the workflow commits nothing and the header chip turns amber once data is more than three days old

## Project Structure

```
├── index.html                              # both calculators (single-page app)
├── netlify.toml                            # publish root + no-cache headers for both data files
├── data/
│   ├── btc-prices.json                     # auto-generated, daily
│   └── sp500-prices.json                   # auto-generated, weekdays
├── scripts/
│   ├── fetch_btc_prices.py                 # Kaggle download → daily closes
│   └── fetch_sp500_prices.py               # yfinance ^GSPC → daily closes
└── .github/
    └── workflows/
        ├── update-btc-data.yml             # daily cron
        └── update-sp500-data.yml           # weekday cron
```

Adding a third asset is a config entry in the `ASSETS` object in `index.html` plus a
fetch script emitting the same schema — the simulation itself needs no changes.

`netlify.toml` is load-bearing twice: `publish = "."` is what makes the page's
absolute `/data/*.json` requests resolve, and the `must-revalidate` headers on
those paths are what stop the CDN serving yesterday's prices.

## Running it locally

The page fetches `/data/*.json` by **absolute path**, and browsers block
`fetch()` on `file://` outright — so opening `index.html` by double-clicking it
will always fail with the "no price data" error. Serve the directory instead:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Any static server works; it just has to serve
the repo root so `/data/…` resolves. No build step, no dependencies, no API keys
— both price files are committed, so the calculator works offline once served.

Rebuilding price data is only needed for fresher numbers than the committed files.
The S&P script needs no credentials; the Bitcoin one does:

```bash
pip install yfinance && python3 scripts/fetch_sp500_prices.py
```

```bash
pip install kaggle && KAGGLE_USERNAME=you KAGGLE_KEY=xxxx python3 scripts/fetch_btc_prices.py
```

### Data file format

Both files share one schema, which is what lets a single engine drive both assets.
Each is a standalone, reusable artifact (BTC ~175 KB, S&P ~783 KB):

```jsonc
{
  "generated": "2026-08-01T09:54:16Z",   // UTC build time
  "source":    "Kaggle/mczielinski — minute-level Bitstamp data aggregated to daily closes",
  "count":     5327,
  "prices":    [ { "ts": 1325376000, "price": 5.0 } ]   // ts = UNIX SECONDS (UTC), ascending
}
```

## DCA Simulation

The calculator supports:
- **Asset**: Bitcoin or S&P 500, switchable in the header and linkable via `?asset=sp500`
- **Start date**: Bitcoin from 28 April 2013, S&P 500 from 3 January 1928 (both default to 1 year ago).
  The Bitcoin dataset reaches back to 2012 — that earlier floor is a deliberate legacy cutoff
- **Frequency**: Weekly, bi-weekly, or monthly (S&P 500 defaults to bi-weekly, matching most US payroll cycles)
- **Amount**: Any USD amount per purchase (defaults to $100)
- **Employer match** (S&P 500 only): an additional per-purchase amount, reported separately in the summary

For each purchase date, the simulator binary-searches for the most recent daily close **at or before** that date — never a later one, so the model can't look ahead — and calculates:
- Total invested (split into your contributions vs employer match, where applicable)
- Total units accumulated — BTC, or fractional index shares
- Average cost per unit
- Current portfolio value
- Total profit/loss
- Return on investment (%) — cumulative over the whole period
- Annualised return (XIRR) — money-weighted, shown once a run spans at least a year

Results are displayed as a summary table, an interactive chart (with ROI % on hover), and a full purchase history table with sortable columns.

### What the model assumes

These are stated on the page too, under *How this works*, but they matter to anyone reading the numbers:

- **"Monthly" means every 30 days**, not the same calendar date — roughly 12.2 purchases a year, with the date drifting earlier over time. Weekly is 7 days, bi-weekly 14.
- **No fees, spreads, or taxes.** A platform charging ~1% per buy leaves ~1% less of the asset every time, so every figure the tool reports is an optimistic upper bound. Nothing is ever sold, so profit is unrealised.
- **Daily closes only** — intraday highs and lows are ignored.
- **Bitcoin prices are single-venue** (Bitstamp), not a cross-exchange index; other venues will differ. S&P 500 figures are index levels, treated as fractional units of an index fund — real funds carry an expense ratio and may not track exactly.
- **Annualised return is XIRR**, solved by Newton's method with a bisection fallback. It is money-weighted, so it accounts for *when* each contribution went in. The naive `(value / invested)^(1/years)` shortcut credits every dollar with the full elapsed period and materially understates a contribution stream — on a 26-year S&P run it reports 5.76%/yr against a true 9.81%/yr.
- **Purchases run through today**, so an earlier start date also means more total dollars invested. Compare runs on ROI rather than absolute profit.
- **Portfolio Value** prices the whole stack at the most recent daily close. In the history table, *Value on Date* prices it as of that row's date instead — which is why the last row and the summary differ.

## Key Features

- **Two assets, one engine** — switch in the header, or deep-link with `?asset=sp500`
- **Always-current data** via automated GitHub Actions pipelines for both assets
- **localStorage caching**, keyed per day, for instant repeat visits
- **Sortable history table** — every column sorts, by click or keyboard
- **ROI tracking on chart hover** — shows return percentage at any point in time
- **Staleness warning** — the header chip turns amber if the data is over three days old
- **Responsive, dark-only design** — works on desktop and mobile
- **No external dependencies at runtime** beyond Chart.js

## Conclusion

This project illustrates how Dollar Cost Averaging can be applied to Bitcoin investments over any time horizon, by replaying purchases at regular intervals against real historical prices.

The clearest thing it demonstrates is the mechanic DCA is named for: because a fixed dollar amount buys more BTC when the price is low, **average cost per BTC lands below the average of the prices actually paid**. Run weekly buys from 2013 and the average cost comes out near \$960 against a mean paid price above \$26,000 — the two numbers are visible side by side in the summary and the history table.

What it does **not** show is whether DCA beats the alternatives. There is no lump-sum or buy-the-dip baseline to compare against, the sample is one asset over one stretch of history, and fees are excluded. Treat the output as "here is what this schedule would have produced," not as evidence that this schedule is best.

The approach adapts to different amounts, frequencies, or other assets — it is a worked example for anyone wanting to understand or implement a DCA strategy, not a recommendation to adopt one.

---

**Disclaimer:** This tool is for educational and informational purposes only. Past performance does not guarantee future results. Bitcoin is a highly volatile asset — always conduct your own research before making any investment decisions.
