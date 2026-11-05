"""Playwright scraper for the public Web Scraper e-commerce demo."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from scrapers.base import BaseScraper
from scrapers.static_scraper import parse_price


def parse_product_text(title: str, price_text: str, description: str = "", rating: str = "", url: str = "") -> dict:
    """Normalize text fields gathered from a rendered product card."""
    price, currency = parse_price(price_text)
    return {"title": title.strip(), "price": price, "currency": currency,
            "description": description.strip() or None, "rating_reviews": rating.strip() or None,
            "product_url": url or None}


class DynamicScraper(BaseScraper):
    """Render the JS quotes demo, then crawl the e-commerce demo with Chromium."""
    quotes_url = "https://quotes.toscrape.com/js/"
    catalog_url = "https://webscraper.io/test-sites/e-commerce/more"

    def scrape(self, max_items: int | None = None) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError
        except ImportError as exc:
            raise RuntimeError("Playwright is missing. Install requirements and run 'playwright install chromium'.") from exc
        self.allowed_by_robots(self.quotes_url)
        self.allowed_by_robots(self.catalog_url)
        items, seen = [], set()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(user_agent=self.config.user_agent)
                    page.goto(self.quotes_url, wait_until="domcontentloaded", timeout=int(self.config.timeout * 1000))
                    page.locator(".quote").first.wait_for(state="visible", timeout=int(self.config.timeout * 1000))
                    self.logger.info("JavaScript rendering demo loaded (%d quotes)", page.locator(".quote").count())
                    self.pace()
                    page.goto(self.catalog_url, wait_until="domcontentloaded", timeout=int(self.config.timeout * 1000))
                    cards = page.locator(".thumbnail")
                    cards.first.wait_for(state="visible", timeout=int(self.config.timeout * 1000))
                    while True:
                        for card in cards.all():
                            title_el = card.locator(".title").first
                            title = title_el.get_attribute("title") or title_el.inner_text().strip()
                            href = title_el.get_attribute("href")
                            price_text = card.locator(".price").first.inner_text() if card.locator(".price").count() else ""
                            desc = card.locator(".description").first.inner_text() if card.locator(".description").count() else ""
                            rating_el = card.locator(".ratings").first
                            rating = rating_el.inner_text() if rating_el.count() else ""
                            url = urljoin(page.url, href or "")
                            if url in seen:
                                continue
                            items.append(parse_product_text(title, price_text, desc, rating, url)); seen.add(url)
                            if max_items and len(items) >= max_items:
                                return items
                        more = page.get_by_text(re.compile(r"load more", re.I))
                        if more.count() and more.first.is_visible() and more.first.is_enabled():
                            before = len(seen)
                            self.pace()
                            more.first.click()
                            try:
                                page.wait_for_function("(n) => document.querySelectorAll('.thumbnail').length > n", before,
                                                       timeout=int(self.config.timeout * 1000))
                            except PlaywrightTimeout:
                                break
                        else:
                            next_link = page.locator("ul.pagination li a[aria-label='Next'], ul.pagination li.next a")
                            if not next_link.count() or not next_link.first.is_enabled():
                                break
                            before_url = page.url
                            self.pace()
                            next_link.first.click()
                            page.wait_for_function("old => location.href !== old", before_url, timeout=int(self.config.timeout * 1000))
                            page.locator(".thumbnail").first.wait_for(state="visible", timeout=int(self.config.timeout * 1000))
                finally:
                    browser.close()
        except PlaywrightError as exc:
            raise RuntimeError(f"Browser scrape failed: {exc}") from exc
        return items
