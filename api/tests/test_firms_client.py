from datetime import date

import httpx
import pytest
import respx

from emberline.data.firms import FirmsAuthError, FirmsClient, FirmsError
from emberline.data.limiter import RateLimiter

KEY = "SECRETKEY123"


async def _nosleep(_: float) -> None:
    return None


def make(http: httpx.AsyncClient, **kw: object) -> FirmsClient:
    return FirmsClient(KEY, http=http, limiter=RateLimiter(1000), sleep=_nosleep, **kw)  # type: ignore[arg-type]


async def test_requires_key() -> None:
    with pytest.raises(FirmsAuthError):
        FirmsClient("")


@respx.mock
async def test_availability_parsed() -> None:
    body = "data_id,min_date,max_date\nMODIS_SP,2000-11-01,2026-07-31\nVIIRS_SNPP_SP,2012-01-20,2026-06-30"
    respx.get(url__regex=r".*/api/data_availability/csv/.*/ALL").mock(
        return_value=httpx.Response(200, text=body)
    )
    async with httpx.AsyncClient() as http:
        av = await make(http).availability()
    assert av["MODIS_SP"].min_date == date(2000, 11, 1)
    assert av["VIIRS_SNPP_SP"].max_date == date(2026, 6, 30)


@respx.mock
async def test_area_url_shape() -> None:
    route = respx.get(url__regex=r".*").mock(return_value=httpx.Response(200, text="a,b\n"))
    async with httpx.AsyncClient() as http:
        await make(http).area_csv("MODIS_SP", (74, 29, 77.5, 32), date(2019, 11, 1), 5)
    assert str(route.calls[0].request.url).endswith(
        f"/api/area/csv/{KEY}/MODIS_SP/74,29,77.5,32/5/2019-11-01"
    )


async def test_day_range_validated() -> None:
    async with httpx.AsyncClient() as http, make(http) as c:
        with pytest.raises(ValueError):
            await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 6)


@respx.mock
async def test_retries_then_succeeds() -> None:
    route = respx.get(url__regex=r".*").mock(
        side_effect=[httpx.Response(503), httpx.Response(429), httpx.Response(200, text="ok\n")]
    )
    async with httpx.AsyncClient() as http:
        c = make(http)
        assert await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1) == "ok\n"
    assert route.call_count == 3 and c.requests_made == 3


@respx.mock
async def test_text_rate_limit_message_is_retried() -> None:
    limit = "MAP_KEY is invalid or your have exceeded your transaction/time limit. Try again later."
    route = respx.get(url__regex=r".*").mock(
        side_effect=[httpx.Response(200, text=limit), httpx.Response(200, text="x,y")]
    )
    async with httpx.AsyncClient() as http:
        assert await make(http).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1) == "x,y"
    assert route.call_count == 2


@respx.mock
async def test_invalid_key_is_not_retried() -> None:
    respx.get(url__regex=r".*mapkey_status.*").mock(
        return_value=httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":1}')
    )
    route = respx.get(url__regex=r".*/api/area/.*").mock(
        return_value=httpx.Response(200, text="Invalid MAP_KEY.")
    )
    async with httpx.AsyncClient() as http:
        with pytest.raises(FirmsAuthError):
            await make(http).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)
    assert route.call_count == 1


@respx.mock
async def test_gives_up_and_never_leaks_key() -> None:
    respx.get(url__regex=r".*").mock(side_effect=httpx.ConnectError(f"boom {KEY}"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(FirmsError) as err:
            await make(http, max_retries=2).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)
    assert KEY not in str(err.value)
    assert "3 attempts" in str(err.value)


@respx.mock
async def test_client_error_is_not_retried() -> None:
    route = respx.get(url__regex=r".*").mock(return_value=httpx.Response(404, text="nope"))
    async with httpx.AsyncClient() as http:
        with pytest.raises(FirmsError):
            await make(http).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)
    assert route.call_count == 1


def test_httpx_request_logging_is_silenced() -> None:
    import logging

    # URLs contain the MAP_KEY, so httpx must not log them at INFO
    assert logging.getLogger("httpx").level >= logging.WARNING


@respx.mock
async def test_budget_exhausted_waits_instead_of_failing() -> None:
    limit = "MAP_KEY is invalid or your have exceeded your transaction/time limit."
    respx.get(url__regex=r".*").mock(
        side_effect=[httpx.Response(200, text=limit)] * 3 + [httpx.Response(200, text="a,b")]
    )
    waits: list[float] = []

    async def rec(s: float) -> None:
        waits.append(s)

    async with httpx.AsyncClient() as http:
        c = FirmsClient(KEY, http=http, limiter=RateLimiter(100), sleep=rec, max_retries=1)
        assert await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1) == "a,b"
    assert waits == [30.0, 30.0, 30.0]


@respx.mock
async def test_budget_stays_exhausted_gives_up() -> None:
    limit = "MAP_KEY is invalid or your have exceeded your transaction/time limit."
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(200, text=limit))
    async with httpx.AsyncClient() as http:
        c = FirmsClient(
            KEY, http=http, limiter=RateLimiter(100), sleep=_nosleep, max_rate_limit_waits=2
        )
        with pytest.raises(FirmsError):
            await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)


@respx.mock
async def test_invalid_key_while_budget_spent_waits_not_fails() -> None:
    respx.get(url__regex=r".*mapkey_status.*").mock(
        side_effect=[
            httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":5000}'),
        ]
    )
    respx.get(url__regex=r".*/api/area/.*").mock(
        side_effect=[httpx.Response(200, text="Invalid MAP_KEY."), httpx.Response(200, text="a,b")]
    )
    async with httpx.AsyncClient() as http:
        c = make(http)
        assert await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1) == "a,b"


@respx.mock
async def test_http_400_transaction_limit_message_is_treated_as_budget() -> None:
    respx.get(url__regex=r".*").mock(
        side_effect=[
            httpx.Response(400, text="Exceeding allowed transaction limit."),
            httpx.Response(200, text="a,b"),
        ]
    )
    async with httpx.AsyncClient() as http:
        assert await make(http).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1) == "a,b"


@respx.mock
async def test_guard_pauses_when_budget_nearly_spent() -> None:
    status = respx.get(url__regex=r".*mapkey_status.*").mock(
        side_effect=[
            httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":4900}'),
            httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":120}'),
        ]
    )
    respx.get(url__regex=r".*/api/area/.*").mock(return_value=httpx.Response(200, text="a,b"))
    waits: list[float] = []

    async def rec(s: float) -> None:
        waits.append(s)

    async with httpx.AsyncClient() as http:
        c = FirmsClient(
            KEY, http=http, limiter=RateLimiter(100), sleep=rec, guard_every=1, budget_reserve=400
        )
        await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)
    assert status.call_count == 2 and waits == [30.0]


@respx.mock
async def test_real_auth_failure_still_raises() -> None:
    respx.get(url__regex=r".*mapkey_status.*").mock(
        return_value=httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":3}')
    )
    respx.get(url__regex=r".*/api/area/.*").mock(
        return_value=httpx.Response(200, text="Invalid MAP_KEY.")
    )
    async with httpx.AsyncClient() as http:
        with pytest.raises(FirmsAuthError):
            await make(http).area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)


@respx.mock
async def test_on_wait_tells_the_caller_when_the_client_pauses() -> None:
    respx.get(url__regex=r".*mapkey_status.*").mock(
        side_effect=[
            httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":4900}'),
            httpx.Response(200, text='{"transaction_limit":5000,"current_transactions":100}'),
        ]
    )
    respx.get(url__regex=r".*/api/area/.*").mock(return_value=httpx.Response(200, text="a,b"))
    said: list[str] = []
    async with httpx.AsyncClient() as http:
        c = FirmsClient(KEY, http=http, limiter=RateLimiter(100), sleep=_nosleep, guard_every=1)
        c.on_wait = said.append
        await c.area_csv("MODIS_SP", (0, 0, 1, 1), date(2020, 1, 1), 1)
    assert said == ["Waiting for NASA's request limit to reset"]
