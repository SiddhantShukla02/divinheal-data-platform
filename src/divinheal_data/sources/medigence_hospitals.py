# -----------------------------------------------------------------------------
# MEDIGENCE HOSPITAL DISCOVERY SOURCE
# -----------------------------------------------------------------------------
# PURPOSE:
#   Fetches lightweight hospital discovery data from MediGence.
#
# INPUT:
#   - MediGence hospital listing endpoint
#
# PROCESS:
#   - Fetches paginated hospital listing responses.
#   - Extracts hospital discovery metadata from hospital cards.
#
# OUTPUT:
#   - List of lightweight hospital discovery dictionaries.
#
# NOTES:
#   - This module intentionally performs lightweight discovery only.
#   - Deep enrichment is intentionally deferred to later pipelines.
#   - Current extraction targets:
#       - hospital name
#       - city
#       - country
#       - source URL
# -----------------------------------------------------------------------------

from __future__ import annotations
# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import json
import requests
import yaml
import math
import re

from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

BASE_URL = "https://medigence.com"
LISTING_ENDPOINT = f"{BASE_URL}/clinics/all"


# -----------------------------------------------------------------------------
# CONFIG HELPERS
# -----------------------------------------------------------------------------

def load_allowed_countries() -> set[str]:
    """Load allowed destination countries from config."""

    config_path = Path("configs/hospital_discovery.yml")

    with open(config_path, "r", encoding="utf-8") as config_file:
        config_data = yaml.safe_load(config_file)

    target_countries = config_data.get(
        "target_countries",
        [],
    )

    allowed_countries = {
        country.strip().lower()
        for country in target_countries
        if country
    }

    return allowed_countries



# -----------------------------------------------------------------------------
# RESPONSE HELPERS
# -----------------------------------------------------------------------------

def extract_listing_html(payload: dict[str, Any]) -> str:
    """Extract raw hospital listing HTML from a MediGence payload."""

    body = payload.get("body", {})

    if not isinstance(body, dict):
        return ""

    message = body.get("message", {})

    if not isinstance(message, dict):
        return ""

    result = message.get("result", "")

    if not isinstance(result, str):
        return ""

    return result


def extract_total_pages(payload: dict[str, Any]) -> int:
    """Extract total listing pages from MediGence payload."""

    body = payload.get("body", {})

    if not isinstance(body, dict):
        return 1

    message = body.get("message", {})

    if not isinstance(message, dict):
        return 1

    total_records = message.get("total_records", 0)

    limit = message.get("limit", 15)

    if not isinstance(total_records, int):
        return 1

    if not isinstance(limit, int):
        return 1

    if limit <= 0:
        return 1

    total_pages = math.ceil(
        total_records / limit
    )

    return max(total_pages, 1)



# -----------------------------------------------------------------------------
# HTML PARSERS
# -----------------------------------------------------------------------------

def parse_listing_html(html: str) -> BeautifulSoup:
    """Parse MediGence listing HTML into a BeautifulSoup document."""

    return BeautifulSoup(html, "lxml")


def extract_hospital_cards(soup: BeautifulSoup) -> list[Any]:
    """Extract raw hospital card elements from a listing page."""

    return soup.select("div.hospital-card")

def extract_hospital_name(hospital_card: Any) -> str:
    """Extract hospital name from one hospital card."""

    hospital_link = hospital_card.select_one("a.hospital-title-csrp")

    if hospital_link is None:
        return ""

    hospital_name = hospital_link.get_text(strip=True)

    return hospital_name

def extract_hospital_url(hospital_card: Any) -> str:
    """Extract hospital profile URL from one hospital card."""

    hospital_link = hospital_card.select_one("a.hospital-title-csrp")

    if hospital_link is None:
        return ""

    hospital_url = hospital_link.get("href", "").strip()

    return hospital_url

def extract_hospital_location(hospital_card: Any) -> tuple[str, str]:
    """Extract hospital city and country from one hospital card."""

    location_element = hospital_card.select_one("p.fs-18.mb-0")

    if location_element is None:
        return "", ""

    location_text = location_element.get_text(strip=True)

    location_parts = [
        part.strip()
        for part in location_text.split(",")
        if part.strip()
    ]

    if len(location_parts) < 2:
        return location_text, ""

    city = location_parts[0]
    country = location_parts[-1]

    return city, country


def extract_hospital_address(
    hospital_card: Any,
) -> str:
    """Extract raw hospital address from one hospital card."""

    address_element = hospital_card.select_one(
        'meta[itemprop="address"]'
    )

    if address_element is None:
        return ""

    address = (
        address_element.get(
            "content",
            "",
        )
        .strip()
    )

    if (
        not address
        or address == "0"
    ):
        return ""

    return address


def extract_bed_count(
    hospital_card: Any,
) -> Optional[int]:
    """Extract hospital bed count."""

    bed_element = hospital_card.find(
        string=lambda text: (
            text
            and "Number of Beds" in text
        )
    )

    if bed_element is None:
        return None

    bed_span = (
        bed_element.parent.find(
            "span"
        )
    )

    if bed_span is None:
        return None

    bed_text = (
        bed_span.get_text(
            strip=True
        )
    )

    digits = "".join(
        char
        for char in bed_text
        if char.isdigit()
    )

    if not digits:
        return None

    return int(digits)


def extract_year_founded(
    hospital_card: Any,
) -> Optional[int]:
    """Extract hospital founded year."""

    year_element = hospital_card.find(
        string=lambda text: (
            text
            and "Year of Establishment"
            in text
        )
    )

    if year_element is None:
        return None

    year_span = (
        year_element.parent.find(
            "span"
        )
    )

    if year_span is None:
        return None

    year_text = (
        year_span.get_text(
            strip=True
        )
    )

    digits = "".join(
        char
        for char in year_text
        if char.isdigit()
    )

    if len(digits) != 4:
        return None

    return int(digits)


def extract_accreditations(
    hospital_card: Any,
) -> List[str]:
    """Extract hospital accreditations."""

    accreditation_meta_tags = (
        hospital_card.select(
            'ul.certify_ic meta[itemprop="name"]'
        )
    )

    accreditations = []

    for meta_tag in accreditation_meta_tags:

        accreditation_name = (
            meta_tag.get(
                "content",
                ""
            )
            .strip()
        )

        if (
            accreditation_name
            and accreditation_name
            not in accreditations
        ):
            accreditations.append(
                accreditation_name
            )

    return accreditations


def extract_hospital_data(
    hospital_card: Any,
) -> dict[str, Any]:
    """Extract structured hospital discovery data from one hospital card."""

    hospital_name = extract_hospital_name(
        hospital_card,
    )

    hospital_url = extract_hospital_url(
        hospital_card,
    )

    city, country = extract_hospital_location(
        hospital_card,
    )

    address_raw = extract_hospital_address(
        hospital_card,
    )

    bed_count = extract_bed_count(
        hospital_card,
    )

    year_founded = extract_year_founded(
            hospital_card,
    )

    accreditations = extract_accreditations(
            hospital_card,
    )

    normalized_city = normalize_city_name(
        city,
    )

    normalized_address = (
        f"{normalized_city}, "
        f"{country.strip().lower()}"
    )

    (
        city_match_status,
        _,
        _,
    ) = get_city_validation_status(
        city=city,
        address_raw=address_raw,
    )

    return {
        "record_id": None,

        "hospital_name": hospital_name,

        "location": {
            "city": city,
            "country": country,
            "address_raw": address_raw,

            "normalized_city": normalized_city,
            "normalized_address": normalized_address,
        },

        "info": {
            "bed_count": bed_count,
            "year_founded": year_founded,
            "accreditations": accreditations,
        },

        "validation": {
            "city_match_status": (
                city_match_status
            ),
        },

        "source": {
            "source_site": "medigence",
            "source_url": hospital_url,
        },
    }


def is_allowed_country(hospital_data: dict[str, str],allowed_countries: set[str]) -> bool:
    """Check whether a hospital belongs to an allowed destination country."""

    location = hospital_data.get(
        "location",
        {},
    )

    if not isinstance(location, dict):
        return False

    country = location.get(
        "country",
        "",
    )

    normalized_country = (
        country.strip()
        .lower()
        .replace("-", " ")
    )

    normalized_allowed_countries = {
        allowed_country.replace("-", " ")
        for allowed_country in allowed_countries
    }

    return (
        normalized_country
        in normalized_allowed_countries
    )


# -----------------------------------------------------------------------------
# VALIDATION HELPERS
# -----------------------------------------------------------------------------

CITY_ALIASES = {
    "bengaluru": [
        "bangalore",
        "banglore",
        "bengaluru",
    ],

    "gurugram": [
        "gurgaon",
        "gurugram",
    ],

    "kozhikode": [
        "calicut",
        "kozhikode",
    ],

    "mumbai": [
        "bombay",
        "mumbai",
    ],

    "delhi": [
        "new delhi",
        "delhi",
    ],
}

def normalize_city_name(
    city_name: str,
) -> str:
    """Convert city names into canonical validation names."""

    normalized_city = (
        city_name.strip()
        .lower()
    )

    for canonical_city, aliases in CITY_ALIASES.items():
        if normalized_city in aliases:
            return canonical_city

    return normalized_city


def address_contains_city_alias(
    canonical_city: str,
    address_text: str,
) -> bool:
    """Check whether address contains any valid city alias."""

    aliases = CITY_ALIASES.get(
        canonical_city,
        [canonical_city],
    )

    normalized_address = (
        address_text.strip()
        .lower()
    )

    for alias in aliases:
        alias_pattern = (
            rf"\b{re.escape(alias)}\b"
        )

        if re.search(
            alias_pattern,
            normalized_address,
        ):
            return True

    return False


def get_city_validation_status(
    city: str,
    address_raw: str,
) -> tuple[str, str, str]:
    """Validate whether address contains a valid city alias."""

    canonical_city = normalize_city_name(
        city,
    )

    normalized_address = (
        address_raw.strip()
        .lower()
    )

    if not normalized_address:
        return (
            "error_missing_address",
            canonical_city,
            normalized_address,
        )

    city_found = address_contains_city_alias(
        canonical_city=canonical_city,
        address_text=normalized_address,
    )

    if city_found:
        return (
            "city_verified",
            canonical_city,
            normalized_address,
        )

    return (
        "error_city_mismatch",
        canonical_city,
        normalized_address,
    )


# -----------------------------------------------------------------------------
# SOURCE FETCHERS
# -----------------------------------------------------------------------------

def fetch_listing_page(page: int) -> dict[str, Any]:
    """Fetch one MediGence hospital listing page."""

    response = requests.get(
        LISTING_ENDPOINT,
        params={"page": page},
        headers={
            "Accept": "*/*",
            "Referer": LISTING_ENDPOINT,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30,
    )

    response.raise_for_status()

    payload: dict[str, Any] = response.json()

    return payload


# -----------------------------------------------------------------------------
# MAIN EXECUTION
# -----------------------------------------------------------------------------

def main() -> None:
    """Run MediGence hospital discovery extraction."""

    payload = fetch_listing_page(page=1)
    print(
        json.dumps(
            payload,
            indent=4,
            ensure_ascii=False,
        )[:15000]
    )

    total_pages = extract_total_pages(payload)

    print(f"Total pages found: {total_pages}")    

    allowed_countries = load_allowed_countries()

    hospitals_data = []

    for page in range(1, total_pages + 1):
        print(f"Fetching page {page}/{total_pages}")

        payload = fetch_listing_page(page=page)

        html = extract_listing_html(payload)

        soup = parse_listing_html(html)

        hospital_cards = extract_hospital_cards(soup)

        for hospital_card in hospital_cards:
            hospital_data = extract_hospital_data(
                hospital_card,
            )

            if not is_allowed_country(
                hospital_data,
                allowed_countries,
            ):
                continue

            hospitals_data.append(hospital_data)

    hospitals_data.sort(
        key=lambda hospital: (
            hospital["location"]["country"],
            hospital["location"]["city"],
            hospital["hospital_name"],
        ),
    )

    for record_id, hospital_data in enumerate(
        hospitals_data,
        start=1,
    ):
        hospital_data["record_id"] = record_id

    output_dir = Path("outputs/raw")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "medigence_hospitals.json"

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(
            hospitals_data,
            output_file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Saved {len(hospitals_data)} hospitals to {output_path}")


if __name__ == "__main__":
    main()