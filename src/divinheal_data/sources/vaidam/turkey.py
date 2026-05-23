import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

BASE_URL = (
    "https://www.vaidam.com/hospitals/turkey?page={page}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0"
    ),
}


# =========================================================
# FETCHING
# =========================================================

def fetch_listing_page(
    page: int,
) -> BeautifulSoup:

    response = requests.get(
        BASE_URL.format(
            page=page,
        ),
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def fetch_detail_page(
    source_url: str,
) -> BeautifulSoup:

    response = requests.get(
        source_url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


# =========================================================
# EXTRACTION
# =========================================================

def extract_hospital_cards(
    soup: BeautifulSoup,
):

    cards = soup.select(
        "div.dr-card-main"
    )

    return cards


def extract_total_pages(
    soup: BeautifulSoup,
) -> int:

    last_page_anchor = soup.select_one(
        'ul.pagination li:last-child a'
    )

    if not last_page_anchor:

        return 1

    last_page_href = (
        last_page_anchor.get(
            "href",
            "",
        )
    )

    if "?page=" not in last_page_href:

        return 1

    try:

        return int(
            last_page_href.split(
                "?page="
            )[-1]
        )

    except ValueError:

        return 1


def extract_hospital_name(
    hospital_card,
    city: str,
) -> str:

    hospital_anchor = hospital_card.select_one(
        "a.text-dark"
    )

    if not hospital_anchor:

        return ""

    hospital_name = (
        hospital_anchor.get_text(
            strip=True,
        )
    )

    city_suffix = (
        f", {city}"
    )

    if hospital_name.endswith(
        city_suffix
    ):

        hospital_name = (
            hospital_name.removesuffix(
                city_suffix
            )
        )

    return hospital_name.strip()


def extract_source_url(
    hospital_card,
) -> str:

    hospital_anchor = hospital_card.select_one(
        "a.text-dark"
    )

    if not hospital_anchor:

        return ""

    return hospital_anchor.get(
        "href",
        "",
    )


def extract_established_year(
    hospital_card,
) -> str:

    feature_rows = hospital_card.select(
        "div.features-box p"
    )

    for row in feature_rows:

        row_text = row.get_text(
            " ",
            strip=True,
        )

        if "Established" in row_text:

            return (
                row_text
                .replace(
                    "Established in:",
                    "",
                )
                .strip()
            )

    return ""


def extract_bed_count(
    hospital_card,
) -> str:

    feature_rows = hospital_card.select(
        "div.features-box p"
    )

    for row in feature_rows:

        row_text = row.get_text(
            " ",
            strip=True,
        )

        if "Number of Beds" in row_text:

            return (
                row_text
                .replace(
                    "Number of Beds:",
                    "",
                )
                .strip()
            )

    return ""


def extract_location(
    hospital_card,
):

    feature_rows = hospital_card.select(
        "div.features-box p"
    )

    for row in feature_rows:

        row_text = row.get_text(
            " ",
            strip=True,
        )

        if "Location:" in row_text:

            cleaned_location = (
                row_text
                .replace(
                    "Location:",
                    "",
                )
                .strip()
            )

            location_parts = [
                part.strip()
                for part in cleaned_location.split(
                    ","
                )
            ]

            if len(location_parts) >= 2:

                country = location_parts[0]

                city = location_parts[1]

                return {
                    "city": city,
                    "country": country,
                }

            return {
                "city": "",
                "country": "",
            }

    return {
        "city": "",
        "country": "",
    }


def extract_raw_address(
    detail_soup: BeautifulSoup,
) -> str:

    location_column = detail_soup.select_one(
        "div.location-column"
    )

    if not location_column:

        return ""

    address_lines = [
        line.get_text(
            strip=True,
        )
        for line in location_column.select(
            "p"
        )
    ]

    cleaned_lines = [
        line
        for line in address_lines
        if line
    ]

    return ", ".join(
        cleaned_lines
    )


# =========================================================
# TRANSFORMATION
# =========================================================

def build_hospital_data(
    hospital_name: str,
    source_url: str,
    established_year: str,
    bed_count: str,
    location_data,
    raw_address: str,
):

    validation_errors = []

    if not hospital_name:

        validation_errors.append(
            "ERROR_MISSING_HOSPITAL_NAME"
        )

    if not bed_count:

        validation_errors.append(
            "ERROR_MISSING_BED_COUNT"
        )

    if not established_year:

        validation_errors.append(
            "ERROR_MISSING_ESTABLISHED_YEAR"
        )

    validation_status = (
        "VALID"
        if not validation_errors
        else ", ".join(
            validation_errors
        )
    )

    return {
        "hospital_name": hospital_name,
        "normalized_location": {
            "city": location_data[
                "city"
            ],
            "country": location_data[
                "country"
            ],
        },
        "details": {
            "established_year": established_year,
            "bed_count": bed_count,
            "raw_address": raw_address,
        },
        "source": {
            "source_name": "vaidam",
            "source_url": source_url,
        },
        "validation": {
            "status": validation_status,
        },
    }


# =========================================================
# ORCHESTRATION
# =========================================================

def main() -> None:

    all_hospitals = []

    output_path = Path(
        "outputs/vaidam_scraper_turkey.json"
    )

    first_page_soup = fetch_listing_page(
        page=1,
    )

    total_pages = extract_total_pages(
        first_page_soup,
    )

    print(
        f"Detected {total_pages} total pages"
    )

    for page in range(
        1,
        total_pages + 1,
    ):

        print(
            f"Fetching page {page}/{total_pages}"
        )

        if page == 1:

            soup = first_page_soup

        else:

            soup = fetch_listing_page(
                page=page,
            )

        cards = extract_hospital_cards(
            soup,
        )

        if not cards:

            print(
                f"No cards found on page {page}. Stopping pagination."
            )

            break

        for card in cards:

            try:

                location_data = extract_location(
                    card,
                )

                hospital_name = (
                    extract_hospital_name(
                        card,
                        city=location_data[
                            "city"
                        ],
                    )
                )

                source_url = extract_source_url(
                    card,
                )

                established_year = (
                    extract_established_year(
                        card,
                    )
                )

                bed_count = extract_bed_count(
                    card,
                )

                detail_soup = fetch_detail_page(
                    source_url,
                )

                raw_address = (
                    extract_raw_address(
                        detail_soup,
                    )
                )

                hospital_data = (
                    build_hospital_data(
                        hospital_name=hospital_name,
                        source_url=source_url,
                        established_year=established_year,
                        bed_count=bed_count,
                        location_data=location_data,
                        raw_address=raw_address,
                    )
                )

                all_hospitals.append(
                    hospital_data
                )

                if len(
                    all_hospitals
                ) % 50 == 0:

                    output_path.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    output_path.write_text(
                        json.dumps(
                            all_hospitals,
                            indent=4,
                        ),
                        encoding="utf-8",
                    )

                    print(
                        f"Checkpoint saved after {len(all_hospitals)} hospitals"
                    )

            except Exception as error:

                print(
                    f"Failed hospital: {error}"
                )

                continue

    for index, hospital in enumerate(
        all_hospitals,
        start=1,
    ):

        reordered_hospital = {
            "record_id": index,
            **hospital,
        }

        all_hospitals[
            index - 1
        ] = reordered_hospital

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            all_hospitals,
            indent=4,
        ),
        encoding="utf-8",
    )

    print(
        f"Saved {len(all_hospitals)} hospitals to {output_path}"
    )


if __name__ == "__main__":

    main()