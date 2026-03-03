"""
scraper_bayut.py — Scrapes Bayut.com using their Algolia-based internal API.
No browser needed — pure httpx JSON calls.
Targets Dubai properties 2M+ AED for sale.
"""
import httpx
import asyncio
import json
import random
from datetime import datetime

# Bayut uses Algolia for search — these are their app/API credentials
# (reverse engineered from browser network tab — public, no auth needed)
ALGOLIA_APP_ID = "5BNAR5PY6Y"
ALGOLIA_API_KEY = "ae1c4bbf5a1c3f8d955b94f9e74c90be"
ALGOLIA_INDEX = "bayut-plp-ar-production"

ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Referer": "https://www.bayut.com/",
    "Origin": "https://www.bayut.com",
}

MIN_PRICE_AED = 2_000_000
HITS_PER_PAGE = 24

# Property type mapping
TYPE_MAP = {
    "apartment": "apartment",
    "flat": "apartment",
    "penthouse": "penthouse",
    "villa": "villa",
    "townhouse": "townhouse",
    "duplex": "apartment",
    "studio": "apartment",
    "hotel apartment": "apartment",
}


def normalize_type(raw: str) -> str:
    if not raw:
        return "apartment"
    return TYPE_MAP.get(raw.lower().strip(), raw.lower().strip())


def parse_location(hit: dict) -> tuple[str, str]:
    """Extract building and area from Bayut location array."""
    locations = hit.get("location", [])
    names = [l.get("name", "") for l in locations if l.get("name")]
    building = names[0] if names else ""
    area = names[1] if len(names) > 1 else ""
    return building, area


def parse_hit(hit: dict) -> dict | None:
    """Parse a single Algolia hit into our listing format."""
    try:
        price = hit.get("price")
        if not price or float(price) < MIN_PRICE_AED:
            return None

        price_aed = round(float(price) / 1_000_000, 6)
        ext_id = hit.get("externalID", hit.get("objectID", ""))
        listing_id = f"by_{ext_id}"
        slug = hit.get("slug", "")
        url = f"https://www.bayut.com/property/details-{slug}.html" if slug else None

        building, area = parse_location(hit)

        # Property type
        category = hit.get("category", [{}])
        type_raw = category[0].get("nameSingular", "") if category else ""
        prop_type = normalize_type(type_raw)

        # Image
        cover = hit.get("coverPhoto", {})
        image_url = cover.get("url") if cover else None

        # Listed date
        created = hit.get("createdAt")
        listed_date = None
        if created:
            try:
                listed_date = datetime.utcfromtimestamp(created).strftime("%Y-%m-%d")
            except Exception:
                pass

        return {
            "id": listing_id,
            "source": "bayut",
            "type": prop_type,
            "beds": hit.get("rooms"),
            "baths": hit.get("baths"),
            "size_sqft": hit.get("area"),
            "title": hit.get("title"),
            "area": area,
            "building": building,
            "url": url,
            "image_url": image_url,
            "listed_date": listed_date,
            "price_aed": price_aed,
        }
    except Exception as e:
        print(f"  [Bayut] parse error: {e}")
        return None


async def fetch_page(client: httpx.AsyncClient, page: int) -> tuple[list, int]:
    """Fetch one page of results. Returns (listings, total_hits)."""
    filters = (
        f"price>={MIN_PRICE_AED}"
        " AND purpose:for-sale"
        " AND city:Dubai"
    )

    payload = {
        "query": "",
        "filters": filters,
        "page": page,
        "hitsPerPage": HITS_PER_PAGE,
        "attributesToRetrieve": [
            "externalID", "objectID", "slug", "title", "price",
            "rooms", "baths", "area", "category", "location",
            "coverPhoto", "purpose", "createdAt", "updatedAt",
            "furnishingStatus", "state",
        ],
        "attributesToHighlight": [],
    }

    try:
        resp = await client.post(ALGOLIA_URL, json=payload, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [Bayut] HTTP {resp.status_code} on page {page}")
            return [], 0

        data = resp.json()
        hits = data.get("hits", [])
        total = data.get("nbHits", 0)
        nb_pages = data.get("nbPages", 0)

        listings = []
        for hit in hits:
            parsed = parse_hit(hit)
            if parsed:
                listings.append(parsed)

        return listings, total, nb_pages

    except Exception as e:
        print(f"  [Bayut] Request error on page {page}: {e}")
        return [], 0, 0


async def run_scrape(max_pages: int = 50) -> list[dict]:
    """
    Main entry point. Scrapes Bayut for Dubai listings 2M+ AED.
    Returns deduplicated list of listing dicts.
    """
    print(f"[Bayut] Starting scrape (max {max_pages} pages, {HITS_PER_PAGE}/page)")
    all_listings = []

    async with httpx.AsyncClient() as client:
        # First page to discover total
        listings, total_hits, nb_pages = await fetch_page(client, 0)
        all_listings.extend(listings)
        print(f"[Bayut] Total hits: {total_hits:,} across {nb_pages} pages")
        print(f"  Page 0: {len(listings)} listings")

        pages_to_fetch = min(nb_pages, max_pages) - 1

        # Fetch remaining pages with gentle rate limiting
        for page in range(1, pages_to_fetch + 1):
            listings, _, _ = await fetch_page(client, page)
            if not listings:
                print(f"  Page {page}: empty, stopping")
                break
            all_listings.extend(listings)
            print(f"  Page {page}/{pages_to_fetch}: {len(listings)} listings (total: {len(all_listings)})")
            await asyncio.sleep(random.uniform(0.3, 0.8))  # gentle rate limiting

    # Deduplicate
    seen = set()
    unique = []
    for l in all_listings:
        if l["id"] not in seen:
            seen.add(l["id"])
            unique.append(l)

    print(f"[Bayut] Done. {len(unique)} unique listings scraped.")
    return unique


if __name__ == "__main__":
    results = asyncio.run(run_scrape(max_pages=2))
    print(json.dumps(results[:2], indent=2, default=str))
