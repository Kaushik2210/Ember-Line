"""Async client for the NASA FIRMS API.

The MAP_KEY is part of the URL path, so every error message is redacted before it can
reach logs or API responses. Rate limiting and exponential backoff are built in.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import math
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date

import httpx

from emberline.data.chunking import MAX_DAY_RANGE
from emberline.data.limiter import RateLimiter

log = logging.getLogger(__name__)

# httpx logs full request URLs at INFO, and the FIRMS MAP_KEY lives in the URL path.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

BASE = "https://firms.modaps.eosdis.nasa.gov"
STATUS_URL = f"{BASE}/mapserver/mapkey_status/"
# FIRMS reports some failures as HTTP 200 with a plain-text body.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _is_error_body(body: str) -> bool:
    head = body[:200]
    return head.startswith(("Invalid", "MAP_KEY is invalid")) or "exceeded your transaction" in head


BBox = tuple[float, float, float, float]


class FirmsError(RuntimeError):
    pass


class FirmsAuthError(FirmsError):
    """The key was rejected. Retrying will not help."""


@dataclass(frozen=True)
class Availability:
    source: str
    min_date: date
    max_date: date


class FirmsClient:
    def __init__(
        self,
        map_key: str,
        http: httpx.AsyncClient | None = None,
        limiter: RateLimiter | None = None,
        max_retries: int = 5,
        rate_limit_wait_s: float = 60.0,
        max_rate_limit_waits: int = 15,
        base_delay_s: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not map_key:
            raise FirmsAuthError("FIRMS_MAP_KEY is not set")
        self._key = map_key
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0))
        self._owns_http = http is None
        self._limiter = limiter or RateLimiter(max_calls=4500)
        self._max_retries = max_retries
        self._rl_wait = rate_limit_wait_s
        self._rl_waits = max_rate_limit_waits
        self._base_delay = base_delay_s
        self._sleep = sleep
        self.requests_made = 0

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> FirmsClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def _redact(self, text: str) -> str:
        return text.replace(self._key, "***")

    async def _get_text(self, url: str, params: dict[str, str] | None = None) -> str:
        last: str = ""
        rl_waits = 0
        attempt = 0
        while attempt <= self._max_retries:
            await self._limiter.acquire()
            self.requests_made += 1
            try:
                resp = await self._http.get(url, params=params)
            except httpx.TransportError as exc:
                last = self._redact(f"{type(exc).__name__}: {exc}")
            else:
                body = resp.text
                if resp.status_code == 200 and not _is_error_body(body):
                    return body
                if body.startswith("Invalid MAP_KEY"):
                    raise FirmsAuthError("FIRMS rejected the MAP_KEY")
                if "exceeded your transaction" in body[:200]:
                    # budget exhausted: wait for the 10-minute window instead of burning retries
                    rl_waits += 1
                    if rl_waits > self._rl_waits:
                        raise FirmsError("FIRMS transaction budget stayed exhausted")
                    log.warning("FIRMS budget exhausted; waiting %.0fs", self._rl_wait)
                    await self._sleep(self._rl_wait)
                    continue
                last = self._redact(f"HTTP {resp.status_code}: {body[:120]!r}")
                if resp.status_code not in _RETRYABLE_STATUS and resp.status_code != 200:
                    raise FirmsError(last)
            attempt += 1
            if attempt <= self._max_retries:
                delay = self._base_delay * 2**attempt + random.uniform(0, 0.5)
                log.warning("FIRMS request failed (%s); retry %d in %.1fs", last, attempt, delay)
                await self._sleep(delay)
        raise FirmsError(f"FIRMS request failed after {self._max_retries + 1} attempts: {last}")

    async def availability(self) -> dict[str, Availability]:
        text = await self._get_text(f"{BASE}/api/data_availability/csv/{self._key}/ALL")
        out: dict[str, Availability] = {}
        for row in csv.DictReader(io.StringIO(text)):
            out[row["data_id"]] = Availability(
                row["data_id"],
                date.fromisoformat(row["min_date"]),
                date.fromisoformat(row["max_date"]),
            )
        return out

    async def key_status(self) -> dict[str, object]:
        """Transaction budget for this key (limit, used, interval)."""
        import json

        text = await self._get_text(STATUS_URL, params={"MAP_KEY": self._key})
        return json.loads(text)  # type: ignore[no-any-return]

    async def area_csv(self, source: str, bbox: BBox, start: date, days: int) -> str:
        if not 1 <= days <= MAX_DAY_RANGE:
            raise ValueError(f"FIRMS day range must be 1-{MAX_DAY_RANGE}")
        w, s, e, n = bbox
        url = f"{BASE}/api/area/csv/{self._key}/{source}/{w:g},{s:g},{e:g},{n:g}/{days}/{start.isoformat()}"
        text = await self._get_text(url)
        # FIRMS bills about one transaction per 1000 rows; the call itself already cost one
        self._limiter.charge(max(0, math.ceil(text.count(chr(10)) / 1000) - 1))
        return text
