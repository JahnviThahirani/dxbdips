"""
main.py — FastAPI backend for DXB Dips
Deployed on Railway
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
import asyncio

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import get_drops, get_stats, get_listing_history

app = FastAPI(title="DXB Dips API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Thread pool for running blocking scrape/db work off the event loop
executor = ThreadPoolExecutor(max_workers=2)

AED_TO_USD = 0.2723


def enrich_drop(d: dict) -> dict:
    listing = d.get("listings") or {}
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
    drops = get_drops(hours=hours, limit=limit, prop_type=type, sort=sort, min_pct=min_pct)
    enriched = [enrich_drop(d) for d in drops]
    return {"drops": enriched, "count": len(enriched), "hours": hours}


@app.get("/api/stats")
async def api_stats(hours: int = Query(24)):
    return get_stats(hours=hours)


@app.get("/api/history/{listing_id}")
async def api_history(listing_id: str):
    data = get_listing_history(listing_id)
    if not data["listing"]:
        raise HTTPException(status_code=404, detail="Listing not found")
    return data


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dxbdips-api", "version": "1.2.0", "source": "propertyfinder"}


@app.post("/api/trigger-scrape")
async def trigger_scrape(
    pages: int = Query(10),
    secret: str = Query(None),
):
    expected = os.environ.get("SCRAPE_SECRET", "dxbdips-scrape-2026")
    if secret != expected:
        raise HTTPException(status_code=401, detail="Invalid secret")

    def run_scrape_sync():
        """Run the scraper in a thread so it never blocks the event loop."""
        import asyncio
        from scraper.runner import run_all
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_all(max_pages=pages))
        except Exception as e:
            print(f"Scrape error: {e}")
        finally:
            loop.close()

    # Submit to thread pool — API stays responsive immediately
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, run_scrape_sync)

    return {"status": "scrape started", "pages": pages, "source": "propertyfinder"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
