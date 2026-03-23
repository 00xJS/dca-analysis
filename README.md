# Dollar Cost Averaging Model for Bitcoin Investments

## Project Background

Dollar Cost Averaging (DCA) is an investment strategy where an investor divides up the total amount to be invested across periodic purchases of a target asset to reduce the impact of volatility on the overall purchase. The goal of this project is to demonstrate how DCA could be applied to Bitcoin investments using historical price data. This approach allows individuals to understand the potential benefits and returns of systematically investing in Bitcoin, similar to how one might contribute to a 401(k) or retirement fund.

## Live Tool

**[₿itcoin DCA Calculator](https://dca-analysis.netlify.app/)** — a browser-based simulator where you set a start date, investment frequency, and dollar amount, then instantly see your total return, portfolio growth chart, and full purchase history.

## Data Source & Workflow

Historical Bitcoin price data is sourced from the **[Kraken OHLC API](https://docs.kraken.com/api/docs/rest-api/get-ohlc-data)** (XBTUSD daily closes). Kraken's public API requires no API key and provides reliable data back to 2013.

**Automated Daily Pipeline:**

1. **GitHub Actions** runs a scheduled job every day at 08:00 UTC (`.github/workflows/update-btc-data.yml`)
2. A **Python script** (`scripts/fetch_btc_prices.py`) fetches the full daily price history from Kraken, paginating in 720-candle chunks
3. The output is written to `data/btc-prices.json` — a static file committed to the repo
4. **Netlify** detects the push and auto-deploys the updated site

This means:
- **No client-side API calls** — the price data is pre-baked and served from the CDN
- **No API keys or secrets** — Kraken's public endpoint is completely free
- **No CORS or rate-limit issues** — the browser only fetches a local static file
- **No manual maintenance** — data stays current automatically

## Project Structure

```
├── index.html                              # DCA calculator (single-page app)
├── data/
│   └── btc-prices.json                     # Auto-generated daily price data
├── scripts/
│   └── fetch_btc_prices.py                 # Kraken API fetch script
└── .github/
    └── workflows/
        └── update-btc-data.yml             # Daily cron job
```

## DCA Simulation

The calculator supports:
- **Start date**: Any date from January 2013 to today (defaults to 1 year ago)
- **Frequency**: Weekly, bi-weekly, or monthly
- **Amount**: Any USD amount per purchase (defaults to $100)

For each purchase date, the simulator finds the closest daily closing price via binary search and calculates:
- Total invested
- Total BTC accumulated
- Average cost per BTC
- Current portfolio value
- Total profit/loss
- Return on investment (%)

Results are displayed as a summary table, an interactive chart (with ROI % on hover), and a full purchase history table with sortable columns.

## Key Features

- **Always-current data** via automated GitHub Actions + Kraken pipeline
- **localStorage caching** with 24-hour TTL for instant repeat visits
- **Graceful fallbacks** — stale cache used if the static file is unavailable
- **Sortable history table** — click #, Date, BTC Bought, or Profit/Loss headers
- **ROI tracking on chart hover** — shows return percentage at any point in time
- **Responsive design** — works on desktop and mobile
- **No external dependencies at runtime** beyond Chart.js

## Conclusion

This project illustrates how Dollar Cost Averaging can be applied to Bitcoin investments over any time horizon. By simulating purchases at regular intervals against real historical prices, the tool shows that DCA can mitigate the impact of price volatility.

- Even with Bitcoin's high volatility, a regular investment strategy like DCA can lead to significant gains over time, especially when viewed as part of a long-term savings plan.
- The ROI calculated from this model underscores the potential of Bitcoin as an investment vehicle when approached systematically.

This model can be adapted for different investment amounts, frequencies, or even applied to other cryptocurrencies or investment vehicles. It serves as a practical example for anyone interested in understanding or implementing DCA strategies in the cryptocurrency market.

---

**Disclaimer:** This tool is for educational and informational purposes only. Past performance does not guarantee future results. Bitcoin is a highly volatile asset — always conduct your own research before making any investment decisions.
