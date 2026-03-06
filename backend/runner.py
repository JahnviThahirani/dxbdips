"""
runner.py — Orchestrates scraping and DB writes for DXB Dips.
Called by Railway API trigger or manually.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.db import upsert_listing, upsert_rental, log_scrape_start, log_scrape_finish
from backend.twitter import post_drops
from scraper.scraper_pf import run_scrape as scrape_pf, run_rental_scrape as scrape_pf_rentals


async def run_sales(max_pages: int = 300):
    print("\n" + "="*60, flush=True)
    print("  DXB DIPS — Sale Listings (Property Finder)", flush=True)
    print(f"  Pages: {max_pages} (~{max_pages * 20} listings)", flush=True)
    print("="*60, flush=True)

    run_id = log_scrape_start("propertyfinder")
    total_drops = 0
    total_listings = 0
    new_sale_drops = []

    try:
        listings = await scrape_pf(max_pages=max_pages)
        total_listings = len(listings)
        print(f"\n[DB] Processing {total_listings} sale listings...", flush=True)

        for i, listing in enumerate(listings):
            result = upsert_listing(listing)
            if result["action"] == "price_drop":
                total_drops += 1
                d = result["drop"]
                d["title"] = listing.get("title")
                d["area"] = listing.get("area")
                d["building"] = listing.get("building")
                d["type"] = listing.get("type")
                d["beds"] = listing.get("beds")
                d["size_sqft"] = listing.get("size_sqft")
                new_sale_drops.append(d)
                print(f"  💜 DROP: {listing['title'][:50]}", flush=True)
                print(f"     {d['old_price_aed']:.2f}M → {d['new_price_aed']:.2f}M AED  (-{d['drop_pct']}%)", flush=True)
            if i % 100 == 0 and i > 0:
                print(f"  [DB] {i}/{total_listings} processed...", flush=True)

        log_scrape_finish(run_id, total_listings, total_drops)
        print(f"\n✓ Sales done — {total_listings} listings, {total_drops} drops\n", flush=True)

    except Exception as e:
        log_scrape_finish(run_id, total_listings, total_drops, status="error")
        print(f"✗ Sale scrape failed: {e}", flush=True)
        raise

    return {"listings": total_listings, "drops": total_drops, "new_drops": new_sale_drops}


async def run_rentals(max_pages: int = 200):
    print("\n" + "="*60, flush=True)
    print("  DXB DIPS — Rental Listings (Property Finder)", flush=True)
    print(f"  Pages: {max_pages} (~{max_pages * 20} listings)", flush=True)
    print("="*60, flush=True)

    total_drops = 0
    total_listings = 0
    new_rental_drops = []

    try:
        listings = await scrape_pf_rentals(max_pages=max_pages)
        total_listings = len(listings)
        print(f"\n[DB] Processing {total_listings} rental listings...", flush=True)

        for i, listing in enumerate(listings):
            result = upsert_rental(listing)
            if result["action"] == "price_drop":
                total_drops += 1
                d = result["drop"]
                d["title"] = listing.get("title")
                d["area"] = listing.get("area")
                d["building"] = listing.get("building")
                d["type"] = listing.get("type")
                d["beds"] = listing.get("beds")
                new_rental_drops.append(d)
                print(f"  🔑 RENTAL DROP: {listing['title'][:50]}", flush=True)
                print(f"     AED {d['old_price_aed']:,.0f} → {d['new_price_aed']:,.0f}/yr  (-{d['drop_pct']}%)", flush=True)
            if i % 100 == 0 and i > 0:
                print(f"  [DB] {i}/{total_listings} processed...", flush=True)

        print(f"\n✓ Rentals done — {total_listings} listings, {total_drops} drops\n", flush=True)

    except Exception as e:
        print(f"✗ Rental scrape failed: {e}", flush=True)
        raise

    return {"listings": total_listings, "drops": total_drops, "new_drops": new_rental_drops}


async def run_all(sale_pages: int = 300, rental_pages: int = 200):
    print("\n" + "="*60, flush=True)
    print("  DXB DIPS — Full Scrape Run", flush=True)
    print(f"  {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", flush=True)
    print(f"  Sale pages: {sale_pages} | Rental pages: {rental_pages}", flush=True)
    print("="*60 + "\n", flush=True)

    sale_result = await run_sales(max_pages=sale_pages)

    print("  [Pause 10s between sale and rental scrape...]", flush=True)
    await asyncio.sleep(10)

    rental_result = await run_rentals(max_pages=rental_pages)

    # Post tweets for all new drops detected this run
    sale_drops = sale_result.get("new_drops", [])
    rental_drops = rental_result.get("new_drops", [])
    print(f"\n[Twitter] Firing post_drops() — {len(sale_drops)} sale drops, {len(rental_drops)} rental drops", flush=True)
    post_drops(sale_drops=sale_drops, rental_drops=rental_drops)

    print("\n" + "="*60, flush=True)
    print(f"  COMPLETE", flush=True)
    print(f"  Sales:   {sale_result['listings']} listings, {sale_result['drops']} drops", flush=True)
    print(f"  Rentals: {rental_result['listings']} listings, {rental_result['drops']} drops", flush=True)
    print("="*60 + "\n", flush=True)

    return {"sales": sale_result, "rentals": rental_result}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=300, help="Sale pages")
    parser.add_argument("--rental-pages", type=int, default=200, help="Rental pages")
    args = parser.parse_args()
    asyncio.run(run_all(sale_pages=args.pages, rental_pages=args.rental_pages))
