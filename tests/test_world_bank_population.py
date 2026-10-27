# -----------------------------------------------------------------------------
# WORLD BANK POPULATION SOURCE TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies World Bank population URL building and response parsing.
#
# INPUT:
#   Functions from divinheal_data.sources.world_bank_population.
#
# PROCESS:
#   - Tests population API URL construction.
#   - Tests latest population extraction from sample World Bank-style responses.
#   - Tests population-to-millions conversion.
#   - Tests high-level result creation while mocking the HTTP fetch layer.
#   - Tests invalid/missing response shapes fail loudly.
#
# OUTPUT:
#   Passing tests for the World Bank population source adapter.
#
# NOTES:
#   - These tests do not call the real World Bank API.
#   - Network behavior should be covered separately with integration/manual tests.
# -----------------------------------------------------------------------------

import pytest

from divinheal_data.sources.world_bank_population import (
    POPULATION_INDICATOR_CODE,
    POPULATION_INDICATOR_NAME,
    build_population_url,
    extract_latest_population,
    get_population_for_country,
    population_to_millions,
)


SAMPLE_WORLD_BANK_RESPONSE = [
    {
        "page": 1,
        "pages": 1,
        "per_page": 100,
        "total": 2,
    },
    [
        {
            "indicator": {
                "id": "SP.POP.TOTL",
                "value": "Population, total",
            },
            "country": {
                "id": "BD",
                "value": "Bangladesh",
            },
            "countryiso3code": "BGD",
            "date": "2024",
            "value": 171466990,
        },
        {
            "indicator": {
                "id": "SP.POP.TOTL",
                "value": "Population, total",
            },
            "country": {
                "id": "BD",
                "value": "Bangladesh",
            },
            "countryiso3code": "BGD",
            "date": "2023",
            "value": 170000000,
        },
    ],
]


def test_build_population_url_normalizes_country_code() -> None:
    url = build_population_url(" bd ")

    assert url == (
        "https://api.worldbank.org/v2/country/BD"
        "/indicator/SP.POP.TOTL?format=json&per_page=100"
    )


def test_extract_latest_population_returns_first_non_empty_value() -> None:
    population, year = extract_latest_population(SAMPLE_WORLD_BANK_RESPONSE)

    assert population == 171466990
    assert year == 2024


def test_extract_latest_population_skips_empty_values() -> None:
    raw_response = [
        {"page": 1},
        [
            {"date": "2024", "value": None},
            {"date": "2023", "value": 170000000},
        ],
    ]

    population, year = extract_latest_population(raw_response)

    assert population == 170000000
    assert year == 2023


def test_extract_latest_population_rejects_invalid_response_shape() -> None:
    with pytest.raises(ValueError, match="metadata and data records"):
        extract_latest_population({"bad": "shape"})


def test_extract_latest_population_rejects_missing_records_list() -> None:
    with pytest.raises(ValueError, match="records must be a list"):
        extract_latest_population([{"page": 1}, {"not": "a list"}])


def test_extract_latest_population_rejects_no_population_values() -> None:
    raw_response = [
        {"page": 1},
        [
            {"date": "2024", "value": None},
            {"date": "2023", "value": None},
        ],
    ]

    with pytest.raises(ValueError, match="No non-empty population value"):
        extract_latest_population(raw_response)


def test_population_to_millions_rounds_to_two_decimals() -> None:
    assert population_to_millions(171466990) == 171.47


def test_get_population_for_country_builds_result(monkeypatch) -> None:
    def fake_fetch_population_response(country_iso_code: str, timeout_seconds: int):
        assert country_iso_code == " bd "
        assert timeout_seconds == 10
        return "https://example.com/world-bank-population", SAMPLE_WORLD_BANK_RESPONSE

    monkeypatch.setattr(
        "divinheal_data.sources.world_bank_population.fetch_population_response",
        fake_fetch_population_response,
    )

    result = get_population_for_country(country_iso_code=" bd ", timeout_seconds=10)

    assert result.country_iso_code == "BD"
    assert result.population == 171466990
    assert result.population_year == 2024
    assert result.population_millions == 171.47
    assert result.indicator_code == POPULATION_INDICATOR_CODE
    assert result.indicator_name == POPULATION_INDICATOR_NAME
    assert result.source_url == "https://example.com/world-bank-population"
    assert result.raw_response == SAMPLE_WORLD_BANK_RESPONSE