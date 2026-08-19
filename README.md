# Mushfiq's Tools

My personal tools dashboard — hosted on GitHub Pages.

## Tools

- **Share Portfolio Tracker** (`share-tracker.html`) — Monthly SIP buy guide with commission, allocation settings, and a performance dashboard. Prices are fetched automatically from DSE.

## Auto price updates

A GitHub Actions workflow (`.github/workflows/fetch-prices.yml`) runs **every hour, Sun–Thu** (Bangladesh time) and scrapes the latest DSE prices into `data/prices.json`. The tracker page reads this file on load.

- Scraper: `scripts/fetch_prices.py`
- Prices + history: `data/prices.json`
- Trigger manually from Actions tab: **Fetch DSE Prices → Run workflow**

## Run locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000

User settings (companies, allocation %, monthly amount, commission) are saved in the browser's localStorage.
