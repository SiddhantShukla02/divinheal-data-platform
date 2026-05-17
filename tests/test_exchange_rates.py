# -----------------------------------------------------------------------------
# EXCHANGE RATE SOURCE TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies exchange-rate URL building and response parsing.
#
# INPUT:
#   Functions from divinheal_data.sources.exchange_rates.
#
# PROCESS:
#   - Tests currency code normalization.
#   - Tests exchange-rate API URL construction.
#   - Tests requested target-rate extraction from sample API responses.
#   - Tests update timestamp extraction.
#   - Tests high-level result creation while mocking the HTTP fetch layer.
#   - Tests invalid/missing response shapes fail loudly.
#
# OUTPUT:
#   Passing tests for the exchange-rate source adapter.
#
# NOTES:
#   - These tests do not call the real exchange-rate API.
#   - Network behavior should be covered separately with integration/manual tests.
# -----------------------------------------------------------------------------

import pytest

from divinheal_data.sources.exchange_rates import (
    EXCHANGE_RATE_BASE_URL,
    build_exchange_rate_url,
    extract_exchange_rates,
    get_exchange_rates_for_currency,
    normalize_currency_code,
)


SAMPLE_EXCHANGE_RATE_RESPONSE = {
    "result": "success",
    "provider": "https://www.exchangerate-api.com",
    "base_code": "BDT",
    "time_last_update_utc": "Sun, 17 May 2026 00:02:31 +0000",
    "rates": {
        "USD": 0.008146,
        "INR": 0.780658,
        "THB": 0.265507,
        "MYR": 0.032166,
        "TRY": 0.370886,
        "KRW": 12.209849,
    },
}


def test_normalize_currency_code_strips_and_uppercases() -> None:
    assert normalize_currency_code(" bdt ") == "BDT"
    assert normalize_currency_code("usd") == "USD"


def test_build_exchange_rate_url_uses_normalized_base_currency() -> None:
    url = build_exchange_rate_url(" bdt ")

    assert url == f"{EXCHANGE_RATE_BASE_URL}/BDT"


def test_extract_exchange_rates_returns_requested_rates_and_update_time() -> None:
    rates, source_update_utc = extract_exchange_rates(
        raw_response=SAMPLE_EXCHANGE_RATE_RESPONSE,
        target_currencies=["usd", " inr ", "THB"],
    )

    assert rates == {
        "USD": 0.008146,
        "INR": 0.780658,
        "THB": 0.265507,
    }
    assert source_update_utc == "Sun, 17 May 2026 00:02:31 +0000"


def test_extract_exchange_rates_rejects_non_dict_response() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        extract_exchange_rates(
            raw_response=["bad", "shape"],
            target_currencies=["USD"],
        )


def test_extract_exchange_rates_rejects_non_success_result() -> None:
    raw_response = {
        "result": "error",
        "error-type": "unsupported-code",
    }

    with pytest.raises(ValueError, match="non-success result: unsupported-code"):
        extract_exchange_rates(
            raw_response=raw_response,
            target_currencies=["USD"],
        )


def test_extract_exchange_rates_rejects_missing_rates_object() -> None:
    raw_response = {
        "result": "success",
        "time_last_update_utc": "Sun, 17 May 2026 00:02:31 +0000",
    }

    with pytest.raises(ValueError, match="must contain a rates object"):
        extract_exchange_rates(
            raw_response=raw_response,
            target_currencies=["USD"],
        )


def test_extract_exchange_rates_rejects_missing_update_time() -> None:
    raw_response = {
        "result": "success",
        "rates": {
            "USD": 0.008146,
        },
    }

    with pytest.raises(ValueError, match="missing time_last_update_utc"):
        extract_exchange_rates(
            raw_response=raw_response,
            target_currencies=["USD"],
        )


def test_extract_exchange_rates_rejects_missing_target_rate() -> None:
    with pytest.raises(ValueError, match="Missing exchange rate for target currency: JPY"):
        extract_exchange_rates(
            raw_response=SAMPLE_EXCHANGE_RATE_RESPONSE,
            target_currencies=["USD", "INR", "JPY"],
        )


def test_get_exchange_rates_for_currency_builds_result(monkeypatch) -> None:
    def fake_fetch_exchange_rate_response(base_currency: str, timeout_seconds: int):
        assert base_currency == "BDT"
        assert timeout_seconds == 10
        return "https://example.com/exchange-rates/BDT", SAMPLE_EXCHANGE_RATE_RESPONSE

    monkeypatch.setattr(
        "divinheal_data.sources.exchange_rates.fetch_exchange_rate_response",
        fake_fetch_exchange_rate_response,
    )

    result = get_exchange_rates_for_currency(
        base_currency=" bdt ",
        target_currencies=["USD", "INR", "KRW"],
        timeout_seconds=10,
    )

    assert result.base_currency == "BDT"
    assert result.target_rates == {
        "USD": 0.008146,
        "INR": 0.780658,
        "KRW": 12.209849,
    }
    assert result.source_update_utc == "Sun, 17 May 2026 00:02:31 +0000"
    assert result.source_url == "https://example.com/exchange-rates/BDT"
    assert result.raw_response == SAMPLE_EXCHANGE_RATE_RESPONSE