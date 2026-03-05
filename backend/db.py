"""
db.py — Supabase client + all database operations for DXB Dips
"""
import os
import time
from datetime import datetime, timezone
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://rtzgkphamillvxkrctdy.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0emdrcGhhbWlsbHZ4a3JjdGR5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI1MjAxOTQsImV4cCI6MjA4ODA5NjE5NH0.rd-iy-Lx0UddIfa6o4xBUzNBelmvmU00mqMGOvRAW8Q")

def get_client(use_service_key: bool = False) -> Client:
    key = SUPABASE_KEY if (use_service_key and SUPABASE_KEY) else SUPABASE_ANON_KEY
    return create_client(SUPABASE_URL, key)


def _with_retry(fn, retries=3, delay=30):
    """Run a DB operation with retries on transient errors (502, connection issues)."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            err = str(e).lower()
            is_transient = any(x in err for x in ["502", "503", "504", "connection", "timeout", "json could not"])
            if is_transient and attempt < retries - 1:
                wait = delay * (attempt + 1)  # 30s, 60s, 90s
                print(f"  [DB] Transient error (attempt {attempt+1}/{retries}), retrying in {wait}s: {str(e)[:80]}")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")


def upsert_listing(listing: dict) -> dict:
    db = get_client(use_service_key=True)
    now = datetime.now(timezone.utc).isoformat()
    lid = listing["id"]
    new_price = listing["price_aed"]

    existing = _with_retry(lambda: db.table("listings").select("*").eq("id", lid).execute())

    if not existing.data:
        _with_retry(lambda: db.table("listings").insert({
            "id": lid,
            "source": listing.get("source", "propertyfinder"),
            "type": listing.get("type"),
            "beds": listing.get("beds"),
            "baths": listing.get("baths"),
            "size_sqft": listing.get("size_sqft"),
            "title": listing.get("title"),
            "area": listing.get("area"),
            "building": listing.get("building"),
            "url": listing.get("url"),
            "image_url": listing.get("image_url"),
            "listed_date": listing.get("listed_date"),
            "last_price": new_price,
            "first_seen": now,
            "last_seen": now,
        }).execute())

        _with_retry(lambda: db.table("price_history").insert({
            "listing_id": lid,
            "price_aed": new_price,
            "scraped_at": now,
        }).execute())

        return {"action": "new", "drop": None}

    old = existing.data[0]
    old_price = old.get("last_price")

    _with_retry(lambda: db.table("listings").update({
        "last_seen": now,
        "last_price": new_price,
        "title": listing.get("title"),
        "area": listing.get("area"),
        "building": listing.get("building"),
        "url": listing.get("url"),
        "image_url": listing.get("image_url"),
        "beds": listing.get("beds"),
        "baths": listing.get("baths"),
        "size_sqft": listing.get("size_sqft"),
        "type": listing.get("type"),
        "is_active": True,
    }).eq("id", lid).execute())

    _with_retry(lambda: db.table("price_history").insert({
        "listing_id": lid,
        "price_aed": new_price,
        "scraped_at": now,
    }).execute())

    if old_price and new_price < old_price - 0.001:
        drop_abs = round(old_price - new_price, 6)
        drop_pct = round((drop_abs / old_price) * 100, 2)

        _with_retry(lambda: db.table("price_drops").insert({
            "listing_id": lid,
            "old_price_aed": old_price,
            "new_price_aed": new_price,
            "drop_abs_aed": drop_abs,
            "drop_pct": drop_pct,
            "detected_at": now,
        }).execute())

        return {"action": "price_drop", "drop": {
            "listing_id": lid,
            "old_price_aed": old_price,
            "new_price_aed": new_price,
            "drop_abs_aed": drop_abs,
            "drop_pct": drop_pct,
            "detected_at": now,
        }}

    return {"action": "unchanged", "drop": None}


def get_drops(hours: int = 24, limit: int = 100,
              prop_type: str = None, sort: str = "abs",
              min_pct: float = None) -> list:
    db = get_client(use_service_key=True)
    query = db.table("price_drops").select("""
        id, listing_id, old_price_aed, new_price_aed,
        drop_abs_aed, drop_pct, detected_at,
        listings (
            id, source, type, beds, baths, size_sqft,
            title, area, building, url, image_url, listed_date, first_seen
        )
    """)

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = query.gte("detected_at", cutoff.isoformat())

    if min_pct:
        query = query.gte("drop_pct", min_pct)

    if sort == "pct":
        query = query.order("drop_pct", desc=True)
    elif sort == "recent":
        query = query.order("detected_at", desc=True)
    elif sort == "price":
        query = query.order("new_price_aed", desc=False)
    else:
        query = query.order("drop_abs_aed", desc=True)

    query = query.limit(limit)
    result = _with_retry(lambda: query.execute())
    drops = result.data or []

    if prop_type:
        drops = [d for d in drops if d.get("listings", {}).get("type") == prop_type]

    return drops


def get_stats(hours: int = 24) -> dict:
    db = get_client(use_service_key=True)
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    drops = _with_retry(lambda: db.table("price_drops").select(
        "drop_pct, drop_abs_aed, new_price_aed"
    ).gte("detected_at", cutoff).execute())

    total_listings = _with_retry(lambda: db.table("listings").select(
        "id", count="exact"
    ).eq("is_active", True).execute())

    last_run = _with_retry(lambda: db.table("scrape_runs").select("*").eq(
        "status", "done"
    ).order("finished_at", desc=True).limit(1).execute())

    drops_data = drops.data or []
    total_drop_value = sum(d["drop_abs_aed"] for d in drops_data)
    avg_pct = sum(d["drop_pct"] for d in drops_data) / len(drops_data) if drops_data else 0
    biggest_pct = max((d["drop_pct"] for d in drops_data), default=0)

    return {
        "total_scanned": total_listings.count or 0,
        "total_drops": len(drops_data),
        "avg_drop_pct": round(avg_pct, 2),
        "biggest_drop_pct": round(biggest_pct, 2),
        "total_drop_value_aed": round(total_drop_value, 2),
        "last_scrape": last_run.data[0] if last_run.data else None,
    }


def get_listing_history(listing_id: str) -> dict:
    db = get_client(use_service_key=True)
    listing = _with_retry(lambda: db.table("listings").select("*").eq("id", listing_id).execute())
    history = _with_retry(lambda: db.table("price_history").select("*").eq(
        "listing_id", listing_id
    ).order("scraped_at").execute())
    drops = _with_retry(lambda: db.table("price_drops").select("*").eq(
        "listing_id", listing_id
    ).order("detected_at").execute())

    return {
        "listing": listing.data[0] if listing.data else None,
        "price_history": history.data or [],
        "drops": drops.data or [],
    }


def log_scrape_start(source: str) -> int:
    db = get_client(use_service_key=True)
    result = _with_retry(lambda: db.table("scrape_runs").insert({
        "source": source,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }).execute())
    return result.data[0]["id"]


def log_scrape_finish(run_id: int, listings_found: int, drops: int, status="done"):
    db = get_client(use_service_key=True)
    _with_retry(lambda: db.table("scrape_runs").update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "listings_found": listings_found,
        "drops_detected": drops,
        "status": status,
    }).eq("id", run_id).execute())


# ─────────────────────────────────────────────
# RENTAL DB OPERATIONS
# ─────────────────────────────────────────────

def upsert_rental(listing: dict) -> dict:
    db = get_client(use_service_key=True)
    now = datetime.now(timezone.utc).isoformat()
    lid = listing["id"]
    new_price = listing["price_aed_yearly"]

    existing = _with_retry(lambda: db.table("rental_listings").select("*").eq("id", lid).execute())

    if not existing.data:
        _with_retry(lambda: db.table("rental_listings").insert({
            "id": lid,
            "source": listing.get("source", "propertyfinder"),
            "type": listing.get("type"),
            "beds": listing.get("beds"),
            "baths": listing.get("baths"),
            "size_sqft": listing.get("size_sqft"),
            "title": listing.get("title"),
            "area": listing.get("area"),
            "building": listing.get("building"),
            "url": listing.get("url"),
            "image_url": listing.get("image_url"),
            "listed_date": listing.get("listed_date"),
            "last_price": new_price,
            "first_seen": now,
            "last_seen": now,
        }).execute())

        _with_retry(lambda: db.table("rental_price_history").insert({
            "listing_id": lid,
            "price_aed_yearly": new_price,
            "scraped_at": now,
        }).execute())

        return {"action": "new", "drop": None}

    old = existing.data[0]
    old_price = old.get("last_price")

    _with_retry(lambda: db.table("rental_listings").update({
        "last_seen": now,
        "last_price": new_price,
        "title": listing.get("title"),
        "area": listing.get("area"),
        "building": listing.get("building"),
        "url": listing.get("url"),
        "image_url": listing.get("image_url"),
        "beds": listing.get("beds"),
        "baths": listing.get("baths"),
        "size_sqft": listing.get("size_sqft"),
        "type": listing.get("type"),
        "is_active": True,
    }).eq("id", lid).execute())

    _with_retry(lambda: db.table("rental_price_history").insert({
        "listing_id": lid,
        "price_aed_yearly": new_price,
        "scraped_at": now,
    }).execute())

    if old_price and new_price < old_price - 1:
        drop_abs = round(old_price - new_price, 2)
        drop_pct = round((drop_abs / old_price) * 100, 2)

        _with_retry(lambda: db.table("rental_price_drops").insert({
            "listing_id": lid,
            "old_price_aed": old_price,
            "new_price_aed": new_price,
            "drop_abs_aed": drop_abs,
            "drop_pct": drop_pct,
            "detected_at": now,
        }).execute())

        return {"action": "price_drop", "drop": {
            "listing_id": lid,
            "old_price_aed": old_price,
            "new_price_aed": new_price,
            "drop_abs_aed": drop_abs,
            "drop_pct": drop_pct,
            "detected_at": now,
        }}

    return {"action": "unchanged", "drop": None}


def get_rental_drops(hours: int = 24, limit: int = 100,
                     prop_type: str = None, sort: str = "abs",
                     min_pct: float = None) -> list:
    db = get_client(use_service_key=True)
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = db.table("rental_price_drops").select("""
        id, listing_id, old_price_aed, new_price_aed,
        drop_abs_aed, drop_pct, detected_at,
        rental_listings (
            id, source, type, beds, baths, size_sqft,
            title, area, building, url, image_url, listed_date, first_seen
        )
    """).gte("detected_at", cutoff.isoformat())

    if min_pct:
        query = query.gte("drop_pct", min_pct)

    if sort == "pct":
        query = query.order("drop_pct", desc=True)
    elif sort == "recent":
        query = query.order("detected_at", desc=True)
    elif sort == "price":
        query = query.order("new_price_aed", desc=False)
    else:
        query = query.order("drop_abs_aed", desc=True)

    query = query.limit(limit)
    result = _with_retry(lambda: query.execute())
    drops = result.data or []

    if prop_type:
        drops = [d for d in drops if d.get("rental_listings", {}).get("type") == prop_type]

    return drops


def get_rental_stats(hours: int = 24) -> dict:
    db = get_client(use_service_key=True)
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    drops = _with_retry(lambda: db.table("rental_price_drops").select(
        "drop_pct, drop_abs_aed, new_price_aed"
    ).gte("detected_at", cutoff).execute())

    total_listings = _with_retry(lambda: db.table("rental_listings").select(
        "id", count="exact"
    ).eq("is_active", True).execute())

    last_run = _with_retry(lambda: db.table("scrape_runs").select("*").eq(
        "status", "done"
    ).order("finished_at", desc=True).limit(1).execute())

    drops_data = drops.data or []
    total_drop_value = sum(d["drop_abs_aed"] for d in drops_data)
    avg_pct = sum(d["drop_pct"] for d in drops_data) / len(drops_data) if drops_data else 0
    biggest_pct = max((d["drop_pct"] for d in drops_data), default=0)

    return {
        "total_scanned": total_listings.count or 0,
        "total_drops": len(drops_data),
        "avg_drop_pct": round(avg_pct, 2),
        "biggest_drop_pct": round(biggest_pct, 2),
        "total_drop_value_aed": round(total_drop_value, 2),
        "last_scrape": last_run.data[0] if last_run.data else None,
    }


def get_rental_listing_history(listing_id: str) -> dict:
    db = get_client(use_service_key=True)
    listing = _with_retry(lambda: db.table("rental_listings").select("*").eq("id", listing_id).execute())
    history = _with_retry(lambda: db.table("rental_price_history").select("*").eq(
        "listing_id", listing_id
    ).order("scraped_at").execute())
    drops = _with_retry(lambda: db.table("rental_price_drops").select("*").eq(
        "listing_id", listing_id
    ).order("detected_at").execute())

    return {
        "listing": listing.data[0] if listing.data else None,
        "price_history": history.data or [],
        "drops": drops.data or [],
    }
