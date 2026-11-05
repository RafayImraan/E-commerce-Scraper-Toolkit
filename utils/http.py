"""Retrying requests session with conservative timeouts."""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HttpClient:
    """GET-only HTTP client with exponential retry for transient failures."""
    def __init__(self, user_agent: str, timeout: float = 20.0, retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        retry = Retry(total=retries, connect=retries, read=retries,
                      status=retries, backoff_factor=0.6,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset({"GET"}), respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self.timeout = timeout

    def get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise RuntimeError(f"Request failed for {url}: {exc}") from exc
