# -----------------------------------------------------------------------------
# EXCHANGE RATE SOURCE ADAPTER
# -----------------------------------------------------------------------------
# PURPOSE:
#   Fetches and parses exchange-rate data for origin currencies.
#
# INPUT:
#   - Base/origin currency code, such as BDT, NGN, GBP, or USD.
#   - Target currency codes, such as USD, INR, THB, MYR, TRY, or KRW.
#   - HTTP timeout setting.
#
# PROCESS:
#   - Builds the exchange-rate API URL for one base currency.
#   - Fetches raw JSON from the exchange-rate API.
#   - Extracts requested target currency rates.
#   - Extracts the source update timestamp.
#   - Returns parsed rates and source metadata.
#
# OUTPUT:
#   - ExchangeRateResult containing:
#       - base currency
#       - target rates
#       - source update timestamp
#       - source URL
#       - raw response JSON
#
# NOTES:
#   - This adapter does not write files directly.
#   - Pipelines decide where raw source responses should be stored.
#   - Missing target currency rates fail loudly instead of using fake values.
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


EXCHANGE_RATE_BASE_URL = "https://open.er-api.com/v6/latest"


@dataclass(frozen=True)
class ExchangeRateResult:
    """Parsed exchange-rate result for one base currency."""

    base_currency: str
    target_rates: dict[str, float]
    source_update_utc: str
    source_url: str
    raw_response: Any


def normalize_currency_code(currency_code: str) -> str:
    """Normalize a currency code for API calls and dictionary lookups."""

    return currency_code.strip().upper()


def build_exchange_rate_url(base_currency: str) -> str:
    """Build the exchange-rate API URL for one base currency."""

    normalized_base_currency = normalize_currency_code(base_currency)

    return f"{EXCHANGE_RATE_BASE_URL}/{normalized_base_currency}"


def fetch_exchange_rate_response(base_currency: str, timeout_seconds: int = 30) -> tuple[str, Any]:
    """Fetch raw exchange-rate JSON for one base currency."""

    source_url = build_exchange_rate_url(base_currency)

    response = requests.get(source_url, timeout=timeout_seconds)
    response.raise_for_status()

    return source_url, response.json()


def extract_exchange_rates(
    raw_response: Any,
    target_currencies: list[str],
) -> tuple[dict[str, float], str]:
    """Extract requested target currency rates from raw API JSON."""

    if not isinstance(raw_response, dict):
        raise ValueError("Exchange-rate response must be a JSON object.")

    if raw_response.get("result") != "success":
        error_type = raw_response.get("error-type", "unknown_error")
        raise ValueError(f"Exchange-rate API returned non-success result: {error_type}")

    raw_rates = raw_response.get("rates")
    if not isinstance(raw_rates, dict):
        raise ValueError("Exchange-rate response must contain a rates object.")

    source_update_utc = raw_response.get("time_last_update_utc", "")
    if not source_update_utc:
        raise ValueError("Exchange-rate response is missing time_last_update_utc.")

    normalized_targets = [normalize_currency_code(currency) for currency in target_currencies]
    extracted_rates: dict[str, float] = {}

    for target_currency in normalized_targets:
        raw_rate = raw_rates.get(target_currency)

        if raw_rate is None:
            raise ValueError(f"Missing exchange rate for target currency: {target_currency}")

        extracted_rates[target_currency] = float(raw_rate)

    return extracted_rates, source_update_utc


def get_exchange_rates_for_currency(
    base_currency: str,
    target_currencies: list[str],
    timeout_seconds: int = 30,
) -> ExchangeRateResult:
    """Fetch and parse exchange rates for one base currency."""

    normalized_base_currency = normalize_currency_code(base_currency)

    source_url, raw_response = fetch_exchange_rate_response(
        base_currency=normalized_base_currency,
        timeout_seconds=timeout_seconds,
    )
    target_rates, source_update_utc = extract_exchange_rates(
        raw_response=raw_response,
        target_currencies=target_currencies,
    )

    return ExchangeRateResult(
        base_currency=normalized_base_currency,
        target_rates=target_rates,
        source_update_utc=source_update_utc,
        source_url=source_url,
        raw_response=raw_response,
    )