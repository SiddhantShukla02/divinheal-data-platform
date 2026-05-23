import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

BASE_URL = (
    "https://www.vaidam.com/hospitals/india?page={page}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0"
    ),
}

OUTPUT_PATH = Path(
    "outputs/vaidam_scraper_india.json"
)


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
# LISTING EXTRACTION
# =========================================================

def extract_hospital_cards(
    soup: BeautifulSoup,
):

    return soup.select(
        "div.dr-card-main"
    )


def extract_total_pages(
    soup: BeautifulSoup,
) -> int:

    last_page_anchor = soup.select_one(
        "ul.pagination li:last-child a"
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

                return {
                    "country": location_parts[0],
                    "city": location_parts[1],
                }

    return {
        "country": "",
        "city": "",
    }


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


# =========================================================
# DETAIL PAGE EXTRACTION
# =========================================================

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


def extract_accreditations(
    detail_soup: BeautifulSoup,
):

    accreditation_images = detail_soup.select(
        "img[alt]"
    )

    accreditations = []

    known_accreditations = [
        "JCI",
        "NABH",
        "NABL",
        "ISO",
    ]

    for image in accreditation_images:

        alt_text = image.get(
            "alt",
            "",
        ).strip()

        if not alt_text:

            continue

        for accreditation in known_accreditations:

            if accreditation.lower() in (
                alt_text.lower()
            ):

                if accreditation not in accreditations:

                    accreditations.append(
                        accreditation
                    )

    return accreditations


def extract_specialties(
    detail_soup: BeautifulSoup,
):

    specialties = []

    specialty_section = detail_soup.select_one(
        "div#speciality"
    )

    if not specialty_section:

        specialty_section = detail_soup.find(
            string=lambda text:
            text
            and "Specialities" in text
        )

        if specialty_section:

            specialty_section = (
                specialty_section.find_parent()
            )

    if not specialty_section:

        return []

    specialty_items = (
        specialty_section.find_all(
            [
                "li",
                "a",
            ]
        )
    )

    for item in specialty_items:

        specialty = item.get_text(
            " ",
            strip=True,
        )

        if not specialty:

            continue

        if len(
            specialty
        ) > 100:

            continue

        specialties.append(
            specialty
        )

    return list(
        dict.fromkeys(
            specialties
        )
    )


def extract_overview_raw(
    detail_soup: BeautifulSoup,
) -> str:

    about_section = detail_soup.find(
        string=lambda text:
        text
        and "About Hospital" in text
    )

    if not about_section:

        return ""

    parent = about_section.find_parent()

    if not parent:

        return ""

    paragraph_tags = parent.find_all_next(
        "p",
        limit=5,
    )

    overview_parts = []

    for paragraph in paragraph_tags:

        paragraph_text = (
            paragraph.get_text(
                " ",
                strip=True,
            )
        )

        if paragraph_text:

            overview_parts.append(
                paragraph_text
            )

    return "\n".join(
        overview_parts
    )


def extract_infrastructure_raw(
    detail_soup: BeautifulSoup,
) -> str:

    infrastructure_section = detail_soup.find(
        string=lambda text:
        text
        and "Infrastructure" in text
    )

    if not infrastructure_section:

        return ""

    parent = infrastructure_section.find_parent()

    if not parent:

        return ""

    paragraph_tags = parent.find_all_next(
        [
            "p",
            "li",
        ],
        limit=20,
    )

    infrastructure_parts = []

    for item in paragraph_tags:

        item_text = item.get_text(
            " ",
            strip=True,
        )

        if item_text:

            infrastructure_parts.append(
                item_text
            )

    return "\n".join(
        infrastructure_parts
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
    accreditations,
    specialties,
    overview_raw: str,
    infrastructure_raw: str,
):

    validation_errors = []

    if not hospital_name:

        validation_errors.append(
            "ERROR_MISSING_HOSPITAL_NAME"
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

        "location": {
            "city": location_data.get(
                "city",
                "",
            ),
            "country": location_data.get(
                "country",
                "",
            ),
            "address_raw": raw_address,
        },

        "info": {
            "bed_count": bed_count,
            "year_founded": established_year,
            "accreditations": (
                accreditations
                if accreditations
                else []
            ),
        },

        "specialties": (
            specialties
            if specialties
            else []
        ),

        "details": {
            "overview_raw": overview_raw,

            "infrastructure_raw": (
                infrastructure_raw
            ),
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
# UTILITIES
# =========================================================

def save_checkpoint(
    hospitals,
) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            hospitals,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# =========================================================
# ORCHESTRATION
# =========================================================

def main() -> None:

    all_hospitals = []

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
        # total_pages + 1,
        2
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
                f"No cards found on page {page}"
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

                accreditations = (
                    extract_accreditations(
                        detail_soup,
                    )
                )

                specialties = (
                    extract_specialties(
                        detail_soup,
                    )
                )

                overview_raw = (
                    extract_overview_raw(
                        detail_soup,
                    )
                )

                infrastructure_raw = (
                    extract_infrastructure_raw(
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
                        accreditations=accreditations,
                        specialties=specialties,
                        overview_raw=overview_raw,
                        infrastructure_raw=infrastructure_raw,
                    )
                )

                all_hospitals.append(
                    hospital_data
                )

                if len(
                    all_hospitals
                ) % 50 == 0:

                    save_checkpoint(
                        all_hospitals,
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

        all_hospitals[
            index - 1
        ] = {
            "record_id": index,
            **hospital,
        }

    save_checkpoint(
        all_hospitals,
    )

    print(
        f"Saved {len(all_hospitals)} hospitals to {OUTPUT_PATH}"
    )


if __name__ == "__main__":

    main()