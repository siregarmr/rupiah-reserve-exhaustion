#!/usr/bin/env python3
# update_trade_data.py
# Fetches annual Indonesian export/import data from BPS API,
# computes monthly average, and writes to bps_trade_latest.csv.

import os
import csv
import sys
import time
import datetime
import requests

BPS_BASE_URL = "https://webapi.bps.go.id/v1/api"
BPS_API_KEY = os.environ.get("BPS_API_KEY")

# All 2‑digit HS chapters (01 to 99)
HS_CODES = [f"{i:02d}" for i in range(1, 100)]

HEADERS = ["year", "monthly_exports_usd", "monthly_imports_usd"]


def fetch_annual_total(api_key: str, trade_type: str, year: int) -> float:
    """
    Fetch annual total export or import value (in USD) for a given year.
    trade_type: 'export' (sumber=1) or 'import' (sumber=2)
    Returns total sum across all HS codes, or 0.0 on failure.
    """
    sumber = "1" if trade_type == "export" else "2"
    total = 0.0

    for hs in HS_CODES:
        params = {
            "sumber": sumber,
            "periode": "2",          # annual data
            "kodehs": hs,
            "jenishs": "1",          # 2‑digit HS level
            "tahun": str(year),
            "key": api_key,
        }
        try:
            resp = requests.get(f"{BPS_BASE_URL}/dataexim",
                                params=params, timeout=15)
            if resp.status_code != 200:
                print(f"Warning: HTTP {resp.status_code} for HS {hs}", file=sys.stderr)
                continue

            data = resp.json()
            if data.get("status") != "OK":
                print(f"Warning: API status not OK for HS {hs}: {data.get('status')}",
                      file=sys.stderr)
                continue

            items = data.get("data", [])
            for item in items:
                try:
                    value = float(item.get("value", 0))
                    total += value
                except (ValueError, TypeError):
                    continue

            # be polite to the API
            time.sleep(0.05)

        except requests.exceptions.RequestException as e:
            print(f"Request error for HS {hs}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error for HS {hs}: {e}", file=sys.stderr)

    return total


def main():
    if not BPS_API_KEY:
        print("ERROR: BPS_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    year = datetime.datetime.now().year

    print(f"Fetching annual trade data for {year}...")
    exports = fetch_annual_total(BPS_API_KEY, "export", year)
    imports = fetch_annual_total(BPS_API_KEY, "import", year)

    if exports == 0.0 and imports == 0.0:
        print("ERROR: No data retrieved for either exports or imports.", file=sys.stderr)
        sys.exit(1)

    # Compute monthly averages (annual total / 12)
    monthly_exports = exports / 12.0
    monthly_imports = imports / 12.0

    # Write CSV
    output_file = "bps_trade_latest.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerow([year, monthly_exports, monthly_imports])

    print(f"Successfully wrote {output_file}")
    print(f"Year: {year}, Monthly avg exports: ${monthly_exports:,.2f} USD, "
          f"Monthly avg imports: ${monthly_imports:,.2f} USD")


if __name__ == "__main__":
    main()
