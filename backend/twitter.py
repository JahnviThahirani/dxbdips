"""
twitter.py — Posts price drop alerts to @DXBDips on X (Twitter)
Called by runner.py after each scrape run.
Strategy: top 3 sales + top 2 rentals by value drop, 5 min apart, dynamic hashtags.
"""
import os
import time
import tweepy

TWEET_DELAY = 300  # 5 minutes between tweets

def get_client():
    return tweepy.Client(
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    )


AREA_HASHTAGS = {
    "palm jumeirah":    "#PalmJumeirah",
    "downtown":         "#DowntownDubai",
    "dubai marina":     "#DubaiMarina",
    "business bay":     "#BusinessBay",
    "jumeirah":         "#Jumeirah",
    "creek":            "#DubaiCreek",
    "dubai hills":      "#DubaiHills",
    "emirates hills":   "#EmiratesHills",
    "arabian ranches":  "#ArabianRanches",
    "meydan":           "#Meydan",
    "bluewaters":       "#Bluewaters",
    "city walk":        "#CityWalk",
    "al barari":        "#AlBarari",
    "yas":              "#YasIsland",
    "saadiyat":         "#SaadiyatIsland",
    "abu dhabi":        "#AbuDhabi",
    "meadows":          "#TheMeadows",
    "springs":          "#TheSprings",
    "sobha":            "#SobhaDubai",
    "damac":            "#DAMAC",
}

BASE_HASHTAGS = "#DubaiRealEstate #DubaiProperty #UAEProperty"

def get_area_hashtag(area: str) -> str:
    if not area:
        return ""
    area_lower = area.lower()
    for key, tag in AREA_HASHTAGS.items():
        if key in area_lower:
            return tag
    return ""


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

    def fmt_m(v): return f"AED {v:.1f}M" if v >= 1 else f"AED {v*1000:.0f}K"

    location_parts = [p for p in [building, area] if p]
    location = " · ".join(location_parts) if location_parts else "Dubai"

    details_parts = [prop_type]
    if beds: details_parts.append(f"{beds} BR")
    if size: details_parts.append(f"{int(size):,} sqft")
    details = " · ".join(details_parts)

    area_tag = get_area_hashtag(area)
    hashtags = f"{BASE_HASHTAGS} {area_tag}".strip()

    tweet = (
        f"🔻 {fmt_m(drop_abs)} drop detected\n\n"
        f"{title[:50]}\n"
        f"📍 {location}\n"
        f"🏠 {details}\n\n"
        f"Was: {fmt_m(old_price)} → Now: {fmt_m(new_price)} (-{drop_pct}%)\n\n"
        f"{hashtags}\n"
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

    def fmt_k(v): return f"AED {v/1000:.0f}K/yr" if v >= 1000 else f"AED {v:.0f}/yr"

    location_parts = [p for p in [building, area] if p]
    location = " · ".join(location_parts) if location_parts else "Dubai"

    details_parts = [prop_type]
    if beds: details_parts.append(f"{beds} BR")
    details = " · ".join(details_parts)

    area_tag = get_area_hashtag(area)
    hashtags = f"{BASE_HASHTAGS} {area_tag}".strip()

    tweet = (
        f"🔑 {fmt_k(drop_abs)} rental drop detected\n\n"
        f"{title[:50]}\n"
        f"📍 {location}\n"
        f"🏠 {details}\n\n"
        f"Was: {fmt_k(old_price)} → Now: {fmt_k(new_price)} (-{drop_pct}%)\n\n"
        f"{hashtags}\n"
        f"dxbdips.com"
    )
    return tweet[:280]


def post_drops(sale_drops: list, rental_drops: list):
    """Post tweets: top 3 sales + top 2 rentals by value drop, 5 min apart."""
    print(f"[Twitter] post_drops() called — {len(sale_drops)} sale, {len(rental_drops)} rental drops", flush=True)

    if not os.environ.get("TWITTER_API_KEY"):
        print("[Twitter] No credentials found, skipping tweets.", flush=True)
        return

    client = get_client()
    posted = 0
    errors = 0

    top_sales = sorted(sale_drops, key=lambda d: d.get("drop_abs_aed", 0), reverse=True)[:3]
    top_rentals = sorted(rental_drops, key=lambda d: d.get("drop_abs_aed", 0), reverse=True)[:2]
    all_drops = [("sale", d) for d in top_sales] + [("rental", d) for d in top_rentals]

    print(f"[Twitter] Posting {len(all_drops)} tweets ({len(top_sales)} sales, {len(top_rentals)} rentals)...", flush=True)

    for i, (kind, drop) in enumerate(all_drops):
        try:
            tweet = format_sale_tweet(drop) if kind == "sale" else format_rental_tweet(drop)
            client.create_tweet(text=tweet)
            posted += 1
            print(f"  🐦 [{posted}/{len(all_drops)}] {kind}: {drop.get('title', '')[:40]}", flush=True)
            if i < len(all_drops) - 1:
                print(f"  [Twitter] Waiting 5 min before next tweet...", flush=True)
                time.sleep(TWEET_DELAY)
        except Exception as e:
            errors += 1
            print(f"  [Twitter] Error: {e}", flush=True)

    print(f"[Twitter] Done — {posted} posted, {errors} errors", flush=True)
