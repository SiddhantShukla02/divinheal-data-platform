"""
Playwright scraper for CureMeAbroad hospital directory.

Paginates through the listing, scrolls each page until all cards load,
opens every hospital's detail page and extracts structured fields
(address, payment methods, accessibility, highlights, room types, images),
then saves the full dataset as JSON.
"""

import json
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright


# =========================================================
# CONFIG
# =========================================================

BASE_URL = "https://curemeabroad.com/hospitals"

OUTPUT_PATH = Path("outputs/raw/curemeabroad_hospitals.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


# =========================================================
# BROWSER HELPERS
# =========================================================

def launch_browser(playwright, *, headless: bool = True):
    """Launch Chromium.  headless=True for CI / production runs."""
    return playwright.chromium.launch(headless=headless)


def load_hospitals_page(page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_selector('a.block[href^="/hospitals/"]')
    dismiss_listing_popups(page)


def scroll_until_complete(page) -> None:
    """Scroll until the card count stabilises (infinite-scroll end)."""
    previous_card_count = 0

    while True:
        page.mouse.wheel(0, 10_000)
        page.wait_for_timeout(2000)

        cards = extract_hospital_cards(page)
        current_card_count = len(cards)

        if current_card_count == previous_card_count:
            break

        previous_card_count = current_card_count

    log.info("Loaded %d cards on this page", current_card_count)


# =========================================================
# LISTING EXTRACTION
# =========================================================

def extract_hospital_cards(page):
    return page.query_selector_all('a.block[href^="/hospitals/"]')


def extract_hospital_name(card) -> str:
    el = card.query_selector("h3")
    return el.inner_text().strip() if el else ""


def extract_description_raw(card) -> str:
    el = card.query_selector("p")
    return el.inner_text().strip() if el else ""


def extract_source_url(card) -> str:
    href = card.get_attribute("href")
    return f"https://curemeabroad.com{href}" if href else ""


def build_listing_data(card) -> dict:
    return {
        "hospital_name": extract_hospital_name(card),
        "description_raw": extract_description_raw(card),
        "source_url": extract_source_url(card),
    }


# =========================================================
# DETAIL PAGE EXTRACTION
# =========================================================

def open_detail_page(browser, source_url: str):
    detail_page = browser.new_page()
    detail_page.goto(source_url, wait_until="domcontentloaded")
    return detail_page


def _extract_sibling_spans(detail_page, heading_text: str) -> list[str]:
    """Find an <h3> by text, return span texts from its next sibling."""
    heading = detail_page.query_selector(f'h3:text("{heading_text}")')
    if not heading:
        return []
    container = heading.evaluate_handle("el => el.nextElementSibling")
    spans = container.query_selector_all("span")
    return [s.inner_text().strip() for s in spans if s.inner_text().strip()]


def extract_payment_methods(detail_page) -> list[str]:
    return _extract_sibling_spans(detail_page, "Payment Method")


def extract_accessibility_features(detail_page) -> list[str]:
    return _extract_sibling_spans(detail_page, "Accessibility Features")


def extract_highlights(detail_page) -> list[str]:
    return _extract_sibling_spans(detail_page, "Highlights")


def extract_room_types(detail_page) -> list[str]:
    return _extract_sibling_spans(detail_page, "Room Types")


def extract_accreditations(detail_page) -> list[str]:
    # TODO: implement once page structure for accreditations is confirmed
    return []


def extract_address_raw(detail_page) -> str | None:
    container = detail_page.query_selector("div.flex.md\\:items-center.gap-1")
    if not container:
        return None
    h4 = container.query_selector("h4")
    if not h4:
        return None
    text = h4.inner_text().strip()
    return text or None


def extract_image_urls(detail_page, source_url: str) -> list[str]:
    """Click the gallery trigger, then collect de-duped image URLs."""
    image_urls: list[str] = []

    gallery_trigger = detail_page.query_selector(
        "div.mb-3.md\\:mb-6 div.cursor-pointer"
    )
    if not gallery_trigger:
        log.warning("Gallery trigger not found: %s", source_url)
        return image_urls

    gallery_trigger.scroll_into_view_if_needed()
    detail_page.wait_for_timeout(1000)
    gallery_trigger.click(force=True)

    try:
        detail_page.wait_for_selector("div.overflow-x-auto", timeout=5000)
    except Exception:
        # Try the expand-gallery fallback button
        expand = detail_page.query_selector('text="+"')
        if expand:
            expand.scroll_into_view_if_needed()
            detail_page.wait_for_timeout(1000)
            expand.click(force=True)
            try:
                detail_page.wait_for_selector("div.overflow-x-auto", timeout=5000)
            except Exception:
                log.warning("Gallery strip failed to open: %s", source_url)
                return image_urls
        else:
            log.warning("Expand gallery button not found: %s", source_url)
            return image_urls

    detail_page.wait_for_timeout(1000)

    for img in detail_page.query_selector_all("div.overflow-x-auto img"):
        url = img.get_attribute("src") or img.get_attribute("data-src")
        if not url:
            continue
        if url.startswith("/"):
            url = f"https://curemeabroad.com{url}"
        url = url.split("&w=", 1)[0]  # strip Next.js width param
        if url not in image_urls:
            image_urls.append(url)

    if not image_urls:
        log.warning("Image extraction failed: %s", source_url)

    return image_urls


# =========================================================
# PARSING
# =========================================================

def parse_highlights(highlights: list[str]) -> dict:
    """Extract structured numbers from highlight strings."""
    parsed: dict = {}
    for h in highlights:
        if ":" in h:
            label, value = h.split(":", 1)
            label = label.strip().lower()
            value = value.strip()
            try:
                if label == "bed count":
                    parsed["bed_count"] = int(value)
                elif label == "icu count":
                    parsed["icu_count"] = int(value)
                elif label == "ot count":
                    parsed["ot_count"] = int(value)
            except ValueError:
                log.warning("Could not parse highlight %r", h)
        elif "Established" in h:
            try:
                parsed["year_founded"] = int(h.split()[-1])
            except ValueError:
                log.warning("Could not parse year from %r", h)
    return parsed


# =========================================================
# TRANSFORMATION
# =========================================================

def build_hospital_data(listing_data: dict, detail_data: dict) -> dict:
    """Merge listing-level and detail-page data into one record."""
    return {**listing_data, **detail_data}


# =========================================================
# EXPORTING
# =========================================================

def save_json(hospitals: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(hospitals, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Saved %d hospitals to %s", len(hospitals), OUTPUT_PATH)


# =========================================================
# PAGINATION
# =========================================================

def go_to_next_page(page) -> bool:
    """Click the pagination next button; return True if a new page loaded."""
    cards_before = extract_hospital_cards(page)
    if not cards_before:
        log.info("No cards found before pagination")
        return False

    first_url_before = cards_before[0].get_attribute("href")

    try:
        remove_blocking_overlays(page)
        next_button = page.locator("nav ul li:last-child button")
        next_button.scroll_into_view_if_needed()
        next_button.click(timeout=5000)
    except Exception as exc:
        log.info("Pagination click failed: %s", exc)
        return False

    for _ in range(20):
        page.wait_for_timeout(1000)
        remove_blocking_overlays(page)

        cards_after = extract_hospital_cards(page)
        if not cards_after:
            continue
        if cards_after[0].get_attribute("href") != first_url_before:
            log.info("Moved to next page")
            return True

    log.info("Pagination timed out — no new page loaded")
    return False


def dismiss_listing_popups(page) -> None:
    """Dismiss cookie banners and modals that block interaction."""
    try:
        btn = page.query_selector('button:text("Reject All")')
        if btn:
            btn.click(force=True)
            page.wait_for_timeout(1000)
            log.info("Cookie popup dismissed")
    except Exception:
        pass

    try:
        close = page.query_selector("button svg.lucide-x")
        if close:
            close.click(force=True)
            page.wait_for_timeout(1000)
            log.info("Modal popup dismissed")
    except Exception:
        pass


def remove_blocking_overlays(page) -> None:
    """Remove fixed/backdrop overlays that intercept clicks."""
    try:
        page.evaluate("""() => {
            document.querySelectorAll(
                'div.fixed.inset-0, div[class*="fixed"][class*="inset-0"], '
                + 'div[class*="backdrop"], div[class*="z-[100001]"]'
            ).forEach(el => el.remove());
        }""")
    except Exception:
        pass


# =========================================================
# ORCHESTRATION
# =========================================================

def main() -> None:
    with sync_playwright() as pw:
        browser = launch_browser(pw)
        page = browser.new_page()
        load_hospitals_page(page)

        hospitals: list[dict] = []
        seen_urls: set[str] = set()

        while True:
            scroll_until_complete(page)
            cards = extract_hospital_cards(page)
            log.info("Found %d hospital cards on current page", len(cards))

            for card in cards:
                listing = build_listing_data(card)
                source_url = listing["source_url"]

                if source_url in seen_urls:
                    continue
                seen_urls.add(source_url)

                log.info("Processing: %s", source_url)
                detail_page = None

                try:
                    detail_page = open_detail_page(browser, source_url)

                    detail_data = {
                        "image_urls": extract_image_urls(detail_page, source_url),
                        "location": {
                            "address_raw": extract_address_raw(detail_page),
                        },
                        "highlights": parse_highlights(
                            extract_highlights(detail_page)
                        ),
                        "payment_methods": extract_payment_methods(detail_page),
                        "room_types": extract_room_types(detail_page),
                        "accessibility_features": extract_accessibility_features(detail_page),
                        "validation": {
                            "image_extraction": (
                                "SUCCESS" if extract_image_urls(detail_page, source_url)
                                else "FAILED"
                            ),
                        },
                    }

                    hospitals.append(build_hospital_data(listing, detail_data))
                    log.info("Extracted %d hospitals so far", len(hospitals))

                except Exception:
                    log.exception("Failed: %s", source_url)

                finally:
                    if detail_page:
                        detail_page.close()

            save_json(hospitals)

            if not go_to_next_page(page):
                break

        log.info("Final hospital count: %d", len(hospitals))
        browser.close()


if __name__ == "__main__":
    main()
