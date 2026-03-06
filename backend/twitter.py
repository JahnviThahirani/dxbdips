"""
twitter.py — Posts price drop alerts to @DXBDips on X (Twitter)
Called by runner.py after each scrape run.
"""
import os
import tweepy

def get_client():
    return tweepy.Client(
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def format_sale_tweet(drop: dict) -> str:
    title = drop.get("title") or "Luxury Property"
    area = drop.get("area") or ""
    building = drop.get("building") or ""
    prop_type = (drop.get("type") or "Property").title()
    beds = drop.get("beds")
    size = drop.get("size_sqft")

    old_price = drop.get("old_price_aed", 0)
    new_price = drop.get("new_price_aed", 0)
    drop_abs = drop.get("drop_abs_aed", 0)
    drop_pct = drop.get("drop_pct", 0)

    # Format prices in millions
    def fmt_m(v): return f"AED {v:.1f}M" if v >= 1 else f"AED {v*1000:.0f}K"

    # Location line
    location_parts = [p for p in [building, area] if p]
    location = " · ".join(location_parts) if location_parts else "Dubai"

    # Property details
    details_parts = [prop_type]
    if beds: details_parts.append(f"{beds} BR")
    if size: details_parts.append(f"{int(size):,} sqft")
    details = " · ".join(details_parts)

    tweet = (
        f"🔻 {fmt_m(drop_abs)} drop detected\n\n"
        f"{title[:50]}\n"
        f"📍 {location}\n"
        f"🏠 {details}\n\n"
        f"Was: {fmt_m(old_price)} → Now: {fmt_m(new_price)} (-{drop_pct}%)\n\n"
        f"dxbdips.com"
    )
    return tweet[:280]


def format_rental_tweet(drop: dict) -> str:
    title = drop.get("title") or "Luxury Rental"
    area = drop.get("area") or ""
    building = drop.get("building") or ""
    prop_type = (drop.get("type") or "Property").title()
    beds = drop.get("beds")

    old_price = drop.get("old_price_aed", 0)
    new_price = drop.get("new_price_aed", 0)
    drop_abs = drop.get("drop_abs_aed", 0)
    drop_pct = drop.get("drop_pct", 0)

    def fmt_k(v):
        return f"AED {v/1000:.0f}K/yr" if v >= 1000 else f"AED {v:.0f}/yr"

    location_parts = [p for p in [building, area] if p]
    location = " · ".join(location_parts) if location_parts else "Dubai"

    details_parts = [prop_type]
    if beds: details_parts.append(f"{beds} BR")
    details = " · ".join(details_parts)

    tweet = (
        f"🔑 {fmt_k(drop_abs)} rental drop detected\n\n"
        f"{title[:50]}\n"
        f"📍 {location}\n"
        f"🏠 {details}\n\n"
        f"Was: {fmt_k(old_price)} → Now: {fmt_k(new_price)} (-{drop_pct}%)\n\n"
        f"dxbdips.com"
    )
    return tweet[:280]


def post_drops(sale_drops: list, rental_drops: list):
    """Post tweets for new price drops. Called after each scrape run."""
    if not os.environ.get("TWITTER_API_KEY"):
        print("[Twitter] No credentials found, skipping tweets.")
        return

    client = get_client()
    posted = 0
    errors = 0

    # Post sale drops (cap at 10 per run to avoid spam)
    for drop in sale_drops[:10]:
        try:
            tweet = format_sale_tweet(drop)
            client.create_tweet(text=tweet)
            posted += 1
            print(f"  🐦 Tweet posted: {drop.get('title', '')[:40]}")
        except Exception as e:
            errors += 1
            print(f"  [Twitter] Error posting sale tweet: {e}")

    # Post rental drops (cap at 5 per run)
    for drop in rental_drops[:5]:
        try:
            tweet = format_rental_tweet(drop)
            client.create_tweet(text=tweet)
            posted += 1
            print(f"  🐦 Tweet posted (rental): {drop.get('title', '')[:40]}")
        except Exception as e:
            errors += 1
            print(f"  [Twitter] Error posting rental tweet: {e}")

    print(f"[Twitter] Done — {posted} posted, {errors} errors")
