"""Async client for the NASA FIRMS API.

The MAP_KEY is part of the URL path, so every error message is redacted before it can
reach logs or API responses. Rate limiting and exponential backoff are built in.

Budget: FIRMS allows a fixed number of transactions per 10-minute window and bills by an
internal formula we do not rely on. With `guard_every` set, the client polls the key-status
endpoint and pauses before the budget runs out, so long downloads wait instead of failing.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
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
# FIRMS reports some failures as HTTP 200 with a plain-text body, others as HTTP 400.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_BUDGET_MARKERS = ("exceeded your transaction", "Exceeding allowed transaction")

BBox = tuple[float, float, float, float]


def _is_budget_body(body: str) -> bool:
    head = body[:200]
    return any(m in head for m in _BUDGET_MARKERS)


def _is_error_body(body: str) -> bool:
    return body[:200].startswith(("Invalid", "MAP_KEY is invalid")) or _is_budget_body(body)


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
        rate_limit_wait_s: float = 30.0,
        max_rate_limit_waits: int = 40,
        base_delay_s: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        guard_every: int | None = None,
        budget_reserve: int = 400,
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
        self._guard_every = guard_every
        self._reserve = budget_reserve
        self._guard_lock = asyncio.Lock()
        self._since_check = 0
        self.requests_made = 0
        # called with a plain-language message whenever the client pauses for the request budget
        self.on_wait: Callable[[str], None] | None = None

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> FirmsClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    def _redact(self, text: str) -> str:
        return text.replace(self._key, "***")

    async def _usage(self) -> tuple[int, int] | None:
        """(used, limit) from the key-status endpoint, or None if it cannot be read."""
        try:
            resp = await self._http.get(STATUS_URL, params={"MAP_KEY": self._key})
            data = json.loads(resp.text)
            return int(data["current_transactions"]), int(data["transaction_limit"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None

    async def _guard(self) -> None:
        """Pause while the key is close to its 10-minute budget."""
        if self._guard_every is None:
            return
        async with self._guard_lock:
            self._since_check += 1
            if self._since_check < self._guard_every:
                return
            self._since_check = 0
            for _ in range(self._rl_waits):
                usage = await self._usage()
                if usage is None or usage[0] < usage[1] - self._reserve:
                    return
                log.warning("FIRMS budget %d/%d used; pausing %.0fs", *usage, self._rl_wait)
                if self.on_wait:
                    self.on_wait("Waiting for NASA's request limit to reset")
                await self._sleep(self._rl_wait)

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
                exhausted = _is_budget_body(body)
                if body.startswith("Invalid MAP_KEY") and not exhausted:
                    # FIRMS also answers this when the budget is spent, so check the status
                    usage = await self._usage()
                    if usage is not None and usage[0] >= usage[1]:
                        exhausted = True
                    else:
                        raise FirmsAuthError("FIRMS rejected the MAP_KEY")
                if exhausted:
                    rl_waits += 1
                    if rl_waits > self._rl_waits:
                        raise FirmsError("FIRMS transaction budget stayed exhausted")
                    log.warning("FIRMS budget exhausted; waiting %.0fs", self._rl_wait)
                    if self.on_wait:
                        self.on_wait("Waiting for NASA's request limit to reset")
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
        text = await self._get_text(STATUS_URL, params={"MAP_KEY": self._key})
        return json.loads(text)  # type: ignore[no-any-return]

    async def area_csv(self, source: str, bbox: BBox, start: date, days: int) -> str:
        if not 1 <= days <= MAX_DAY_RANGE:
            raise ValueError(f"FIRMS day range must be 1-{MAX_DAY_RANGE}")
        await self._guard()
        w, s, e, n = bbox
        url = (
            f"{BASE}/api/area/csv/{self._key}/{source}/"
            f"{w:g},{s:g},{e:g},{n:g}/{days}/{start.isoformat()}"
        )
        return await self._get_text(url)
