"""
main.py — FastAPI backend for DXB Dips
Deployed on Railway
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
import asyncio
import time

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import get_drops, get_stats, get_listing_history, get_client, get_rental_drops, get_rental_stats, get_rental_listing_history

def fetch_listing(listing_id: str) -> dict:
    db = get_client(use_service_key=True)
    result = db.table("listings").select("*").eq("id", listing_id).execute()
    return result.data[0] if result.data else {}

def fetch_rental_listing(listing_id: str) -> dict:
    db = get_client(use_service_key=True)
    result = db.table("rental_listings").select("*").eq("id", listing_id).execute()
    return result.data[0] if result.data else {}

app = FastAPI(title="DXB Dips API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dxbdips.com",
        "https://www.dxbdips.com",
        "http://localhost:5173",   # local dev
        "http://localhost:5174",   # local dev (alternate port)
        "http://localhost:4173",   # local preview
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Thread pool for running blocking scrape/db work off the event loop
executor = ThreadPoolExecutor(max_workers=2)

# ─── In-memory cache ───────────────────────────────────────────────────────────
# Keyed by (endpoint, hours, sort) → {data, ts}
# TTL: 10 minutes. Serves stale data instantly; refreshes in background on expiry.
_cache: dict = {}
CACHE_TTL = 600  # 10 minutes

def cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None

def cache_set(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}

AED_TO_USD = 0.2723


def enrich_drop(d: dict) -> dict:
    listing = d.get("listings") or {}
    if not listing.get("title"):
        listing = fetch_listing(d["listing_id"])
    return {
        "id":             d["id"],
        "listing_id":     d["listing_id"],
        "detected_at":    d["detected_at"],
        "old_price_aed":  d["old_price_aed"],
        "new_price_aed":  d["new_price_aed"],
        "drop_abs_aed":   d["drop_abs_aed"],
        "drop_pct":       d["drop_pct"],
        "drop_abs_usd":   round(d["drop_abs_aed"] * AED_TO_USD * 1_000_000),
        "new_price_usd":  round(d["new_price_aed"] * AED_TO_USD, 4),
        "old_price_usd":  round(d["old_price_aed"] * AED_TO_USD, 4),
        "source":         listing.get("source", "propertyfinder"),
        "type":           listing.get("type"),
        "beds":           listing.get("beds"),
        "baths":          listing.get("baths"),
        "size_sqft":      listing.get("size_sqft"),
        "title":          listing.get("title"),
        "area":           listing.get("area"),
        "building":       listing.get("building"),
        "url":            listing.get("url"),
        "image_url":      listing.get("image_url"),
        "listed_date":    listing.get("listed_date"),
        "first_seen":     listing.get("first_seen"),
    }


@app.get("/api/drops")
async def api_drops(
    hours: int = Query(24, description="24 | 168 (7d) | 720 (30d)"),
    limit: int = Query(100),
    type: str = Query(None),
    min_pct: float = Query(None),
    sort: str = Query("abs"),
):
    key = f"drops:{hours}:{sort}:{type}:{min_pct}:{limit}"
    cached = cache_get(key)
    if cached:
        return cached
    drops = get_drops(hours=hours, limit=limit, prop_type=type, sort=sort, min_pct=min_pct)
    enriched = [enrich_drop(d) for d in drops]
    result = {"drops": enriched, "count": len(enriched), "hours": hours}
    cache_set(key, result)
    return result


@app.get("/api/stats")
async def api_stats(hours: int = Query(24)):
    key = f"stats:{hours}"
    cached = cache_get(key)
    if cached:
        return cached
    result = get_stats(hours=hours)
    cache_set(key, result)
    return result


@app.get("/api/history/{listing_id}")
async def api_history(listing_id: str):
    data = get_listing_history(listing_id)
    if not data["listing"]:
        raise HTTPException(status_code=404, detail="Listing not found")
    return data


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dxbdips-api", "version": "1.3.0", "source": "propertyfinder"}

@app.head("/health")
async def health_head():
    return Response(status_code=200)



AED_TO_USD_YEARLY = 0.2723  # same rate, but price is raw AED not millions


def enrich_rental_drop(d: dict) -> dict:
    listing = d.get("rental_listings") or {}
    if not listing.get("title"):
        listing = fetch_rental_listing(d["listing_id"])
    return {
        "id":             d["id"],
        "listing_id":     d["listing_id"],
        "detected_at":    d["detected_at"],
        "old_price_aed":  d["old_price_aed"],   # raw AED/yr
        "new_price_aed":  d["new_price_aed"],   # raw AED/yr
        "drop_abs_aed":   d["drop_abs_aed"],     # raw AED/yr
        "drop_pct":       d["drop_pct"],
        "old_price_usd":  round(d["old_price_aed"] * AED_TO_USD_YEARLY),
        "new_price_usd":  round(d["new_price_aed"] * AED_TO_USD_YEARLY),
        "drop_abs_usd":   round(d["drop_abs_aed"] * AED_TO_USD_YEARLY),
        "listing_type":   "rental",
        "source":         listing.get("source", "propertyfinder"),
        "type":           listing.get("type"),
        "beds":           listing.get("beds"),
        "baths":          listing.get("baths"),
        "size_sqft":      listing.get("size_sqft"),
        "title":          listing.get("title"),
        "area":           listing.get("area"),
        "building":       listing.get("building"),
        "url":            listing.get("url"),
        "image_url":      listing.get("image_url"),
        "listed_date":    listing.get("listed_date"),
        "first_seen":     listing.get("first_seen"),
    }


@app.get("/api/rental-drops")
async def api_rental_drops(
    hours: int = Query(24),
    limit: int = Query(100),
    type: str = Query(None),
    min_pct: float = Query(None),
    sort: str = Query("abs"),
):
    key = f"rental-drops:{hours}:{sort}:{type}:{min_pct}:{limit}"
    cached = cache_get(key)
    if cached:
        return cached
    drops = get_rental_drops(hours=hours, limit=limit, prop_type=type, sort=sort, min_pct=min_pct)
    enriched = [enrich_rental_drop(d) for d in drops]
    result = {"drops": enriched, "count": len(enriched), "hours": hours}
    cache_set(key, result)
    return result


@app.get("/api/rental-stats")
async def api_rental_stats(hours: int = Query(24)):
    key = f"rental-stats:{hours}"
    cached = cache_get(key)
    if cached:
        return cached
    result = get_rental_stats(hours=hours)
    cache_set(key, result)
    return result


@app.get("/api/rental-history/{listing_id}")
async def api_rental_history(listing_id: str):
    data = get_rental_listing_history(listing_id)
    if not data["listing"]:
        raise HTTPException(status_code=404, detail="Rental listing not found")
    return data


@app.post("/api/trigger-scrape")
async def trigger_scrape(
    pages: int = Query(300),
    rental_pages: int = Query(200),
    secret: str = Query(None),
):
    expected = os.environ.get("SCRAPE_SECRET", "dxbdips-scrape-2026")
    if secret != expected:
        raise HTTPException(status_code=401, detail="Invalid secret")

    def run_scrape_sync():
        """Run the scraper in a thread so it never blocks the event loop."""
        import asyncio
        # FIX: was incorrectly importing from scraper.runner — must be backend.runner
        from backend.runner import run_all
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_all(sale_pages=pages, rental_pages=rental_pages))
        except Exception as e:
            print(f"Scrape error: {e}", flush=True)
        finally:
            loop.close()

    # Submit to thread pool — API stays responsive immediately
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_scrape_sync)

    # Clear cache so next request picks up fresh data after scrape completes
    _cache.clear()
    return {"status": "scrape started", "pages": pages, "rental_pages": rental_pages, "source": "propertyfinder"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
