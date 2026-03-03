"""
scraper_bayut.py — Scrapes Bayut.com using their GraphQL API.
"""
import httpx
import asyncio
import json
from datetime import datetime

GRAPHQL_URL = "https://gateway.bayut.com/api/graphql"

HEADERS = {
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

QUERY = """
query GetListings($page: Int!, $hitsPerPage: Int!) {
  properties(
    purpose: "for-sale"
    locationExternalIDs: "5002"
    residentialTypes: ["apartment", "villa", "penthouse", "townhouse"]
    priceMin: 2000000
    page: $page
    hitsPerPage: $hitsPerPage
    lang: "en"
  ) {
    hits {
      externalID
      title
      price
      rooms
      baths
      area
      location {
        name
      }
      propertyType {
        name
      }
      slug
      coverPhoto {
        url
      }
    }
    nbHits
    nbPages
  }
}
"""


def normalize_type(raw: str) -> str:
    if not raw:
        return "apartment"
    return TYPE_MAP.get(raw.lower().strip(), raw.lower().strip())


def parse_hit(hit: dict) -> dict | None:
    try:
        price = hit.get("price")
        if not price or price < MIN_PRICE_AED:
            return None

        locations = hit.get("location", [])
        names = [l.get("name", "") for l in locations if l.get("name")]
        building = names[0] if names else ""
        area = names[1] if len(names) > 1 else ""

        prop_type = hit.get("propertyType", {})
        type_name = prop_type.get("name", "") if prop_type else ""

        cover = hit.get("coverPhoto", {})
        image_url = cover.get("url", "") if cover else ""

        return {
            "id": f"bayut_{hit['externalID']}",
            "source": "bayut",
            "type": normalize_type(type_name),
            "beds": hit.get("rooms") or 0,
            "baths": hit.get("baths") or 0,
            "size_sqft": round(hit.get("area") or 0),
            "price_aed": int(price),
            "title": hit.get("title", "")[:200],
            "building": building[:100],
            "area": area[:100],
            "url": f"https://www.bayut.com/property/details-{hit.get('slug', '')}.html",
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
                "query": QUERY,
                "variables": {"page": page, "hitsPerPage": HITS_PER_PAGE},
            }
            try:
                resp = await client.post(GRAPHQL_URL, json=payload, timeout=20)
                resp.raise_for_status()
                data = resp.json()

                props = data.get("data", {}).get("properties", {})
                hits = props.get("hits", [])
                nb_pages = props.get("nbPages", 0)

                if page == 0:
                    print(f"[Bayut] Total hits: {props.get('nbHits', 0)} across {nb_pages} pages")

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
