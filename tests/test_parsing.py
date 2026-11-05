"""Offline tests for parsing and normalization helpers."""
import json
from pathlib import Path

from scrapers.static_scraper import parse_books, parse_price
from scrapers.dynamic_scraper import parse_product_text
from scrapers.shopify_scraper import normalize_product

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_price():
    assert parse_price("£1,234.50") == (1234.5, "GBP")
    assert parse_price("no price") == (None, None)


def test_parse_books_fixture():
    html = (FIXTURES / "books_page.html").read_text(encoding="utf-8")
    items, next_url = parse_books(html, "https://books.toscrape.com/catalogue/page.html")
    assert items[0]["title"] == "Sample Book"
    assert items[0]["rating"] == "Three"
    assert items[0]["price"] == 12.5
    assert items[0]["product_url"].endswith("catalogue/sample_1/index.html")
    assert next_url.endswith("catalogue/page-2.html")


def test_dynamic_normalization():
    row = parse_product_text("  Device ", "$9.99", " description ", "4 reviews", "https://example.com/p")
    assert row["title"] == "Device"
    assert row["price"] == 9.99 and row["currency"] == "USD"
    assert row["description"] == "description"


def test_shopify_fixture_normalization():
    product = json.loads((FIXTURES / "shopify_product.json").read_text(encoding="utf-8"))
    row = normalize_product(product, "https://store.example")
    assert row["price"] == 15.5
    assert row["available"] is True
    assert row["variants_available"] == 1
    assert row["variants_count"] == 2
    assert "tags" not in row
    assert row["product_url"] == "https://store.example/products/demo-tee"


def test_shopify_optional_tags_and_explicit_currency():
    product = json.loads((FIXTURES / "shopify_product.json").read_text(encoding="utf-8"))
    row = normalize_product(product, "https://store.example", currency="EUR", include_tags=True)
    assert row["currency"] == "EUR"
    assert row["tags"] == ["cotton", "demo"]
    assert row["available"] is True
    assert row["variants_available"] == 1


def test_shopify_currency_from_meta_and_cli_fallback(caplog):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from scrapers.shopify_scraper import ShopifyScraper

    scraper = ShopifyScraper("https://store.example", delay=0, currency="CAD")
    scraper.http.get = Mock(return_value=SimpleNamespace(json=lambda: {"currency": "USD"}))
    assert scraper.get_currency() == "USD"

    fallback = ShopifyScraper("https://store.example", delay=0, currency="CAD")
    fallback.http.get = Mock(side_effect=RuntimeError("meta endpoint unavailable"))
    assert fallback.get_currency() == "CAD"

    unknown = ShopifyScraper("https://store.example", delay=0)
    unknown.http.get = Mock(side_effect=RuntimeError("meta endpoint unavailable"))
    assert unknown.get_currency() is None
    assert "currency is unknown" in caplog.text
