"""Books to Scrape static HTML crawler."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper


def parse_price(text: str) -> tuple[float | None, str | None]:
    """Extract numeric amount and an optional ISO-like currency code."""
    clean = text.strip()
    match = re.search(r"[-+]?\d[\d.,]*", clean)
    amount = None
    if match:
        number = match.group()
        if "," in number and "." in number:
            decimal_mark = "," if number.rfind(",") > number.rfind(".") else "."
            thousands_mark = "." if decimal_mark == "," else ","
            number = number.replace(thousands_mark, "").replace(decimal_mark, ".")
        elif "," in number:
            tail = number.rsplit(",", 1)[1]
            number = number.replace(",", ".") if len(tail) in {1, 2} else number.replace(",", "")
        elif number.count(".") > 1:
            head, tail = number.rsplit(".", 1)
            number = head.replace(".", "") + ("." + tail if len(tail) in {1, 2} else tail)
        amount = float(number)
    currencies = {"\u00a3": "GBP", "Â£": "GBP", "$": "USD", "\u20ac": "EUR", "â‚¬": "EUR",
                  "GBP": "GBP", "USD": "USD", "EUR": "EUR"}
    upper = clean.upper()
    currency = next((code for marker, code in currencies.items() if marker.upper() in upper), None)
    return amount, currency


def parse_books(html: str, page_url: str) -> tuple[list[dict], str | None]:
    """Parse product cards and the next-page URL from a Books to Scrape page."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for card in soup.select("article.product_pod"):
        title_link = card.select_one("h3 a")
        if not title_link:
            continue
        price, currency = parse_price(card.select_one(".price_color").get_text(" ", strip=True) if card.select_one(".price_color") else "")
        image = card.select_one(".image_container img")
        rating = next((c for c in (card.select_one(".star-rating").get("class", []) if card.select_one(".star-rating") else []) if c != "star-rating"), None)
        records.append({"title": title_link.get("title") or title_link.get_text(" ", strip=True),
                        "price": price, "currency": currency,
                        "availability": card.select_one(".availability").get_text(" ", strip=True) if card.select_one(".availability") else None,
                        "rating": rating,
                        "product_url": urljoin(page_url, title_link.get("href", "")),
                        "image_url": urljoin(page_url, image.get("src", "")) if image else None})
    next_link = soup.select_one("li.next a")
    return records, urljoin(page_url, next_link.get("href", "")) if next_link else None


class StaticScraper(BaseScraper):
    """Crawl paginated Books to Scrape catalog pages."""
    start_url = "https://books.toscrape.com/"

    def scrape(self, max_items: int | None = None) -> list[dict]:
        self.allowed_by_robots(self.start_url)
        url, records, seen = self.start_url, [], set()
        while url:
            self.pace()
            self.logger.info("Fetching %s", url)
            page_records, next_url = parse_books(self.http.get(url).text, url)
            for item in page_records:
                if item["product_url"] not in seen:
                    records.append(item); seen.add(item["product_url"])
                    if max_items and len(records) >= max_items:
                        return records
            url = next_url
        return records
