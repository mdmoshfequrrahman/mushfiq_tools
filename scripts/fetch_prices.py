#!/usr/bin/env python3
"""
DSE price scraper for mushfiq_tools.
Fetches last trading price (or yesterday's closing) for each configured
ticker from the DSE website and writes data/prices.json with history.
"""
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CONTEXT = ssl.create_default_context()

BASE_URL = "https://www.dse.com.bd/displayCompany.php?name={}"
LISTING_URL = "https://www.dse.com.bd/company_listing.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
DATA_FILE = os.path.join(DATA_DIR, "prices.json")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.json")

# Default tickers. The frontend settings can define more, but this is the
# baseline set the scraper keeps up to date.
TICKERS = ["SQURPHARMA", "BRACBANK", "GP", "EBL", "BSRMSTEEL"]


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (ssl.SSLError, urllib.error.URLError) as exc:
        # Some environments lack the CA store; fall back to unverified
        # context for this public price page (GitHub Actions has valid certs).
        fallback = ssl.create_default_context()
        fallback.check_hostname = False
        fallback.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=30, context=fallback) as resp:
            return resp.read().decode("utf-8", errors="ignore")


def fetch_company_list():
    """Scrape the full DSE company listing into a list of {ticker, name}."""
    html = fetch_html(LISTING_URL)
    pairs = re.findall(
        r"displayCompany\.php\?name=([A-Z0-9_]+)'\s+class='ab1[^']*'>"
        r"[^<]*</a>\s*<span[^>]*>\(([^)]*)\)",
        html,
    )
    seen = set()
    out = []
    for ticker, name in pairs:
        ticker = ticker.strip()
        name = name.strip()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        out.append({"ticker": ticker, "name": name})
    out.sort(key=lambda c: c["ticker"])
    return out


def parse_price(html):
    """Extract Last Trading Price; fall back to Yesterday's Closing Price."""
    idx = html.find("Last Trading Price")
    if idx == -1:
        return None
    seg = html[idx : idx + 3000]
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", seg)
    if not cells:
        return None
    raw = cells[0].strip().replace(",", "")
    if raw in ("", "-"):
        m = re.search(
            r"Yesterday's Closing Price</th>\s*<td[^>]*>([^<]*)</td>", html
        )
        if m:
            raw = m.group(1).strip().replace(",", "")
        else:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def load_existing():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"lastUpdated": None, "prices": {}, "history": []}


def main():
    prices = {}
    for ticker in TICKERS:
        try:
            html = fetch_html(BASE_URL.format(ticker))
            price = parse_price(html)
            if price is not None:
                prices[ticker] = price
                print(f"{ticker}: {price}")
            else:
                print(f"{ticker}: parse failed", file=sys.stderr)
        except Exception as exc:
            print(f"{ticker}: error {exc}", file=sys.stderr)

    if not prices:
        print("No prices fetched, aborting.", file=sys.stderr)
        sys.exit(1)

    # refresh the full company list (ticker + name) for the searchable picker
    try:
        companies = fetch_company_list()
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
            json.dump(companies, f, indent=1, ensure_ascii=False)
        print(f"Wrote {len(companies)} companies to {COMPANIES_FILE}")
    except Exception as exc:
        print(f"company list: error {exc}", file=sys.stderr)

    data = load_existing()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # keep existing prices for tickers that failed this run
    for t in TICKERS:
        if t not in prices and t in data.get("prices", {}):
            prices[t] = data["prices"][t]

    data["prices"] = prices
    data["lastUpdated"] = now

    # append a history snapshot (one per UTC day)
    day = now[:10]
    history = data.get("history", [])
    snapshot = {"date": day, "prices": dict(prices)}
    if history and history[-1].get("date") == day:
        history[-1] = snapshot
    else:
        history.append(snapshot)
    data["history"] = history[-180:]  # keep ~6 months

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(prices)} prices to {DATA_FILE} (history: {len(history)})")


if __name__ == "__main__":
    main()
