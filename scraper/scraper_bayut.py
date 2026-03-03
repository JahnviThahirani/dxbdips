"""
scraper_bayut.py — Scrapes Bayut.com using their Algolia-based internal API.
No browser needed — pure httpx JSON calls.
Targets Dubai properties 2M+ AED for sale.
"""
import httpx
import asyncio
from datetime import datetime

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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

MIN_PRICE_AED = 2_000_000
HITS_PER_PAGE = 24

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


def parse_location(hit: dict) -> tuple:
    locations = hit.get("location", [])
    names = [l.get("name", "") for l in locations if l.get("name")]
    building = names[0] if names else ""
    area = names[1] if len(names) > 1 else ""
    return building, area


def parse_hit(hit: dict) -> dict | None:
    try:
        price = hit.get("price")
        if not price or price < MIN_PRICE_AED:
            return None

        building, area = parse_location(hit)

        photos = hit.get("coverPhoto", {}) or {}
        image_url = photos.get("url", "") if isinstance(photos, dict) else ""

        return {
            "id": f"bayut_{hit['objectID']}",
            "source": "bayut",
            "type": normalize_type(hit.get("category", "")),
            "beds": hit.get("beds") or 0,
            "baths": hit.get("baths") or 0,
            "size_sqft": round(hit.get("area") or 0),
            "price_aed": int(price),
            "title": hit.get("title", "")[:200],
            "building": building[:100],
            "area": area[:100],
            "url": f"https://www.bayut.com{hit.get('slug', '')}",
            "image_url": image_url[:500],
            "scraped_at": datetime.utcnow().isoformat(),
        }
    except Exception:
        return None


async def scrape(max_pages: int = 50) -> list[dict]:
    listings = []
    seen_ids = set()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        for page in range(max_pages):
            payload = {
                "query": "",
                "hitsPerPage": HITS_PER_PAGE,
                "page": page,
                "filters": f"price >= {MIN_PRICE_AED} AND purpose:for-sale AND location.country.slug:united-arab-emirates",
                "facetFilters": [["location.country.slug:united-arab-emirates"]],
            }
            try:
                resp = await client.post(ALGOLIA_URL, json=payload, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                hits = data.get("hits", [])
                nb_pages = data.get("nbPages", 0)

                if page == 0:
                    print(f"[Bayut] Total hits: {data.get('nbHits', 0)} across {nb_pages} pages")

                if not hits:
                    break

                page_listings = []
                for hit in hits:
                    parsed = parse_hit(hit)
                    if parsed and parsed["id"] not in seen_ids:
                        seen_ids.add(parsed["id"])
                        page_listings.append(parsed)

                listings.extend(page_listings)
                print(f"  Page {page}: {len(page_listings)} listings")

                if page >= nb_pages - 1:
                    break

                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"  [Bayut] Request error on page {page}: {e}")
                break

    print(f"[Bayut] Done. {len(listings)} unique listings scraped.")
    return listings


async def run_scrape(max_pages: int = 50) -> list[dict]:
    return await scrape(max_pages)
