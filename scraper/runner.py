"""
runner.py — Orchestrates scraping and DB writes for DXB Dips.
Called by Railway API trigger or manually.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.db import upsert_listing, log_scrape_start, log_scrape_finish
from scraper.scraper_pf import run_scrape as scrape_pf


async def run_all(max_pages: int = 10):
    print("\n" + "="*60)
    print("  DXB DIPS — Scrape Run (Property Finder)")
    print(f"  {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*60 + "\n")

    run_id = log_scrape_start("propertyfinder")
    total_drops = 0
    total_listings = 0

    try:
        listings = await scrape_pf(max_pages=max_pages)
        total_listings = len(listings)

        print(f"\n[DB] Processing {total_listings} listings...")
        for i, listing in enumerate(listings):
            result = upsert_listing(listing)
            if result["action"] == "price_drop":
                total_drops += 1
                d = result["drop"]
                print(f"  💜 DROP: {listing['title'][:50]}")
                print(f"     {d['old_price_aed']:.4f}M → {d['new_price_aed']:.4f}M AED  (-{d['drop_pct']}%)")
            if i % 50 == 0 and i > 0:
                print(f"  [DB] {i}/{total_listings} processed...")

        log_scrape_finish(run_id, total_listings, total_drops)
        print(f"\n✓ Done — {total_listings} listings, {total_drops} drops detected\n")

    except Exception as e:
        log_scrape_finish(run_id, total_listings, total_drops, status="error")
        print(f"✗ Scrape failed: {e}")
        raise

    return {"listings": total_listings, "drops": total_drops}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(run_all(max_pages=args.pages))
