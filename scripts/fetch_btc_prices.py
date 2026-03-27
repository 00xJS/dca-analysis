#!/usr/bin/env python3
"""
fetch_btc_prices.py
───────────────────
Builds data/btc-prices.json from Kaggle:

  mczielinski/bitcoin-historical-data
  Minute-level Bitstamp OHLCV from 2012 → today.
  Aggregated to daily closes (last non-NaN close per UTC day).

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
from datetime import datetime, timezone
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
KAGGLE_DATASET = "mczielinski/bitcoin-historical-data"
OUTPUT_PATH    = Path(__file__).resolve().parent.parent / "data" / "btc-prices.json"


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


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        csv_file    = download_kaggle_dataset(tmp)
        kaggle_data = parse_kaggle_csv(csv_file)

    if not kaggle_data:
        print("ERROR: Kaggle parse returned no data. Aborting.")
        sys.exit(1)

    print(f"Kaggle data range: {min(kaggle_data)} → {max(kaggle_data)}")

    # Convert {date_str: price} → [{ts, price}] sorted ascending
    prices = []
    for date_str, close in sorted(kaggle_data.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        prices.append({"ts": int(dt.timestamp()), "price": close})

    # Write output
    output = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":    "Kaggle/mczielinski — minute-level Bitstamp data aggregated to daily closes",
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
