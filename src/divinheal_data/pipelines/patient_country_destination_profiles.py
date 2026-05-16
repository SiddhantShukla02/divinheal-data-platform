# -----------------------------------------------------------------------------
# PATIENT COUNTRY DESTINATION PROFILE PIPELINE
# -----------------------------------------------------------------------------
# PURPOSE:
#   Generates the first multi-destination patient-country profile output.
#
# INPUT:
#   - configs/origin_countries.yml
#   - configs/destinations.yml
#   - schemas/target/patient_country_destination_profiles.csv
#
# PROCESS:
#   - Loads origin/patient countries from config.
#   - Loads destination countries from config.
#   - Creates one row for each origin country and destination country pair.
#   - Fills only safe config identity fields.
#   - Leaves unsourced research/enrichment fields blank.
#   - Marks missing/source-required fields explicitly.
#   - Writes a human-facing CSV and run summary under outputs/.
#
# OUTPUT:
#   - outputs/patient_country_destination_profiles/latest/
#       - patient_country_destination_profiles.csv
#       - run_summary.json
#
# NOTES:
#   - This is a matrix-generation slice, not a fully enriched data pipeline.
#   - This module does not fetch World Bank, FX, visa, hospital, or embassy data.
#   - Do not add guessed/manual/fake values here. Add source adapters later.
# -----------------------------------------------------------------------------

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from divinheal_data.core.run_context import RunContext
from divinheal_data.core.statuses import RecordStatus


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ORIGIN_COUNTRIES_CONFIG_PATH = PROJECT_ROOT / "configs/origin_countries.yml"
DESTINATIONS_CONFIG_PATH = PROJECT_ROOT / "configs/destinations.yml"
TARGET_SCHEMA_PATH = PROJECT_ROOT / "schemas/target/patient_country_destination_profiles.csv"

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


SOURCE_REQUIRED_FIELDS = [
    "origin_currency_to_usd",
    "origin_population_millions",
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


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    """Write rows to CSV using the target schema column order."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON file with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def build_profile_row(
    origin: dict[str, str],
    destination: dict[str, str],
    target_columns: list[str],
) -> dict[str, str]:
    """Build one origin country and destination country profile row."""

    row = {
        "origin_country_slug": origin.get("origin_country_slug", ""),
        "origin_country_name": origin.get("origin_country_name", ""),
        "origin_country_name_local": origin.get("origin_country_name_local", ""),
        "origin_iso_country_code": origin.get("origin_iso_country_code", ""),
        "origin_primary_locale": origin.get("origin_primary_locale", ""),
        "origin_secondary_locales": origin.get("origin_secondary_locales", ""),
        "origin_currency_code": origin.get("origin_currency_code", ""),
        "origin_currency_to_usd": "",
        "origin_population_millions": "",
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
        "source_population": "",
        "source_fx": "",
        "source_outbound_stats": "",
        "verified_date": "",
        "verified_by": "",
        "record_status": RecordStatus.MISSING_SOURCE.value,
        "confidence_score": "0.20",
        "filled_fields": ";".join(SEED_FILLED_FIELDS),
        "missing_fields": ";".join(SOURCE_REQUIRED_FIELDS),
        "needs_review_fields": ";".join(SOURCE_REQUIRED_FIELDS),
    }

    return {column: row.get(column, "") for column in target_columns}


def build_profiles(
    origins: list[dict[str, str]],
    destinations: list[dict[str, str]],
    target_columns: list[str],
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
                )
            )

    return rows


def run_pipeline() -> dict[str, Any]:
    """Run the patient country destination profile pipeline."""

    context = RunContext(pipeline_name="patient_country_destination_profiles")

    origins = read_origin_countries(ORIGIN_COUNTRIES_CONFIG_PATH)
    destinations = read_destinations(DESTINATIONS_CONFIG_PATH)
    target_columns = read_target_columns(TARGET_SCHEMA_PATH)

    rows = build_profiles(
        origins=origins,
        destinations=destinations,
        target_columns=target_columns,
    )

    output_csv_path = LATEST_OUTPUT_DIR / "patient_country_destination_profiles.csv"
    summary_path = LATEST_OUTPUT_DIR / "run_summary.json"

    write_csv(output_csv_path, rows, target_columns)

    summary = {
        "run_id": context.run_id,
        "pipeline_name": context.pipeline_name,
        "started_at": context.started_at.isoformat(),
        "origin_country_count": len(origins),
        "destination_country_count": len(destinations),
        "output_row_count": len(rows),
        "output_csv_path": str(output_csv_path.relative_to(PROJECT_ROOT)),
        "record_status": RecordStatus.MISSING_SOURCE.value,
        "notes": [
            "Generated origin country and destination country matrix.",
            "Filled only config identity fields.",
            "Source-backed enrichment is intentionally not included in this slice.",
            "Missing fields are explicitly listed per row.",
        ],
    }

    write_json(summary_path, summary)

    return summary


def main() -> None:
    """CLI entry point for manual local runs."""

    summary = run_pipeline()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()