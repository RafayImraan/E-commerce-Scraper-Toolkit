"""Command line interface for the e-commerce scraper toolkit."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scrapers.static_scraper import StaticScraper
from scrapers.dynamic_scraper import DynamicScraper
from scrapers.shopify_scraper import ShopifyScraper
from utils.export import export_items
from utils.logging_setup import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect public product data and export CSV or JSON.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("static", "dynamic", "shopify"):
        sub = commands.add_parser(name)
        sub.add_argument("--out", required=True, help="Output path ending in .csv or .json")
        sub.add_argument("--max-items", type=int, default=None, help="Stop after this many unique items")
        sub.add_argument("--delay", type=float, default=1.0, help="Seconds between requests/actions (default: 1)")
        sub.add_argument("--verbose", action="store_true", help="Enable debug logging")
        if name == "shopify":
            sub.add_argument("--store", required=True, help="Shopify store base URL")
            sub.add_argument("--currency", help="Fallback currency code when store meta.json has none")
            sub.add_argument("--include-tags", action="store_true", help="Include product tags in the output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.max_items is not None and args.max_items < 1:
        raise SystemExit("--max-items must be a positive integer")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative")
    configure_logging(args.verbose)
    try:
        scraper = {
            "static": lambda: StaticScraper(delay=args.delay),
            "dynamic": lambda: DynamicScraper(delay=args.delay),
            "shopify": lambda: ShopifyScraper(
                args.store, delay=args.delay, currency=args.currency, include_tags=args.include_tags
            ),
        }[args.command]()
        items = scraper.scrape(max_items=args.max_items)
        count = export_items(items, Path(args.out))
        logging.info("Exported %d items to %s", count, args.out)
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        logging.error("Scrape failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
