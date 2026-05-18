# -----------------------------------------------------------------------------
# PATIENT COUNTRY DESTINATION PROFILE PIPELINE
# -----------------------------------------------------------------------------
# PURPOSE:
#   Generates the multi-destination patient-country profile output.
#
# INPUT:
#   - configs/origin_countries.yml
#   - configs/destinations.yml
#   - schemas/target/patient_country_destination_profiles.csv
#
# PROCESS:
#   - Loads origin/patient countries from config.
#   - Loads destination countries from config.
#   - Fetches official World Bank population data for each origin country.
#   - Fetches exchange-rate data for each origin currency.
#   - Stores raw World Bank and exchange-rate API responses under data/raw/.
#   - Creates one row for each origin country and destination country pair.
#   - Fills safe config identity fields.
#   - Fills source-backed population fields where World Bank data is available.
#   - Fills source-backed currency fields where exchange-rate data is available.
#   - Leaves other unsourced research/enrichment fields blank.
#   - Marks missing/source-required fields explicitly.
#   - Writes a human-facing CSV and run summary under outputs/.
#
# OUTPUT:
#   - outputs/patient_country_destination_profiles/latest/
#       - patient_country_destination_profiles.csv
#       - run_summary.json
#   - data/raw/patient_country_destination_profiles/<run_id>/world_bank_population/
#       - <origin_iso_country_code>.json
#   - data/raw/patient_country_destination_profiles/<run_id>/exchange_rates/
#       - <origin_currency_code>.json
#
# NOTES:
#   - This module currently enriches population and exchange-rate data.
#   - This module does not fetch visa, hospital, city, treatment, or embassy data.
#   - Do not add guessed/manual/fake values here. Add source adapters later.
# -----------------------------------------------------------------------------

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from divinheal_data.core.run_context import RunContext
from divinheal_data.core.settings import load_settings
from divinheal_data.core.statuses import RecordStatus
from divinheal_data.sources.exchange_rates import ExchangeRateResult, get_exchange_rates_for_currency
from divinheal_data.sources.world_bank_population import PopulationResult, get_population_for_country


# -----------------------------------------------------------------------------
# PATHS AND CONSTANTS
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ORIGIN_COUNTRIES_CONFIG_PATH = PROJECT_ROOT / "configs/origin_countries.yml"
DESTINATIONS_CONFIG_PATH = PROJECT_ROOT / "configs/destinations.yml"
TARGET_SCHEMA_PATH = PROJECT_ROOT / "schemas/target/patient_country_destination_profiles.csv"

RAW_DATA_ROOT = PROJECT_ROOT / "data/raw/patient_country_destination_profiles"
OUTPUT_ROOT = PROJECT_ROOT / "outputs/patient_country_destination_profiles"
LATEST_OUTPUT_DIR = OUTPUT_ROOT / "latest"


SEED_FILLED_FIELDS = [
    "origin_country_slug",
    "origin_country_name",
    "origin_country_name_local",
    "origin_iso_country_code",
    "origin_primary_locale",
    "origin_secondary_locales",
    "origin_currency_code",
    "destination_country_slug",
    "destination_country_name",
    "destination_region",
    "destination_currency_code",
]


POPULATION_FILLED_FIELDS = [
    "origin_population_millions",
    "origin_population_year",
    "source_population",
]


SOURCE_REQUIRED_FIELDS = [
    "origin_currency_to_usd",
    "origin_currency_to_destination_currency",
    "exchange_rate_date",
    "origin_population_millions",
    "origin_population_year",
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
]



# -----------------------------------------------------------------------------
# CONFIG AND SCHEMA READERS
# -----------------------------------------------------------------------------

def read_target_columns(path: Path) -> list[str]:
    """Read the target schema header row."""

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        return next(reader)


def read_yaml_list(path: Path, key: str) -> list[dict[str, str]]:
    """Read a named list of dictionaries from a YAML config file."""

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    records = config.get(key, [])

    if not isinstance(records, list):
        raise ValueError(f"{path} must contain a '{key}' list.")

    return records


def read_origin_countries(path: Path) -> list[dict[str, str]]:
    """Read origin country config."""

    return read_yaml_list(path=path, key="origin_countries")


def read_destinations(path: Path) -> list[dict[str, str]]:
    """Read destination country config."""

    return read_yaml_list(path=path, key="destinations")


# -----------------------------------------------------------------------------
# OUTPUT WRITERS
# -----------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    """Write rows to CSV using the target schema column order."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    """Write rows to a human-friendly Excel workbook."""

    path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "patient_profiles"

    worksheet.append(columns)

    for row in rows:
        worksheet.append([row.get(column, "") for column in columns])

    header_font = Font(bold=True)
    header_alignment = Alignment(wrap_text=True, vertical="top")

    for cell in worksheet[1]:
        cell.font = header_font
        cell.alignment = header_alignment

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    wrapped_columns = {
        "source_population",
        "source_fx",
        "filled_fields",
        "missing_fields",
        "needs_review_fields",
    }

    for column_index, column_name in enumerate(columns, start=1):
        column_letter = get_column_letter(column_index)
        max_length = len(column_name)

        for cell in worksheet[column_letter]:
            cell_value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(cell_value))

            if column_name in wrapped_columns:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 60)

    workbook.save(path)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON data with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# REPORT BUILDERS
# -----------------------------------------------------------------------------

def build_missing_fields_report(
    rows: list[dict[str, str]],
    target_columns: list[str],
) -> list[dict[str, str]]:
    """Build a field-level missing-data report for generated output rows."""

    total_row_count = len(rows)
    report_rows = []

    for column in target_columns:
        missing_row_count = sum(1 for row in rows if not row.get(column, "").strip())

        missing_percentage = (
            round((missing_row_count / total_row_count) * 100, 2)
            if total_row_count
            else 0.0
        )

        report_rows.append(
            {
                "field_name": column,
                "missing_row_count": str(missing_row_count),
                "total_row_count": str(total_row_count),
                "missing_percentage": str(missing_percentage),
            }
        )

    return report_rows


# -----------------------------------------------------------------------------
# RAW SOURCE PATH BUILDERS
# -----------------------------------------------------------------------------

def build_population_raw_path(context: RunContext, origin_iso_country_code: str) -> Path:
    """Build the raw JSON path for one origin country's World Bank response."""

    safe_country_code = origin_iso_country_code.strip().upper()

    return RAW_DATA_ROOT / context.run_id / "world_bank_population" / f"{safe_country_code}.json"


def build_exchange_rate_raw_path(context: RunContext, origin_currency_code: str) -> Path:
    """Build the raw JSON path for one origin currency's exchange-rate response."""

    safe_currency_code = origin_currency_code.strip().upper()

    return RAW_DATA_ROOT / context.run_id / "exchange_rates" / f"{safe_currency_code}.json"


# -----------------------------------------------------------------------------
# EXCHANGE-RATE TARGET HELPERS
# -----------------------------------------------------------------------------

def get_destination_currency_codes(destinations: list[dict[str, str]]) -> list[str]:
    """Return unique destination currency codes plus USD for exchange-rate enrichment."""

    currency_codes = {"USD"}

    for destination in destinations:
        currency_code = destination.get("destination_currency_code", "").strip().upper()

        if currency_code:
            currency_codes.add(currency_code)

    return sorted(currency_codes)

# -----------------------------------------------------------------------------
# SOURCE ENRICHMENT FETCHERS
# -----------------------------------------------------------------------------

def fetch_population_results(
    origins: list[dict[str, str]],
    context: RunContext,
    timeout_seconds: int,
) -> tuple[dict[str, PopulationResult], list[dict[str, str]]]:
    """Fetch World Bank population data for origin countries."""

    population_by_country_code: dict[str, PopulationResult] = {}
    failures: list[dict[str, str]] = []

    for origin in origins:
        country_code = origin.get("origin_iso_country_code", "").strip().upper()

        if not country_code:
            failures.append(
                {
                    "origin_country_slug": origin.get("origin_country_slug", ""),
                    "origin_iso_country_code": "",
                    "failure_reason": "Missing origin ISO country code.",
                }
            )
            continue

        try:
            result = get_population_for_country(
                country_iso_code=country_code,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            failures.append(
                {
                    "origin_country_slug": origin.get("origin_country_slug", ""),
                    "origin_iso_country_code": country_code,
                    "failure_reason": str(exc),
                }
            )
            continue

        population_by_country_code[country_code] = result
        write_json(
            path=build_population_raw_path(context, country_code),
            payload=result.raw_response,
        )

    return population_by_country_code, failures


def fetch_exchange_rate_results(
    origins: list[dict[str, str]],
    destinations: list[dict[str, str]],
    context: RunContext,
    timeout_seconds: int,
) -> tuple[dict[str, ExchangeRateResult], list[dict[str, str]]]:
    """Fetch exchange-rate data for origin currencies."""

    exchange_rates_by_currency_code: dict[str, ExchangeRateResult] = {}
    failures: list[dict[str, str]] = []
    target_currencies = get_destination_currency_codes(destinations)

    origin_currency_codes = {
        origin.get("origin_currency_code", "").strip().upper()
        for origin in origins
        if origin.get("origin_currency_code", "").strip()
    }

    for currency_code in sorted(origin_currency_codes):
        try:
            result = get_exchange_rates_for_currency(
                base_currency=currency_code,
                target_currencies=target_currencies,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            failures.append(
                {
                    "origin_currency_code": currency_code,
                    "target_currencies": ";".join(target_currencies),
                    "failure_reason": str(exc),
                }
            )
            continue

        exchange_rates_by_currency_code[currency_code] = result
        write_json(
            path=build_exchange_rate_raw_path(context, currency_code),
            payload=result.raw_response,
        )

    missing_currency_origins = [
        origin.get("origin_country_slug", "")
        for origin in origins
        if not origin.get("origin_currency_code", "").strip()
    ]

    for origin_country_slug in missing_currency_origins:
        failures.append(
            {
                "origin_country_slug": origin_country_slug,
                "origin_currency_code": "",
                "target_currencies": ";".join(target_currencies),
                "failure_reason": "Missing origin currency code.",
            }
        )

    return exchange_rates_by_currency_code, failures


# -----------------------------------------------------------------------------
# SOURCE VALUE BUILDERS
# -----------------------------------------------------------------------------

def build_source_population_value(population_result: PopulationResult | None) -> str:
    """Build the source description for the population field."""

    if population_result is None:
        return ""

    return (
        f"World Bank {population_result.indicator_code} "
        f"({population_result.population_year}) | {population_result.source_url}"
    )


def build_source_fx_value(exchange_rate_result: ExchangeRateResult | None) -> str:
    """Build the source description for exchange-rate fields."""

    if exchange_rate_result is None:
        return ""

    return (
        f"open.er-api.com latest rates for {exchange_rate_result.base_currency} "
        f"({exchange_rate_result.source_update_utc}) | {exchange_rate_result.source_url}"
    )


def get_exchange_rate_for_target(
    exchange_rate_result: ExchangeRateResult | None,
    target_currency_code: str,
) -> str:
    """Return an exchange rate for a target currency as a string."""

    if exchange_rate_result is None:
        return ""

    normalized_target_currency = target_currency_code.strip().upper()

    if not normalized_target_currency:
        return ""

    rate = exchange_rate_result.target_rates.get(normalized_target_currency)

    if rate is None:
        return ""

    return str(rate)


# -----------------------------------------------------------------------------
# FIELD STATUS BUILDERS
# -----------------------------------------------------------------------------

def build_missing_fields(
    population_result: PopulationResult | None,
    exchange_rate_result: ExchangeRateResult | None,
    destination_currency_code: str,
) -> list[str]:
    """Build the missing field list for one output row."""

    missing_fields = SOURCE_REQUIRED_FIELDS.copy()

    if population_result is not None:
        population_fields = {
            "origin_population_millions",
            "origin_population_year",
            "source_population",
        }
        missing_fields = [field for field in missing_fields if field not in population_fields]

    if exchange_rate_result is not None:
        exchange_rate_fields = {
            "origin_currency_to_usd",
            "exchange_rate_date",
            "source_fx",
        }

        if destination_currency_code.strip().upper() in exchange_rate_result.target_rates:
            exchange_rate_fields.add("origin_currency_to_destination_currency")

        missing_fields = [field for field in missing_fields if field not in exchange_rate_fields]

    return missing_fields


def build_filled_fields(
    population_result: PopulationResult | None,
    exchange_rate_result: ExchangeRateResult | None,
    destination_currency_code: str,
) -> list[str]:
    """Build the filled field list for one output row."""

    fields = SEED_FILLED_FIELDS.copy()

    if population_result is not None:
        fields.extend(POPULATION_FILLED_FIELDS)

    if exchange_rate_result is not None:
        fields.extend(
            [
                "origin_currency_to_usd",
                "exchange_rate_date",
                "source_fx",
            ]
        )

        if destination_currency_code.strip().upper() in exchange_rate_result.target_rates:
            fields.append("origin_currency_to_destination_currency")

    return fields


# -----------------------------------------------------------------------------
# ROW BUILDERS
# -----------------------------------------------------------------------------

def build_profile_row(
    origin: dict[str, str],
    destination: dict[str, str],
    target_columns: list[str],
    population_by_country_code: dict[str, PopulationResult] | None = None,
    exchange_rates_by_currency_code: dict[str, ExchangeRateResult] | None = None,
) -> dict[str, str]:
    """Build one origin country and destination country profile row."""

    country_code = origin.get("origin_iso_country_code", "").strip().upper()
    origin_currency_code = origin.get("origin_currency_code", "").strip().upper()
    destination_currency_code = destination.get("destination_currency_code", "").strip().upper()

    population_result = None
    if population_by_country_code is not None:
        population_result = population_by_country_code.get(country_code)

    exchange_rate_result = None
    if exchange_rates_by_currency_code is not None:
        exchange_rate_result = exchange_rates_by_currency_code.get(origin_currency_code)

    missing_fields = build_missing_fields(
        population_result=population_result,
        exchange_rate_result=exchange_rate_result,
        destination_currency_code=destination_currency_code,
    )
    filled_fields = build_filled_fields(
        population_result=population_result,
        exchange_rate_result=exchange_rate_result,
        destination_currency_code=destination_currency_code,
    )

    row = {
        "origin_country_slug": origin.get("origin_country_slug", ""),
        "origin_country_name": origin.get("origin_country_name", ""),
        "origin_country_name_local": origin.get("origin_country_name_local", ""),
        "origin_iso_country_code": origin.get("origin_iso_country_code", ""),
        "origin_primary_locale": origin.get("origin_primary_locale", ""),
        "origin_secondary_locales": origin.get("origin_secondary_locales", ""),
        "origin_currency_code": origin.get("origin_currency_code", ""),
        "origin_currency_to_usd": get_exchange_rate_for_target(
            exchange_rate_result=exchange_rate_result,
            target_currency_code="USD",
        ),
        "origin_currency_to_destination_currency": get_exchange_rate_for_target(
            exchange_rate_result=exchange_rate_result,
            target_currency_code=destination_currency_code,
        ),
        "exchange_rate_date": (
            exchange_rate_result.source_update_utc if exchange_rate_result else ""
        ),
        "origin_population_millions": (
            str(population_result.population_millions) if population_result else ""
        ),
        "origin_population_year": (
            str(population_result.population_year) if population_result else ""
        ),
        "destination_country_slug": destination.get("destination_country_slug", ""),
        "destination_country_name": destination.get("destination_country_name", ""),
        "destination_region": destination.get("destination_region", ""),
        "destination_currency_code": destination.get("destination_currency_code", ""),
        "estimated_annual_outbound_medical_travel": "",
        "estimated_share_to_destination_pct": "",
        "top_treatments_sought": "",
        "top_origin_cities": "",
        "destination_arrival_cities": "",
        "language_support_priority": "",
        "cultural_notes": "",
        "embassy_or_consulate_info": "",
        "source_population": build_source_population_value(population_result),
        "source_fx": build_source_fx_value(exchange_rate_result),
        "source_outbound_stats": "",
        "verified_date": "",
        "verified_by": "",
        "record_status": (
            RecordStatus.NEEDS_REVIEW.value
            if population_result or exchange_rate_result
            else RecordStatus.MISSING_SOURCE.value
        ),
        "confidence_score": "0.50"
        if population_result and exchange_rate_result
        else "0.35"
        if population_result or exchange_rate_result
        else "0.20",
        "filled_fields": ";".join(filled_fields),
        "missing_fields": ";".join(missing_fields),
        "needs_review_fields": ";".join(missing_fields),
    }

    return {column: row.get(column, "") for column in target_columns}


def build_profiles(
    origins: list[dict[str, str]],
    destinations: list[dict[str, str]],
    target_columns: list[str],
    population_by_country_code: dict[str, PopulationResult] | None = None,
    exchange_rates_by_currency_code: dict[str, ExchangeRateResult] | None = None,
) -> list[dict[str, str]]:
    """Build all origin country and destination country profile rows."""

    rows = []

    for origin in origins:
        for destination in destinations:
            rows.append(
                build_profile_row(
                    origin=origin,
                    destination=destination,
                    target_columns=target_columns,
                    population_by_country_code=population_by_country_code,
                    exchange_rates_by_currency_code=exchange_rates_by_currency_code,
                )
            )

    return rows


# -----------------------------------------------------------------------------
# ROW BUILDERS
# -----------------------------------------------------------------------------

def run_pipeline() -> dict[str, Any]:
    """Run the patient country destination profile pipeline."""

    settings = load_settings()
    context = RunContext(pipeline_name="patient_country_destination_profiles")

    origins = read_origin_countries(ORIGIN_COUNTRIES_CONFIG_PATH)
    destinations = read_destinations(DESTINATIONS_CONFIG_PATH)
    target_columns = read_target_columns(TARGET_SCHEMA_PATH)

    population_by_country_code, population_failures = fetch_population_results(
        origins=origins,
        context=context,
        timeout_seconds=settings.http_timeout_seconds,
    )
    exchange_rates_by_currency_code, exchange_rate_failures = fetch_exchange_rate_results(
        origins=origins,
        destinations=destinations,
        context=context,
        timeout_seconds=settings.http_timeout_seconds,
    )

    rows = build_profiles(
        origins=origins,
        destinations=destinations,
        target_columns=target_columns,
        population_by_country_code=population_by_country_code,
        exchange_rates_by_currency_code=exchange_rates_by_currency_code,
    )

    output_csv_path = LATEST_OUTPUT_DIR / "patient_country_destination_profiles.csv"
    output_xlsx_path = LATEST_OUTPUT_DIR / "FOR_READING_patient_country_destination_profiles.xlsx"
    summary_path = LATEST_OUTPUT_DIR / "run_summary.json"

    write_csv(output_csv_path, rows, target_columns)
    write_xlsx(output_xlsx_path, rows, target_columns)

    missing_fields_report_path = LATEST_OUTPUT_DIR / "missing_fields_report.csv"
    missing_fields_report_columns = [
        "field_name",
        "missing_row_count",
        "total_row_count",
        "missing_percentage",
    ]
    missing_fields_report_rows = build_missing_fields_report(
        rows=rows,
        target_columns=target_columns,
    )

    write_csv(
        path=missing_fields_report_path,
        rows=missing_fields_report_rows,
        columns=missing_fields_report_columns,
    )

    summary = {
        "run_id": context.run_id,
        "pipeline_name": context.pipeline_name,
        "started_at": context.started_at.isoformat(),
        "origin_country_count": len(origins),
        "destination_country_count": len(destinations),
        "output_row_count": len(rows),
        "population_enriched_country_count": len(population_by_country_code),
        "population_failed_country_count": len(population_failures),
        "population_failures": population_failures,
        "exchange_rate_enriched_currency_count": len(exchange_rates_by_currency_code),
        "exchange_rate_failed_currency_count": len(exchange_rate_failures),
        "exchange_rate_failures": exchange_rate_failures,
        "output_csv_path": str(output_csv_path.relative_to(PROJECT_ROOT)),
        "output_xlsx_path": str(output_xlsx_path.relative_to(PROJECT_ROOT)),
        "missing_fields_report_path": str(missing_fields_report_path.relative_to(PROJECT_ROOT)),
        "raw_population_dir": str(
            (RAW_DATA_ROOT / context.run_id / "world_bank_population").relative_to(
                PROJECT_ROOT
            )
        ),
        "raw_exchange_rate_dir": str(
            (RAW_DATA_ROOT / context.run_id / "exchange_rates").relative_to(PROJECT_ROOT)
        ),
        "notes": [
            "Generated origin country and destination country matrix.",
            "Filled config identity fields.",
            "Enriched origin population using World Bank SP.POP.TOTL where available.",
            "Enriched exchange rates using open.er-api.com where available.",
            "Other source-backed enrichments are intentionally not included in this slice.",
            "Missing fields are explicitly listed per row.",
        ],
    }

    write_json(summary_path, summary)

    return summary

# -----------------------------------------------------------------------------
# CLI ENTRY POINT
# -----------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for manual local runs."""

    summary = run_pipeline()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()