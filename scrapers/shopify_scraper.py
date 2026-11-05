"""Public Shopify products.json endpoint scraper."""
from __future__ import annotations

from urllib.parse import urlparse

from scrapers.base import BaseScraper


def normalize_product(product: dict, store_url: str, currency: str | None = None,
                      include_tags: bool = False) -> dict:
    """Convert a Shopify product API record into a concise product row."""
    variants = product.get("variants") or []
    prices = [float(v["price"]) for v in variants if v.get("price") not in (None, "")]
    images = product.get("images") or []
    handle = product.get("handle", "")
    root = store_url.rstrip("/")
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    row = {"id": product.get("id"), "title": product.get("title"),
            "vendor": product.get("vendor"), "product_type": product.get("product_type"),
            "price": min(prices) if prices else None, "currency": currency,
            "available": any(bool(v.get("available")) for v in variants),
            "variants_available": sum(bool(v.get("available")) for v in variants),
            "variants_count": len(variants), "tags": product.get("tags", []),
            "product_url": f"{root}/products/{handle}" if handle else None,
            "image_url": (images[0].get("src") if images else None)}
    row["currency"] = currency or product.get("currency")
    if include_tags:
        row["tags"] = tags
    else:
        row.pop("tags")
    return row


class ShopifyScraper(BaseScraper):
    """Fetch products from a Shopify store's public JSON catalog."""
    def __init__(self, store_url: str, delay: float = 1.0, currency: str | None = None,
                 include_tags: bool = False):
        super().__init__(delay)
        parsed = urlparse(store_url if "://" in store_url else f"https://{store_url}")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("--store must be a valid http(s) store URL")
        self.store_url = f"{parsed.scheme}://{parsed.netloc}"
        self.fallback_currency = currency
        self.include_tags = include_tags

    def get_currency(self) -> str | None:
        """Prefer the store's meta.json currency, with a CLI fallback."""
        self.pace()
        try:
            payload = self.http.get(f"{self.store_url}/meta.json").json()
            currency = payload.get("currency") if isinstance(payload, dict) else None
            if currency:
                self.logger.info("Using store currency %s from meta.json", currency)
                return str(currency)
        except (RuntimeError, ValueError) as exc:
            self.logger.warning("Could not determine currency from meta.json (%s)", exc)
        if self.fallback_currency:
            self.logger.info("Using fallback currency %s", self.fallback_currency)
            return self.fallback_currency
        self.logger.warning("Store currency is unknown; the currency column will be empty")
        return None

    def scrape(self, max_items: int | None = None) -> list[dict]:
        currency = self.get_currency()
        items, seen, page = [], set(), 1
        while True:
            self.pace()
            url = f"{self.store_url}/products.json?limit=250&page={page}"
            self.logger.info("Fetching Shopify page %d", page)
            payload = self.http.get(url).json()
            products = payload.get("products", [])
            if not products:
                break
            for product in products:
                if product.get("id") in seen:
                    continue
                seen.add(product.get("id"))
                items.append(normalize_product(product, self.store_url, currency, self.include_tags))
                if max_items and len(items) >= max_items:
                    return items
            if len(products) < 250:
                break
            page += 1
        return items
