import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import time
import asyncio
import aiohttp

# =========================================================
# CONFIG
# =========================================================


BASE_URL = (
    "https://www.vaidam.com/hospitals/{country}?page={page}"
)

country_list = [
    "india",
    "germany",
    "turkey",
    "united-arab-emirates",
    "tunisia",
    "south-korea",
    "egypt",
    "spain",
    "france",
    "malaysia",
    "thailand",
    "cyprus",
    "south-africa",
    "singapore",
    "israel",
    "czech-republic",
    "austria",
    "poland",
    "switzerland",
] 

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


# =========================================================
# FETCHING
# =========================================================

async def fetch_listing_page(
    session: aiohttp.ClientSession,
    page: int,
    country: str,
) -> BeautifulSoup:

    async with session.get(
        BASE_URL.format(page=page, country=country),
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        response.raise_for_status()
        html = await response.text()
        return BeautifulSoup(html, "html.parser")


async def fetch_detail_page(
    session: aiohttp.ClientSession,
    source_url: str,
) -> BeautifulSoup:

    async with session.get(
        source_url,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        response.raise_for_status()
        html = await response.text()
        return BeautifulSoup(html, "html.parser")


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


def extract_image_urls(
    detail_soup: BeautifulSoup,
) -> list:

    image_section = detail_soup.select_one(
        "div.hos-img-statics"
    )

    if not image_section:
        return []

    images = image_section.select(
        "img.hospital-pic"
    )

    return [
        img.get("src", "")
        for img in images
        if img.get("src", "")
    ]


def extract_treatments(detail_soup: BeautifulSoup) -> list:

    accordion = detail_soup.select_one("div#acrdnDrDepart")

    if not accordion:
        return []

    treatments = []

    for anchor in accordion.select("div.accordion-header a[title]"):

        title = anchor.get("title", "").strip()

        if title:
            treatments.append(title.title())  # "CARDIOLOGY AND CARDIAC SURGERY" → "Cardiology And Cardiac Surgery"

    return list(dict.fromkeys(treatments))  # dedupe


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
    overview_raw: str,
    infrastructure_raw: str,
    image_urls,
    treatments,
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

        "image_urls": image_urls,

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

        "treatments": treatments if treatments else [],

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
    output_path: Path, 
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
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

async def main() -> None:

    all_hospitals = []
    OUTPUT_PATH = Path("outputs/raw/vaidam_hospitals.json")

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        for country in country_list:

            try:

                hospital_count_tracker = len(all_hospitals)

                first_page_soup = await fetch_listing_page(session, page=1, country=country)
                await asyncio.sleep(1)

                total_pages = extract_total_pages(first_page_soup)

                print(f"Working on {country} now...")
                print(f"Detected {total_pages} total pages")

                for page in range(1, total_pages + 1):

                    print(f"Fetching page {page}/{total_pages}    |   For country {country}")

                    if page == 1:
                        soup = first_page_soup
                    else:
                        soup = await fetch_listing_page(session, page=page, country=country)
                        await asyncio.sleep(1)

                    cards = extract_hospital_cards(soup)

                    if not cards:
                        print(f"No cards found on page {page}")
                        break

                    # Step 1 — extract card metadata synchronously (just BS4 parsing, fast)
                    card_data_list = []
                    for card in cards:
                        location_data = extract_location(card)
                        card_data_list.append({
                            "location_data": location_data,
                            "hospital_name": extract_hospital_name(card, city=location_data["city"]),
                            "source_url": extract_source_url(card),
                            "established_year": extract_established_year(card),
                            "bed_count": extract_bed_count(card),
                        })

                    # Step 2 — fetch all detail pages on this page concurrently
                    detail_results = await asyncio.gather(
                        *[fetch_detail_page(session, c["source_url"]) for c in card_data_list],
                        return_exceptions=True,
                    )

                    # Step 3 — process each result
                    for card_data, detail_result in zip(card_data_list, detail_results):

                        try:

                            if isinstance(detail_result, Exception):
                                print(f"Failed hospital: {detail_result}")
                                continue

                            detail_soup = detail_result

                            hospital_data = build_hospital_data(
                                hospital_name=card_data["hospital_name"],
                                source_url=card_data["source_url"],
                                established_year=card_data["established_year"],
                                bed_count=card_data["bed_count"],
                                location_data=card_data["location_data"],
                                raw_address=extract_raw_address(detail_soup),
                                accreditations=extract_accreditations(detail_soup),
                                overview_raw=extract_overview_raw(detail_soup),
                                infrastructure_raw=extract_infrastructure_raw(detail_soup),
                                image_urls=extract_image_urls(detail_soup),
                                treatments=extract_treatments(detail_soup),
                            )

                            hospital_data = {"record_id": len(all_hospitals) + 1, **hospital_data}
                            all_hospitals.append(hospital_data)

                            if len(all_hospitals) % 50 == 0:
                                save_checkpoint(all_hospitals, OUTPUT_PATH)
                                print(f"Checkpoint saved after {len(all_hospitals)} hospitals")

                        except Exception as error:
                            print(f"Failed hospital: {error}")
                            continue

            except Exception as country_error:
                print(f"COUNTRY FAILED — {country}: {country_error}")
                save_checkpoint(all_hospitals, OUTPUT_PATH)
                print(f"Emergency checkpoint saved with {len(all_hospitals)} hospitals")
                continue

            save_checkpoint(all_hospitals, OUTPUT_PATH)
            print(f"Saved {len(all_hospitals) - hospital_count_tracker} hospitals from {country}")
            print("\n Switching to next country now.\n\n")

        print(f"Extraction Finished   -   {len(all_hospitals)} Hospitals extracted in total")


if __name__ == "__main__":
    asyncio.run(main())
