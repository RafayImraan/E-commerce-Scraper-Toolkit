# E-commerce Scraper Toolkit

A small Python CLI for collecting public product data from static catalogs, JavaScript-rendered demo pages, and Shopify's public product endpoint. It exports product records to CSV or JSON.

## Features

- Books to Scrape product-card extraction with next-page link handling and normalized prices.
- Playwright Chromium rendering of the JavaScript quotes demo and product-card extraction from the Web Scraper demo.
- Shopify `/products.json` extraction with page-number handling, variant availability, and minimum variant price.
- CSV/JSON export, duplicate removal, robots.txt checks, request pacing, and transient-failure retries.

## Install

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python main.py static --out output/books.csv
python main.py dynamic --out output/products.json
python main.py shopify --store https://YOUR-SHOPIFY-STORE.example --out output/shopify.csv
python main.py shopify --store https://YOUR-SHOPIFY-STORE.example --out output/shopify.csv --include-tags --currency USD
```

Use `--max-items 8` for a short run, `--delay 1` to set pacing, and `--verbose` for debug logs. Output format is selected by `.csv` or `.json`.

Shopify currency is read from `/meta.json` when available. `--currency` is the fallback; if neither provides a currency, the value is left blank and a warning is logged. Tags are omitted by default. Use `--include-tags` to include them; JSON stores tags as a list, while CSV joins tags with ` | `.

`available` means at least one variant is in stock. `variants_available` is the count of in-stock variants.

Example Books CSV rows:

```text
title,price,currency,availability,rating,product_url,image_url
A Light in the Attic,51.77,GBP,In stock,Three,https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html,...
Tipping the Velvet,53.74,GBP,In stock,One,https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html,...
```

## How it works / design notes

`BaseScraper` centralizes pacing, user-agent configuration, and robots checks. The requests client configures bounded exponential retries for transient HTTP and network failures. Static pages are parsed with BeautifulSoup; dynamic pages are rendered in headless Chromium and the browser is closed in a `finally` block. Shopify products are read from the supplied store's public `/products.json` endpoint. Parsing, normalization, export, and robots behavior have offline tests.

## Tested on

Live runs performed on 2026-11-05:

- `https://books.toscrape.com/` - static scraper with `--max-items 8`; generated eight-row CSV and JSON samples. This verified the first page only, not a complete multi-page crawl.
- `https://quotes.toscrape.com/js/` - Playwright rendered the page and found 10 quotes.
- `https://webscraper.io/test-sites/e-commerce/more` - the dynamic scraper exported the three product cards shown. No load-more or pagination control was present in that run.
- `https://allbirds.com` - `python main.py shopify --store https://allbirds.com --out sample_output/shopify.csv --max-items 10 --delay 1`; exported 10 products. `/meta.json` supplied `USD`; tags were omitted by default.

Offline-only checks use saved Books to Scrape HTML and Shopify product JSON fixtures, and mocks for de-duplication, CSV/JSON export, retry policy, and robots.txt. Shopify currency fallback, tag formatting, and availability calculations are tested offline. The full pytest suite passed with 18 tests after the Shopify run above.

## Responsible use

Use public data only. Respect each site's robots.txt, terms, rate limits, and applicable laws. Do not collect login-gated or personal data. The demo targets are intended for practice; check permission before using this toolkit against other sites.

Services: custom scrapers, scheduled price monitoring and maintenance available.
