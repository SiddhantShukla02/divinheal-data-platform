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
#   - Tests raw World Bank path generation.
#   - Tests matrix rows without population enrichment.
#   - Tests matrix rows with population enrichment.
#   - Tests CSV and JSON writing helpers.
#
# OUTPUT:
#   Passing tests for the matrix-generation and population-enrichment slice.
#
# NOTES:
#   - These tests do not fetch online data.
#   - These tests do not depend on live World Bank responses.
#   - World Bank adapter tests separately verify population parsing behavior.
# -----------------------------------------------------------------------------

import csv
import json
from pathlib import Path

import pytest

from divinheal_data.core.run_context import RunContext
from divinheal_data.core.statuses import RecordStatus
from divinheal_data.pipelines.patient_country_destination_profiles import (
    SOURCE_REQUIRED_FIELDS,
    PopulationResult,
    build_filled_fields,
    build_missing_fields,
    build_population_raw_path,
    build_profile_row,
    build_profiles,
    build_source_population_value,
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


def test_build_source_population_value_returns_blank_without_result() -> None:
    assert build_source_population_value(None) == ""


def test_build_source_population_value_includes_indicator_year_and_url() -> None:
    population_result = make_population_result()

    source_value = build_source_population_value(population_result)

    assert source_value == (
        "World Bank SP.POP.TOTL (2024) | "
        "https://api.worldbank.org/v2/country/BD/indicator/SP.POP.TOTL"
    )


def test_build_missing_fields_keeps_population_fields_without_population_result() -> None:
    missing_fields = build_missing_fields(None)

    assert "origin_population_millions" in missing_fields
    assert "origin_population_year" in missing_fields
    assert "source_population" in missing_fields


def test_build_missing_fields_removes_population_fields_when_population_exists() -> None:
    population_result = make_population_result()

    missing_fields = build_missing_fields(population_result)

    assert "origin_population_millions" not in missing_fields
    assert "origin_population_year" not in missing_fields
    assert "source_population" not in missing_fields
    assert "origin_currency_to_usd" in missing_fields
    assert "source_fx" in missing_fields


def test_build_filled_fields_adds_population_fields_when_population_exists() -> None:
    population_result = make_population_result()

    filled_fields = build_filled_fields(population_result)

    assert "origin_country_slug" in filled_fields
    assert "destination_country_slug" in filled_fields
    assert "origin_population_millions" in filled_fields
    assert "origin_population_year" in filled_fields
    assert "source_population" in filled_fields


def test_build_profile_row_without_population_marks_population_missing() -> None:
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
    assert row["origin_population_millions"] == ""
    assert row["origin_population_year"] == ""
    assert row["source_population"] == ""
    assert row["embassy_or_consulate_info"] == ""

    assert row["record_status"] == RecordStatus.MISSING_SOURCE.value
    assert row["confidence_score"] == "0.20"

    assert "origin_country_slug" in row["filled_fields"]
    assert "destination_country_slug" in row["filled_fields"]
    assert row["missing_fields"] == ";".join(SOURCE_REQUIRED_FIELDS)
    assert row["needs_review_fields"] == ";".join(SOURCE_REQUIRED_FIELDS)


def test_build_profile_row_with_population_fills_population_fields() -> None:
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

    row = build_profile_row(
        origin=origin,
        destination=destination,
        target_columns=TARGET_COLUMNS,
        population_by_country_code={"BD": population_result},
    )

    assert row["origin_population_millions"] == "171.47"
    assert row["origin_population_year"] == "2024"
    assert row["source_population"] == (
        "World Bank SP.POP.TOTL (2024) | "
        "https://api.worldbank.org/v2/country/BD/indicator/SP.POP.TOTL"
    )

    assert row["record_status"] == RecordStatus.NEEDS_REVIEW.value
    assert row["confidence_score"] == "0.35"

    assert "origin_population_millions" in row["filled_fields"]
    assert "origin_population_year" in row["filled_fields"]
    assert "source_population" in row["filled_fields"]

    assert "origin_population_millions" not in row["missing_fields"]
    assert "origin_population_year" not in row["missing_fields"]
    assert "source_population" not in row["missing_fields"]
    assert "origin_currency_to_usd" in row["missing_fields"]
    assert "source_fx" in row["missing_fields"]


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


def test_build_profiles_passes_population_results_to_rows() -> None:
    origins = [
        {"origin_country_slug": "bangladesh", "origin_iso_country_code": "BD"},
    ]

    destinations = [
        {"destination_country_slug": "india"},
        {"destination_country_slug": "thailand"},
    ]

    population_result = make_population_result(country_iso_code="BD")

    rows = build_profiles(
        origins=origins,
        destinations=destinations,
        target_columns=[
            "origin_country_slug",
            "destination_country_slug",
            "origin_population_millions",
            "origin_population_year",
        ],
        population_by_country_code={"BD": population_result},
    )

    assert rows == [
        {
            "origin_country_slug": "bangladesh",
            "destination_country_slug": "india",
            "origin_population_millions": "171.47",
            "origin_population_year": "2024",
        },
        {
            "origin_country_slug": "bangladesh",
            "destination_country_slug": "thailand",
            "origin_population_millions": "171.47",
            "origin_population_year": "2024",
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

    with output_path.open("r", encoding="utf-8", newline="") as file:
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