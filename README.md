# Dollar Cost Averaging Calculator — Bitcoin

## Project Background

Dollar Cost Averaging (DCA) is an investment strategy where an investor divides up the total amount to be invested across periodic purchases of a target asset, to reduce the impact of volatility on the overall purchase. This project replays that strategy against real historical **Bitcoin** prices, so you can see what a fixed schedule of purchases would actually have produced in a highly volatile asset.

## Live Tool

**[₿itcoin DCA Calculator](https://dca-btc-with-me.netlify.app/)** — a browser-based simulator. Set a start date, contribution frequency and dollar amount, and your total return, portfolio growth chart, and full purchase history update live as you go.

> The S&P 500 / 401(k) calculator is a separate project: https://project401k.netlify.app/

## Data Source & Workflow

The calculator is driven by pre-baked static JSON committed to this repo.

| | Bitcoin |
|---|---|
| Source | [Kaggle `mczielinski`](https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data) — minute-level Bitstamp, aggregated to daily closes |
| Coverage | 2012-01-01 → today (5,300+ closes) |
| Schedule | Daily, 08:00 UTC |
| Credentials | **Requires `KAGGLE_USERNAME` + `KAGGLE_KEY`** |
| Script | `scripts/fetch_btc_prices.py` |
| Output | `data/btc-prices.json` |

Kaggle downloads require authentication, so add `KAGGLE_USERNAME` and `KAGGLE_KEY` under *Settings → Secrets and variables → Actions*. Generate them from your Kaggle account under *Settings → API → Create New Token*. **Expired Kaggle credentials are the most likely cause of stale data** — the job fails, commits nothing, and the site keeps serving the last good file.

The scheduled Action writes the JSON, commits it, and Netlify auto-deploys. This means:

- **No client-side API calls** — price data is pre-baked and served from the CDN
- **No credentials in the browser** — secrets are only ever read by the Actions runner
- **No CORS or rate-limit issues** — the browser only fetches a local static file
- **One upstream dependency** — the dataset is volunteer-maintained on Kaggle. If it stalls, the workflow commits nothing and the header chip turns amber once data is more than three days old

## Project Structure

```
├── index.html                              # the calculator (single-page app)
├── netlify.toml                            # publish root + no-cache header for the data file
├── data/
│   └── btc-prices.json                     # auto-generated, daily
├── scripts/
│   └── fetch_btc_prices.py                 # Kaggle download → daily closes
├── tests/
│   ├── engine.test.mjs                     # simulate(), xirr(), the formatters
│   ├── timezone.test.mjs                   # same plan, three timezones
│   ├── harness.mjs                         # pulls the inline <script> into a vm
│   └── fixtures/
│       └── prices.json                     # committed synthetic price series
└── .github/
    └── workflows/
        ├── update-btc-data.yml             # daily cron
        └── test.yml                        # node --test on push and PR
```

`netlify.toml` is load-bearing twice: `publish = "."` is what makes the page's
absolute `/data/btc-prices.json` request resolve, and the `must-revalidate` header
on that path is what stops the CDN serving yesterday's prices.

## Running it locally

The page fetches `/data/btc-prices.json` by **absolute path**, and browsers block
`fetch()` on `file://` outright — so opening `index.html` by double-clicking it
will always fail with the "no price data" error. Serve the directory instead:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Any static server works; it just has to serve
the repo root so `/data/…` resolves. No build step, no dependencies, no API keys
— the price file is committed, so the calculator works offline once served.

Rebuilding price data is only needed for fresher numbers than the committed file,
and that part *does* need Kaggle credentials:

```bash
pip install kaggle && KAGGLE_USERNAME=you KAGGLE_KEY=xxxx python3 scripts/fetch_btc_prices.py
```

### Data file format

`data/btc-prices.json` is a standalone, reusable artifact (~175 KB):

```jsonc
{
  "generated": "2026-08-01T09:54:16Z",   // UTC build time
  "source":    "Kaggle/mczielinski — minute-level Bitstamp data aggregated to daily closes",
  "count":     5327,
  "prices":    [ { "ts": 1325376000, "price": 5.0 } ]   // ts = UNIX SECONDS (UTC), ascending
}
```

## Tests

No dependencies and no install step — the engine is exercised straight out of
`index.html`:

```bash
node --test tests/*.test.mjs
```

`tests/harness.mjs` extracts the inline `<script>`, evaluates it in a `node:vm`
context against a minimal DOM stub, and hands back the pure functions. The boot
code at the end of the script is cut off, so nothing fetches or renders.

- **`engine.test.mjs`** — golden results for several plans (purchase counts,
  totals, units, final value, ROI, average cost and the last history row), XIRR
  against closed-form cases including one it cannot solve, the *averaging effect*
  invariant that average cost never exceeds the mean price paid, the guard that a
  purchase never fills at a close later than its own date, the start-date rules,
  and the formatters.
- **`timezone.test.mjs`** — runs the same plans in child processes under `TZ=UTC`,
  `TZ=America/New_York` and `TZ=Australia/Sydney` and requires byte-identical
  output. The schedule steps with `setUTCDate()`; stepping in local time would
  drift by an hour across a daylight-saving change and can roll a purchase back
  onto the previous UTC day, filling it at the previous close.

Every expectation runs against `tests/fixtures/prices.json` — a small, committed,
deterministic series in the same schema as the real file — and against an end date
passed into `simulate()`. Nothing depends on `data/btc-prices.json` or on today's
date, so the daily data job can never turn the suite red.


## DCA Simulation

The calculator supports:
- **Start date**: Any date from 28 April 2013 to today (defaults to 1 year ago).
  The dataset reaches back to 2012 — the 2013 floor is a deliberate legacy cutoff.
  Quick presets (1Y · 3Y · 5Y · 10Y · Max — the horizons the original notebook studied) sit above the
  date field, and a timeline slider scrubs the start date through history
- **Frequency**: Weekly, bi-weekly, or monthly (defaults to weekly)
- **Amount**: Any USD amount per purchase (defaults to $100)
- **Shareable plans**: once you change anything, the address bar links to exactly the plan on screen
  (`?start=2020-01-01&freq=7&amt=100`), and *Copy link* puts it on the clipboard

For each purchase date, the simulator binary-searches for the most recent daily close **at or before** that date — never a later one, so the model can't look ahead — and calculates:
- Total invested
- Total BTC accumulated
- Average cost per BTC
- Current portfolio value
- Total profit/loss
- Return on investment (%) — cumulative over the whole period
- Annualised return (XIRR) — money-weighted, shown once a run spans at least a year

Results update live — there is no Run button. The page leads with the portfolio value and a plain-English
summary of the plan, then six KPI tiles, a chart of portfolio value against total invested (linear or log
scale, gain/loss shading between the lines, and a readout of value, invested and ROI at whatever date the
pointer is on), an **averaging effect** card, and a collapsible purchase history with sortable columns and
CSV export.

### What the model assumes

These are stated on the page too, under *How this works*, but they matter to anyone reading the numbers:

- **"Monthly" means every 30 days**, not the same calendar date — roughly 12.2 purchases a year, with the date drifting earlier over time. Weekly is 7 days, bi-weekly 14.
- **No fees, spreads, or taxes.** A platform charging ~1% per buy leaves ~1% less BTC every time, so every figure the tool reports is an optimistic upper bound. Nothing is ever sold, so profit is unrealised.
- **Daily closes only** — intraday highs and lows are ignored.
- **Prices are single-venue** (Bitstamp BTC/USD), not a cross-exchange index; other venues will differ.
- **Annualised return is XIRR**, solved by Newton's method with a bisection fallback. It is money-weighted, so it accounts for *when* each contribution went in. The naive `(value / invested)^(1/years)` shortcut credits every dollar with the full elapsed period and materially understates a contribution stream — on a weekly run from 2013 it reports roughly 39%/yr against a true 59%/yr.
- **Purchases run through today**, so an earlier start date also means more total dollars invested. Compare runs on ROI rather than absolute profit.
- **Portfolio Value** prices the whole stack at the most recent daily close. In the history table, *Value on Date* prices it as of that row's date instead — which is why the last row and the summary differ.

## Key Features

- **Live results** — every change re-runs the simulation; drag the start-date timeline and watch the numbers move
- **Shareable links** — the URL encodes the whole plan: start date, frequency and amount
- **Always-current data** via an automated daily GitHub Actions + Kaggle pipeline
- **localStorage caching**, keyed per day, for instant repeat visits
- **Sortable history table** — every column sorts, by click or keyboard; the order survives live re-runs; exports to CSV
- **Chart readout** — value, invested and ROI at any date, on a linear or log scale
- **Averaging effect** — average cost per BTC against the average price on your purchase dates
- **Staleness warning** — the header chip turns amber if the data is over three days old
- **Responsive, dark-only design** — works on desktop and mobile
- **No external dependencies at runtime** beyond Chart.js (pinned to 4.5.1, with an SRI hash)

## Conclusion

This project illustrates how Dollar Cost Averaging can be applied to Bitcoin investments over any time horizon, by replaying purchases at regular intervals against real historical prices.

The clearest thing it demonstrates is the mechanic DCA is named for: because a fixed dollar amount buys more BTC when the price is low, **average cost per BTC lands below the average of the prices actually paid**. Run weekly buys from 2013 and the average cost comes out near \$970 against a mean paid price above \$26,000 — the two numbers sit side by side in the page's *averaging effect* card.

What it does **not** show is whether DCA beats the alternatives. There is no lump-sum or buy-the-dip baseline to compare against, the sample is one asset over one stretch of history, and fees are excluded. Treat the output as "here is what this schedule would have produced," not as evidence that this schedule is best.

The approach adapts to different amounts, frequencies, or other assets — it is a worked example for anyone wanting to understand or implement a DCA strategy, not a recommendation to adopt one.

---

**Disclaimer:** This tool is for educational and informational purposes only. Past performance does not guarantee future results. Bitcoin is a highly volatile asset — always conduct your own research before making any investment decisions.
