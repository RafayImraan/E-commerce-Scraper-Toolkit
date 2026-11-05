"""Offline behavior tests; all network responses are mocked."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scrapers.base import BaseScraper
from scrapers.static_scraper import StaticScraper, parse_price
from utils.export import export_items
from utils.http import HttpClient


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("£12.50", (12.5, "GBP")),
        ("$1,234.56", (1234.56, "USD")),
        ("€9,99", (9.99, "EUR")),
        ("EUR 18.25", (18.25, "EUR")),
        ("not listed", (None, None)),
    ],
)
def test_price_normalization_formats(text, expected):
    assert parse_price(text) == expected


def test_static_scraper_deduplicates_product_urls():
    first = '''<article class="product_pod"><h3><a href="/product/1" title="One">One</a></h3>
    <p class="price_color">£2.00</p></article><li class="next"><a href="/page-2">next</a></li>'''
    second = '''<article class="product_pod"><h3><a href="/product/1" title="One">One</a></h3>
    <p class="price_color">£2.00</p></article>'''
    scraper = StaticScraper(delay=0)
    scraper.allowed_by_robots = Mock(return_value=True)
    scraper.http.get = Mock(side_effect=[SimpleNamespace(text=first), SimpleNamespace(text=second)])

    items = scraper.scrape()

    assert len(items) == 1
    assert scraper.http.get.call_count == 2


def test_export_selects_json_by_extension(tmp_path: Path):
    items = [{"title": "Tea", "price": 2.5, "tags": ["herbal", "loose leaf"]}]
    output = tmp_path / "nested" / "items.json"
    assert export_items(items, output) == 1
    assert json.loads(output.read_text(encoding="utf-8")) == items


def test_export_selects_csv_by_extension(tmp_path: Path):
    items = [{"title": "Tea", "price": 2.5, "tags": ["herbal", "loose leaf"]}]
    output = tmp_path / "items.csv"
    assert export_items(items, output) == 1
    with output.open(encoding="utf-8-sig", newline="") as handle:
        assert list(csv.DictReader(handle)) == [
            {"title": "Tea", "price": "2.5", "tags": "herbal | loose leaf"}
        ]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_http_retry_policy_covers_rate_limits_and_server_errors(status):
    # Model transient HTTP responses without opening a network connection.
    response = Mock(status=status, headers={})
    response.get_redirect_location.return_value = None
    policy = HttpClient("test-agent", retries=3).session.get_adapter("https://").max_retries

    next_attempt = policy.increment(method="GET", url="https://unit.test/items", response=response)

    assert next_attempt.total == 2
    assert status in next_attempt.status_forcelist
    assert next_attempt.backoff_factor == 0.6
    assert "GET" in next_attempt.allowed_methods
    # A second consecutive transient response gets the configured exponential delay.
    second_attempt = next_attempt.increment(method="GET", url="https://unit.test/items", response=response)
    assert second_attempt.get_backoff_time() == pytest.approx(1.2)


def test_robots_rules_are_checked_cached_and_warn_when_disallowed(caplog):
    scraper = BaseScraper(delay=0)
    scraper.http.get = Mock(return_value=SimpleNamespace(
        status_code=200,
        text="User-agent: *\nDisallow: /private\nAllow: /",
    ))

    assert scraper.allowed_by_robots("https://unit.test/catalog") is True
    assert scraper.allowed_by_robots("https://unit.test/private/item") is False

    assert scraper.http.get.call_count == 1
    assert "robots.txt disallows" in caplog.text
