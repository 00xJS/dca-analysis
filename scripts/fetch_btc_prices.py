#!/usr/bin/env python3
"""
fetch_btc_prices.py
───────────────────
Fetches the full daily BTC/USD closing-price history from Kraken's
public OHLC endpoint (no API key required) and writes it to
data/btc-prices.json for the DCA calculator to consume.

Kraken OHLC endpoint:
  GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440&since=<unix>

Response candle format (index → field):
  0 time | 1 open | 2 high | 3 low | 4 close | 5 vwap | 6 volume | 7 count

Pagination: each response includes a `result.last` timestamp; pass that
as `since` on the next request. Stop when last ≤ previous since value
or no candles are returned.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
PAIR            = "XBTUSD"
INTERVAL        = 1440                  # daily candles (minutes)
START_TIMESTAMP = 1357344000            # 2013-01-05 — earliest Kraken BTC data
REQUEST_DELAY   = 1.2                   # seconds between requests (polite to API)
MAX_RETRIES     = 3
OUTPUT_PATH     = Path(__file__).resolve().parent.parent / "data" / "btc-prices.json"


# ── Fetch helpers ─────────────────────────────────────────────────────────────
def fetch_ohlc(since: int, attempt: int = 0) -> tuple[list, int]:
    """Fetch one page of OHLC candles from Kraken. Returns (candles, last_ts)."""
    url = f"{KRAKEN_OHLC_URL}?pair={PAIR}&interval={INTERVAL}&since={since}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "btc-dca-calculator/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        if data.get("error"):
            raise RuntimeError(f"Kraken API error: {data['error']}")

        # Kraken quirk: request uses "XBTUSD" but the response key is
        # "XXBTZUSD" (their internal XX-prefix for crypto, Z-prefix for fiat).
        # Dynamically grab the first result key that isn't "last".
        pair_keys = [k for k in data["result"] if k != "last"]
        if not pair_keys:
            return [], since
        candles = data["result"][pair_keys[0]]
        last_ts = int(data["result"].get("last", since))
        return candles, last_ts

    except (urllib.error.URLError, RuntimeError) as exc:
        if attempt < MAX_RETRIES - 1:
            wait = 2 ** attempt * 2
            print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s (error: {exc})")
            time.sleep(wait)
            return fetch_ohlc(since, attempt + 1)
        raise


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    all_prices: list[dict] = []
    since = START_TIMESTAMP
    now   = int(time.time())
    page  = 0

    print(f"Fetching BTC/USD daily prices from Kraken (pair={PAIR}, interval=1d) …")

    while since < now:
        candles, last_ts = fetch_ohlc(since)

        if not candles:
            print("  No candles returned — reached end of available data.")
            break

        page += 1
        for c in candles:
            ts    = int(c[0])
            close = float(c[4])
            if close > 0:
                all_prices.append({"ts": ts, "price": close})

        newest = datetime.fromtimestamp(candles[-1][0], tz=timezone.utc).date()
        print(f"  Page {page}: {len(candles)} candles, newest = {newest}")

        if last_ts <= since:
            break                       # no forward progress — stop
        since = last_ts
        time.sleep(REQUEST_DELAY)

    # ── De-duplicate and sort ascending ──────────────────────────────────────
    seen:   set[int]        = set()
    unique: list[dict]      = []
    for p in sorted(all_prices, key=lambda x: x["ts"]):
        if p["ts"] not in seen:
            seen.add(p["ts"])
            unique.append(p)

    # ── Write output ──────────────────────────────────────────────────────────
    output = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":    "Kraken OHLC API – XBTUSD daily closes – no API key required",
        "count":     len(unique),
        "prices":    unique,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")
    print(f"\nDone — {len(unique)} price points written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
