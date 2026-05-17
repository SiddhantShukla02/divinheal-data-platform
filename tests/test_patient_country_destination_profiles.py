# -----------------------------------------------------------------------------
# PATIENT COUNTRY DESTINATION PROFILE PIPELINE TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies the patient-country destination profile pipeline behavior.
#
# INPUT:
#   Functions from divinheal_data.pipelines.patient_country_destination_profiles.
#
# PROCESS:
#   - Tests target schema reading.
#   - Tests YAML list reading.
#   - Tests raw source path generation.
#   - Tests matrix rows without source enrichment.
#   - Tests matrix rows with population enrichment.
#   - Tests matrix rows with exchange-rate enrichment.
#   - Tests CSV and JSON writing helpers.
#
# OUTPUT:
#   Passing tests for the matrix-generation, population-enrichment, and
#   exchange-rate-enrichment pipeline slice.
#
# NOTES:
#   - These tests do not fetch online data.
#   - These tests do not depend on live World Bank or exchange-rate responses.
#   - Source adapter tests separately verify parsing behavior.
# -----------------------------------------------------------------------------

import csv
import json
from pathlib import Path

import pytest

from divinheal_data.core.run_context import RunContext
from divinheal_data.core.statuses import RecordStatus
from divinheal_data.pipelines.patient_country_destination_profiles import (
    SOURCE_REQUIRED_FIELDS,
    ExchangeRateResult,
    PopulationResult,
    build_exchange_rate_raw_path,
    build_filled_fields,
    build_missing_fields,
    build_population_raw_path,
    build_profile_row,
    build_missing_fields_report,
    build_profiles,
    build_source_fx_value,
    build_source_population_value,
    get_destination_currency_codes,
    get_exchange_rate_for_target,
    read_target_columns,
    read_yaml_list,
    write_csv,
    write_json,
)


TARGET_COLUMNS = [
    "origin_country_slug",
    "origin_country_name",
    "origin_country_name_local",
    "origin_iso_country_code",
    "origin_primary_locale",
    "origin_secondary_locales",
    "origin_currency_code",
    "origin_currency_to_usd",
    "origin_currency_to_destination_currency",
    "exchange_rate_date",
    "origin_population_millions",
    "origin_population_year",
    "destination_country_slug",
    "destination_country_name",
    "destination_region",
    "destination_currency_code",
    "estimated_annual_outbound_medical_travel",
    "estimated_share_to_destination_pct",
    "top_treatments_sought",
    "top_origin_cities",
    "destination_arrival_cities",
    "language_support_priority",
    "cultural_notes",
    "embassy_or_consulate_info",
    "source_population",
    "source_fx",
    "source_outbound_stats",
    "verified_date",
    "verified_by",
    "record_status",
    "confidence_score",
    "filled_fields",
    "missing_fields",
    "needs_review_fields",
]


def make_population_result(country_iso_code: str = "BD") -> PopulationResult:
    return PopulationResult(
        country_iso_code=country_iso_code,
        population=171466990,
        population_year=2024,
        population_millions=171.47,
        indicator_code="SP.POP.TOTL",
        indicator_name="Population, total",
        source_url="https://api.worldbank.org/v2/country/BD/indicator/SP.POP.TOTL",
        raw_response=[{"page": 1}, [{"date": "2024", "value": 171466990}]],
    )


def make_exchange_rate_result(base_currency: str = "BDT") -> ExchangeRateResult:
    return ExchangeRateResult(
        base_currency=base_currency,
        target_rates={
            "USD": 0.008146,
            "INR": 0.780658,
            "THB": 0.265507,
        },
        source_update_utc="Sun, 17 May 2026 00:02:31 +0000",
        source_url=f"https://open.er-api.com/v6/latest/{base_currency}",
        raw_response={
            "result": "success",
            "base_code": base_currency,
            "time_last_update_utc": "Sun, 17 May 2026 00:02:31 +0000",
            "rates": {
                "USD": 0.008146,
                "INR": 0.780658,
                "THB": 0.265507,
            },
        },
    )


def test_read_target_columns_reads_csv_header(tmp_path: Path) -> None:
    schema_path = tmp_path / "target_schema.csv"
    schema_path.write_text("first_column,second_column,third_column\n", encoding="utf-8")

    columns = read_target_columns(schema_path)

    assert columns == ["first_column", "second_column", "third_column"]


def test_read_yaml_list_reads_expected_key(tmp_path: Path) -> None:
    yaml_path = tmp_path / "origin_countries.yml"
    yaml_path.write_text(
        """
origin_countries:
  - origin_country_slug: bangladesh
    origin_country_name: Bangladesh
""",
        encoding="utf-8",
    )

    records = read_yaml_list(yaml_path, "origin_countries")

    assert records == [
        {
            "origin_country_slug": "bangladesh",
            "origin_country_name": "Bangladesh",
        }
    ]


def test_read_yaml_list_rejects_non_list_key(tmp_path: Path) -> None:
    yaml_path = tmp_path / "bad_config.yml"
    yaml_path.write_text(
        """
origin_countries:
  origin_country_slug: bangladesh
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must contain a 'origin_countries' list"):
        read_yaml_list(yaml_path, "origin_countries")


def test_build_population_raw_path_uses_run_id_and_country_code() -> None:
    context = RunContext(
        pipeline_name="patient_country_destination_profiles",
        run_id="test_run_id",
    )

    path = build_population_raw_path(
        context=context,
        origin_iso_country_code=" bd ",
    )

    assert path.as_posix().endswith(
        "data/raw/patient_country_destination_profiles/"
        "test_run_id/world_bank_population/BD.json"
    )


def test_build_exchange_rate_raw_path_uses_run_id_and_currency_code() -> None:
    context = RunContext(
        pipeline_name="patient_country_destination_profiles",
        run_id="test_run_id",
    )

    path = build_exchange_rate_raw_path(
        context=context,
        origin_currency_code=" bdt ",
    )

    assert path.as_posix().endswith(
        "data/raw/patient_country_destination_profiles/test_run_id/exchange_rates/BDT.json"
    )


def test_get_destination_currency_codes_includes_unique_destinations_and_usd() -> None:
    destinations = [
        {"destination_currency_code": "INR"},
        {"destination_currency_code": "THB"},
        {"destination_currency_code": " inr "},
        {"destination_currency_code": ""},
    ]

    assert get_destination_currency_codes(destinations) == ["INR", "THB", "USD"]


def test_build_source_population_value_returns_blank_without_result() -> None:
    assert build_source_population_value(None) == ""


def test_build_source_population_value_includes_indicator_year_and_url() -> None:
    population_result = make_population_result()

    source_value = build_source_population_value(population_result)

    assert source_value == (
        "World Bank SP.POP.TOTL (2024) | "
        "https://api.worldbank.org/v2/country/BD/indicator/SP.POP.TOTL"
    )


def test_build_source_fx_value_returns_blank_without_result() -> None:
    assert build_source_fx_value(None) == ""


def test_build_source_fx_value_includes_base_currency_update_time_and_url() -> None:
    exchange_rate_result = make_exchange_rate_result()

    source_value = build_source_fx_value(exchange_rate_result)

    assert source_value == (
        "open.er-api.com latest rates for BDT "
        "(Sun, 17 May 2026 00:02:31 +0000) | "
        "https://open.er-api.com/v6/latest/BDT"
    )


def test_get_exchange_rate_for_target_returns_blank_without_result() -> None:
    assert get_exchange_rate_for_target(None, "USD") == ""


def test_get_exchange_rate_for_target_returns_blank_for_missing_target() -> None:
    exchange_rate_result = make_exchange_rate_result()

    assert get_exchange_rate_for_target(exchange_rate_result, "KRW") == ""


def test_get_exchange_rate_for_target_returns_rate_as_string() -> None:
    exchange_rate_result = make_exchange_rate_result()

    assert get_exchange_rate_for_target(exchange_rate_result, " inr ") == "0.780658"


def test_build_missing_fields_keeps_population_and_fx_fields_without_results() -> None:
    missing_fields = build_missing_fields(
        population_result=None,
        exchange_rate_result=None,
        destination_currency_code="INR",
    )

    assert "origin_population_millions" in missing_fields
    assert "origin_population_year" in missing_fields
    assert "source_population" in missing_fields
    assert "origin_currency_to_usd" in missing_fields
    assert "origin_currency_to_destination_currency" in missing_fields
    assert "exchange_rate_date" in missing_fields
    assert "source_fx" in missing_fields


def test_build_missing_fields_removes_population_fields_when_population_exists() -> None:
    population_result = make_population_result()

    missing_fields = build_missing_fields(
        population_result=population_result,
        exchange_rate_result=None,
        destination_currency_code="INR",
    )

    assert "origin_population_millions" not in missing_fields
    assert "origin_population_year" not in missing_fields
    assert "source_population" not in missing_fields
    assert "origin_currency_to_usd" in missing_fields
    assert "source_fx" in missing_fields


def test_build_missing_fields_removes_fx_fields_when_fx_exists() -> None:
    exchange_rate_result = make_exchange_rate_result()

    missing_fields = build_missing_fields(
        population_result=None,
        exchange_rate_result=exchange_rate_result,
        destination_currency_code="INR",
    )

    assert "origin_currency_to_usd" not in missing_fields
    assert "origin_currency_to_destination_currency" not in missing_fields
    assert "exchange_rate_date" not in missing_fields
    assert "source_fx" not in missing_fields
    assert "origin_population_millions" in missing_fields


def test_build_filled_fields_adds_population_fields_when_population_exists() -> None:
    population_result = make_population_result()

    filled_fields = build_filled_fields(
        population_result=population_result,
        exchange_rate_result=None,
        destination_currency_code="INR",
    )

    assert "origin_country_slug" in filled_fields
    assert "destination_country_slug" in filled_fields
    assert "origin_population_millions" in filled_fields
    assert "origin_population_year" in filled_fields
    assert "source_population" in filled_fields
    assert "source_fx" not in filled_fields


def test_build_filled_fields_adds_fx_fields_when_fx_exists() -> None:
    exchange_rate_result = make_exchange_rate_result()

    filled_fields = build_filled_fields(
        population_result=None,
        exchange_rate_result=exchange_rate_result,
        destination_currency_code="INR",
    )

    assert "origin_currency_to_usd" in filled_fields
    assert "origin_currency_to_destination_currency" in filled_fields
    assert "exchange_rate_date" in filled_fields
    assert "source_fx" in filled_fields
    assert "origin_population_millions" not in filled_fields


def test_build_profile_row_without_enrichment_marks_source_fields_missing() -> None:
    origin = {
        "origin_country_slug": "bangladesh",
        "origin_country_name": "Bangladesh",
        "origin_country_name_local": "বাংলাদেশ",
        "origin_iso_country_code": "BD",
        "origin_primary_locale": "bn",
        "origin_secondary_locales": "en",
        "origin_currency_code": "BDT",
    }

    destination = {
        "destination_country_slug": "india",
        "destination_country_name": "India",
        "destination_region": "South Asia",
        "destination_currency_code": "INR",
    }

    row = build_profile_row(
        origin=origin,
        destination=destination,
        target_columns=TARGET_COLUMNS,
    )

    assert row["origin_country_slug"] == "bangladesh"
    assert row["origin_country_name"] == "Bangladesh"
    assert row["origin_country_name_local"] == "বাংলাদেশ"
    assert row["origin_iso_country_code"] == "BD"
    assert row["origin_primary_locale"] == "bn"
    assert row["origin_secondary_locales"] == "en"
    assert row["origin_currency_code"] == "BDT"

    assert row["destination_country_slug"] == "india"
    assert row["destination_country_name"] == "India"
    assert row["destination_region"] == "South Asia"
    assert row["destination_currency_code"] == "INR"

    assert row["origin_currency_to_usd"] == ""
    assert row["origin_currency_to_destination_currency"] == ""
    assert row["exchange_rate_date"] == ""
    assert row["origin_population_millions"] == ""
    assert row["origin_population_year"] == ""
    assert row["source_population"] == ""
    assert row["source_fx"] == ""
    assert row["embassy_or_consulate_info"] == ""

    assert row["record_status"] == RecordStatus.MISSING_SOURCE.value
    assert row["confidence_score"] == "0.20"

    assert "origin_country_slug" in row["filled_fields"]
    assert "destination_country_slug" in row["filled_fields"]
    assert row["missing_fields"] == ";".join(SOURCE_REQUIRED_FIELDS)
    assert row["needs_review_fields"] == ";".join(SOURCE_REQUIRED_FIELDS)


def test_build_profile_row_with_population_and_fx_fills_source_fields() -> None:
    origin = {
        "origin_country_slug": "bangladesh",
        "origin_country_name": "Bangladesh",
        "origin_country_name_local": "বাংলাদেশ",
        "origin_iso_country_code": "BD",
        "origin_primary_locale": "bn",
        "origin_secondary_locales": "en",
        "origin_currency_code": "BDT",
    }

    destination = {
        "destination_country_slug": "india",
        "destination_country_name": "India",
        "destination_region": "South Asia",
        "destination_currency_code": "INR",
    }

    population_result = make_population_result(country_iso_code="BD")
    exchange_rate_result = make_exchange_rate_result(base_currency="BDT")

    row = build_profile_row(
        origin=origin,
        destination=destination,
        target_columns=TARGET_COLUMNS,
        population_by_country_code={"BD": population_result},
        exchange_rates_by_currency_code={"BDT": exchange_rate_result},
    )

    assert row["origin_population_millions"] == "171.47"
    assert row["origin_population_year"] == "2024"
    assert row["source_population"] == (
        "World Bank SP.POP.TOTL (2024) | "
        "https://api.worldbank.org/v2/country/BD/indicator/SP.POP.TOTL"
    )

    assert row["origin_currency_to_usd"] == "0.008146"
    assert row["origin_currency_to_destination_currency"] == "0.780658"
    assert row["exchange_rate_date"] == "Sun, 17 May 2026 00:02:31 +0000"
    assert row["source_fx"] == (
        "open.er-api.com latest rates for BDT "
        "(Sun, 17 May 2026 00:02:31 +0000) | "
        "https://open.er-api.com/v6/latest/BDT"
    )

    assert row["record_status"] == RecordStatus.NEEDS_REVIEW.value
    assert row["confidence_score"] == "0.50"

    assert "origin_population_millions" in row["filled_fields"]
    assert "source_population" in row["filled_fields"]
    assert "origin_currency_to_usd" in row["filled_fields"]
    assert "origin_currency_to_destination_currency" in row["filled_fields"]
    assert "source_fx" in row["filled_fields"]

    assert "origin_population_millions" not in row["missing_fields"]
    assert "origin_population_year" not in row["missing_fields"]
    assert "source_population" not in row["missing_fields"]
    assert "origin_currency_to_usd" not in row["missing_fields"]
    assert "origin_currency_to_destination_currency" not in row["missing_fields"]
    assert "exchange_rate_date" not in row["missing_fields"]
    assert "source_fx" not in row["missing_fields"]


def test_build_profile_row_matches_target_columns_only() -> None:
    origin = {
        "origin_country_slug": "bangladesh",
        "origin_country_name": "Bangladesh",
        "extra_origin_field": "should_not_appear",
    }

    destination = {
        "destination_country_slug": "india",
        "destination_country_name": "India",
        "extra_destination_field": "should_not_appear",
    }

    row = build_profile_row(
        origin=origin,
        destination=destination,
        target_columns=["origin_country_slug", "destination_country_slug"],
    )

    assert row == {
        "origin_country_slug": "bangladesh",
        "destination_country_slug": "india",
    }


def test_build_profiles_creates_origin_destination_matrix() -> None:
    origins = [
        {"origin_country_slug": "bangladesh"},
        {"origin_country_slug": "nigeria"},
    ]

    destinations = [
        {"destination_country_slug": "india"},
        {"destination_country_slug": "thailand"},
        {"destination_country_slug": "turkey"},
    ]

    rows = build_profiles(
        origins=origins,
        destinations=destinations,
        target_columns=["origin_country_slug", "destination_country_slug"],
    )

    assert rows == [
        {"origin_country_slug": "bangladesh", "destination_country_slug": "india"},
        {"origin_country_slug": "bangladesh", "destination_country_slug": "thailand"},
        {"origin_country_slug": "bangladesh", "destination_country_slug": "turkey"},
        {"origin_country_slug": "nigeria", "destination_country_slug": "india"},
        {"origin_country_slug": "nigeria", "destination_country_slug": "thailand"},
        {"origin_country_slug": "nigeria", "destination_country_slug": "turkey"},
    ]


def test_build_profiles_passes_population_and_fx_results_to_rows() -> None:
    origins = [
        {
            "origin_country_slug": "bangladesh",
            "origin_iso_country_code": "BD",
            "origin_currency_code": "BDT",
        },
    ]

    destinations = [
        {"destination_country_slug": "india", "destination_currency_code": "INR"},
        {"destination_country_slug": "thailand", "destination_currency_code": "THB"},
    ]

    population_result = make_population_result(country_iso_code="BD")
    exchange_rate_result = make_exchange_rate_result(base_currency="BDT")

    rows = build_profiles(
        origins=origins,
        destinations=destinations,
        target_columns=[
            "origin_country_slug",
            "destination_country_slug",
            "origin_population_millions",
            "origin_population_year",
            "origin_currency_to_usd",
            "origin_currency_to_destination_currency",
        ],
        population_by_country_code={"BD": population_result},
        exchange_rates_by_currency_code={"BDT": exchange_rate_result},
    )

    assert rows == [
        {
            "origin_country_slug": "bangladesh",
            "destination_country_slug": "india",
            "origin_population_millions": "171.47",
            "origin_population_year": "2024",
            "origin_currency_to_usd": "0.008146",
            "origin_currency_to_destination_currency": "0.780658",
        },
        {
            "origin_country_slug": "bangladesh",
            "destination_country_slug": "thailand",
            "origin_population_millions": "171.47",
            "origin_population_year": "2024",
            "origin_currency_to_usd": "0.008146",
            "origin_currency_to_destination_currency": "0.265507",
        },
    ]


def test_build_missing_fields_report_counts_blank_values() -> None:
    rows = [
        {
            "origin_country_slug": "bangladesh",
            "origin_population_millions": "171.47",
            "embassy_or_consulate_info": "",
        },
        {
            "origin_country_slug": "nigeria",
            "origin_population_millions": "232.68",
            "embassy_or_consulate_info": "",
        },
        {
            "origin_country_slug": "kenya",
            "origin_population_millions": "",
            "embassy_or_consulate_info": "",
        },
    ]

    report_rows = build_missing_fields_report(
        rows=rows,
        target_columns=[
            "origin_country_slug",
            "origin_population_millions",
            "embassy_or_consulate_info",
        ],
    )

    assert report_rows == [
        {
            "field_name": "origin_country_slug",
            "missing_row_count": "0",
            "total_row_count": "3",
            "missing_percentage": "0.0",
        },
        {
            "field_name": "origin_population_millions",
            "missing_row_count": "1",
            "total_row_count": "3",
            "missing_percentage": "33.33",
        },
        {
            "field_name": "embassy_or_consulate_info",
            "missing_row_count": "3",
            "total_row_count": "3",
            "missing_percentage": "100.0",
        },
    ]


def test_build_missing_fields_report_handles_empty_rows() -> None:
    report_rows = build_missing_fields_report(
        rows=[],
        target_columns=[
            "origin_country_slug",
            "origin_population_millions",
        ],
    )

    assert report_rows == [
        {
            "field_name": "origin_country_slug",
            "missing_row_count": "0",
            "total_row_count": "0",
            "missing_percentage": "0.0",
        },
        {
            "field_name": "origin_population_millions",
            "missing_row_count": "0",
            "total_row_count": "0",
            "missing_percentage": "0.0",
        },
    ]

    
def test_write_csv_writes_rows_with_target_column_order(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "output.csv"
    rows = [
        {
            "second_column": "B",
            "first_column": "A",
        }
    ]

    write_csv(
        path=output_path,
        rows=rows,
        columns=["first_column", "second_column"],
    )

    with output_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        written_rows = list(reader)

    assert reader.fieldnames == ["first_column", "second_column"]
    assert written_rows == [{"first_column": "A", "second_column": "B"}]


def test_write_json_writes_readable_json(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "summary.json"
    payload = {
        "pipeline_name": "patient_country_destination_profiles",
        "output_row_count": 40,
    }

    write_json(output_path, payload)

    with output_path.open("r", encoding="utf-8") as file:
        saved_payload = json.load(file)

    assert saved_payload == payload