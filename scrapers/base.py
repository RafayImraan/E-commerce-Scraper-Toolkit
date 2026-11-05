"""Shared scraper configuration and lifecycle helpers."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin

from utils.http import HttpClient


@dataclass(frozen=True)
class ScraperConfig:
    delay: float = 1.0
    timeout: float = 20.0
    retries: int = 3
    user_agent: str = (
        "EcomScraperToolkit/1.0 "
        "(+https://github.com/RafayImraan/E-commerce-Scraper-Toolkit; "
        "educational public-data scraper)"
    )


class BaseScraper:
    """Base class providing HTTP access, pacing, and robots.txt checks."""
    def __init__(self, delay: float = 1.0):
        self.config = ScraperConfig(delay=delay)
        self.logger = logging.getLogger(self.__class__.__module__)
        self.http = HttpClient(self.config.user_agent, self.config.timeout, self.config.retries)
        self._last_request = 0.0
        self._robots: dict[str, bool] = {}

    def pace(self) -> None:
        remaining = self.config.delay - (time.monotonic() - self._last_request)
        if self._last_request and remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def allowed_by_robots(self, url: str) -> bool:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        if robots_url not in self._robots:
            try:
                response = self.http.get(robots_url)
                self._robots[robots_url] = response.text if response.status_code < 400 else ""
            except RuntimeError as exc:
                self.logger.warning("Could not read %s (%s); proceeding cautiously", robots_url, exc)
                self._robots[robots_url] = ""
        content = self._robots[robots_url]
        if content:
            from urllib.robotparser import RobotFileParser
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(content.splitlines())
            allowed = parser.can_fetch(self.config.user_agent, url)
            if not allowed:
                self.logger.warning("robots.txt disallows %s; proceeding as requested", url)
        else:
            allowed = True
        return allowed

    @staticmethod
    def absolute_url(base: str, href: str | None) -> str:
        return urljoin(base, href or "")

    def scrape(self, max_items: int | None = None) -> list[dict]:
        raise NotImplementedError
