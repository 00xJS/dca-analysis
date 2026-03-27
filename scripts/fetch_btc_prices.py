#!/usr/bin/env python3
"""
fetch_btc_prices.py
───────────────────
Builds data/btc-prices.json from two sources:

  1. Kaggle — mczielinski/bitcoin-historical-data
     Minute-level Bitstamp OHLCV from 2012 → near-today.
     Aggregated to daily closes (last non-NaN close per UTC day).

  2. Kraken — public OHLC API (no key required)
     Fills any gap between Kaggle's last date and today.

Run daily via GitHub Actions. Requires env vars:
  KAGGLE_USERNAME  — your Kaggle username
  KAGGLE_KEY       — your Kaggle API key
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
KAGGLE_DATASET  = "mczielinski/bitcoin-historical-data"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
PAIR            = "XBTUSD"
INTERVAL        = 1440          # daily candles (minutes)
REQUEST_DELAY   = 1.2           # seconds between Kraken requests
MAX_RETRIES     = 3
OUTPUT_PATH     = Path(__file__).resolve().parent.parent / "data" / "btc-prices.json"


# ── Kaggle: download + parse ───────────────────────────────────────────────────
def download_kaggle_dataset(dest_dir: str) -> Path:
    """Download and unzip the Kaggle dataset. Returns path to the CSV file."""
    username = os.environ.get("KAGGLE_USERNAME", "").strip()
    key      = os.environ.get("KAGGLE_KEY", "").strip()

    if not username or not key:
        raise EnvironmentError(
            "KAGGLE_USERNAME and KAGGLE_KEY environment variables must be set."
        )

    # Write kaggle.json so the CLI can authenticate
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    kaggle_json = kaggle_dir / "kaggle.json"
    kaggle_json.write_text(json.dumps({"username": username, "key": key}))
    kaggle_json.chmod(0o600)

    print(f"Downloading Kaggle dataset: {KAGGLE_DATASET} …")
    result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", KAGGLE_DATASET,
         "--unzip", "-p", dest_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"kaggle CLI failed:\n{result.stderr}")

    # Find the CSV (dataset may have one or more CSV files — take the largest)
    csvs = list(Path(dest_dir).glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No CSV found in {dest_dir} after download.")
    csv_file = max(csvs, key=lambda p: p.stat().st_size)
    print(f"  Using file: {csv_file.name} ({csv_file.stat().st_size // 1_000_000} MB)")
    return csv_file


def parse_kaggle_csv(csv_file: Path) -> dict[str, float]:
    """
    Stream the minute-level CSV and return {date_str: close_price}.
    Keeps the last valid close seen for each UTC date.
    Columns: Timestamp, Open, High, Low, Close, Volume_(BTC), ...
    """
    print("Parsing CSV → daily closes …")
    daily: dict[str, float] = {}
    rows_read = 0

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_read += 1
            try:
                ts    = int(float(row["Timestamp"]))
                close = row.get("Close", "").strip()
                if not close or close.lower() in ("nan", ""):
                    continue
                close = float(close)
                if close <= 0:
                    continue
                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                daily[date_str] = close      # last close of the day wins
            except (ValueError, KeyError):
                continue

    print(f"  {rows_read:,} rows read → {len(daily)} unique trading days")
    return daily


# ── Kraken: fill the gap ───────────────────────────────────────────────────────
def fetch_kraken_ohlc(since: int, attempt: int = 0) -> tuple[list, int]:
    """Fetch one page of daily OHLC candles from Kraken."""
    url = f"{KRAKEN_OHLC_URL}?pair={PAIR}&interval={INTERVAL}&since={since}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "btc-dca-calculator/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        if data.get("error"):
            raise RuntimeError(f"Kraken API error: {data['error']}")

        pair_keys = [k for k in data["result"] if k != "last"]
        if not pair_keys:
            return [], since
        candles = data["result"][pair_keys[0]]
        last_ts = int(data["result"].get("last", since))
        return candles, last_ts

    except (urllib.error.URLError, RuntimeError) as exc:
        if attempt < MAX_RETRIES - 1:
            wait = 2 ** attempt * 2
            print(f"  Kraken retry {attempt + 1}/{MAX_RETRIES} after {wait}s ({exc})")
            time.sleep(wait)
            return fetch_kraken_ohlc(since, attempt + 1)
        raise


def fetch_kraken_gap(from_date_str: str) -> dict[str, float]:
    """
    Fetch daily closes from Kraken for dates strictly after from_date_str.
    Returns {date_str: close_price}.
    """
    from_dt  = datetime.strptime(from_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    since_ts = int(from_dt.timestamp())
    now_ts   = int(time.time())
    gap: dict[str, float] = {}

    print(f"Fetching Kraken gap: {from_date_str} → today …")

    while since_ts < now_ts:
        candles, last_ts = fetch_kraken_ohlc(since_ts)
        if not candles:
            break
        for c in candles:
            ts    = int(c[0])
            close = float(c[4])
            if close <= 0:
                continue
            date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            if date_str > from_date_str:        # only dates we don't have yet
                gap[date_str] = close
        if last_ts <= since_ts:
            break
        since_ts = last_ts
        time.sleep(REQUEST_DELAY)

    print(f"  {len(gap)} new day(s) from Kraken")
    return gap


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        csv_file    = download_kaggle_dataset(tmp)
        kaggle_data = parse_kaggle_csv(csv_file)

    if not kaggle_data:
        print("ERROR: Kaggle parse returned no data. Aborting.")
        sys.exit(1)

    # Fill any gap between Kaggle's last date and today using Kraken
    last_kaggle_date = max(kaggle_data)
    print(f"Kaggle data range: {min(kaggle_data)} → {last_kaggle_date}")

    today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    if last_kaggle_date < today_str:
        kraken_gap = fetch_kraken_gap(last_kaggle_date)
        kaggle_data.update(kraken_gap)
    else:
        print("Kaggle data is current — no Kraken gap needed.")

    # Convert {date_str: price} → [{ts, price}] sorted ascending
    prices = []
    for date_str, close in sorted(kaggle_data.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        prices.append({"ts": int(dt.timestamp()), "price": close})

    # Write output
    output = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":    "Kaggle/mczielinski (minute → daily) + Kraken gap fill",
        "count":     len(prices),
        "prices":    prices,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")

    first = datetime.fromtimestamp(prices[0]["ts"],  tz=timezone.utc).date()
    last  = datetime.fromtimestamp(prices[-1]["ts"], tz=timezone.utc).date()
    print(f"\nDone — {len(prices)} daily price points ({first} → {last})")
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
