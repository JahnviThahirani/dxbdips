"""
scraper_pf.py — Property Finder scraper for DXB Dips
Reads __NEXT_DATA__ JSON embedded in PF search pages.
"""
import re
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

log = logging.getLogger("dxbdips.scraper_pf")

BASE_URL = "https://www.propertyfinder.ae/en/search"
DELAY_SECONDS = 2.5
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # seconds to wait between retries

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# c=1 for-sale, rp=y price-reduced, ob=mr most-recent, pf=4000000 min price 4M AED
SEARCH_PARAMS = {"c": "1", "fu": "0", "rp": "y", "ob": "mr", "pf": "4000000"}

# c=2 for-rent, rp=y price-reduced, ob=mr most-recent, pf=250000 min rent 250K AED/yr
RENTAL_SEARCH_PARAMS = {"c": "2", "fu": "0", "rp": "y", "ob": "mr", "pf": "250000"}


def fetch_page(page: int, params: dict = None) -> Optional[dict]:
    if params is None:
        params = SEARCH_PARAMS
    req_params = {**params, "page": str(page)}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = httpx.get(
                BASE_URL, params=req_params, headers=HEADERS,
                timeout=30,  # increased from 20
                follow_redirects=True
            )
            log.info(f"PF page {page}: HTTP {resp.status_code} (attempt {attempt})")

            if resp.status_code == 429:
                # Rate limited — wait longer
                wait = RETRY_DELAYS[attempt - 1] * 2
                log.warning(f"PF page {page}: rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                log.warning(f"PF page {page}: non-200 status {resp.status_code}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAYS[attempt - 1])
                continue

            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                resp.text, re.DOTALL
            )
            if not match:
                log.warning(f"PF page {page}: __NEXT_DATA__ not found (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAYS[attempt - 1])
                continue

            return json.loads(match.group(1))

        except httpx.TimeoutException as e:
            log.warning(f"PF page {page}: timeout on attempt {attempt} — {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[attempt - 1]
                log.info(f"PF page {page}: retrying in {wait}s...")
                time.sleep(wait)

        except httpx.NetworkError as e:
            log.warning(f"PF page {page}: network error on attempt {attempt} — {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[attempt - 1]
                log.info(f"PF page {page}: retrying in {wait}s...")
                time.sleep(wait)

        except Exception as e:
            log.error(f"PF page {page}: unexpected error on attempt {attempt} — {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAYS[attempt - 1])

    log.error(f"PF page {page}: all {MAX_RETRIES} attempts failed, skipping page")
    return None


def to_int(val) -> Optional[int]:
    """Convert '7+' or '7' or 7 to int, None if not parseable."""
    if val is None:
        return None
    try:
        return int(str(val).replace("+", "").strip())
    except (ValueError, TypeError):
        return None


def parse_listing(raw: dict, listing_type: str = "sale") -> Optional[dict]:
    """Convert a PF listing into DXB Dips' unified listing schema."""
    try:
        prop = raw.get("property", {})
        if not prop:
            return None

        price_block = prop.get("price", {})
        price_value = price_block.get("value")
        if not price_value:
            return None

        location = prop.get("location", {})
        size = prop.get("size", {})
        coords = location.get("coordinates", {})
        images = prop.get("images", [])
        image_url = images[0].get("medium") if images else None

        if listing_type == "rental":
            # Rental prices stored as raw AED per year (not millions)
            price_aed = round(float(price_value), 2)
            price_field = "price_aed_yearly"
        else:
            # Sale prices stored in millions to match existing schema
            price_aed = round(price_value / 1_000_000, 4)
            price_field = "price_aed"

        result = {
            "id":          f"pf_{prop['id']}",
            "source":      "propertyfinder",
            "listing_type": listing_type,
            "type":        prop.get("property_type"),
            "beds":        to_int(prop.get("bedrooms")),
            "baths":       to_int(prop.get("bathrooms")),
            "size_sqft":   size.get("value") if size.get("unit") == "sqft" else None,
            "title":       prop.get("title"),
            "area":        location.get("path_name"),
            "building":    location.get("name"),
            "url":         prop.get("share_url"),
            "image_url":   image_url,
            "listed_date": prop.get("listed_date"),
            "reference":   prop.get("reference"),
            "lat":         coords.get("lat"),
            "lon":         coords.get("lon"),
            price_field:   price_aed,
        }
        return result
    except Exception as e:
        log.warning(f"parse_listing failed: {e}")
        return None


async def run_scrape(max_pages: int = 10) -> list[dict]:
    """Scrape for-sale listings. Main entry point for runner.py."""
    log.info(f"PF sale scraper starting — {max_pages} pages")
    all_listings = []
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5

    for page in range(1, max_pages + 1):
        log.info(f"Scraping PF sale page {page}/{max_pages}...")
        data = fetch_page(page, params=SEARCH_PARAMS)

        if not data:
            consecutive_failures += 1
            log.warning(f"Page {page} failed ({consecutive_failures} consecutive failures)")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log.error(f"Stopping after {MAX_CONSECUTIVE_FAILURES} consecutive failures")
                break
            time.sleep(RETRY_DELAYS[1])
            continue

        consecutive_failures = 0

        try:
            raw_listings = data["props"]["pageProps"]["searchResult"]["listings"]
        except (KeyError, TypeError):
            log.warning(f"Could not find listings on page {page}, skipping")
            consecutive_failures += 1
            continue

        log.info(f"Page {page}: {len(raw_listings)} raw listings")
        parsed = [parse_listing(r, listing_type="sale") for r in raw_listings]
        parsed = [p for p in parsed if p is not None]
        all_listings.extend(parsed)
        log.info(f"Page {page}: {len(parsed)} parsed (total: {len(all_listings)})")

        if page < max_pages:
            time.sleep(DELAY_SECONDS)

    log.info(f"PF sale scrape complete — {len(all_listings)} listings total")
    return all_listings


async def run_rental_scrape(max_pages: int = 10) -> list[dict]:
    """Scrape for-rent listings (250K+ AED/yr)."""
    log.info(f"PF rental scraper starting — {max_pages} pages")
    all_listings = []
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5

    for page in range(1, max_pages + 1):
        log.info(f"Scraping PF rental page {page}/{max_pages}...")
        data = fetch_page(page, params=RENTAL_SEARCH_PARAMS)

        if not data:
            consecutive_failures += 1
            log.warning(f"Rental page {page} failed ({consecutive_failures} consecutive failures)")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log.error(f"Stopping after {MAX_CONSECUTIVE_FAILURES} consecutive failures")
                break
            time.sleep(RETRY_DELAYS[1])
            continue

        consecutive_failures = 0

        try:
            raw_listings = data["props"]["pageProps"]["searchResult"]["listings"]
        except (KeyError, TypeError):
            log.warning(f"Could not find rental listings on page {page}, skipping")
            consecutive_failures += 1
            continue

        log.info(f"Rental page {page}: {len(raw_listings)} raw listings")
        parsed = [parse_listing(r, listing_type="rental") for r in raw_listings]
        parsed = [p for p in parsed if p is not None]
        all_listings.extend(parsed)
        log.info(f"Rental page {page}: {len(parsed)} parsed (total: {len(all_listings)})")

        if page < max_pages:
            time.sleep(DELAY_SECONDS)

    log.info(f"PF rental scrape complete — {len(all_listings)} listings total")
    return all_listings
