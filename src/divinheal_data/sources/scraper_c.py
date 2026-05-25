from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
)


# =========================================================
# CONFIG
# =========================================================

BASE_URL = (
    "https://curemeabroad.com/hospitals"
)

SOURCE_NAME = (
    "curemeabroad"
)

OUTPUT_PATH = Path(
    "outputs/curemeabroad_hospitals.json"
)


# =========================================================
# BROWSER HELPERS
# =========================================================

def launch_browser(
    playwright,
):

    return playwright.chromium.launch(
        headless=False,
    )


def load_hospitals_page(
    page,
) -> None:

    page.goto(
        BASE_URL,
        wait_until="networkidle",
    )


def scroll_until_complete(
    page,
) -> None:

    previous_card_count = 0

    while True:

        page.mouse.wheel(
            0,
            10000,
        )

        page.wait_for_timeout(
            2000,
        )

        cards = extract_hospital_cards(
            page,
        )

        current_card_count = len(
            cards
        )

        print(
            f"Loaded {current_card_count} cards"
        )

        if (
            current_card_count
            == previous_card_count
        ):

            break

        previous_card_count = (
            current_card_count
        )


# =========================================================
# LISTING EXTRACTION
# =========================================================

def extract_hospital_cards(
    page,
):

    return page.query_selector_all(
        'a.block[href^="/hospitals/"]'
    )


def extract_hospital_name(
    card,
) -> str:

    hospital_name_element = (
        card.query_selector(
            "h3"
        )
    )

    if not hospital_name_element:

        return ""

    return (
        hospital_name_element.inner_text()
        .strip()
    )


def extract_description_raw(
    card,
) -> str:

    description_element = (
        card.query_selector(
            "p"
        )
    )

    if not description_element:

        return ""

    return (
        description_element.inner_text()
        .strip()
    )


def extract_source_url(
    card,
) -> str:

    hospital_url = card.get_attribute(
        "href"
    )

    if not hospital_url:

        return ""

    return (
        f"https://curemeabroad.com{hospital_url}"
    )


def build_listing_data(
    card,
):

    hospital_name = (
        extract_hospital_name(
            card,
        )
    )

    description_raw = (
        extract_description_raw(
            card,
        )
    )

    source_url = (
        extract_source_url(
            card,
        )
    )

    return {
        "hospital_name": hospital_name,

        "description_raw": (
            description_raw
        ),

        "source": {
            "source_name": (
                SOURCE_NAME
            ),

            "source_url": (
                source_url
            ),
        },
    }


# =========================================================
# DETAIL PAGE EXTRACTION
# =========================================================

def open_detail_page(
    browser,
    source_url: str,
):

    detail_page = browser.new_page()

    detail_page.goto(
        source_url,
        wait_until="domcontentloaded",
    )

    return detail_page


def extract_location(
    detail_page,
) -> str or None:

    location_container = (
        detail_page.query_selector(
            'div.flex.md\\:items-center.gap-1'
        )
    )

    if not location_container:
        return None 

    address_element = (
        location_container.query_selector(
            'h4'
        )
    )

    if not address_element:
        return None

    address_raw = address_element.inner_text()

    if not address_raw:
        return None

    print(address_raw) if address_raw else print("error , container not found")

    return address_raw


def extract_payment_methods(
    detail_page,
):

    payment_methods = []

    payment_heading = (
        detail_page.query_selector(
            'h3:text("Payment Method")'
        )
    )

    if not payment_heading:

        return payment_methods

    payment_container = (
        payment_heading.evaluate_handle(
            """
            element => element.nextElementSibling
            """
        )
    )

    payment_elements = (
        payment_container.query_selector_all(
            "span"
        )
    )

    for element in payment_elements:

        payment_text = (
            element.inner_text()
            .strip()
        )

        if not payment_text:

            continue

        payment_methods.append(
            payment_text
        )

    return payment_methods


def extract_accessibility_features(
    detail_page,
):

    accessibility_features = []

    accessibility_heading = (
        detail_page.query_selector(
            'h3:text("Accessibility Features")'
        )
    )

    if not accessibility_heading:

        return accessibility_features

    accessibility_container = (
        accessibility_heading.evaluate_handle(
            """
            element => element.nextElementSibling
            """
        )
    )

    accessibility_elements = (
        accessibility_container.query_selector_all(
            "span"
        )
    )

    for element in accessibility_elements:

        accessibility_text = (
            element.inner_text()
            .strip()
        )

        if not accessibility_text:

            continue

        accessibility_features.append(
            accessibility_text
        )

    return accessibility_features


def extract_highlights(
    detail_page,
):

    highlights = []

    highlights_heading = (
        detail_page.query_selector(
            'h3:text("Highlights")'
        )
    )

    if not highlights_heading:

        return highlights

    highlights_container = (
        highlights_heading.evaluate_handle(
            """
            element => element.nextElementSibling
            """
        )
    )

    highlight_elements = (
        highlights_container.query_selector_all(
            "span"
        )
    )

    for element in highlight_elements:

        highlight_text = (
            element.inner_text()
            .strip()
        )

        if not highlight_text:

            continue

        highlights.append(
            highlight_text
        )

    return highlights


def extract_room_types(
    detail_page,
):

    room_types = []

    room_types_heading = (
        detail_page.query_selector(
            'h3:text("Room Types")'
        )
    )

    if not room_types_heading:

        return room_types

    room_types_container = (
        room_types_heading.evaluate_handle(
            """
            element => element.nextElementSibling
            """
        )
    )

    room_type_elements = (
        room_types_container.query_selector_all(
            "span"
        )
    )

    for element in room_type_elements:

        room_type_text = (
            element.inner_text()
            .strip()
        )

        if not room_type_text:

            continue

        room_types.append(
            room_type_text
        )

    return room_types


def extract_accreditations(
    detail_page,
):

    return []


def extract_address_raw(
    detail_page,
) -> str:

    return ""


# =========================================================
# TRANSFORMATION
# =========================================================

def build_hospital_data(
    listing_data,
    detail_data=None,
):

    return {
        **listing_data,
    }


# =========================================================
# PERSISTENCE
# =========================================================

def save_json(
    hospitals,
) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        str(hospitals),
        encoding="utf-8",
    )


# =========================================================
# ORCHESTRATION
# =========================================================

def main():

    with sync_playwright() as playwright:

        browser = launch_browser(
            playwright,
        )

        page = browser.new_page()

        load_hospitals_page(
            page,
        )

        scroll_until_complete(
            page,
        )

        cards = extract_hospital_cards(
            page,
        )

        print(
            f"Found {len(cards)} hospital cards"
        )

        hospitals = []

        for card in cards[:1]:

            listing_data = (
                build_listing_data(
                    card,
                )
            )

            detail_page = (
                open_detail_page(
                    browser,
                    listing_data[
                        "source"
                    ][
                        "source_url"
                    ],
                )
            )

            extract_location(
                detail_page,
            )

            payment_methods = (
                extract_payment_methods(
                    detail_page,
                )
            )

            accessibility_features = (
                extract_accessibility_features(
                    detail_page,
                )
            )

            highlights = (
                extract_highlights(
                    detail_page,
                )
            )

            room_types = (
                extract_room_types(
                    detail_page,
                )
            )

            print(
                payment_methods
            )

            print(
                accessibility_features
            )

            print(
                highlights
            )

            print(
                room_types
            )

            detail_page.close()

            hospitals.append(
                listing_data,
            )

        print(
            f"\nExtracted {len(hospitals)} hospitals"
        )

        print(
            hospitals[0]
        )

        input(
            "\nPress ENTER to close browser..."
        )

        browser.close()


if __name__ == "__main__":

    main()