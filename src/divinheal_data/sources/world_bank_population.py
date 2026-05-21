# -----------------------------------------------------------------------------
# WORLD BANK POPULATION SOURCE ADAPTER
# -----------------------------------------------------------------------------
# PURPOSE:
#   Fetches and parses official World Bank population data for origin countries.
#
# INPUT:
#   - ISO 2-letter country code, such as BD, NG, US, or GB.
#   - HTTP timeout setting.
#
# PROCESS:
#   - Builds the World Bank Indicators API URL for total population.
#   - Fetches raw JSON from the World Bank API.
#   - Finds the latest year with a non-empty population value.
#   - Converts raw population count into population in millions.
#   - Returns both parsed values and source metadata.
#
# OUTPUT:
#   - PopulationResult containing:
#       - country ISO code
#       - population value
#       - population year
#       - population in millions
#       - source URL
#       - raw response JSON
#
# NOTES:
#   - This adapter does not write files directly.
#   - Pipelines decide where raw source responses should be stored.
#   - World Bank indicator SP.POP.TOTL means total population.
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"
POPULATION_INDICATOR_CODE = "SP.POP.TOTL"
POPULATION_INDICATOR_NAME = "Population, total"


@dataclass(frozen=True)
class PopulationResult:
    """Parsed World Bank population result for one country."""

    country_iso_code: str
    population: int
    population_year: int
    population_millions: float
    indicator_code: str
    indicator_name: str
    source_url: str
    raw_response: Any


def build_population_url(country_iso_code: str) -> str:
    """Build the World Bank population API URL for one country."""

    normalized_country_code = country_iso_code.strip().upper()

    return (
        f"{WORLD_BANK_BASE_URL}/country/{normalized_country_code}"
        f"/indicator/{POPULATION_INDICATOR_CODE}"
        "?format=json&per_page=100"
    )


def fetch_population_response(country_iso_code: str, timeout_seconds: int = 30) -> tuple[str, Any]:
    """Fetch raw World Bank population JSON for one country."""

    source_url = build_population_url(country_iso_code)

    response = requests.get(source_url, timeout=timeout_seconds)
    response.raise_for_status()

    return source_url, response.json()


def extract_latest_population(raw_response: Any) -> tuple[int, int]:
    """Extract the latest non-empty population value and year from raw World Bank JSON."""

    if not isinstance(raw_response, list) or len(raw_response) < 2:
        raise ValueError("World Bank response must be a list with metadata and data records.")

    records = raw_response[1]

    if not isinstance(records, list):
        raise ValueError("World Bank population records must be a list.")

    for record in records:
        if not isinstance(record, dict):
            continue

        raw_value = record.get("value")
        raw_year = record.get("date")

        if raw_value is None or raw_year is None:
            continue

        return int(raw_value), int(raw_year)

    raise ValueError("No non-empty population value found in World Bank response.")


def population_to_millions(population: int) -> float:
    """Convert raw population count into millions rounded to two decimals."""

    return round(population / 1_000_000, 2)


def get_population_for_country(
    country_iso_code: str,
    timeout_seconds: int = 30,
) -> PopulationResult:
    """Fetch and parse latest World Bank population data for one country."""

    source_url, raw_response = fetch_population_response(
        country_iso_code=country_iso_code,
        timeout_seconds=timeout_seconds,
    )
    population, population_year = extract_latest_population(raw_response)

    return PopulationResult(
        country_iso_code=country_iso_code.strip().upper(),
        population=population,
        population_year=population_year,
        population_millions=population_to_millions(population),
        indicator_code=POPULATION_INDICATOR_CODE,
        indicator_name=POPULATION_INDICATOR_NAME,
        source_url=source_url,
        raw_response=raw_response,
    )