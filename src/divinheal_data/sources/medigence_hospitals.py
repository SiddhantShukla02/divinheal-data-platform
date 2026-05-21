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

from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

BASE_URL = "https://medigence.com"
LISTING_ENDPOINT = f"{BASE_URL}/clinics/all"


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

def extract_hospital_address(hospital_card: Any) -> str:
    """Extract raw hospital address from one hospital card."""

    address_meta = hospital_card.select_one('meta[itemprop="address"]')

    if address_meta is None:
        return ""

    address = address_meta.get("content", "").strip()

    return address

def extract_hospital_data(hospital_card: Any) -> dict[str, str]:
    """Extract structured hospital discovery data from one hospital card."""

    hospital_name = extract_hospital_name(hospital_card)

    hospital_url = extract_hospital_url(hospital_card)

    city, country = extract_hospital_location(hospital_card)

    address_raw = extract_hospital_address(hospital_card)

    return {
        "hospital_name": hospital_name,
        "source_url": hospital_url,
        "city": city,
        "country": country,
        "address_raw": address_raw,
        "source_site": "medigence",
    }



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

if __name__ == "__main__":
    payload = fetch_listing_page(page=1)

    html = extract_listing_html(payload)

    soup = parse_listing_html(html)

    hospital_cards = extract_hospital_cards(soup)

    hospitals_data = [
        extract_hospital_data(hospital_card)
        for hospital_card in hospital_cards
    ]

    output_dir = Path("outputs/raw")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "medigence_hospitals_page_1.json"

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(
            hospitals_data,
            output_file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Saved {len(hospitals_data)} hospitals to {output_path}")