"""One requests session per API, with retries on rate limits and server errors plus a minimum gap between calls."""
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiClient:
    """Thin GET wrapper: retries, per-client throttling, JSON decoding."""

    def __init__(self, base_url: str, user_agent: str, min_interval: float = 0.0):
        self.base_url = base_url.rstrip("/")
        self.min_interval = min_interval
        self._last_call = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        retry = Retry(total=5, backoff_factor=1.0,
                      status_forcelist=(429, 500, 502, 503, 504),
                      respect_retry_after_header=True)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get(self, path: str, params: dict | None = None, allow_404: bool = False):
        """GET base_url + path and return parsed JSON (or None on 404 if allow_404)."""
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.get(url, params=params, timeout=60)
        self._last_call = time.monotonic()
        if allow_404 and resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
