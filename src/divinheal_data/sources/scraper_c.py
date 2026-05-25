import json

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

OUTPUT_PATH = Path(
    "outputs/raw/curemeabroad_hospitals.json"
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
        wait_until="domcontentloaded",
    )

    page.wait_for_selector(
        'a.block[href^="/hospitals/"]'
    )

    dismiss_listing_popups(
        page,
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

        if (
            current_card_count
            == previous_card_count
        ):

            break

        previous_card_count = (
            current_card_count
        )

    print(f"Loaded {current_card_count} cards")


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

        "source_url": source_url,
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

    return address_raw


def extract_image_urls(
    detail_page,
    source_url,
):

    image_urls = []

    gallery_trigger = (
        detail_page.query_selector(
            'div.mb-3.md\\:mb-6 div.cursor-pointer'
        )
    )

    if not gallery_trigger:

        print(
            f"Gallery trigger not found: {source_url}"
        )

        return image_urls

    gallery_trigger.scroll_into_view_if_needed()

    detail_page.wait_for_timeout(
        1000
    )

    gallery_trigger.click(
        force=True
    )

    try:

        detail_page.wait_for_selector(
            'div.overflow-x-auto',
            timeout=5000,
        )

    except:

        expand_gallery_button = (
            detail_page.query_selector(
                'text="+'
            )
        )

        if expand_gallery_button:

            expand_gallery_button.scroll_into_view_if_needed()

            detail_page.wait_for_timeout(
                1000
            )

            expand_gallery_button.click(
                force=True
            )

            try:

                detail_page.wait_for_selector(
                    'div.overflow-x-auto',
                    timeout=5000,
                )

            except:

                print(
                    f"Gallery strip failed to open: {source_url}"
                )

                return image_urls

        else:

            print(
                f"Expand gallery button not found: {source_url}"
            )

            return image_urls

    detail_page.wait_for_timeout(
        1000
    )

    image_elements = (
        detail_page.query_selector_all(
            'div.overflow-x-auto img'
        )
    )

    print(
        f"Found {len(image_elements)} image elements"
    )

    for image_element in image_elements:

        image_url = (
            image_element.get_attribute(
                "src"
            )
            or image_element.get_attribute(
                "data-src"
            )
        )

        if not image_url:

            continue

        if image_url.startswith(
            "/"
        ):

            image_url = (
                "https://curemeabroad.com"
                + image_url
            )

        image_url = image_url.split(
            "&w=",
            1,
        )[0]

        if image_url in image_urls:

            continue

        image_urls.append(
            image_url
        )

    if not image_urls:

        print(
            f"Image extraction failed: {source_url}"
        )

    return image_urls


# =========================================================
# PARSING
# =========================================================

def parse_highlights(
    highlights
):  

    parsed_highlights = {}

    for highlight in highlights:
        if ":" in highlight:

            label, value = highlight.split(":")

            label = label.strip().lower()
            value = value.strip()

            if label == "bed count":
                parsed_highlights["bed_count"] = int(value)
            elif label == "icu count":
                parsed_highlights["icu_count"] = int(value)
            elif label == "ot count":
                parsed_highlights["ot_count"] = int(value)
            
        elif "Established" in highlight:

            value = highlight.split()[-1]

            parsed_highlights["year_founded"] = int(value)
   
    return parsed_highlights

# =========================================================
# TRANSFORMATION
# =========================================================

def build_hospital_data(
    listing_data=None,
    detail_data=None,
):

    return {
        **listing_data,
        **detail_data,
    }


# =========================================================
# EXPORTING
# =========================================================

def save_json(
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


# ============================================================
# PAGINATION
# ============================================================

def go_to_next_page(
    page,
):

    cards_before = (
        extract_hospital_cards(
            page,
        )
    )

    if not cards_before:

        print(
            "No cards found before pagination"
        )

        return False

    first_url_before = (
        cards_before[0]
        .get_attribute(
            "href"
        )
    )

    try:

        remove_blocking_overlays(
            page,
        )

        next_button = (
            page.locator(
                'nav ul li:last-child button'
            )
        )

        next_button.scroll_into_view_if_needed()

        next_button.click(
            timeout=5000,
        )

    except Exception as error:

        print(
            f"Pagination click failed: {error}"
        )

        return False

    for _ in range(20):

        page.wait_for_timeout(
            1000
        )

        remove_blocking_overlays(
            page,
        )

        cards_after = (
            extract_hospital_cards(
                page,
            )
        )

        if not cards_after:

            continue

        first_url_after = (
            cards_after[0]
            .get_attribute(
                "href"
            )
        )

        if (
            first_url_after
            != first_url_before
        ):

            print(
                "Moved to next page"
            )

            return True

    print(
        "Pagination failed"
    )

    return False


def dismiss_listing_popups(
    page,
):

    try:

        reject_cookie_button = (
            page.query_selector(
                'button:text("Reject All")'
            )
        )

        if reject_cookie_button:

            reject_cookie_button.click(
                force=True
            )

            page.wait_for_timeout(
                1000
            )

            print(
                "Cookie popup dismissed"
            )

    except:

        pass

    try:

        modal_close_button = (
            page.query_selector(
                'button svg.lucide-x'
            )
        )

        if modal_close_button:

            modal_close_button.click(
                force=True
            )

            page.wait_for_timeout(
                1000
            )

            print(
                "Modal popup dismissed"
            )

    except:

        pass


def remove_blocking_overlays(
    page,
):

    try:

        page.evaluate(
            """
            () => {

                const overlays = document.querySelectorAll(
                    `
                    div.fixed.inset-0,
                    div[class*="fixed"][class*="inset-0"],
                    div[class*="backdrop"],
                    div[class*="z-[100001]"]
                    `
                );

                overlays.forEach(
                    overlay => overlay.remove()
                );
            }
            """
        )

    except:

        pass



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

        hospitals = []

        seen_urls = set()

        while True:

            scroll_until_complete(
                page,
            )

            cards = extract_hospital_cards(
                page,
            )

            print(
                f"Found {len(cards)} hospital cards"
            )

            for card in cards:

                listing_data = (
                    build_listing_data(
                        card,
                    )
                )

                source_url = (
                    listing_data[
                        "source_url"
                    ]
                )

                if source_url in seen_urls:

                    continue

                seen_urls.add(
                    source_url
                )

                print(
                    f"\nProcessing: {source_url}"
                )

                try:

                    detail_page = (
                        open_detail_page(
                            browser,
                            source_url,
                        )
                    )

                    address_raw = (
                        extract_address_raw(
                            detail_page,
                        )
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

                    parsed_highlights = (
                        parse_highlights(
                            highlights,
                        )
                    )

                    room_types = (
                        extract_room_types(
                            detail_page,
                        )
                    )

                    image_urls = (
                        extract_image_urls(
                            detail_page,
                            source_url,
                        )
                    )

                    detail_data = {

                        "image_urls": image_urls,

                        "location": {
                            "address_raw": address_raw,
                        },

                        "highlights": (
                            parsed_highlights
                        ),

                        "payment_methods": (
                            payment_methods
                        ),

                        "room_types": (
                            room_types
                        ),

                        "accessibility_features": (
                            accessibility_features
                        ),

                        "validation": {

                            "image_extraction": (
                                "SUCCESS"
                                if image_urls
                                else "FAILED"
                            ),

                            "image_count": len(
                                image_urls
                            ),
                        },
                    }

                    hospital_data = (
                        build_hospital_data(
                            listing_data,
                            detail_data,
                        )
                    )

                    hospitals.append(
                        hospital_data,
                    )

                    print(
                        f"Extracted {len(hospitals)} hospitals"
                    )

                except Exception as error:

                    print(
                        f"Failed: {source_url}"
                    )

                    print(
                        error
                    )

                finally:

                    detail_page.close()

                
            save_json(
                hospitals
            )

            print(
                f"Saved JSON to {OUTPUT_PATH}"
            )

            has_next_page = (
                go_to_next_page(
                    page,
                )
            )

            if not has_next_page:

                break

        print(
            f"\nFinal hospital count: {len(hospitals)}"
        )

        browser.close()

if __name__ == "__main__":

    main()