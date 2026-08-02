# Dollar Cost Averaging Model for Bitcoin Investments

## Project Background

Dollar Cost Averaging (DCA) is an investment strategy where an investor divides up the total amount to be invested across periodic purchases of a target asset to reduce the impact of volatility on the overall purchase. The goal of this project is to demonstrate how DCA could be applied to Bitcoin investments using historical price data. This approach allows individuals to understand the potential benefits and returns of systematically investing in Bitcoin, similar to how one might contribute to a 401(k) or retirement fund.

## Live Tool

**[₿itcoin DCA Calculator](https://dca-btc-with-me.netlify.app/)** — a browser-based simulator where you set a start date, investment frequency, and dollar amount, then instantly see your total return, portfolio growth chart, and full purchase history.

## Data Source & Workflow

Historical Bitcoin price data comes from the **[mczielinski/bitcoin-historical-data](https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data)** dataset on Kaggle — minute-level Bitstamp BTC/USD bars, aggregated here down to a single closing price per UTC day. The current build covers **2012-01-01 to today** (5,300+ daily closes, no gaps longer than one day).

Kaggle downloads require authentication, so the pipeline depends on two repository secrets — `KAGGLE_USERNAME` and `KAGGLE_KEY`. Generate them from your Kaggle account under *Settings → API → Create New Token*, then add them under *Settings → Secrets and variables → Actions* in this repo.

**Automated Daily Pipeline:**

1. **GitHub Actions** runs a scheduled job every day at 08:00 UTC (`.github/workflows/update-btc-data.yml`)
2. A **Python script** (`scripts/fetch_btc_prices.py`) downloads the dataset with the `kaggle` CLI and streams the minute-level CSV, keeping the last valid close for each UTC day
3. The output is written to `data/btc-prices.json` — a static file committed to the repo
4. **Netlify** detects the push and auto-deploys the updated site

This means:
- **No client-side API calls** — the price data is pre-baked and served from the CDN
- **No credentials in the browser** — the Kaggle secrets are only ever read by the GitHub Actions runner
- **No CORS or rate-limit issues** — the browser only fetches a local static file
- **One upstream dependency** — freshness relies on the Kaggle dataset continuing to be updated. If it stalls, the workflow commits nothing and the site keeps serving the last good file, and the page's status chip turns amber once the data is more than three days old

## Project Structure

```
├── index.html                              # DCA calculator (single-page app)
├── netlify.toml                            # publish root + no-cache header for the data file
├── data/
│   └── btc-prices.json                     # Auto-generated daily price data
├── scripts/
│   └── fetch_btc_prices.py                 # Kaggle download → daily closes
└── .github/
    └── workflows/
        └── update-btc-data.yml             # Daily cron job
```

`netlify.toml` is load-bearing twice: `publish = "."` is what makes the page's
absolute `/data/btc-prices.json` request resolve, and the `must-revalidate`
header on that path is what stops the CDN serving yesterday's prices.

## Running it locally

The page fetches `/data/btc-prices.json` by **absolute path**, and browsers block
`fetch()` on `file://` outright — so opening `index.html` by double-clicking it
will always fail with the "no price data" error. Serve the directory instead:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Any static server works; it just has to serve
the repo root so `/data/…` resolves. No build step, no dependencies, no API keys
— `data/btc-prices.json` is committed, so the calculator works offline once served.

Rebuilding the price data is only needed if you want fresher numbers than the
committed file, and that part *does* need Kaggle credentials:

```bash
pip install kaggle
KAGGLE_USERNAME=you KAGGLE_KEY=xxxx python3 scripts/fetch_btc_prices.py
```

### Data file format

`data/btc-prices.json` is a standalone artifact — ~14 years of daily closes in
about 175 KB, with no gaps longer than a day — and is reusable on its own:

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
- **Start date**: Any date from 28 April 2013 to today (defaults to 1 year ago). The dataset reaches
  further back than this — the earlier floor is a deliberate legacy cutoff, see *Data Source* above
- **Frequency**: Weekly, bi-weekly, or monthly
- **Amount**: Any USD amount per purchase (defaults to $100)

For each purchase date, the simulator binary-searches for the most recent daily close **at or before** that date — never a later one, so the model can't look ahead — and calculates:
- Total invested
- Total BTC accumulated
- Average cost per BTC
- Current portfolio value
- Total profit/loss
- Return on investment (%)

Results are displayed as a summary table, an interactive chart (with ROI % on hover), and a full purchase history table with sortable columns.

### What the model assumes

These are stated on the page too, under *How this works*, but they matter to anyone reading the numbers:

- **"Monthly" means every 30 days**, not the same calendar date — roughly 12.2 purchases a year, with the date drifting earlier over time. Weekly is 7 days, bi-weekly 14.
- **No fees, spreads, or taxes.** A platform charging ~1% per buy leaves ~1% less BTC every time, so every figure the tool reports is an optimistic upper bound. Nothing is ever sold, so profit is unrealised.
- **Daily closes only** — intraday highs and lows are ignored.
- **Single venue.** Prices are Bitstamp BTC/USD, not a cross-exchange index; other venues will differ.
- **Purchases run through today**, so an earlier start date also means more total dollars invested. Compare runs on ROI rather than absolute profit.
- **Portfolio Value** prices the whole stack at the most recent daily close. In the history table, *Value on Date* prices it as of that row's date instead — which is why the last row and the summary differ.

## Key Features

- **Always-current data** via automated GitHub Actions + Kaggle pipeline
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
